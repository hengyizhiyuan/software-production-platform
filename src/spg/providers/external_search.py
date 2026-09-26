"""Read-only GitHub and Brave connectors for public evidence acquisition."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from hashlib import sha256
from html.parser import HTMLParser
import ipaddress
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from spg.domain.external_search import SearchEvidence, SearchFailure, SearchProviderError


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class BoundedPublicHttp:
    """Small HTTPS read transport; never sends credentials to arbitrary URLs."""

    def __init__(self, *, timeout: float = 10.0, max_bytes: int = 250_000) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.opener = build_opener(_NoRedirect())

    @staticmethod
    def _check_url(url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "Only public HTTPS resources can be fetched")
        try:
            addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
        except OSError as error:
            raise SearchProviderError(SearchFailure.NETWORK_FAILURE, "Public source DNS lookup failed") from error
        if not addresses or any(
            not ipaddress.ip_address(item[4][0]).is_global for item in addresses
        ):
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "Private or non-public addresses cannot be fetched")

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> tuple[bytes, str]:
        for _ in range(3):
            self._check_url(url)
            request = Request(
                url,
                headers={"User-Agent": "Watt-Evidence-Research/1.0", **(headers or {})},
                method="GET",
            )
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    content_type = response.headers.get("Content-Type", "")
                    body = response.read(self.max_bytes + 1)
                    if len(body) > self.max_bytes:
                        raise SearchProviderError(SearchFailure.FETCH_FAILED, "Source exceeds bounded fetch size")
                    return body, content_type
            except HTTPError as error:
                if error.code in {301, 302, 303, 307, 308}:
                    location = error.headers.get("Location")
                    if location:
                        if headers and any(key.casefold() in {"authorization", "x-subscription-token"} for key in headers):
                            raise SearchProviderError(SearchFailure.FETCH_FAILED, "Authenticated provider redirected unexpectedly") from error
                        url = urljoin(url, location)
                        continue
                if error.code == 429 or (error.code == 403 and (
                    error.headers.get("X-RateLimit-Remaining") == "0"
                    or error.headers.get("Retry-After") is not None
                )):
                    category = SearchFailure.RATE_LIMITED
                elif error.code in {401, 403}:
                    category = SearchFailure.CREDENTIAL_REQUIRED
                elif error.code >= 500:
                    category = SearchFailure.PROVIDER_UNAVAILABLE
                else:
                    category = SearchFailure.FETCH_FAILED
                raise SearchProviderError(category, f"Public source returned HTTP {error.code}") from error
            except (URLError, TimeoutError, OSError) as error:
                raise SearchProviderError(SearchFailure.NETWORK_FAILURE, "Public source network request failed") from error
        raise SearchProviderError(SearchFailure.FETCH_FAILED, "Public source redirected too many times")


def _identity(url: str) -> str:
    return "external-search:" + sha256(url.encode()).hexdigest()[:24]


def _evidence(
    *, source_type: str, provider: str, query: str, title: str, url: str,
    rank: int, snippet: str = "", metadata: dict | None = None,
    inspected_content: str | None = None,
) -> SearchEvidence:
    return SearchEvidence(
        evidence_id=_identity(url), source_type=source_type, provider=provider,
        query=query, title=title or url, url=url, retrieved_at=datetime.now(UTC),
        rank=rank, snippet=snippet[:1000], inspected_content=inspected_content,
        metadata=metadata or {},
        completeness="INSPECTED" if inspected_content else "SEARCH_RESULT",
    )


class GitHubPublicSearchProvider:
    identity = "github-rest-public"

    def __init__(self, http: BoundedPublicHttp, *, token: str | None = None) -> None:
        self.http = http
        self.token = token

    def _json(self, url: str) -> dict | list:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body, _ = self.http.get(url, headers=headers)
        try:
            result = json.loads(body)
        except ValueError as error:
            raise SearchProviderError(SearchFailure.PROVIDER_UNAVAILABLE, "GitHub returned invalid JSON") from error
        if not isinstance(result, (dict, list)):
            raise SearchProviderError(SearchFailure.PROVIDER_UNAVAILABLE, "GitHub returned an unexpected payload")
        return result

    def search(self, query: str, kind: str = "repositories", *, limit: int = 6) -> tuple[SearchEvidence, ...]:
        if kind not in {"repositories", "code", "issues"}:
            raise SearchProviderError(SearchFailure.UNSUPPORTED_SEARCH_TYPE, f"Unsupported GitHub search: {kind}")
        if kind == "code" and not self.token:
            raise SearchProviderError(SearchFailure.CREDENTIAL_REQUIRED, "GitHub code search requires a read credential")
        exact_query = query + (" is:issue" if kind == "issues" else "")
        payload = self._json(f"https://api.github.com/search/{kind}?q={quote(exact_query)}&per_page={limit}")
        if not isinstance(payload, dict):
            raise SearchProviderError(SearchFailure.PROVIDER_UNAVAILABLE, "GitHub search returned an unexpected payload")
        items = payload.get("items")
        if not isinstance(items, list):
            raise SearchProviderError(SearchFailure.PROVIDER_UNAVAILABLE, "GitHub search has no result list")
        results = []
        for rank, item in enumerate(items[:limit], start=1):
            if not isinstance(item, dict) or not isinstance(item.get("html_url"), str):
                continue
            if urlsplit(item["html_url"]).hostname != "github.com":
                continue
            repo = item.get("repository") if isinstance(item.get("repository"), dict) else {}
            if item.get("private") is True or repo.get("private") is True:
                continue
            if kind == "repositories":
                owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
                license = item.get("license") if isinstance(item.get("license"), dict) else {}
                metadata = {
                    "owner": owner.get("login"),
                    "stars": item.get("stargazers_count"),
                    "forks": item.get("forks_count"),
                    "language": item.get("language"),
                    "updated_at": item.get("updated_at"),
                    "license": license.get("spdx_id"),
                    "default_branch": item.get("default_branch"),
                }
                title = item.get("full_name") or item.get("name")
                snippet = item.get("description") or ""
            else:
                metadata = {"repository": repo.get("full_name"), "state": item.get("state")}
                title = item.get("title") or item.get("name") or item["html_url"]
                snippet = item.get("body") or item.get("path") or ""
            results.append(_evidence(
                source_type="GITHUB", provider=self.identity, query=query,
                title=title, url=item["html_url"], rank=rank,
                snippet=snippet, metadata=metadata,
            ))
        return tuple(results)

    def inspect_repository(self, evidence: SearchEvidence) -> SearchEvidence:
        parts = urlsplit(evidence.url)
        names = parts.path.strip("/").split("/")
        if parts.hostname != "github.com" or len(names) < 2:
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "Not a GitHub repository URL")
        owner, repo = names[:2]
        if not all(name.replace("-", "").replace("_", "").replace(".", "").isalnum() for name in (owner, repo)):
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "Invalid public repository identity")
        root = f"https://api.github.com/repos/{owner}/{repo}"
        metadata = self._json(root)
        if not isinstance(metadata, dict):
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "GitHub repository returned an unexpected payload")
        if metadata.get("private") is True:
            raise SearchProviderError(SearchFailure.CREDENTIAL_REQUIRED, "Private repository research is not admitted")
        try:
            readme = self._json(root + "/readme")
        except SearchProviderError as error:
            if error.category is not SearchFailure.FETCH_FAILED:
                raise
            readme = {}
        if not isinstance(readme, dict):
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "GitHub README returned an unexpected payload")
        content = readme.get("content")
        if readme.get("encoding") == "base64" and isinstance(content, str):
            material = base64.b64decode(content).decode("utf-8", errors="replace")[:9000]
        else:
            material = "README unavailable; repository metadata and root paths inspected."
        paths = []
        try:
            listing = self._json(root + "/contents")
            if isinstance(listing, list):
                paths = [item.get("path") for item in listing if isinstance(item, dict) and item.get("path")]
        except SearchProviderError:
            pass
        package_summary = ""
        package_path = next((path for path in (
            "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml",
        ) if path in paths), None)
        if package_path is not None:
            try:
                package_file = self._json(root + "/contents/" + quote(package_path))
                if (isinstance(package_file, dict)
                        and package_file.get("encoding") == "base64"
                        and isinstance(package_file.get("content"), str)):
                    package_summary = base64.b64decode(package_file["content"]).decode(
                        "utf-8", errors="replace"
                    )[:1800]
            except (SearchProviderError, ValueError):
                pass
        license = metadata.get("license") if isinstance(metadata.get("license"), dict) else {}
        selected = {
            **evidence.metadata,
            "stars": metadata.get("stargazers_count"),
            "forks": metadata.get("forks_count"),
            "language": metadata.get("language"),
            "updated_at": metadata.get("updated_at"),
            "license": license.get("spdx_id"),
            "default_branch": metadata.get("default_branch"),
            "root_paths": ", ".join(paths[:25]),
            "package_manifest": package_path,
        }
        return evidence.model_copy(update={
            "inspected_content": (
                f"Repository metadata: {metadata.get('description') or ''}; root paths: {', '.join(paths[:25])}.\n"
                f"README ({evidence.url}/blob/{metadata.get('default_branch') or 'HEAD'}/{readme.get('path') or 'README.md'}):\n{material}"
                + (f"\nPackage manifest ({package_path}):\n{package_summary}" if package_summary else "")
            )[:9000],
            "metadata": selected,
            "completeness": "INSPECTED",
            "retrieved_at": datetime.now(UTC),
        })

    def fetch_resource(self, url: str) -> SearchEvidence:
        """Inspect one public repository or exact public file selected by Human."""

        parts = urlsplit(url)
        names = parts.path.strip("/").split("/")
        if parts.hostname != "github.com" or len(names) < 2:
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "Not a public GitHub resource URL")
        owner, repo = names[:2]
        if not all(name.replace("-", "").replace("_", "").replace(".", "").isalnum()
                   for name in (owner, repo)):
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "Invalid public repository identity")
        if len(names) >= 5 and names[2] == "blob":
            ref, path = names[3], "/".join(names[4:])
            if not all(part.replace("-", "").replace("_", "").replace(".", "").isalnum()
                       for part in (owner, repo, *path.split("/"))):
                raise SearchProviderError(SearchFailure.FETCH_FAILED, "Invalid public file path")
            repository = self._json(f"https://api.github.com/repos/{owner}/{repo}")
            if not isinstance(repository, dict) or repository.get("private") is True:
                raise SearchProviderError(SearchFailure.CREDENTIAL_REQUIRED, "Private repository research is not admitted")
            payload = self._json(
                f"https://api.github.com/repos/{owner}/{repo}/contents/"
                f"{quote(path)}?ref={quote(ref)}"
            )
            if not isinstance(payload, dict) or payload.get("encoding") != "base64":
                raise SearchProviderError(SearchFailure.FETCH_FAILED, "GitHub resource is not a text file")
            material = base64.b64decode(payload.get("content") or "").decode("utf-8", errors="replace")[:9000]
            if not material:
                raise SearchProviderError(SearchFailure.FETCH_FAILED, "GitHub file has no inspectable text")
            return _evidence(
                source_type="GITHUB", provider=self.identity, query=url,
                title=f"{owner}/{repo}/{path}", url=url, rank=1,
                inspected_content=material,
                metadata={"repository": f"{owner}/{repo}", "path": path, "ref": ref},
            )
        if len(names) == 2:
            evidence = _evidence(
                source_type="GITHUB", provider=self.identity, query=url,
                title=f"{owner}/{repo}", url=url, rank=1,
            )
            return self.inspect_repository(evidence)
        raise SearchProviderError(SearchFailure.UNSUPPORTED_SEARCH_TYPE, "Unsupported GitHub resource shape")

    def inspect_result(self, evidence: SearchEvidence) -> SearchEvidence:
        source = urlsplit(evidence.url)
        if source.hostname != "github.com":
            raise SearchProviderError(SearchFailure.FETCH_FAILED, "Not a GitHub result URL")
        parts = source.path.strip("/").split("/")
        if len(parts) == 2:
            return self.inspect_repository(evidence)
        if len(parts) >= 5 and parts[2] == "blob":
            fetched = self.fetch_resource(evidence.url)
            return evidence.model_copy(update={
                "inspected_content": fetched.inspected_content,
                "completeness": "INSPECTED",
                "retrieved_at": fetched.retrieved_at,
                "metadata": {**evidence.metadata, **fetched.metadata},
            })
        if len(parts) == 4 and parts[2] == "issues" and parts[3].isdigit():
            owner, repo, _, number = parts
            repository = self._json(f"https://api.github.com/repos/{owner}/{repo}")
            if not isinstance(repository, dict) or repository.get("private") is True:
                raise SearchProviderError(SearchFailure.CREDENTIAL_REQUIRED, "Private issue research is not admitted")
            issue = self._json(f"https://api.github.com/repos/{owner}/{repo}/issues/{number}")
            if not isinstance(issue, dict):
                raise SearchProviderError(SearchFailure.FETCH_FAILED, "GitHub issue returned an unexpected payload")
            content = (issue.get("body") or issue.get("title") or "").strip()
            if not content:
                raise SearchProviderError(SearchFailure.FETCH_FAILED, "GitHub issue has no inspectable text")
            return evidence.model_copy(update={
                "inspected_content": content[:9000],
                "completeness": "INSPECTED",
                "retrieved_at": datetime.now(UTC),
                "metadata": {**evidence.metadata, "state": issue.get("state"),
                             "updated_at": issue.get("updated_at")},
            })
        raise SearchProviderError(SearchFailure.UNSUPPORTED_SEARCH_TYPE, "Unsupported GitHub search result shape")


class BraveWebSearchProvider:
    identity = "brave-web-search"

    def __init__(self, http: BoundedPublicHttp, *, api_key: str | None) -> None:
        self.http = http
        self.api_key = api_key

    def search(self, query: str, *, limit: int = 6) -> tuple[SearchEvidence, ...]:
        if not self.api_key:
            raise SearchProviderError(SearchFailure.CREDENTIAL_REQUIRED, "Brave Web Search API key is not configured")
        body, _ = self.http.get(
            f"https://api.search.brave.com/res/v1/web/search?q={quote(query)}&count={limit}",
            headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
        )
        try:
            payload = json.loads(body)
            items = payload.get("web", {}).get("results", [])
        except (ValueError, AttributeError) as error:
            raise SearchProviderError(SearchFailure.PROVIDER_UNAVAILABLE, "Web provider returned invalid results") from error
        if not isinstance(items, list):
            raise SearchProviderError(SearchFailure.PROVIDER_UNAVAILABLE, "Web provider has no result list")
        results = []
        for rank, item in enumerate(items[:limit], start=1):
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            if not isinstance(url, str) or not url.startswith("https://"):
                continue
            results.append(_evidence(
                source_type="WEB", provider=self.identity, query=query,
                title=item.get("title") or url, url=url, rank=rank,
                snippet=item.get("description") or "",
                metadata={"domain": urlsplit(url).hostname},
            ))
        return tuple(results)


class _PublicText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs):
        if tag in {"script", "style", "nav", "footer"}:
            self.hidden += 1

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "nav", "footer"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def inspect_web_resource(http: BoundedPublicHttp, evidence: SearchEvidence) -> SearchEvidence:
    body, content_type = http.get(evidence.url, headers={"Accept": "text/html,text/plain"})
    if not any(item in content_type for item in ("text/html", "text/plain")):
        raise SearchProviderError(SearchFailure.FETCH_FAILED, "Source is not inspectable public text")
    source = body.decode("utf-8", errors="replace")
    if "text/html" in content_type:
        parser = _PublicText()
        parser.feed(source)
        source = " ".join(parser.parts)
    content = " ".join(source.split())[:9000]
    if not content:
        raise SearchProviderError(SearchFailure.FETCH_FAILED, "Source page has no readable text")
    return evidence.model_copy(update={
        "inspected_content": content,
        "completeness": "INSPECTED",
        "retrieved_at": datetime.now(UTC),
    })

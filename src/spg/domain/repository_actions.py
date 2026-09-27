"""Conservative Human command witnesses for existing Repository Asset actions.

Only direct commands allow local effects. Model suggestions, reference URLs,
future intentions, instructions to search for other repositories, and questions
about how to perform an operation are not execution authority.
"""
from dataclasses import dataclass
import re

from spg.domain.action_admission import ActionFamily

_URL = re.compile(r"https?://[^\s<>，,。；;、！？”“\"'()（）]+")
_NON_COMMAND = re.compile(r"不要|别|不需要|以后|将来|可能|如何|怎么|怎样|if\b|might\b|later\b|don't|do not|how to", re.I)
_ACQUIRE = re.compile(r"(?<![A-Za-z])clone(?![A-Za-z])|克隆|(?:把|将).{0,60}?(?:拉取|下载)(?:下来|到本地)|(?:拉取|下载|获取)\s*(?:(?:这个|该|当前)\s*)?(?:仓库|项目|https?://)|(?:pull|acquire)\s+(?:(?:this|the)\s+)?(?:repo(?:sitory)?|project|https?://)", re.I)
_INSPECT = re.compile(r"(?:看看|看下|检查|分析|inspect|examine).{0,40}?(?:项目|仓库|repo|框架|技术栈)|(?:项目|仓库|repo).{0,30}?(?:什么框架|技术栈)", re.I)
_BRANCH = re.compile(r"(?:切(?:换到|到|出)?\s*(?:(?:一个|一条)\s*)?(?:本地\s*)?(?:分支\s*)?|(?:创建|新建)\s*(?:(?:一个|一条|新)\s*)?(?:本地\s*)?分支\s*[:：]?\s*|(?:checkout|switch(?: to)?)\s+(?:(?:local\s+)?branch\s+)?|create\s+(?:a\s+)?(?:local\s+)?branch\s+)(?P<name>[A-Za-z0-9][A-Za-z0-9._/-]{0,127})(?:\s*(?:分支|branch))?", re.I)
_QUERY = re.compile(r"(?:当前|现在|目前|哪个|什么|current|which).{0,15}?(?:分支|branch)|(?:分支|branch).{0,15}?(?:哪个|什么|current|which)", re.I)
_DIRECT = re.compile(r"^\s*(?:clone|克隆|拉取|下载|pull|acquire|获取|inspect|examine|请|先|帮我|帮忙|把|将|切|创建|新建|checkout|switch|create|please|can you|could you|help me)", re.I)


@dataclass(frozen=True)
class RepositoryAction:
    family: ActionFamily
    source: str | None = None
    branch: str | None = None
    target_ambiguous: bool = False


def repository_actions(text: str) -> tuple[RepositoryAction, ...]:
    # Split independent clauses: unknown future modification does not erase clone.
    clauses = re.split(r"[，,。；;\n]|然后|接着|\band then\b", text)
    sources = _URL.findall(text)
    source = sources[0].rstrip(".，。") if len(set(sources)) == 1 else None
    result = []
    for clause in clauses:
        if re.search(r"类似|有没有|寻找|similar|search for|explain|解释|说明|命令是什么", clause, re.I):
            continue
        if _NON_COMMAND.search(clause):
            # Inspection explicitly before a future decision is still read-only.
            inspection = _INSPECT.search(clause)
            future = re.search(r"以后|将来|可能|later|might", clause, re.I)
            if not (inspection and _DIRECT.search(clause)
                    and (future is None or future.start() > inspection.start())
                    and not re.search(r"不要|别|如何|怎么|don't|do not|how to", clause, re.I)):
                continue
        if _ACQUIRE.search(clause) and _DIRECT.search(clause):
            result.append(RepositoryAction(ActionFamily.ACQUIRE_REPOSITORY, source,
                target_ambiguous=len(set(sources)) > 1))
        elif _INSPECT.search(clause) and _DIRECT.search(clause):
            result.append(RepositoryAction(ActionFamily.INSPECT, source,
                target_ambiguous=len(set(sources)) > 1))
        branch = _BRANCH.search(clause)
        if branch and _DIRECT.search(clause) and not _NON_COMMAND.search(clause) and not _QUERY.search(clause) and not re.search(r"了吗|是否|已经|\byet\b", clause, re.I):
            tail = clause[branch.end():].strip(' 。.!?？！')
            if tail and tail.lower() not in {'please', '谢谢', '麻烦了'}:
                continue
            if re.search(r'\bcheckout\b', clause, re.I) and not re.search(r'\bbranch\b', clause, re.I):
                continue
            name = branch['name']
            if name.lower() not in {"repo", "repository", "this", "branch"}:
                result.append(RepositoryAction(ActionFamily.LOCAL_BRANCH, branch=name))
    if _QUERY.search(text) and not any(item.family is ActionFamily.LOCAL_BRANCH for item in result):
        result.append(RepositoryAction(ActionFamily.INSPECT))
    return tuple(dict.fromkeys(result))

from spg.application.preview_security import PREVIEW_CONTENT_SECURITY_POLICY


def test_preview_allows_passive_https_images_with_active_boundaries_intact() -> None:
    directives = {
        parts[0]: tuple(parts[1:])
        for directive in PREVIEW_CONTENT_SECURITY_POLICY.split(";")
        if (parts := directive.strip().split())
    }

    assert directives["img-src"] == ("'self'", "data:", "blob:", "https:")
    assert directives["default-src"] == ("'self'",)
    assert directives["script-src"] == ("'self'", "'unsafe-inline'")
    assert directives["connect-src"] == ("'none'",)
    assert "*" not in PREVIEW_CONTENT_SECURITY_POLICY

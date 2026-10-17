"""Security policy shared by Watt's passive static-Web preview surfaces."""

STATIC_AUDIO_SUFFIXES = {".mp3", ".wav"}
MAX_STATIC_AUDIO_BYTES = 8_000_000

PREVIEW_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src 'none'; "
    "img-src 'self' data: blob: https:; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'none'"
)

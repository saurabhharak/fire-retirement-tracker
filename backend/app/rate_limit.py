"""Rate limiting configuration."""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_key(request: Request) -> str:
    """Rate-limit key: the real client IP behind the edge proxy.

    Render terminates TLS at a shared proxy, so request.client.host is the
    proxy IP for every request — without this, all users share one bucket
    and any burst locks everyone out. The RIGHTMOST X-Forwarded-For entry is
    appended by our trusted proxy and cannot be spoofed; leftmost entries
    are client-controlled.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[-1].strip() or get_remote_address(request)
    return get_remote_address(request)


limiter = Limiter(key_func=_client_key)

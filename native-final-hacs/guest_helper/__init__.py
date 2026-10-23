"""Early external QA fence; no HomeCircle product bytes are changed."""
import sys

_PROVIDER_SUFFIXES = ("apple.com", "icloud.com", "icloud-content.com", "life360.com")
_DENIED = 0


def _audit(event, args):
    global _DENIED
    if event == "socket.getaddrinfo" and args:
        host = args[0]
        if isinstance(host, bytes):
            host = host.decode("ascii", errors="ignore")
        if isinstance(host, str) and any(
            host.lower().rstrip(".") == suffix or host.lower().rstrip(".").endswith("." + suffix)
            for suffix in _PROVIDER_SUFFIXES
        ):
            _DENIED += 1
            raise OSError("qa_provider_network_refused")


sys.addaudithook(_audit)


def provider_requests_denied():
    return _DENIED

"""Exact-origin, read-only Marketplace HTTPS/SNI preflight; inert by default.

An explicit opt-in performs DNS + one server-authenticated TLS handshake only.
No HTTP method, body, cookie, application route, credential, local file write,
process, service or VPS configuration change. Untrusted data is never reflected.
"""
from __future__ import annotations

import ipaddress
import socket
import ssl
import sys
from typing import Final, Sequence


CANONICAL_HOST: Final = "marketplace.open-trust-layer.org"
CANONICAL_ORIGIN: Final = "https://marketplace.open-trust-layer.org/"
CANONICAL_PORT: Final = 443
CONNECT_TIMEOUT_SECONDS: Final = 5.0
MAX_DNS_ANSWERS: Final = 8
EXACT_PROBE_OPT_IN: Final = "PROBE_MARKETPLACE_CANONICAL_HTTPS_READONLY_V1"
INERT_STATUS: Final = "status=INERT_CANONICAL_HTTPS_PROBE_NOT_RUN"
INVALID_OPT_IN: Final = "status=BLOCKED_CANONICAL_HTTPS_OPT_IN_INVALID"
SUCCESS_STATUS: Final = "status=CANONICAL_HTTPS_TLS_VERIFIED"
FAILURE_STATUSES: Final = frozenset((
    "status=BLOCKED_DNS_UNAVAILABLE",
    "status=BLOCKED_DNS_UNSAFE",
    "status=BLOCKED_TLS_CONFIGURATION",
    "status=BLOCKED_TLS_CERTIFICATE",
    "status=BLOCKED_TLS_HANDSHAKE",
    "status=BLOCKED_TLS_TIMEOUT",
    "status=BLOCKED_TLS_TRANSPORT",
))


def probe_canonical_https_tls(
    *,
    resolver=None,
    socket_factory=None,
    context_factory=None,
) -> str:
    """Check only canonical DNS and server-authenticated TLS; no HTTP requests.

    Dependency injection is used exclusively for offline negative-path tests;
    the CLI supplies no provider or host overrides.
    """
    resolve = socket.getaddrinfo if resolver is None else resolver
    make_socket = socket.socket if socket_factory is None else socket_factory
    make_context = ssl.create_default_context if context_factory is None else context_factory

    try:
        ctx = make_context(ssl.Purpose.SERVER_AUTH)
        if ctx.verify_mode != ssl.CERT_REQUIRED or ctx.check_hostname is not True:
            return "status=BLOCKED_TLS_CONFIGURATION"
        if ctx.minimum_version < ssl.TLSVersion.TLSv1_2:
            return "status=BLOCKED_TLS_CONFIGURATION"

        answers = resolve(
            CANONICAL_HOST, CANONICAL_PORT, socket.AF_INET,
            socket.SOCK_STREAM, socket.IPPROTO_TCP,
        )
        if not isinstance(answers, (list, tuple)) or not 1 <= len(answers) <= MAX_DNS_ANSWERS:
            return "status=BLOCKED_DNS_UNAVAILABLE"
        validated: list[tuple[str, int]] = []
        for row in answers:
            if not isinstance(row, tuple) or len(row) != 5:
                return "status=BLOCKED_DNS_UNSAFE"
            family, socktype, protocol, _canonical, address = row
            if (family, socktype, protocol) != (
                socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP
            ):
                return "status=BLOCKED_DNS_UNSAFE"
            if (
                not isinstance(address, tuple) or len(address) != 2
                or type(address[0]) is not str or type(address[1]) is not int
                or address[1] != CANONICAL_PORT
            ):
                return "status=BLOCKED_DNS_UNSAFE"
            candidate = ipaddress.ip_address(address[0])
            if not isinstance(candidate, ipaddress.IPv4Address) or not candidate.is_global:
                return "status=BLOCKED_DNS_UNSAFE"
            validated.append((str(candidate), CANONICAL_PORT))

        # All resolved targets have been checked before any connection.
        with make_socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP) as raw:
            raw.settimeout(CONNECT_TIMEOUT_SECONDS)
            raw.connect(validated[0])  # numeric public IPv4; no DNS re-resolution
            with ctx.wrap_socket(raw, server_hostname=CANONICAL_HOST):
                return SUCCESS_STATUS

    except socket.gaierror:
        return "status=BLOCKED_DNS_UNAVAILABLE"
    except ssl.SSLCertVerificationError:
        return "status=BLOCKED_TLS_CERTIFICATE"
    except (TimeoutError, socket.timeout):
        return "status=BLOCKED_TLS_TIMEOUT"
    except ssl.SSLError:
        return "status=BLOCKED_TLS_HANDSHAKE"
    except ValueError:
        return "status=BLOCKED_DNS_UNSAFE"
    except OSError:
        return "status=BLOCKED_TLS_TRANSPORT"
    except Exception:
        # Never reflect a provider exception, URL, token, hostname override, or path.
        return "status=BLOCKED_TLS_CONFIGURATION"


def main(argv: Sequence[str] | None = None) -> int:
    args = tuple(sys.argv[1:] if argv is None else argv)
    if not args:
        print(INERT_STATUS)
        return 0
    if args != ("--probe-canonical-https", EXACT_PROBE_OPT_IN):
        print(INVALID_OPT_IN)
        return 2
    status = probe_canonical_https_tls()
    print(status)
    return 0 if status == SUCCESS_STATUS else 3


if __name__ == "__main__":
    raise SystemExit(main())

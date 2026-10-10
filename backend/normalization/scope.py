from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class ScopeConfig:
    allowed_hosts: list[str] = field(default_factory=list)
    allowed_schemes: list[str] = field(default_factory=lambda: ["http", "https"])
    exclude_paths: list[str] = field(default_factory=list)
    allow_private_networks: bool = False


def is_private_network(host: str) -> bool:
    """Check if host resolves to a private/loopback address."""
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        pass
    if host.endswith(".local") or host.endswith(".internal"):
        return True
    try:
        results = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _, _, _, _, sockaddr in results:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
                if addr.is_private or addr.is_loopback or addr.is_link_local:
                    return True
            except ValueError:
                continue
    except (socket.gaierror, OSError):
        pass
    return False


def is_in_scope(url: str, scope: ScopeConfig) -> bool:
    """Validate URL against scope configuration."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if not parsed.scheme or not parsed.hostname:
        return False

    if parsed.scheme.lower() not in [s.lower() for s in scope.allowed_schemes]:
        return False

    hostname = parsed.hostname.lower()
    if scope.allowed_hosts and hostname not in [h.lower() for h in scope.allowed_hosts]:
        return False

    if not scope.allow_private_networks and is_private_network(hostname):
        return False

    path = parsed.path or "/"
    for excluded in scope.exclude_paths:
        if path.startswith(excluded) or path == excluded:
            return False

    return True


def validate_redirect(original_url: str, redirect_url: str, scope: ScopeConfig) -> bool:
    """Ensure redirect destination stays in scope."""
    return is_in_scope(redirect_url, scope)

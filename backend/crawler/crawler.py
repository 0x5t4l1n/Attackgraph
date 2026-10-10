from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

from backend.crawler.extractors import extract_links, extract_forms, extract_js_urls, FormInfo
from backend.crawler.robots import fetch_robots_txt, RobotsRules

logger = logging.getLogger(__name__)


@dataclass
class CrawlConfig:
    target_url: str = ""
    allowed_hosts: list[str] = field(default_factory=list)
    allowed_schemes: list[str] = field(default_factory=lambda: ["http", "https"])
    exclude_paths: list[str] = field(default_factory=list)
    max_depth: int = 3
    max_concurrent: int = 5
    max_pages: int = 500
    request_timeout: float = 30.0
    rate_limit_rps: float = 10.0
    max_response_size: int = 10 * 1024 * 1024
    respect_robots_txt: bool = True
    follow_redirects: bool = True
    max_redirects: int = 5
    allow_private_networks: bool = False
    auth_cookies: dict[str, str] | None = None
    auth_headers: dict[str, str] | None = None
    user_agent: str = "AttackGraph/0.1 Security Research Crawler"


@dataclass
class CrawlResult:
    url: str
    normalized_url: str
    method: str
    status_code: int | None
    content_type: str | None
    headers: dict = field(default_factory=dict)
    body_preview: str | None = None
    discovered_urls: list[str] = field(default_factory=list)
    forms: list[dict] = field(default_factory=list)
    parent_url: str | None = None
    depth: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    redirect_chain: list[str] = field(default_factory=list)


@dataclass
class CrawlProgress:
    pages_discovered: int = 0
    pages_crawled: int = 0
    pages_queued: int = 0
    current_url: str | None = None
    errors: list[str] = field(default_factory=list)
    status: str = "pending"


class WebCrawler:
    """Asynchronous web crawler with scope enforcement, rate limiting, and cancellation."""

    def __init__(self, config: CrawlConfig) -> None:
        self.config = config
        self._visited: set[str] = set()
        self._discovered: set[str] = set()
        self._queue: asyncio.Queue[tuple[str, str | None, int]] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        self._cancel_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # not paused initially
        self._progress = CrawlProgress()
        self._robots: RobotsRules | None = None
        self._rate_delay = 1.0 / config.rate_limit_rps if config.rate_limit_rps > 0 else 0
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()

    @property
    def progress(self) -> CrawlProgress:
        return self._progress

    async def pause(self) -> None:
        self._pause_event.clear()
        self._progress.status = "paused"

    async def resume(self) -> None:
        self._pause_event.set()
        self._progress.status = "running"

    async def cancel(self) -> None:
        self._cancel_event.set()
        self._progress.status = "cancelled"

    async def crawl(self) -> AsyncGenerator[CrawlResult, None]:
        self._progress.status = "running"

        target = self.config.target_url.rstrip("/")
        if not self.config.allowed_hosts:
            parsed = urlparse(target)
            if parsed.hostname:
                self.config.allowed_hosts = [parsed.netloc.lower()]

        cookies = httpx.Cookies()
        if self.config.auth_cookies:
            for k, v in self.config.auth_cookies.items():
                cookies.set(k, v)

        headers = {"User-Agent": self.config.user_agent}
        if self.config.auth_headers:
            headers.update(self.config.auth_headers)

        async with httpx.AsyncClient(
            cookies=cookies,
            headers=headers,
            follow_redirects=False,
            timeout=httpx.Timeout(self.config.request_timeout),
            verify=True,
        ) as client:
            if self.config.respect_robots_txt:
                self._robots = await fetch_robots_txt(client, target)
                for sitemap_url in (self._robots.sitemaps or []):
                    if self._is_in_scope(sitemap_url):
                        await self._try_parse_sitemap(client, sitemap_url)

            await self._try_parse_sitemap(client, urljoin(target, "/sitemap.xml"))

            norm_target = self._normalize(target)
            self._queue.put_nowait((target, None, 0))
            self._discovered.add(norm_target)
            self._progress.pages_discovered = 1
            self._progress.pages_queued = 1

            while not self._cancel_event.is_set():
                await self._pause_event.wait()
                if self._cancel_event.is_set():
                    break

                try:
                    url, parent, depth = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                self._progress.pages_queued = self._queue.qsize()

                norm = self._normalize(url)
                if norm in self._visited:
                    continue
                if self._progress.pages_crawled >= self.config.max_pages:
                    self._progress.status = "completed"
                    break

                self._visited.add(norm)
                self._progress.current_url = url

                async with self._semaphore:
                    result = await self._fetch_page(client, url, parent, depth)

                self._progress.pages_crawled += 1

                if result.error:
                    self._progress.errors.append(f"{url}: {result.error}")

                if depth < self.config.max_depth and not result.error:
                    for discovered in result.discovered_urls:
                        dn = self._normalize(discovered)
                        if dn not in self._discovered and dn not in self._visited:
                            self._discovered.add(dn)
                            self._queue.put_nowait((discovered, url, depth + 1))
                            self._progress.pages_discovered += 1

                self._progress.pages_queued = self._queue.qsize()
                yield result

        if not self._cancel_event.is_set():
            self._progress.status = "completed"
        self._progress.current_url = None

    async def _rate_limit(self) -> None:
        if self._rate_delay <= 0:
            return
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._rate_delay:
                await asyncio.sleep(self._rate_delay - elapsed)
            self._last_request_time = time.monotonic()

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        parent_url: str | None,
        depth: int,
    ) -> CrawlResult:
        result = CrawlResult(
            url=url,
            normalized_url=self._normalize(url),
            method="GET",
            status_code=None,
            content_type=None,
            parent_url=parent_url,
            depth=depth,
        )

        redirect_chain: list[str] = []
        current_url = url

        try:
            for _ in range(self.config.max_redirects + 1):
                await self._rate_limit()

                resp = await client.get(current_url, follow_redirects=False)
                result.status_code = resp.status_code
                result.headers = dict(resp.headers)
                result.content_type = resp.headers.get("content-type", "")

                content_length = resp.headers.get("content-length")
                if content_length and int(content_length) > self.config.max_response_size:
                    result.error = f"Response too large: {content_length} bytes"
                    return result

                if resp.is_redirect and self.config.follow_redirects:
                    location = resp.headers.get("location", "")
                    if not location:
                        break
                    redirect_target = urljoin(current_url, location)
                    if not self._is_in_scope(redirect_target):
                        result.error = f"Redirect out of scope: {redirect_target}"
                        break
                    redirect_chain.append(current_url)
                    current_url = redirect_target
                    continue

                result.redirect_chain = redirect_chain
                if redirect_chain:
                    result.url = current_url
                    result.normalized_url = self._normalize(current_url)

                body = resp.text
                if len(body) > self.config.max_response_size:
                    body = body[: self.config.max_response_size]

                result.body_preview = body[:10240] if body else None

                ct = result.content_type or ""
                if "html" in ct.lower():
                    links = extract_links(body, current_url)
                    js_urls = extract_js_urls(body, current_url)
                    forms = extract_forms(body, current_url)

                    in_scope_links: list[str] = []
                    for link in links + js_urls:
                        if self._is_in_scope(link) and self._is_robots_allowed(link):
                            in_scope_links.append(link)

                    for form in forms:
                        if self._is_in_scope(form.action):
                            in_scope_links.append(form.action)

                    result.discovered_urls = list(set(in_scope_links))
                    result.forms = [
                        {
                            "action": f.action,
                            "method": f.method,
                            "fields": [
                                {"name": ff.name, "type": ff.type, "required": ff.required}
                                for ff in f.fields
                            ],
                            "enctype": f.enctype,
                        }
                        for f in forms
                    ]

                break
        except httpx.TimeoutException:
            result.error = "Request timed out"
        except httpx.ConnectError as exc:
            result.error = f"Connection error: {exc}"
        except httpx.HTTPError as exc:
            result.error = f"HTTP error: {exc}"
        except Exception as exc:
            result.error = f"Unexpected error: {exc}"

        return result

    async def _try_parse_sitemap(self, client: httpx.AsyncClient, sitemap_url: str) -> None:
        if not self._is_in_scope(sitemap_url):
            return
        try:
            resp = await client.get(sitemap_url, timeout=10.0, follow_redirects=True)
            if resp.status_code != 200:
                return
            ct = resp.headers.get("content-type", "")
            if "xml" not in ct and "text" not in ct:
                return
            soup = BeautifulSoup(resp.text, "lxml")
            for loc in soup.find_all("loc"):
                url_text = loc.get_text(strip=True)
                if url_text and self._is_in_scope(url_text):
                    norm = self._normalize(url_text)
                    if norm not in self._discovered:
                        self._discovered.add(norm)
                        self._queue.put_nowait((url_text, sitemap_url, 1))
                        self._progress.pages_discovered += 1
        except Exception as exc:
            logger.debug("Failed to parse sitemap %s: %s", sitemap_url, exc)

    def _normalize(self, url: str) -> str:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower()
        port = parsed.port
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            port = None
        netloc = f"{host}:{port}" if port else host
        path = parsed.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return f"{scheme}://{netloc}{path}"

    def _is_in_scope(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        if not parsed.scheme or not parsed.hostname:
            return False
        if parsed.scheme.lower() not in [s.lower() for s in self.config.allowed_schemes]:
            return False
        hostname = parsed.hostname.lower()
        netloc = parsed.netloc.lower()
        if self.config.allowed_hosts:
            allowed = [h.lower() for h in self.config.allowed_hosts]
            if hostname not in allowed and netloc not in allowed:
                return False
        if not self.config.allow_private_networks and self._is_private(hostname):
            return False
        path = parsed.path or "/"
        for excluded in self.config.exclude_paths:
            if path.startswith(excluded) or path == excluded:
                return False
        return True

    def _is_robots_allowed(self, url: str) -> bool:
        if not self.config.respect_robots_txt or self._robots is None:
            return True
        return self._robots.is_allowed(url, self.config.user_agent)

    @staticmethod
    def _is_private(host: str) -> bool:
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
                try:
                    addr = ipaddress.ip_address(sockaddr[0])
                    if addr.is_private or addr.is_loopback or addr.is_link_local:
                        return True
                except ValueError:
                    continue
        except (socket.gaierror, OSError):
            pass
        return False

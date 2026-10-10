from __future__ import annotations

import logging
from dataclasses import dataclass, field
from fnmatch import fnmatch
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


@dataclass
class _Rule:
    path: str
    allow: bool


@dataclass
class RobotsRules:
    rules: dict[str, list[_Rule]] = field(default_factory=dict)
    sitemaps: list[str] = field(default_factory=list)

    def is_allowed(self, url: str, user_agent: str = "*") -> bool:
        parsed = urlparse(url)
        path = parsed.path or "/"

        ua_lower = user_agent.lower()
        agent_rules: list[_Rule] | None = None
        for ua_key, rules in self.rules.items():
            if ua_key == ua_lower or ua_key == "*":
                if ua_key == ua_lower:
                    agent_rules = rules
                    break
        if agent_rules is None:
            agent_rules = self.rules.get("*", [])

        for rule in reversed(agent_rules):
            if rule.path == "/" and not rule.allow:
                return False
            if path.startswith(rule.path) or fnmatch(path, rule.path):
                return rule.allow

        return True


def parse_robots_txt(content: str) -> RobotsRules:
    result = RobotsRules()
    current_agents: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if ":" not in line:
            continue

        directive, _, value = line.partition(":")
        directive = directive.strip().lower()
        value = value.strip()

        if directive == "user-agent":
            current_agents = [value.lower()]
        elif directive == "disallow" and current_agents:
            if value:
                for agent in current_agents:
                    result.rules.setdefault(agent, []).append(_Rule(path=value, allow=False))
        elif directive == "allow" and current_agents:
            if value:
                for agent in current_agents:
                    result.rules.setdefault(agent, []).append(_Rule(path=value, allow=True))
        elif directive == "sitemap":
            if value:
                result.sitemaps.append(value)

    return result


async def fetch_robots_txt(client: httpx.AsyncClient, base_url: str) -> RobotsRules:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        resp = await client.get(robots_url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200 and "text" in (resp.headers.get("content-type", "")):
            return parse_robots_txt(resp.text)
    except httpx.HTTPError as exc:
        logger.debug("Failed to fetch robots.txt from %s: %s", robots_url, exc)
    except Exception as exc:
        logger.debug("Unexpected error fetching robots.txt: %s", exc)

    return RobotsRules()

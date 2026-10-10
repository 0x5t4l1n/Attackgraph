from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


@dataclass
class FormField:
    name: str
    type: str
    required: bool
    value: str | None = None


@dataclass
class FormInfo:
    action: str
    method: str
    fields: list[FormField] = field(default_factory=list)
    enctype: str = "application/x-www-form-urlencoded"


_JS_URL_RE = re.compile(
    r"""(?:fetch|axios\.(?:get|post|put|delete|patch)|window\.location(?:\.href)?\s*=|\.open)\s*\(\s*"""
    r"""['"]([^'"]{4,256})['"]"""
    r"""|['"](/(?:api|v[0-9]|auth|admin|user|account|graphql|webhook|internal)[^\s'"]{0,256})['"]""",
    re.IGNORECASE,
)


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: set[str] = set()

    tag_attrs = [
        ("a", "href"),
        ("link", "href"),
        ("script", "src"),
        ("img", "src"),
        ("iframe", "src"),
        ("form", "action"),
        ("area", "href"),
        ("base", "href"),
    ]

    for tag_name, attr_name in tag_attrs:
        for tag in soup.find_all(tag_name, **{attr_name: True}):
            raw = tag.get(attr_name, "")
            if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
                continue
            resolved = urljoin(base_url, raw)
            parsed = urlparse(resolved)
            if parsed.scheme in ("http", "https"):
                urls.add(resolved)

    return list(urls)


def extract_forms(html: str, base_url: str) -> list[FormInfo]:
    soup = BeautifulSoup(html, "lxml")
    forms: list[FormInfo] = []

    for form_tag in soup.find_all("form"):
        action_raw = form_tag.get("action", "")
        action = urljoin(base_url, action_raw) if action_raw else base_url
        method = (form_tag.get("method") or "GET").upper()
        enctype = form_tag.get("enctype", "application/x-www-form-urlencoded")

        fields: list[FormField] = []
        for inp in form_tag.find_all(["input", "select", "textarea"]):
            name = inp.get("name")
            if not name:
                continue
            inp_type = inp.get("type", "text") if inp.name == "input" else inp.name
            required = inp.has_attr("required")
            value = inp.get("value")
            fields.append(FormField(name=name, type=inp_type, required=required, value=value))

        forms.append(FormInfo(action=action, method=method, fields=fields, enctype=enctype))

    return forms


def extract_js_urls(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: set[str] = set()

    for script in soup.find_all("script"):
        text = script.string
        if not text:
            continue
        for match in _JS_URL_RE.finditer(text):
            raw = match.group(1) or match.group(2)
            if not raw:
                continue
            resolved = urljoin(base_url, raw)
            parsed = urlparse(resolved)
            if parsed.scheme in ("http", "https"):
                urls.add(resolved)

    return list(urls)


def extract_meta_info(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    info: dict[str, str | None] = {"title": None, "description": None, "robots": None}

    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        info["title"] = title_tag.string.strip()

    desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if desc_tag:
        info["description"] = desc_tag.get("content")

    robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    if robots_tag:
        info["robots"] = robots_tag.get("content")

    return info

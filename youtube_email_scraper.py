#!/usr/bin/env python3
"""
YouTube Email Scraper
=====================
Extract publicly listed contact emails from YouTube channels.

It works by fetching a channel's "About" page, parsing the embedded
`ytInitialData` JSON, and pulling emails out of the channel description and
listed external links. Optionally it also scans the descriptions of the
channel's most recent videos (creators frequently put a business email there).

Supports a single channel URL or batch input (many URLs at once).

Usage
-----
    # single channel
    python youtube_email_scraper.py -u https://www.youtube.com/@TechOnEarth

    # several channels on the command line
    python youtube_email_scraper.py -u https://youtube.com/@a https://youtube.com/@b

    # batch from a file (one URL/handle per line, '#' comments allowed)
    python youtube_email_scraper.py -f channels.txt -o results.csv

    # also scan the 15 most recent video descriptions per channel
    python youtube_email_scraper.py -f channels.txt --videos 15

Accepted inputs per channel (all normalized automatically):
    https://www.youtube.com/@Handle
    https://www.youtube.com/channel/UCxxxx
    https://www.youtube.com/c/CustomName
    https://www.youtube.com/user/LegacyName
    @Handle
    Handle

Notes
-----
* Only emails the creator chose to publish publicly are returned. The
  CAPTCHA-gated "Business email" reveal button is intentionally NOT bypassed.
* Be polite: a delay between requests is applied by default. Scraping at scale
  may violate YouTube's Terms of Service — use responsibly and lawfully.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Iterable

import requests

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Email regex. Reasonably strict; trailing-dot / TLD handled in cleanup.
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,24}"
)

# Obfuscated forms people use to dodge naive scrapers, e.g.
#   "name (at) gmail (dot) com" / "name [at] gmail [dot] com" / "name at gmail dot com"
# The "at"/"dot" tokens MUST be bracketed or whitespace-delimited — never glued
# inside a real word (otherwise "Atualizadas. Os" would parse as es@ualizadas.os).
_AT = r"(?:[\(\[\{]\s*at\s*[\)\]\}]|\s+at\s+)"
_DOT = r"(?:[\(\[\{]\s*dot\s*[\)\]\}]|\s+dot\s+)"
OBFUSCATED_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)" + _AT +
    r"([a-zA-Z0-9.\-]+?)" + _DOT + r"([a-zA-Z]{2,24})",
    re.IGNORECASE,
)

# Extensions / junk that the loose regex sometimes catches inside page scripts.
BAD_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".js", ".css",
    ".json", ".woff", ".woff2", ".ttf", ".ico", ".mp4",
)
# Domains that are almost never a real contact email.
BAD_DOMAIN_HINTS = ("example.com", "sentry.io", "schema.org", "youtube.com",
                    "google.com", "googleapis.com", "gstatic.com", "ggpht.com")

# Plausible TLDs: common gTLDs + every ISO 3166-1 country code. An email whose
# TLD isn't here is almost certainly a regex false positive (e.g. ".os").
_COMMON_GTLDS = {
    "com", "net", "org", "edu", "gov", "mil", "int", "info", "biz", "io", "co",
    "ai", "app", "dev", "me", "tv", "online", "store", "shop", "site", "tech",
    "xyz", "live", "media", "email", "pro", "name", "mobi", "us", "uk", "eu",
    "asia", "cloud", "digital", "agency", "studio", "design", "world", "group",
}
_CC_TLDS = {
    "ac","ad","ae","af","ag","ai","al","am","ao","aq","ar","as","at","au","aw",
    "ax","az","ba","bb","bd","be","bf","bg","bh","bi","bj","bm","bn","bo","br",
    "bs","bt","bw","by","bz","ca","cc","cd","cf","cg","ch","ci","ck","cl","cm",
    "cn","co","cr","cu","cv","cw","cx","cy","cz","de","dj","dk","dm","do","dz",
    "ec","ee","eg","er","es","et","eu","fi","fj","fk","fm","fo","fr","ga","gb",
    "gd","ge","gf","gg","gh","gi","gl","gm","gn","gp","gq","gr","gt","gu","gw",
    "gy","hk","hn","hr","ht","hu","id","ie","il","im","in","io","iq","ir","is",
    "it","je","jm","jo","jp","ke","kg","kh","ki","km","kn","kp","kr","kw","ky",
    "kz","la","lb","lc","li","lk","lr","ls","lt","lu","lv","ly","ma","mc","md",
    "me","mg","mh","mk","ml","mm","mn","mo","mp","mq","mr","ms","mt","mu","mv",
    "mw","mx","my","mz","na","nc","ne","nf","ng","ni","nl","no","np","nr","nu",
    "nz","om","pa","pe","pf","pg","ph","pk","pl","pm","pn","pr","ps","pt","pw",
    "py","qa","re","ro","rs","ru","rw","sa","sb","sc","sd","se","sg","sh","si",
    "sk","sl","sm","sn","so","sr","ss","st","sv","sx","sy","sz","tc","td","tf",
    "tg","th","tj","tk","tl","tm","tn","to","tr","tt","tv","tw","tz","ua","ug",
    "uk","us","uy","uz","va","vc","ve","vg","vi","vn","vu","wf","ws","ye","yt",
    "za","zm","zw",
}
VALID_TLDS = _COMMON_GTLDS | _CC_TLDS


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass
class ChannelResult:
    input: str
    channel_url: str = ""
    channel_name: str = ""
    channel_id: str = ""
    country: str = ""
    subscribers: str = ""
    emails: list[str] = field(default_factory=list)
    source: str = ""          # where the email(s) came from
    status: str = "ok"        # ok | no_email | error
    error: str = ""

    @property
    def emails_str(self) -> str:
        return "; ".join(self.emails)


# --------------------------------------------------------------------------- #
# URL handling
# --------------------------------------------------------------------------- #

def normalize_channel_url(raw: str) -> str:
    """Turn any user-supplied channel reference into a canonical channel URL."""
    s = raw.strip()
    if not s:
        return ""
    # bare handle / name
    if s.startswith("@"):
        return f"https://www.youtube.com/{s}"
    if "youtube.com" not in s and "youtu.be" not in s:
        # treat as a handle
        return f"https://www.youtube.com/@{s.lstrip('@')}"
    if not s.startswith("http"):
        s = "https://" + s
    # strip query/fragment and any trailing /about, /videos, etc. variants
    s = s.split("?")[0].split("#")[0].rstrip("/")
    for tail in ("/about", "/videos", "/featured", "/streams", "/community",
                 "/playlists", "/shorts"):
        if s.endswith(tail):
            s = s[: -len(tail)]
    return s


def about_url(channel_url: str) -> str:
    return channel_url.rstrip("/") + "/about"


# --------------------------------------------------------------------------- #
# Email extraction helpers
# --------------------------------------------------------------------------- #

def clean_email(e: str) -> str:
    e = e.strip().strip(".,;:'\"()<>[]").lower()
    return e


def valid_email(e: str) -> bool:
    if not e or "@" not in e:
        return False
    if e.endswith(BAD_SUFFIXES):
        return False
    if len(e) > 100:
        return False
    domain = e.split("@", 1)[1]
    if any(h in domain for h in BAD_DOMAIN_HINTS):
        return False
    # TLD must be plausible — kills regex junk like "es@ualizadas.os".
    tld = domain.rsplit(".", 1)[-1]
    if tld not in VALID_TLDS:
        return False
    return True


def extract_emails(text: str) -> list[str]:
    """Pull plain and lightly-obfuscated emails out of free text."""
    found: list[str] = []
    for m in EMAIL_RE.findall(text or ""):
        e = clean_email(m)
        if valid_email(e):
            found.append(e)
    for local, dom, tld in OBFUSCATED_RE.findall(text or ""):
        e = clean_email(f"{local}@{dom}.{tld}")
        if valid_email(e):
            found.append(e)
    # de-dup, preserve order
    seen, out = set(), []
    for e in found:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


# --------------------------------------------------------------------------- #
# YouTube parsing
# --------------------------------------------------------------------------- #

def parse_yt_initial_data(html: str) -> dict:
    for pat in (
        r"var ytInitialData\s*=\s*(\{.*?\})\s*;</script>",
        r'window\["ytInitialData"\]\s*=\s*(\{.*?\})\s*;</script>',
        r"ytInitialData\s*=\s*(\{.*?\})\s*;",
    ):
        m = re.search(pat, html, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    return {}


def _walk_collect(obj, key_names: set[str], out: list):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in key_names and isinstance(v, str):
                out.append(v)
            _walk_collect(v, key_names, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk_collect(item, key_names, out)


def extract_channel_meta(data: dict, page_html: str) -> dict:
    """Pull description, name, country, id, subscriber count, external links."""
    meta = {"description": "", "name": "", "country": "", "channel_id": "",
            "subscribers": "", "links": []}

    # Description: pick the longest "description" string found.
    descs: list[str] = []
    _walk_collect(data, {"description", "channelDescription"}, descs)
    if descs:
        meta["description"] = max(descs, key=len)

    # aboutChannelViewModel holds clean structured fields on modern layouts.
    def find_first(o, key):
        if isinstance(o, dict):
            if key in o:
                return o[key]
            for v in o.values():
                r = find_first(v, key)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = find_first(v, key)
                if r is not None:
                    return r
        return None

    about = find_first(data, "aboutChannelViewModel")
    if isinstance(about, dict):
        meta["description"] = about.get("description", meta["description"])
        meta["country"] = about.get("country", "") or meta["country"]
        meta["channel_id"] = about.get("channelId", "") or meta["channel_id"]
        sub = about.get("subscriberCountText", "")
        meta["subscribers"] = sub if isinstance(sub, str) else meta["subscribers"]
        for link in about.get("links", []) or []:
            try:
                url = (link["channelExternalLinkViewModel"]["link"]["content"])
                meta["links"].append(url)
            except (KeyError, TypeError):
                pass

    # Fallbacks from page metadata / microformat.
    if not meta["name"]:
        m = re.search(r'<meta property="og:title" content="([^"]+)"', page_html)
        if m:
            meta["name"] = m.group(1)
    if not meta["channel_id"]:
        m = re.search(r'"channelId":"(UC[\w\-]+)"', page_html)
        if m:
            meta["channel_id"] = m.group(1)
    if not meta["country"]:
        m = re.search(r'"country":"([^"]+)"', page_html)
        if m:
            meta["country"] = m.group(1)

    # Decode HTML entities so names read "TV Box & Mini PC", not "...&amp;...".
    meta["name"] = html.unescape(meta["name"])
    meta["description"] = html.unescape(meta["description"])
    return meta


# --------------------------------------------------------------------------- #
# Networking
# --------------------------------------------------------------------------- #

def fetch(session: requests.Session, url: str, retries: int = 3,
          timeout: int = 25) -> str:
    last_err = None
    for attempt in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            last_err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(last_err or "request failed")


def scan_recent_videos(session: requests.Session, channel_url: str,
                       limit: int) -> tuple[list[str], str]:
    """Fetch the /videos page, grab recent video IDs, scan their descriptions."""
    emails: list[str] = []
    src = ""
    try:
        html = fetch(session, channel_url.rstrip("/") + "/videos")
    except RuntimeError:
        return emails, src
    vids = []
    seen = set()
    for vid in re.findall(r'"videoId":"([\w\-]{11})"', html):
        if vid not in seen:
            seen.add(vid)
            vids.append(vid)
        if len(vids) >= limit:
            break
    for vid in vids:
        try:
            vhtml = fetch(session, f"https://www.youtube.com/watch?v={vid}")
        except RuntimeError:
            continue
        # The description sits in shortDescription within ytInitialPlayerResponse.
        m = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', vhtml)
        desc = ""
        if m:
            try:
                desc = json.loads('"' + m.group(1) + '"')
            except json.JSONDecodeError:
                desc = m.group(1)
        for e in extract_emails(desc):
            if e not in emails:
                emails.append(e)
                if not src:
                    src = f"video:{vid}"
        time.sleep(0.4)
    return emails, src


# --------------------------------------------------------------------------- #
# Per-channel pipeline
# --------------------------------------------------------------------------- #

def scrape_channel(session: requests.Session, raw_input: str,
                   video_limit: int = 0) -> ChannelResult:
    result = ChannelResult(input=raw_input)
    channel_url = normalize_channel_url(raw_input)
    if not channel_url:
        result.status = "error"
        result.error = "empty/invalid input"
        return result
    result.channel_url = channel_url

    try:
        html = fetch(session, about_url(channel_url))
    except RuntimeError as e:
        result.status = "error"
        result.error = str(e)
        return result

    data = parse_yt_initial_data(html)
    meta = extract_channel_meta(data, html)
    result.channel_name = meta["name"]
    result.channel_id = meta["channel_id"]
    result.country = meta["country"]
    result.subscribers = meta["subscribers"]

    emails: list[str] = []
    # 1) channel description
    for e in extract_emails(meta["description"]):
        if e not in emails:
            emails.append(e)
    if emails:
        result.source = "about_description"

    # 2) external links text (rarely contains a mailto, but cheap to check)
    if meta["links"]:
        for e in extract_emails(" ".join(meta["links"])):
            if e not in emails:
                emails.append(e)
                result.source = result.source or "about_links"

    # 3) optional: recent video descriptions
    if not emails and video_limit > 0:
        vemails, vsrc = scan_recent_videos(session, channel_url, video_limit)
        for e in vemails:
            if e not in emails:
                emails.append(e)
        if emails:
            result.source = vsrc or "video_description"

    result.emails = emails
    result.status = "ok" if emails else "no_email"
    return result


# --------------------------------------------------------------------------- #
# Input / output
# --------------------------------------------------------------------------- #

def read_input_file(path: str) -> list[str]:
    items: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                items.append(line)
    return items


def write_csv(path: str, results: Iterable[ChannelResult]) -> None:
    cols = ["input", "channel_url", "channel_name", "channel_id", "country",
            "subscribers", "emails", "source", "status", "error"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in results:
            d = asdict(r)
            d["emails"] = r.emails_str
            w.writerow([d[c] for c in cols])


def write_json(path: str, results: list[ChannelResult]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([asdict(r) for r in results], fh, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Extract public contact emails from YouTube channels.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-u", "--url", nargs="+", default=[],
                   help="one or more channel URLs/handles")
    p.add_argument("-f", "--file",
                   help="file with one channel URL/handle per line")
    p.add_argument("-o", "--output",
                   help="output path (.csv or .json). Defaults to stdout only.")
    p.add_argument("--videos", type=int, default=0, metavar="N",
                   help="if no email on About page, scan N recent video "
                        "descriptions (default 0 = off)")
    p.add_argument("--delay", type=float, default=1.5,
                   help="seconds to wait between channels (default 1.5)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    inputs: list[str] = list(args.url)
    if args.file:
        try:
            inputs.extend(read_input_file(args.file))
        except OSError as e:
            print(f"error: cannot read {args.file}: {e}", file=sys.stderr)
            return 2
    # de-dup preserving order
    seen, deduped = set(), []
    for i in inputs:
        if i not in seen:
            seen.add(i)
            deduped.append(i)
    inputs = deduped

    if not inputs:
        build_parser().print_help()
        return 1

    session = requests.Session()
    results: list[ChannelResult] = []
    total = len(inputs)
    for idx, raw in enumerate(inputs, 1):
        print(f"[{idx}/{total}] {raw} ...", end=" ", flush=True, file=sys.stderr)
        res = scrape_channel(session, raw, video_limit=args.videos)
        results.append(res)
        if res.status == "ok":
            print(f"OK  {res.emails_str}", file=sys.stderr)
        elif res.status == "no_email":
            print("no email found", file=sys.stderr)
        else:
            print(f"ERROR {res.error}", file=sys.stderr)
        if idx < total:
            time.sleep(args.delay)

    # console summary
    print()
    found = sum(1 for r in results if r.status == "ok")
    for r in results:
        if r.emails:
            print(f"{r.channel_name or r.channel_url}\t{r.emails_str}")
    print(f"\nScanned {total} channel(s); found emails for {found}.",
          file=sys.stderr)

    if args.output:
        if args.output.lower().endswith(".json"):
            write_json(args.output, results)
        else:
            write_csv(args.output, results)
        print(f"Saved results to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""모든 페이지의 언어 선택기를 KO/EN/中文/日本語 4개로 맞춥니다 (멱등).

원본 미러는 KO·EN 두 개짜리 `.seg` 를 갖고 있습니다. 여기에 zh·ja 를 더하고
각 언어의 링크가 **같은 경로**를 가리키도록 계산합니다
(예: /k-mods/guide/install/ → /k-mods/ja/guide/install/).
hreflang alternates 도 4개로 맞춥니다.

    python3 tools/add_locales.py --check
    python3 tools/add_locales.py
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n_build import LANG_ATTR, SITE, base_route, switcher_html  # noqa: E402

LIVE = "https://dogebi.github.io"


def current_locale(page: str) -> str:
    rel = os.path.relpath(page, SITE).split(os.sep)
    return rel[0] if len(rel) > 2 and rel[0] in ("en", "zh", "ja") else "ko"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    pages = sorted(glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True))
    if not pages:
        sys.exit("페이지 없음")
    changed = clean = 0
    for page in pages:
        html = open(page, encoding="utf-8").read()
        soup = BeautifulSoup(html, "html.parser")
        seg = soup.select_one("nav.seg")
        if seg is None:
            print("세그먼트 없음:", os.path.relpath(page, SITE), file=sys.stderr)
            continue
        code = current_locale(page)
        route = base_route(page)
        want = switcher_html(route, code)
        have = "".join(str(a) for a in seg.find_all("a"))
        needs = have.replace(' aria-current="true"', "") != want.replace(' aria-current="true"', "")
        if needs:
            if args.check:
                changed += 1
                continue
            seg.clear()
            seg.append(BeautifulSoup(want, "html.parser"))
            # hreflang alternates 4개 유지
            for tag in soup.find_all("link", rel="alternate"):
                lang = tag.get("hreflang")
                if not lang or lang == "x-default":
                    continue
                for lcode, lattr in LANG_ATTR.items():
                    if lattr == lang:
                        prefix = "" if lcode == "ko" else lcode + "/"
                        tag["href"] = f"{LIVE}/k-mods/{prefix}{route}".rstrip("/") + "/"
            open(page, "w", encoding="utf-8").write(str(soup))
            changed += 1
        else:
            clean += 1
    if args.check:
        print(f"check: {clean} pages already 4-language, {changed} need the pass")
        return 1 if changed else 0
    print(f"switcher: {changed} pages rewritten, {clean} already ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

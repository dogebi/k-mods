#!/usr/bin/env python3
"""미러 사이트의 sitemap 을 다시 만듭니다 (ko/en/zh/ja + hreflang 교차 링크).

원본 sitemap-0.xml 은 미러에 받아지지 않았고, sitemap-index.xml 은 원본 주소를
가리킨 채였습니다. 여기서 네 로케일 304개 URL 을 dogebi 주소로 다시 씁니다.

    python3 tools/make_sitemap.py
"""

from __future__ import annotations

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
LIVE = "https://dogebi.github.io"
LANG = {"": "ko", "en/": "en", "zh/": "zh-Hans", "ja/": "ja"}


def routes() -> list[str]:
    out = []
    for page in sorted(glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True)):
        rel = os.path.relpath(os.path.dirname(page), SITE).replace(os.sep, "/")
        if rel == ".":
            out.append("")
            continue
        out.append(re.sub(r"^(en|zh|ja)/", "", rel))
    return sorted(set(out))


def url(prefix: str, route: str) -> str:
    path = f"{LIVE}/k-mods/{prefix}{route}"
    return path.rstrip("/") + "/"


def main() -> None:
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    count = 0
    for route in routes():
        for prefix, lang in LANG.items():
            rows.append("<url>")
            rows.append(f"<loc>{url(prefix, route)}</loc>")
            for other_prefix, other_lang in LANG.items():
                rows.append(f'<xhtml:link rel="alternate" hreflang="{other_lang}" '
                            f'href="{url(other_prefix, route)}"/>')
            rows.append('<xhtml:link rel="alternate" hreflang="x-default" '
                        f'href="{url("", route)}"/>')
            rows.append("</url>")
            count += 1
    rows.append("</urlset>")
    open(os.path.join(SITE, "sitemap-0.xml"), "w", encoding="utf-8").write("\n".join(rows))

    index = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
             f'<sitemap><loc>{LIVE}/k-mods/sitemap-0.xml</loc></sitemap></sitemapindex>')
    open(os.path.join(SITE, "sitemap-index.xml"), "w", encoding="utf-8").write(index)
    print(f"sitemap: {count} URLs ({len(routes())} routes x 4 locales)")


if __name__ == "__main__":
    main()

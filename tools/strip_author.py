#!/usr/bin/env python3
"""꼬리글의 '만든 사람 / Author / 作者 / 作成者' 메뉴를 지웁니다 (멱등).

이 항목은 사이트 루트(https://dogebi.github.io/)로 나가는 개인 사이트 링크라
목록 사이트의 메뉴로는 필요 없다는 판단(사용자 요청). 다른 꼬리글 링크
(GitHub·설치 가이드·안전 가이드·기여하기·mod 제안하기)는 그대로 둡니다.

zh/ja 페이지는 ko 페이지에서 생성되므로 ko/en 트리에만 적용하면
다음 빌드에서 나머지 로케일도 자동으로 빠집니다.

    python3 tools/strip_author.py --check
    python3 tools/strip_author.py
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
# 꼬리글 메뉴의 '만든 사람' 링크 = 사이트 루트. mod 링크(/k-mods/…)와 구분된다.
AUTHOR_LINK = re.compile(r'<a\b[^>]*href="https://dogebi\.github\.io/"[^>]*>[^<]*</a>')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    pages = sorted(p for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True)
                   if not any(os.sep + c + os.sep in p for c in ("en", "zh", "ja"))
                   or os.sep + "en" + os.sep in p)
    changed = total = 0
    for page in pages:
        html = open(page, encoding="utf-8").read()
        found = AUTHOR_LINK.findall(html)
        if not found:
            continue
        changed += 1
        total += len(found)
        if args.check:
            continue
        open(page, "w", encoding="utf-8").write(AUTHOR_LINK.sub("", html))

    if args.check:
        print(f"check: {total} author links in {changed} pages (ko/en)")
        return 1 if total else 0
    print(f"author menu removed: {total} links in {changed} pages (ko/en; zh/ja follow on rebuild)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""머리글의 GitHub 아이콘 링크를 이 저장소(dogebi/k-mods)로 돌립니다 (멱등).

원본 미러의 모든 페이지에는 머리글 오른쪽에 GitHub 아이콘이 있고, 그 href 는
원본 저장소(SeongGwangJu/k-mods)를 가리킵니다. 이 사이트의 저장소는 dogebi/k-mods 이므로
그 링크만 바꿉니다.

건드리지 않는 것:
  · 설치 명령 `/plugin marketplace add SeongGwangJu/k-mods` — 마켓플레이스 파일이 있는
    원본을 가리켜야 설치가 됩니다
  · 본문·꼬리글의 원본 저장소 링크, 커밋·이슈·편집 링크 — 출처 표기와 기여 경로

    python3 tools/patch_links.py            # 적용
    python3 tools/patch_links.py --check    # 남은 개수만 확인
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
UPSTREAM = "https://github.com/SeongGwangJu/k-mods"
OURS = "https://github.com/dogebi/k-mods"
# aria-label 로 머리글 아이콘만 정확히 집는다 (꼬리글 링크·본문 링크는 그대로)
HEADER_ICON = f'<a class="icon-btn" href="{UPSTREAM}" aria-label="GitHub"'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    pages = sorted(glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True))
    if not pages:
        sys.exit(f"no pages under {SITE}")

    patched = clean = leftover = 0
    for page in pages:
        html = open(page, encoding="utf-8").read()
        if HEADER_ICON in html:
            if args.check:
                leftover += 1
                continue
            html = html.replace(HEADER_ICON, HEADER_ICON.replace(UPSTREAM, OURS))
            open(page, "w", encoding="utf-8").write(html)
            patched += 1
        else:
            clean += 1

    if args.check:
        print(f"check: {clean} pages point at {OURS}, {leftover} still at {UPSTREAM}")
        return 1 if leftover else 0
    print(f"header GitHub icon -> {OURS} ({patched} patched, {clean} already)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

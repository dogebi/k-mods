#!/usr/bin/env python3
"""종이 테마를 모든 HTML 페이지에 붙입니다 (멱등).

  - </head> 앞에 paper.css 링크와 Noto Serif KR 폰트 링크를 넣습니다
  - 이미 들어 있으면 그대로 둡니다 (재실행 안전)
  - 두 링크가 실제로 반영됐는지 세어서 보고합니다

    python3 tools/apply_theme.py            # 적용
    python3 tools/apply_theme.py --check    # 적용 여부만 확인
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
MARK = 'href="/k-mods/paper.css"'
FONT = 'family=Noto+Serif+KR'
SNIPPET = (
    '<link rel="stylesheet" href="/k-mods/paper.css">\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&amp;display=swap">\n'
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    pages = sorted(glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True))
    if not pages:
        sys.exit(f"no pages under {SITE}")
    ok = missing = 0
    for page in pages:
        html = open(page, encoding="utf-8").read()
        if MARK in html and FONT in html:
            ok += 1
            continue
        if args.check:
            missing += 1
            print("missing theme:", os.path.relpath(page, ROOT))
            continue
        if "</head>" not in html:
            sys.exit(f"{page}: no </head>")
        html = html.replace("</head>", SNIPPET + "</head>", 1)
        open(page, "w", encoding="utf-8").write(html)
        ok += 1
    print(f"{'checked' if args.check else 'applied'}: {ok} pages themed, {missing} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

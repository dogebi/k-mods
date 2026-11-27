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
FONT = 'family=Hahmlet'
OLD_FONT = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&amp;display=swap">\n'
)
STYLE_LINK = '<link rel="stylesheet" href="/k-mods/paper.css">\n'
FONT_LINK = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@400;500;700&amp;'
    'family=IBM+Plex+Sans+KR:wght@400;500;600;700&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap">\n'
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
        need_mark = MARK not in html
        need_font = FONT not in html
        if not need_mark and not need_font:
            ok += 1
            continue
        if args.check:
            missing += 1
            print("missing theme:", os.path.relpath(page, ROOT))
            continue
        if "</head>" not in html:
            sys.exit(f"{page}: no </head>")
        add = ""
        if need_mark:
            add += STYLE_LINK
        if need_font:
            # 예전 폰트 링크(Noto Serif KR) 가 남아 있으면 걷어내고 새 폰트로 바꾼다
            if OLD_FONT in html:
                html = html.replace(OLD_FONT, "", 1)
            add += FONT_LINK
        html = html.replace("</head>", add + "</head>", 1)
        open(page, "w", encoding="utf-8").write(html)
        ok += 1
    print(f"{'checked' if args.check else 'applied'}: {ok} pages themed, {missing} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

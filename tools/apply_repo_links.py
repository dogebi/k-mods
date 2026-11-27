#!/usr/bin/env python3
"""사이트에 남은 원본 저장소 표기를 dogebi/k-mods 로 바꿉니다 (멱등).

원본 미러는 저장소 이름을 세 종류로 박아 두었습니다.

  · 표시 문구      "SeongGwangJu/k-mods의 registry에서 자동 생성됩니다"
  · 설치 명령      `/plugin marketplace add SeongGwangJu/k-mods`
  · 링크           github.com/SeongGwangJu/k-mods/blob|tree|issues|edit|commit/…

이 사이트의 저장소는 dogebi/k-mods 이므로 전부 바꿉니다. 링크가 404 가 되지 않도록
저장소 쪽에 원본 파일(registry·mods·CONTRIBUTING·이슈 템플릿·marketplace.json)을
같이 두었고, 커밋 해시는 원본 이력을 `upstream` 브랜치로 밀어 넣어 살아 있게 했습니다.

개인 프로필(github.com/SeongGwangJu)은 건드리지 않습니다 — 저장소가 아니라 저자입니다.

    python3 tools/apply_repo_links.py --check
    python3 tools/apply_repo_links.py
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
I18N = os.path.join(ROOT, "data", "i18n")
FROM = "SeongGwangJu/k-mods"
TO = "dogebi/k-mods"


def patch_text(text: str) -> tuple[str, int]:
    count = text.count(FROM)
    return (text.replace(FROM, TO), count) if count else (text, 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    total_files = total_hits = 0

    # 1) 페이지 (ko/en/zh/ja 전부)
    for page in sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)):
        html = open(page, encoding="utf-8").read()
        new, hits = patch_text(html)
        if not hits:
            continue
        total_files += 1
        total_hits += hits
        if not args.check:
            open(page, "w", encoding="utf-8").write(new)

    # 2) 사전 (키 = 원문, 값 = 번역)  — 페이지와 같은 치환을 해야 게이트가 어긋나지 않는다
    dict_files = [os.path.join(I18N, "ko-strings.json")]
    dict_files += glob.glob(os.path.join(I18N, "out", "*", "*.json"))
    dict_files += glob.glob(os.path.join(I18N, "chunks", "*.json"))
    dict_files += [os.path.join(I18N, f"{code}.json") for code in ("zh", "ja")]
    for path in dict_files:
        if not os.path.exists(path):
            continue
        raw = open(path, encoding="utf-8").read()
        new, hits = patch_text(raw)
        if not hits:
            continue
        total_files += 1
        total_hits += hits
        if not args.check:
            json.loads(new)  # 깨진 JSON 을 쓰지 않는다
            open(path, "w", encoding="utf-8").write(new)

    if args.check:
        print(f"check: {total_hits} occurrences in {total_files} files still at {FROM}")
        return 1 if total_hits else 0
    print(f"repo links -> {TO}: {total_hits} occurrences in {total_files} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

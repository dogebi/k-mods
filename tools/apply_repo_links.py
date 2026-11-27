#!/usr/bin/env python3
"""사이트에 남은 원본 저장소·저자·사이트 주소의 흔적을 dogebi 로 바꿉니다 (멱등).

원본 미러는 세 가지를 박아 두었습니다.

  · 저장소      SeongGwangJu/k-mods   (표시 문구·설치 명령·blob|tree|issues|edit|commit 링크)
  · 사이트 주소  seonggwangju.github.io/k-mods/…  (canonical·og:url·og:image·JSON-LD @id·item url)
  · 저자        github.com/SeongGwangJu  (카드의 'by …' 링크, JSON-LD author.url·author.name)

이 사이트의 주인은 dogebi 이므로 전부 바꿉니다. 링크가 404 가 되지 않도록
저장소에 원본 파일(registry·mods·CONTRIBUTING·이슈 템플릿·marketplace.json)을 함께 두었고,
커밋 해시는 원본 이력을 `upstream` 브랜치로 밀어 넣어 살아 있게 했습니다.

사전(ko-strings.json 키, out/*.json 번역값)에도 같은 치환을 겁니다 —
페이지 문자열과 사전 키가 어긋나면 빌드 게이트가 번역 누락으로 판정합니다.

    python3 tools/apply_repo_links.py --check
    python3 tools/apply_repo_links.py
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
I18N = os.path.join(ROOT, "data", "i18n")

# 순서가 중요하다: 호스트 → 저장소 → 프로필 → 남은 이름
REPLACEMENTS = [
    (re.compile(r"seonggwangju\.github\.io", re.I), "dogebi.github.io"),
    (re.compile(r"github\.com/SeongGwangJu(?![\w.-])", re.I), "github.com/dogebi"),
    (re.compile(r"SeongGwangJu/k-mods", re.I), "dogebi/k-mods"),
    (re.compile(r"SeongGwangJu(?![A-Za-z0-9_.-])", re.I), "dogebi"),
    (re.compile(r"Seong Gwang Ju", re.I), "dogebi"),
]
RESIDUE = re.compile(r"seonggwangju", re.I)


def patch(text: str) -> tuple[str, int]:
    hits = len(RESIDUE.findall(text))
    if not hits:
        return text, 0
    for pattern, repl in REPLACEMENTS:
        text = pattern.sub(repl, text)
    return text, hits


def targets() -> list[str]:
    files = sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True))
    files += sorted(glob.glob(os.path.join(SITE, "*.txt")))
    files += [os.path.join(I18N, "ko-strings.json")]
    files += sorted(glob.glob(os.path.join(I18N, "out", "*", "*.json")))
    files += sorted(glob.glob(os.path.join(I18N, "chunks", "*.json")))
    files += [os.path.join(I18N, f"{code}.json") for code in ("zh", "ja")]
    return [f for f in files if os.path.exists(f)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    changed = total = 0
    for path in targets():
        raw = open(path, encoding="utf-8").read()
        new, hits = patch(raw)
        if not hits:
            continue
        changed += 1
        total += hits
        if args.check:
            continue
        if path.endswith(".json"):
            try:
                json.loads(new)
            except json.JSONDecodeError:
                sys.exit(f"{path}: 치환 결과가 JSON 이 아니다 — 쓰지 않음")
        open(path, "w", encoding="utf-8").write(new)

    if args.check:
        print(f"check: {total} occurrences in {changed} files still say seonggwangju")
        return 1 if total else 0
    print(f"repo/author/site -> dogebi: {total} occurrences in {changed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

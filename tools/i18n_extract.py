#!/usr/bin/env python3
"""k-mods 미러의 한국어 문자열을 로케일 사전으로 뽑습니다.

152페이지(한국어 76 + 영어 76) 중 **한국어 트리만** 훑어, 텍스트 노드와
번역이 필요한 속성(title/aria-label/alt/placeholder)을 중복 없이 모읍니다.
같은 문자열은 한 번만 번역하고, 빌드 단계에서 다시 페이지에 뿌립니다.

    python3 tools/i18n_extract.py                 # data/i18n/ko-strings.json + chunks/
    python3 tools/i18n_extract.py --stats
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import statistics

from bs4 import BeautifulSoup, Comment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
OUT = os.path.join(ROOT, "data", "i18n")
SKIP_PARENTS = {"script", "style", "svg", "code", "pre", "noscript"}
SKIP_ATTRS = {"title", "aria-label", "alt", "placeholder"}
HANGUL = re.compile(r"[가-힣]")
# 번역하지 않는 것: 순수 숫자·기호·경로·명령·버전
# ASCII 만으로 이루어진 토큰(경로·명령·버전)은 번역하지 않는다.
# \w 를 쓰면 파이썬이 한글까지 단어 문자로 보아 한글 문자열을 통째로 걸러 버린다.
NO_TRANSLATE = re.compile(r"^[\s\d\W_]+$|^[A-Za-z0-9_./:@#\[\]{}<>=+*~-]+$")


def pages() -> list[str]:
    out = [p for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True)
           if os.sep + "en" + os.sep not in p and os.sep + "zh" + os.sep not in p
           and os.sep + "ja" + os.sep not in p]
    return sorted(out)


def rel(page: str) -> str:
    return "/" + os.path.relpath(os.path.dirname(page), SITE).replace(os.sep, "/").strip(".").strip("/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()

    text_counts: collections.Counter = collections.Counter()
    text_first: dict[str, str] = {}
    attr_counts: collections.Counter = collections.Counter()
    attr_first: dict[str, str] = {}

    all_pages = pages()
    for page in all_pages:
        soup = BeautifulSoup(open(page, encoding="utf-8").read(), "html.parser")
        where = rel(page) or "/"
        for el in soup.find_all(True):
            for name in SKIP_ATTRS:
                value = el.get(name)
                if isinstance(value, str) and HANGUL.search(value):
                    attr_counts[value] += 1
                    attr_first.setdefault(value, where)
        for node in soup.find_all(string=True):
            if isinstance(node, Comment):
                continue
            if any(parent.name in SKIP_PARENTS for parent in node.parents):
                continue
            text = " ".join(node.split())
            if not text or not HANGUL.search(text) or NO_TRANSLATE.match(text):
                continue
            text_counts[text] += 1
            text_first.setdefault(text, where)

    strings = sorted(text_counts, key=lambda t: (text_first[t], t))
    attrs = sorted(attr_counts, key=lambda t: (attr_first[t], t))

    # --merge: 이미 번역이 끝난 사전의 id 를 고정하고, 새로 발견된 문자열만 뒤에 덧붙인다
    existing = os.path.join(OUT, "ko-strings.json")
    if args.merge and os.path.exists(existing):
        old = json.load(open(existing, encoding="utf-8"))
        keep_ids = {item["ko"]: item["i"] for item in old["strings"]}
        keep_attr = {item["ko"]: item["i"] for item in old["attrs"]}
        merged = list(old["strings"])
        new_items = []
        next_id = max(keep_ids.values(), default=-1) + 1
        for text in strings:
            if text in keep_ids:
                continue
            new_items.append({"i": next_id, "ko": text, "ctx": text_first[text], "n": text_counts[text]})
            merged.append(new_items[-1])
            next_id += 1
        merged_attrs = list(old["attrs"])
        new_attrs = []
        next_a = max(keep_attr.values(), default=-1) + 1
        for text in attrs:
            if text in keep_attr:
                continue
            new_attrs.append({"i": next_a, "ko": text, "ctx": attr_first[text]})
            merged_attrs.append(new_attrs[-1])
            next_a += 1
        print(f"merge: 기존 {len(old['strings'])} + 신규 {len(new_items)} = {len(merged)} 문자열, "
              f"속성 +{len(new_attrs)}")
        payload = {"source": "ko", "pages": len(all_pages), "strings": merged, "attrs": merged_attrs}
        json.dump(payload, open(existing, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if new_items:
            json.dump({"ids": [i["i"] for i in new_items], "items": new_items},
                      open(os.path.join(OUT, "chunks", "extra-strings.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        if new_attrs:
            json.dump({"ids": [i["i"] for i in new_attrs], "items": new_attrs},
                      open(os.path.join(OUT, "chunks", "extra-attrs.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        print("wrote chunks/extra-strings.json" if new_items else "신규 문자열 없음")
        return 0
    print(f"pages: {len(all_pages)}")
    print(f"unique strings: {len(strings)} ({sum(len(s) for s in strings)} chars, "
          f"median {statistics.median(len(s) for s in strings):.0f})")
    print(f"unique attributes: {len(attrs)} ({sum(len(a) for a in attrs)} chars)")
    if args.stats:
        for s in strings[:5]:
            print("  ", repr(s[:60]))

    os.makedirs(OUT, exist_ok=True)
    payload = {
        "source": "ko",
        "pages": len(all_pages),
        "strings": [{"i": i, "ko": s, "ctx": text_first[s], "n": text_counts[s]}
                    for i, s in enumerate(strings)],
        "attrs": [{"i": i, "ko": s, "ctx": attr_first[s]} for i, s in enumerate(attrs)],
    }
    path = os.path.join(OUT, "ko-strings.json")
    json.dump(payload, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", os.path.relpath(path, ROOT))

    # 번역 청크: 한 덩어리 9,000자 안팎으로 잘라 병렬 번역에 쓴다
    chunk_dir = os.path.join(OUT, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    for old in glob.glob(os.path.join(chunk_dir, "*.json")):
        os.remove(old)
    budget, chunks, current, size = 9000, [], [], 0
    for item in payload["strings"]:
        if size + len(item["ko"]) > budget and current:
            chunks.append(current)
            current, size = [], 0
        current.append(item)
        size += len(item["ko"])
    if current:
        chunks.append(current)
    for n, chunk in enumerate(chunks, 1):
        json.dump({"ids": [c["i"] for c in chunk], "items": chunk},
                  open(os.path.join(chunk_dir, f"strings-{n:02d}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    json.dump({"ids": [a["i"] for a in payload["attrs"]], "items": payload["attrs"]},
              open(os.path.join(chunk_dir, "attrs-01.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"chunks: {len(chunks)} strings + 1 attrs -> {os.path.relpath(chunk_dir, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

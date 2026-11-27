#!/usr/bin/env python3
"""페이지가 참조하는데 로컬에 없는 파일을 모아서 받아 옵니다.

미러는 html/css/js/png/woff2 위주로 받아 두므로, 미리보기 영상(mp4)·webp 처럼
페이지마다 새로 붙는 파일이 빠질 수 있습니다. 이 스크립트가 참조를 훑어 빠진 것만
내려받고, 남은 누락이 있으면 0 이 아닌 값으로 끝납니다.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
ORIGIN = "https://seonggwangju.github.io"
REF = re.compile(r'(?:href|src|poster|data-src)="(/k-mods/[^"\s]+)')
SRCSET = re.compile(r'srcset="([^"]+)"')


def local_path(rel: str) -> str:
    p = os.path.join(ROOT, rel.lstrip("/"))
    return os.path.join(p, "index.html") if os.path.isdir(p) else p


def main() -> int:
    missing: set[str] = set()
    for page in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
        html = open(page, encoding="utf-8", errors="replace").read()
        refs = REF.findall(html)
        # srcset="a 640w, b 1088w" 안의 URL 은 첫 토큰만 잡히므로 따로 훑는다
        for group in SRCSET.findall(html):
            for part in group.split(","):
                url = part.strip().split(" ")[0]
                if url.startswith("/k-mods/"):
                    refs.append(url)
        for ref in refs:
            clean = ref.split("#")[0].split("?")[0]
            if not clean or clean.endswith("/"):
                continue
            if not os.path.exists(local_path(clean)):
                missing.add(clean)
    if not missing:
        print("refs: complete")
        return 0
    print(f"refs: {len(missing)} missing -> downloading")
    proxy = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:1098"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    failed = 0
    for rel in sorted(missing):
        dest = local_path(rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            with opener.open(ORIGIN + rel, timeout=45) as r, open(dest, "wb") as f:
                f.write(r.read())
        except Exception as exc:  # noqa: BLE001 - 어떤 실패든 보고만 하고 계속
            failed += 1
            print(f"  fail {rel}: {exc}")
    print(f"downloaded {len(missing) - failed}/{len(missing)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

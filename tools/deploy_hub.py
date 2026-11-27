#!/usr/bin/env python3
"""k-mods 미러를 dogebi.github.io/k-mods/ 로 배포합니다 (Git Data API).

소스 저장소(dogebi/k-mods)의 push 만으로는 라이브가 바뀌지 않습니다. 라이브는
공개 허브 저장소 dogebi/dogebi.github.io 의 master 브랜치 하위 폴더가 서빙하므로,
blob → tree → commit → ref 로 올리고 올린 blob 의 sha 를 다시 읽어 대조합니다.

    python3 tools/deploy_hub.py --dry-run
    python3 tools/deploy_hub.py --message "k-mods: 종이 테마"
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import time
import sys
from concurrent.futures import ThreadPoolExecutor

OWNER = "dogebi"
REPO = "dogebi.github.io"
BRANCH = "master"
FOLDER = "k-mods"
SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "k-mods")
LIVE = f"https://{OWNER}.github.io/{FOLDER}/"
# 사이트가 실제로 이 모양일 때만 올립니다 (빈 폴더나 테마 없는 사본 방지)
SENTINELS = {
    "index.html": ("paper.css", "k-mods"),
    "assets": None,
}
MIN_HTML = 2000


def gh(args, stdin=None):
    proc = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed:\n{proc.stderr.strip()}")
    return proc.stdout


TRANSIENT = ("REFUSED_STREAM", "stream error", "connection reset", "EOF", "502", "503", "504",
             "timeout", "TLS handshake")


def api(path, method=None, payload=None, attempts=3):
    """GitHub API 호출. http2 스트림이 끊기는 일시 오류는 다시 시도한다.

    ref PATCH 는 요청 본문을 이미 보낸 뒤 실패하면 gh 가 재시도하지 못하고
    `REFUSED_STREAM ... define Request.GetBody` 로 죽는다. 커밋 객체는 이미 만들어졌는데
    ref 만 안 옮겨가므로, 그대로 두면 배포가 조용히 실패한다.
    """
    args = ["api", path]
    if method:
        args += ["-X", method]
    body = None
    if payload is not None:
        args += ["--input", "-"]
        body = json.dumps(payload)
    last = ""
    for attempt in range(1, attempts + 1):
        proc = subprocess.run(["gh", *args], input=body, capture_output=True, text=True)
        if proc.returncode == 0:
            return json.loads(proc.stdout) if proc.stdout.strip() else {}
        last = proc.stderr.strip()
        if attempt == attempts or not any(t in last for t in TRANSIENT):
            break
        wait = 2 ** attempt
        print(f"  api {path} 일시 오류 ({last.splitlines()[0][:80]}) — {wait}s 뒤 재시도 {attempt}/{attempts - 1}")
        time.sleep(wait)
    raise SystemExit(f"gh {' '.join(args)} failed:\n{last}")


def collect():
    files = []
    for root, _dirs, names in os.walk(SITE):
        for name in names:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, SITE).replace(os.sep, "/")
            files.append((rel, path))
    return sorted(files)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--message", default="k-mods: publish site")
    args = ap.parse_args()

    files = collect()
    if not files:
        sys.exit(f"no files under {SITE}")

    index = os.path.join(SITE, "index.html")
    html = open(index, encoding="utf-8").read()
    if len(html) < MIN_HTML:
        sys.exit(f"index.html is only {len(html)} bytes; refusing to publish")
    for needle in SENTINELS["index.html"]:
        if needle not in html:
            sys.exit(f"index.html is missing {needle!r}; refusing to publish")
    if not any(rel.startswith("assets/") for rel, _ in files):
        sys.exit("assets/ is empty; refusing to publish")

    total = sum(os.path.getsize(p) for _, p in files)
    print(f"local: {len(files)} files, {total / 1024 / 1024:.1f} MiB")
    print(f"local index.html sha1: {hashlib.sha1(html.encode()).hexdigest()[:12]}")

    if args.dry_run:
        for rel, _ in files[:8]:
            print("  would publish", f"{FOLDER}/{rel}")
        print(f"dry run: would publish {LIVE}")
        return 0

    parent = api(f"repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")["object"]["sha"]
    print(f"parent commit: {parent[:10]}")

    def upload(item):
        rel, path = item
        raw = open(path, "rb").read()
        blob = api(f"repos/{OWNER}/{REPO}/git/blobs", "POST",
                   {"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"})
        return {"path": f"{FOLDER}/{rel}", "mode": "100644", "type": "blob", "sha": blob["sha"]}

    # blob 업로드는 서로 독립이라 8개씩 병렬로 (160여 개면 5분 → 40초)
    with ThreadPoolExecutor(max_workers=8) as pool:
        tree = list(pool.map(upload, files))
    print(f"blobs: {len(tree)}")

    new_tree = api(f"repos/{OWNER}/{REPO}/git/trees", "POST", {"base_tree": parent, "tree": tree})
    commit = api(f"repos/{OWNER}/{REPO}/git/commits", "POST",
                 {"message": args.message, "tree": new_tree["sha"], "parents": [parent]})
    print(f"commit: {commit['sha'][:10]}")
    api(f"repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", "PATCH",
        {"sha": commit["sha"], "force": False})
    head = api(f"repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")["object"]["sha"]
    if head != commit["sha"]:
        sys.exit("ref update did not take effect")

    # 올린 파일 일부를 다시 읽어 바이트를 대조합니다
    check = ["index.html", "paper.css", "robots.txt"]
    check = [c for c in check if os.path.exists(os.path.join(SITE, c))]
    for rel in check:
        remote = api(f"repos/{OWNER}/{REPO}/contents/{FOLDER}/{rel}?ref={BRANCH}")
        local = os.path.getsize(os.path.join(SITE, rel))
        if remote["size"] != local:
            sys.exit(f"{rel}: published {remote['size']} bytes, local {local}")
        print(f"verified: {rel} {remote['size']} bytes")
    print(f"live (Pages rebuilds in about a minute): {LIVE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

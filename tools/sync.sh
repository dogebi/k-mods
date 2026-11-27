#!/usr/bin/env bash
# k-mods 미러를 원본과 맞추고, 테마를 다시 입히고, 커밋·푸시·배포까지 한 번에.
#
#   bash tools/sync.sh            # 동기화 + 커밋 + 푸시 + 배포
#   bash tools/sync.sh --check    # 바뀐 게 있는지만 확인 (커밋 없음)
#
# 크론은 이 파일만 부릅니다. 변경이 없으면 아무 것도 커밋하지 않습니다.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM="https://seonggwangju.github.io/k-mods/"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1
LOG_DIR="$HOME/.hermes/cache/scratch"
mkdir -p "$LOG_DIR"
say() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

cd "$ROOT" || exit 1
say "sync start ($([ $CHECK_ONLY = 1 ] && echo check || echo full))"

# 1) 원본에서 바뀐 페이지만 다시 받는다 (--timestamping 은 mtime 비교)
wget --quiet -r -nH --no-parent --no-convert-links -e robots=off \
  --timestamping --reject-regex '\.(zip|mp4|tar\.gz|map)$' --level=8 \
  -A 'html,css,js,json,svg,png,webp,woff2,xml,txt,mp4' \
  -P "$ROOT" "$UPSTREAM" || say "wget reported an error (continuing)"

# 2) 새 페이지가 참조하는 파일 중 빠진 것을 보충
python3 "$ROOT/tools/fetch_missing.py" || say "fetch_missing failed"

# 3) 종이 테마 다시 입히기 (멱등)
python3 "$ROOT/tools/apply_theme.py" || { say "apply_theme failed"; exit 1; }

# 4) 변경 확인
if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
  say "no upstream changes"
  exit 0
fi
CHANGED=$(git status --porcelain | wc -l)
say "changed paths: $CHANGED"
[ $CHECK_ONLY = 1 ] && { git status --porcelain | head -20; exit 0; }

# 5) 커밋 + 푸시
git add -A
git commit -q -m "sync: upstream $(date '+%Y-%m-%d') 반영 (${CHANGED}개 파일)" || say "nothing to commit"
PROXY=http://127.0.0.1:1098
git -c http.proxy="$PROXY" -c https.proxy="$PROXY" push -q origin main \
  || say "push failed (will retry next run)"

# 6) 허브 배포
python3 "$ROOT/tools/deploy_hub.py" --message "k-mods: upstream sync $(date '+%Y-%m-%d')" \
  || { say "deploy failed"; exit 1; }
say "sync done"

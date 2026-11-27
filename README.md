# k-mods (종이 테마 미러)

[seonggwangju.github.io/k-mods](https://seonggwangju.github.io/k-mods/) 의 정적 사본에
[1in8b.life](https://1in8b.life/zh-hans/) 의 화면 언어를 입힌 배포판입니다.

- 라이브: https://dogebi.github.io/k-mods/
- 원본: https://github.com/SeongGwangJu/k-mods (MIT, `NOTICE.md` 참고)

원본 카탈로그는 한국어 152페이지(카탈로그·mod 69종·가이드 6편, 영어판 포함)로 되어 있고,
이 저장소는 **빌드 산출물을 그대로 미러링한 뒤 테마 한 겹만 덧입힙니다.** 원본의 생성
스크립트(`scripts/build.mjs`)나 레지스트리는 가져오지 않습니다 — 바뀌면 다시 받아 옵니다.

## 구조

```
k-mods/                     사본 + 테마 (그대로 배포되는 폴더)
  index.html, en/, mods/, guide/, assets/, previews/, fonts/, og/
  paper.css                 1in8b 스타일로 다시 칠하는 오버레이 (base.css 는 손대지 않음)
tools/
  sync.sh                   원본 동기화 → 테마 재적용 → 커밋/푸시 → 허브 배포
  apply_theme.py            모든 페이지 </head> 에 paper.css 와 Noto Serif KR 링크 삽입 (멱등)
  fetch_missing.py          페이지가 참조하는데 빠진 파일(mp4·webp 등)만 내려받기
  deploy_hub.py             dogebi.github.io/k-mods/ 로 Git Data API 배포 + 바이트 대조
```

## 테마 (paper.css)

원본은 CSS 변수(`--bg/--surface/--ink/--accent/--line/…`)로 짜여 있어서, 변수와 컴포넌트만
다시 칠하면 152페이지가 한 번에 바뀝니다. 1in8b에서 가져온 것:

| 요소 | 값 |
| --- | --- |
| 종이 바탕 | `#EBF0ED` + 26px 점 무늬(45% 투명도) |
| 카드/표면 | `#F7FAF8`, 1px `#C7D2CE` 괘선, 4px 모서리, 그림자 없음 |
| 본문 잉크 | `#13212A` / 보조 `#4A5A61` / 흐림 `#5F6E72` |
| 강조(크림슨) | `#8C1D3C` — 링크, 호버, 현재 위치 |
| 도장(청록) | `#0F6E68` — 점 표식, 포커스 링, 원본 배지 |
| 머리글자 | `Noto Serif KR` (없으면 나눔명조·바탕·AppleMyungjo) |
| 숫자·코드 | `JetBrains Mono` 유지 |
| 다크 | `#12171A` 바탕 / `#1A2024` 표면 / 크림슨 `#D8677F` |

원본의 다크 테마 토글, 언어 전환(KO/EN), 카테고리 필터, 미리보기 영상은 그대로 동작합니다.

## 동기화

```bash
bash tools/sync.sh --check     # 원본에 바뀐 게 있는지만 확인
bash tools/sync.sh             # 받아서 테마 다시 입히고 커밋·푸시·배포
python3 tools/deploy_hub.py --dry-run
```

Hermes 크론이 매일 09:40 KST 에 `tools/sync.sh` 를 돌립니다. 변경이 없으면 커밋하지 않습니다.

## 배포 구조

원본 저장소 push 만으로는 라이브가 바뀌지 않습니다. 라이브 `dogebi.github.io/k-mods/` 는
공개 허브 저장소 `dogebi/dogebi.github.io` 의 `master` 브랜치 하위 폴더가 서빙하므로,
`tools/deploy_hub.py` 가 blob → tree → commit → ref 로 올리고 올린 파일 크기를 다시 읽어
대조합니다. 허브 루트의 `.nojekyll` 이 있어 `_` 로 시작하는 자산도 그대로 올라갑니다.

## 범위와 한계

- canonical·hreflang·og:url 은 **원본 주소를 그대로 둡니다**. 미러이므로 검색 엔진이 원본을
  정본으로 보게 하는 편이 맞습니다.
- 원본이 빌드 산출물만 공개하므로, 카탈로그 데이터(registry JSON)는 미러에 없습니다.
  항목을 고치려면 원본 저장소에 기여해야 합니다.
- `Noto Serif KR` 은 Google Fonts 에서 받습니다. 차단된 네트워크에서는 나눔명조·바탕으로
  대체되고 레이아웃은 그대로 유지됩니다.
- 미리보기 영상(mp4)은 원본과 같은 경로로 함께 받아 두었습니다(약 2MB).

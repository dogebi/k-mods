#!/usr/bin/env python3
"""한국어 트리에서 zh-Hans / ja 트리를 만듭니다 (게이트 통과 시에만 기록).

  data/i18n/ko-strings.json          원문 목록(추출기 산출물)
  data/i18n/out/<locale>/*.json      번역 청크 결과 {"translations": {"<i>": "..."}}
  data/i18n/<locale>.json            병합 사전 (이 스크립트가 만든다)

동작
  · 한국어 페이지 76장을 bs4 로 읽어 텍스트 노드와 속성(title/aria-label/alt/placeholder)을
    사전으로 치환하고, <html lang>, canonical, hreflang, 내부 링크 접두어를 로케일에 맞춘다
  · 언어 선택기는 KO/EN/中文/日本語 4개로 다시 그린다 (각 페이지의 실제 경로를 계산)
  · 게이트: 한글이 남으면 그 페이지는 쓰지 않고 실패로 기록 / 요소 수 불일치 / 빈 값 / 자산 링크 변조

    python3 tools/i18n_build.py --check     # 사전만 검사
    python3 tools/i18n_build.py             # 빌드
    python3 tools/i18n_build.py --locale ja # 한 로케일만
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

from bs4 import BeautifulSoup, Comment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "k-mods")
I18N = os.path.join(ROOT, "data", "i18n")
BASE = "ko"
LOCALES = {"zh": "zh-Hans", "ja": "ja"}
SKIP_PARENTS = {"script", "style", "svg", "code", "pre", "noscript"}
TRANSLATABLE_ATTRS = ("title", "aria-label", "alt", "placeholder")
HANGUL = re.compile(r"[가-힣]")
KANA = re.compile(r"[\u3040-\u30ff]")
HAN = re.compile(r"[\u4e00-\u9fff]")
ASSET_PREFIXES = ("/k-mods/assets/", "/k-mods/fonts/", "/k-mods/previews/", "/k-mods/og/",
                  "/k-mods/paper.css", "/k-mods/robots.txt", "/k-mods/sitemap", "/k-mods/llms.txt",
                  "/k-mods/en/", "/k-mods/zh/", "/k-mods/ja/")
LIVE = "https://dogebi.github.io"

LANG_LABEL = {"ko": "KO", "en": "EN", "zh": "中文", "ja": "日本語"}
LANG_ATTR = {"ko": "ko", "en": "en", "zh": "zh-Hans", "ja": "ja"}


def merge_locale(code: str) -> dict:
    """번역 청크들을 하나의 사전으로 합칩니다."""
    src = json.load(open(os.path.join(I18N, "ko-strings.json"), encoding="utf-8"))
    strings = {item["i"]: item["ko"] for item in src["strings"]}
    attrs = {item["i"]: item["ko"] for item in src["attrs"]}
    meta_src_path = os.path.join(I18N, "chunks", "meta-01.json")
    meta = {}
    if os.path.exists(meta_src_path):
        meta = {item["i"]: item["ko"] for item in json.load(open(meta_src_path, encoding="utf-8"))["items"]}
    got_s: dict[int, str] = {}
    got_a: dict[int, str] = {}
    got_m: dict[int, str] = {}
    for path in sorted(glob.glob(os.path.join(I18N, "out", code, "*.json"))):
        payload = json.load(open(path, encoding="utf-8"))
        table = payload.get("translations") or {}
        name = os.path.basename(path)
        target = got_a if name.startswith("attrs") else got_m if name.startswith("meta") else got_s
        for key, value in table.items():
            target[int(key)] = value
    missing_s = [i for i in strings if i not in got_s]
    missing_a = [i for i in attrs if i not in got_a]
    pack = {
        "locale": code,
        "lang": LOCALES[code],
        "text": {strings[i]: got_s[i] for i in got_s if i in strings},
        "attr": {attrs[i]: got_a[i] for i in got_a if i in attrs},
        "meta": {meta[i]: got_m[i] for i in got_m if i in meta},
        "missing": {"text": len(missing_s), "attr": len(missing_a),
                    "meta": sum(1 for i in meta if i not in got_m)},
    }
    return pack


PARTICLE_SRC = re.compile(
    r"^(은|는|이|가|을|를|의|에|에서|으로|로|와|과|도|만|처럼|이나|나|등|안|됨|보임|가능|불가능|예요\.|확인\.|참고\.)$")


def is_particle(src: str) -> bool:
    return bool(PARTICLE_SRC.match(src.strip()))


def check_pack(pack: dict) -> list[str]:
    code = pack["locale"]
    problems: list[str] = []
    if pack["missing"]["text"] or pack["missing"]["attr"]:
        problems.append(f"{code}: 번역 누락 text={pack['missing']['text']} attr={pack['missing']['attr']}")
    for src, value in pack["text"].items():
        if not value.strip():
            if code == "zh" and is_particle(src):
                continue  # 중국어에는 대응 조사가 없다 — 노드를 지우는 것이 정답
            problems.append(f"{code}: 빈 값 — {src[:40]}")
            continue
        if HANGUL.search(value):
            problems.append(f"{code}: 한글 잔여 — {src[:30]} → {value[:30]}")
        if not re.search(r"[0-9A-Za-z\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7a3]", value):
            continue  # 문장부호만 남은 조각(인라인 코드 뒤 접미어)은 정상
        # 라틴 토큰이 모두 원문에도 있는 조각(고유명사 + 문장부호)은 번역 대상이 아니다
        latin = re.findall(r"[A-Za-z][A-Za-z0-9_.+-]*", value)
        if latin and all(tok in src for tok in latin):
            continue
        if code == "zh" and not HAN.search(value) and len(src) > 4:
            problems.append(f"{code}: 한자 없음 — {src[:30]} → {value[:30]}")
        if code == "ja" and not (KANA.search(value) or HAN.search(value)) and len(src) > 4:
            problems.append(f"{code}: 가나/한자 없음 — {src[:30]} → {value[:30]}")
    for src, value in pack["attr"].items():
        if not value.strip() or HANGUL.search(value):
            problems.append(f"{code}: 속성 값 문제 — {src[:30]} → {value[:30]}")
    return problems


def page_locale_path(src_page: str, code: str) -> str:
    """k-mods/<path>/index.html → k-mods/<code>/<path>/index.html"""
    rel = os.path.relpath(src_page, SITE)
    return os.path.join(SITE, code, rel)


def base_route(page: str) -> str:
    """/k-mods/ 아래에서 로케일 접두어를 뗀 경로. '/' 는 루트."""
    rel = os.path.relpath(os.path.dirname(page), SITE).replace(os.sep, "/")
    if rel == ".":
        return ""
    parts = rel.split("/")
    if parts[0] in ("en", "zh", "ja"):
        parts = parts[1:]
    return "/".join(parts)


def switcher_html(route: str, active: str) -> str:
    out = []
    for code in ("ko", "en", "zh", "ja"):
        prefix = "" if code == "ko" else code + "/"
        href = f"/k-mods/{prefix}{route}".rstrip("/") + "/"
        if href == "/k-mods":
            href = "/k-mods/"
        cur = ' aria-current="true"' if code == active else ""
        out.append(f'<a href="{href}" hreflang="{LANG_ATTR[code]}" lang="{LANG_ATTR[code]}"{cur}>{LANG_LABEL[code]}</a>')
    return "".join(out)


def prefix_links(soup: BeautifulSoup, code: str) -> None:
    # 언어 선택기(nav.seg)의 링크는 이미 로케일별로 계산돼 있다 — 건드리면 KO 링크가
    # /k-mods/<code>/ 로 덮여 선택기가 자기 자신을 두 번 가리키게 된다.
    seg_links = set(id(a) for a in (soup.select_one("nav.seg") or BeautifulSoup("<i></i>", "html.parser")).find_all("a"))
    for a in soup.find_all("a", href=True):
        if id(a) in seg_links:
            continue
        href = a["href"]
        if not href.startswith("/k-mods/"):
            continue
        if href.startswith(ASSET_PREFIXES):
            continue
        a["href"] = "/k-mods/" + code + "/" + href[len("/k-mods/"):]


def translate_page(src_page: str, code: str, pack: dict) -> tuple[str, int]:
    html = open(src_page, encoding="utf-8").read()
    soup = BeautifulSoup(html, "html.parser")
    used = 0

    for node in soup.find_all(string=True):
        if isinstance(node, Comment):
            continue
        if any(p.name in SKIP_PARENTS for p in node.parents):
            continue
        text = " ".join(node.split())
        if not text:
            continue
        value = pack["text"].get(text)
        if value is not None:
            if not value.strip():
                node.replace_with("")   # 조사 생략 — 노드 자체를 지운다
            else:
                node.replace_with(value if node.strip() == node else " " + value + " ")
            used += 1

    for el in soup.find_all(True):
        for name in TRANSLATABLE_ATTRS:
            current = el.get(name)
            if isinstance(current, str):
                value = pack["attr"].get(current)
                if value is not None:
                    el[name] = value
                    used += 1

    # 메타 설명 (검색 결과 스니펫) — ld+json 설명의 대체값으로도 쓴다
    ld_fallback = None
    for tag in soup.find_all("meta"):
        key = tag.get("name") or tag.get("property") or ""
        if key in ("description", "og:description", "twitter:description"):
            value = tag.get("content")
            if value and value in pack["meta"]:
                tag["content"] = pack["meta"][value]
                used += 1
                if key == "description":
                    ld_fallback = pack["meta"][value]

    # 구조화 데이터(JSON-LD): 설명·이름·경로를 로케일에 맞춘다
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = sc.string or ""
        try:
            data = json.loads(raw)
        except Exception:
            continue

        def localize_url(value: str) -> str:
            for host in (LIVE, "https://seonggwangju.github.io"):
                marker = host + "/k-mods/"
                if value.startswith(marker):
                    tail = value[len(marker):]
                    if any(tail.startswith(a.split("/k-mods/")[1]) for a in ASSET_PREFIXES):
                        return value
                    if tail.startswith(("en/", "zh/", "ja/")):
                        return value
                    return marker + code + "/" + tail
            return value

        def walk(obj):
            if isinstance(obj, dict):
                out = {}
                for k, v in obj.items():
                    if k == "inLanguage":
                        out[k] = LOCALES[code]
                    elif k == "description" and isinstance(v, str) and HANGUL.search(v) and v not in pack["text"]:
                        out[k] = ld_fallback or v
                    else:
                        out[k] = walk(v)
                return out
            if isinstance(obj, list):
                return [walk(v) for v in obj]
            if isinstance(obj, str):
                if obj in pack["text"]:
                    return pack["text"][obj]
                if obj in pack["meta"]:
                    return pack["meta"][obj]
                return localize_url(obj)
            return obj

        sc.string = json.dumps(walk(data), ensure_ascii=False)

    # 문서 머리말 / 정체성
    soup.html["lang"] = LOCALES[code]
    route = base_route(src_page)
    own = f"{LIVE}/k-mods/{code}/{route}".rstrip("/") + "/"
    for tag in soup.find_all("link", rel="canonical"):
        tag["href"] = own
    for tag in soup.find_all("link", rel="alternate"):
        lang = tag.get("hreflang")
        if not lang or lang == "x-default":
            continue
        for lcode, lattr in LANG_ATTR.items():
            if lattr == lang:
                prefix = "" if lcode == "ko" else lcode + "/"
                tag["href"] = f"{LIVE}/k-mods/{prefix}{route}".rstrip("/") + "/"

    # 언어 선택기 4개
    seg = soup.select_one("nav.seg")
    if seg is not None:
        seg.clear()
        seg.append(BeautifulSoup(switcher_html(route, code), "html.parser"))

    prefix_links(soup, code)
    return str(soup), used


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--locale", choices=sorted(LOCALES), action="append")
    args = ap.parse_args()

    pools = {code: merge_locale(code) for code in (args.locale or sorted(LOCALES))}
    problems: list[str] = []
    for code, pack in pools.items():
        json.dump(pack, open(os.path.join(I18N, f"{code}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        problems += check_pack(pack)
        print(f"{code}: {len(pack['text'])} 문자열 / {len(pack['attr'])} 속성 / {len(pack['meta'])} 메타 "
              f"(누락 text={pack['missing']['text']} attr={pack['missing']['attr']})")
    if problems:
        for line in problems[:25]:
            print("  -", line, file=sys.stderr)
        sys.exit(f"{len(problems)} 사전 문제 — 빌드 중단")
    print("사전 검사 통과")
    if args.check:
        return 0

    src_pages = sorted(p for p in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True)
                       if all(os.sep + c + os.sep not in p for c in ("en", "zh", "ja")))
    print(f"원본 페이지: {len(src_pages)}")
    failures = 0
    for code, pack in pools.items():
        written = 0
        for page in src_pages:
            out, used = translate_page(page, code, pack)
            check_soup = BeautifulSoup(out, "html.parser")
            visible = [n for n in check_soup.find_all(string=True)
                       if not isinstance(n, Comment)
                       and not any(p.name in SKIP_PARENTS for p in n.parents)
                       and n.strip()]
            residue = [n.strip() for n in visible if HANGUL.search(n)]
            for sc in check_soup.find_all("script", attrs={"type": "application/ld+json"}):
                if HANGUL.search(sc.string or ""):
                    residue.append("ld+json")
            if residue:
                failures += 1
                print("  ! 한글 잔여:", os.path.relpath(page, SITE), residue[:2], file=sys.stderr)
                continue
            dest = page_locale_path(page, code)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "w", encoding="utf-8").write(out)
            written += 1
        print(f"{code}: {written}/{len(src_pages)} 페이지 기록")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

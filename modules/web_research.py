"""
웹 리서치 모듈.

블로그 제목과 요약(키워드/위치/메모)을 바탕으로 웹에서 관련 배경 정보를
수집해, AI가 글을 더 풍부하게 쓰도록 참고 자료를 제공한다.

사용하는 소스
  - 네이버 검색 오픈API (블로그·지역)   : 한국 후기·장소 정보 — 키 있을 때만
      · 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET
  - 구글 Custom Search JSON API         : 일반 웹 검색 — 키 있을 때만
      · 환경변수 GOOGLE_CSE_KEY / GOOGLE_CSE_CX
  - 위키백과(한국어) 검색·요약 API      : 배경 상식 — 키 불필요
  - DuckDuckGo Instant Answer API       : 개요·관련 토픽 — 키 불필요

설계 원칙
  - 네이버·구글은 키가 있으면 쓰고, 없으면 조용히 건너뛴다(무료 소스만으로도 동작).
  - 네트워크/파싱 실패는 조용히 무시하고 '수집한 만큼만' 반환한다.
    (웹 정보가 없어도 블로그 생성 자체는 항상 되어야 하므로)
  - 반환은 사람이 읽을 수 있는 요약 문자열 + 출처 URL 목록.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests

_TIMEOUT = 8  # 초
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppData/BlogWriter (research; contact: local-app)"
    )
}


@dataclass
class ResearchResult:
    query: str = ""
    snippets: list[str] = field(default_factory=list)   # 수집한 정보 조각들
    sources: list[str] = field(default_factory=list)    # 출처 URL

    @property
    def has_content(self) -> bool:
        return bool(self.snippets)

    def to_reference_text(self, max_chars: int = 1600) -> str:
        """AI 프롬프트에 넣을 '참고 자료' 텍스트로 변환."""
        if not self.snippets:
            return ""
        lines = []
        total = 0
        for i, s in enumerate(self.snippets, 1):
            s = s.strip()
            if not s:
                continue
            piece = f"{i}. {s}"
            if total + len(piece) > max_chars:
                remain = max_chars - total
                if remain > 40:
                    lines.append(piece[:remain] + "…")
                break
            lines.append(piece)
            total += len(piece)
        return "\n".join(lines)


def _clean(text: str) -> str:
    """HTML 태그/과도한 공백 제거."""
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_relevant(title: str, query: str) -> bool:
    """
    위키백과 문서 제목이 검색어와 실제로 관련 있는지 대략 판정.
    제목의 토큰(2글자 이상) 중 하나라도 검색어에 포함되면 관련으로 본다.
    (예: 검색어 '다이슨 V15 무선청소기' → 제목 '재규격화군'은 무관 → 제외)
    """
    q = query.replace(" ", "")
    title_tokens = [t for t in re.split(r"[\s·()（）,]+", title) if len(t) >= 2]
    if not title_tokens:
        return title in q
    for tok in title_tokens:
        if tok in q or q.find(tok) != -1:
            return True
    return False


def _wikipedia_ko(query: str, max_items: int = 2) -> tuple[list[str], list[str]]:
    """한국어 위키백과에서 검색 → 상위 문서 요약 추출."""
    snippets: list[str] = []
    sources: list[str] = []
    try:
        # 1) 검색으로 문서 제목 찾기
        r = requests.get(
            "https://ko.wikipedia.org/w/api.php",
            params={
                "action": "query", "list": "search", "srsearch": query,
                "format": "json", "srlimit": max_items,
            },
            headers=_HEADERS, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        hits = r.json().get("query", {}).get("search", [])
    except Exception:
        return snippets, sources

    for hit in hits[:max_items]:
        title = hit.get("title")
        if not title:
            continue
        # 검색어와 무관한 문서(동음이의어 오매칭)는 건너뜀
        if not _is_relevant(title, query):
            continue
        try:
            # 2) 문서 요약(intro extract) 가져오기
            rr = requests.get(
                "https://ko.wikipedia.org/w/api.php",
                params={
                    "action": "query", "prop": "extracts",
                    "exintro": 1, "explaintext": 1, "titles": title,
                    "format": "json", "redirects": 1,
                },
                headers=_HEADERS, timeout=_TIMEOUT,
            )
            rr.raise_for_status()
            pages = rr.json().get("query", {}).get("pages", {})
            for _, page in pages.items():
                extract = _clean(page.get("extract", ""))
                if extract:
                    # 너무 길면 앞 2~3문장만
                    sentences = re.split(r"(?<=[.。!?])\s+", extract)
                    summary = " ".join(sentences[:3]).strip()
                    if summary:
                        snippets.append(f"[위키백과 '{title}'] {summary}")
                        sources.append(
                            "https://ko.wikipedia.org/wiki/" + title.replace(" ", "_")
                        )
        except Exception:
            continue
    return snippets, sources


def _duckduckgo_instant(query: str) -> tuple[list[str], list[str]]:
    """DuckDuckGo Instant Answer API에서 개요/관련 토픽 추출."""
    snippets: list[str] = []
    sources: list[str] = []
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=_HEADERS, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return snippets, sources

    abstract = _clean(data.get("AbstractText", ""))
    if abstract:
        snippets.append(f"[개요] {abstract}")
        src = data.get("AbstractURL")
        if src:
            sources.append(src)

    # 관련 토픽에서 짧은 설명 몇 개
    for topic in data.get("RelatedTopics", [])[:3]:
        if isinstance(topic, dict):
            txt = _clean(topic.get("Text", ""))
            if txt and len(txt) > 15:
                snippets.append(f"[관련] {txt}")
                if topic.get("FirstURL"):
                    sources.append(topic["FirstURL"])
    return snippets, sources


def _naver_search(query: str, max_items: int = 3) -> tuple[list[str], list[str]]:
    """
    네이버 검색 오픈API로 블로그·지역 정보를 수집.
    키(NAVER_CLIENT_ID / NAVER_CLIENT_SECRET)가 없으면 조용히 빈 결과 반환.
    (출처: https://developers.naver.com/docs/serviceapi/search/blog/blog.md)
    """
    import os
    cid = os.environ.get("NAVER_CLIENT_ID", "").strip()
    csec = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    snippets: list[str] = []
    sources: list[str] = []
    if not (cid and csec):
        return snippets, sources

    headers = {**_HEADERS, "X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec}
    # 블로그 후기 + 지역(장소) 정보 둘 다 시도
    for kind, label in (("blog", "네이버 블로그"), ("local", "네이버 지역정보")):
        try:
            r = requests.get(
                f"https://openapi.naver.com/v1/search/{kind}",
                params={"query": query, "display": max_items, "sort": "sim"},
                headers=headers, timeout=_TIMEOUT,
            )
            r.raise_for_status()
            items = r.json().get("items", [])
        except Exception:
            continue
        for it in items[:max_items]:
            title = _clean(it.get("title", ""))
            desc = _clean(it.get("description", ""))
            text = (title + " — " + desc).strip(" —")
            if text and len(text) > 10:
                snippets.append(f"[{label}] {text}")
                link = it.get("link") or it.get("roadAddress")
                if link:
                    sources.append(link)
    return snippets, sources


def _google_search(query: str, max_items: int = 3) -> tuple[list[str], list[str]]:
    """
    구글 Custom Search JSON API로 웹 검색 결과 수집.
    키(GOOGLE_CSE_KEY / GOOGLE_CSE_CX)가 없으면 조용히 빈 결과 반환.
    (출처: https://developers.google.com/custom-search/v1/using_rest)
    """
    import os
    key = os.environ.get("GOOGLE_CSE_KEY", "").strip()
    cx = os.environ.get("GOOGLE_CSE_CX", "").strip()
    snippets: list[str] = []
    sources: list[str] = []
    if not (key and cx):
        return snippets, sources

    try:
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": key, "cx": cx, "q": query,
                    "num": max_items, "hl": "ko", "lr": "lang_ko"},
            headers=_HEADERS, timeout=_TIMEOUT,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
    except Exception:
        return snippets, sources

    for it in items[:max_items]:
        title = _clean(it.get("title", ""))
        snippet = _clean(it.get("snippet", ""))
        text = (title + " — " + snippet).strip(" —")
        if text and len(text) > 10:
            snippets.append(f"[구글 검색] {text}")
            if it.get("link"):
                sources.append(it["link"])
    return snippets, sources


def research(title: str, keywords: str = "", location: str = "",
             extra: str = "", style: str = "") -> ResearchResult:
    """
    제목 + 요약 정보를 조합해 웹에서 배경 정보를 수집한다.

    title    : 가게명/여행지/제품명 (핵심)
    keywords : 특징 키워드
    location : 위치(맛집/여행)
    extra    : 추가 메모
    style    : 블로그 스타일(맛집/여행/제품) — 검색어 보강용
    """
    # 검색어 구성: 제목을 중심으로 위치/키워드를 덧붙임
    parts = [p for p in [title, location, keywords] if p and p.strip()]
    query = " ".join(parts).strip() or (title or "").strip()
    result = ResearchResult(query=query)
    if not query:
        return result

    seen = set()

    def _add(snips, srcs):
        for s in snips:
            key = s[:60]
            if key not in seen:
                seen.add(key)
                result.snippets.append(s)
        for u in srcs:
            if u and u not in result.sources:
                result.sources.append(u)

    # 1) 네이버 검색 (한국 블로그 후기·지역 정보에 강함) — 키 있을 때만
    _add(*_naver_search(query))

    # 2) 구글 Custom Search (일반 웹 검색) — 키 있을 때만
    _add(*_google_search(query))

    # 3) 위키백과 (제목 위주로 정확도 높게) — 키 불필요
    wiki_q = " ".join([p for p in [title, location] if p]).strip() or query
    _add(*_wikipedia_ko(wiki_q))

    # 4) DuckDuckGo 개요 — 키 불필요
    _add(*_duckduckgo_instant(query))

    return result

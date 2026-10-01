"""
AI 블로그 작성 도우미
"""
import os
import io
import json
import base64
import time
import markdown
import streamlit as st
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI 블로그 작성기",
    page_icon="✍️",
    layout="wide",               # ← wide 레이아웃으로 변경
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* 전체 여백 축소 */
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    h1 { font-size: 1.5rem !important; margin-bottom: 0 !important; }

    /* 생성 버튼 */
    div[data-testid="stButton"] > button {
        background: #03C75A !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        width: 100%;
    }
    div[data-testid="stButton"] > button:hover { background: #02a847 !important; }

    /* 기록 카드 */
    .hist-card {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 10px;
        cursor: pointer;
        transition: border-color .15s;
    }
    .hist-card:hover { border-color: #03C75A; }
    .hist-title { font-weight: 700; font-size: 0.95rem; color: #111; }
    .hist-meta  { font-size: 0.75rem; color: #888; margin-top: 2px; }
    .hist-preview { font-size: 0.8rem; color: #555;
                    margin-top: 6px; line-height: 1.5;
                    display: -webkit-box; -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical; overflow: hidden; }

    /* 사진 그리드 */
    [data-testid="stImage"] img { border-radius: 8px; }

    /* 구분선 */
    hr { margin: 0.8rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 기록 저장/로드 (JSON 파일)
# ══════════════════════════════════════════════════════════════════════════════
# 작성 기록은 '접속자별 세션'에만 보관한다(st.session_state).
#   - 공개 배포 시 방문자끼리 기록이 섞이지 않고, 개인정보가 서버에 남지 않는다.
#   - 브라우저 탭(세션)을 닫으면 기록도 사라진다.
_HISTORY_KEY = "history"

def load_history() -> list:
    return st.session_state.get(_HISTORY_KEY, [])

def save_history(history: list):
    st.session_state[_HISTORY_KEY] = history

def add_to_history(title: str, style: str, content: str, html: str,
                   inputs: dict | None = None):
    history = load_history()
    history.insert(0, {
        "id":      datetime.now().strftime("%Y%m%d%H%M%S"),
        "date":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "title":   title,
        "style":   style,
        "content": content,
        "html":    html,
        "chars":   len(content.replace("\n","").replace(" ","")),
        # 내가 입력한 내용(요청)을 함께 보관 → 결과를 보고 다시 수정·재생성할 수 있게
        "inputs":  inputs or {},
    })
    save_history(history[:50])   # 최근 50개만 유지


# ══════════════════════════════════════════════════════════════════════════════
# AI / 유틸 함수
# ══════════════════════════════════════════════════════════════════════════════
GEMINI_MODEL = "gemini-3.6-flash"

def build_prompt(style, title, location, keywords, extra, tone, img_descs, length,
                 web_reference=""):
    photos_text = (
        "\n".join(f"  사진{i+1}: {d}" for i, d in enumerate(img_descs))
        if img_descs else "  사진 없음 — 텍스트 정보만으로 작성"
    )
    length_map = {
        "짧게 (500자 내외)":   "500자 내외 (핵심만 간결하게)",
        "보통 (800~1000자)":   "800~1000자",
        "길게 (1500자 이상)":  "1500자 이상 (풍부하고 상세하게)",
        "매우 길게 (2000자+)": "2000자 이상 (최대한 자세하고 풍성하게)",
    }

    # 데일리 문 스타일 전용 톤 지시문
    if tone == "🌙 데일리 문 스타일":
        tone_inst = (
            "아래는 실제 '데일리 문(bling2min)' 블로거의 글쓰기 특징이다. 이 스타일을 정확히 따라 작성할 것.\n\n"
            "【말투와 어미】\n"
            "  · 기본 어미: '~했다', '~있었음', '~없음', '~인듯', '~인가봄' (반말/해라체)\n"
            "  · 귀여운 어미도 섞기: '~했당', '~좋았당', '~이었당'\n"
            "  · 감탄/리액션: 'ㅎ_ㅎ', 'ㅋㅋㅋㅋ', 'ㅠㅠ', 'ㅎㅎ' 를 문장 끝에 자연스럽게 섞기\n"
            "  · 독자에게 말 걸기: '~분들은 ~해보시길 바랍니당' 식의 마무리\n\n"
            "【문장 구조】\n"
            "  · 문장을 극히 짧게 끊기 (1~2줄 이내)\n"
            "  · 각 문장 사이에 빈 줄을 넣어 여백 확보\n"
            "  · 한 문단에 2~3문장 이하\n\n"
            "【내용 구성】\n"
            "  · 소제목(##)으로 장소/섹션별 구분\n"
            "  · 번호 이모지(1️⃣ 2️⃣ 3️⃣)로 리스트 정리\n"
            "  · 본인 솔직한 감상을 중간중간 삽입 ('괜히 반갑고 그래', '선택의 여지가 없음' 식)\n"
            "  · 가격·운영시간·위치 등 실용 정보는 글 말미에 따로 정리\n"
            "  · 과장 없이 담백하게, 그러나 개성 있게\n\n"
            "【이모지】\n"
            "  · 화려한 이모지 남발 금지\n"
            "  · 번호 이모지(1️⃣~5️⃣)와 포인트용 이모지 몇 개만 사용\n\n"
            "【마무리】\n"
            "  · '~분들께 강추', '만족스러운 ~이 되시길 ㅎㅎ' 식의 독자 배려 마무리"
        )
    elif tone == "📔 혼잣말 일기체":
        tone_inst = (
            "독자에게 설명하는 글이 아니라, '나 자신에게 오늘의 경험을 기록하듯' 쓰는 "
            "일기·회고 문체로 작성할 것.\n\n"
            "【시점과 태도】\n"
            "  · 1인칭('나는', '내가') 중심으로, 혼잣말하듯 담담하게 적는다.\n"
            "  · 독자를 부르거나('여러분', '~하세요') 광고하듯 권하지 않는다.\n"
            "  · 그 순간의 생각·감정·망설임을 솔직하게 적는다 "
            "('왜 그랬을까', '괜히 뭉클했다', '이건 좀 아쉬웠다').\n\n"
            "【말투와 어미】\n"
            "  · 과거 회상형 서술체: '~했다', '~였다', '~더라', '~했던 것 같다'.\n"
            "  · 차분하고 사색적인 톤. 과한 이모지·감탄사·유행어는 쓰지 않는다.\n"
            "  · 이모지는 꼭 필요할 때 아주 드물게만.\n\n"
            "【문장과 흐름】\n"
            "  · 시간 순서(그날의 흐름)대로 자연스럽게 이어간다.\n"
            "  · 사실 나열보다 '그때 무엇을 느꼈는지'에 무게를 둔다.\n"
            "  · 소제목(##)은 그날의 장면·순간을 떠올리는 느낌으로 (예: '도착하던 순간', '다시 떠올려보면').\n\n"
            "【마무리】\n"
            "  · 교훈이나 추천으로 끝맺지 말고, 오늘을 돌아보는 혼잣말로 조용히 마무리한다 "
            "('오늘은 이걸로 충분했다', '다음에 또 오게 될까').\n"
            "  · 해시태그는 과하지 않게, 기록용 메모처럼 담담하게 단다."
        )
    else:
        tone_inst = tone

    base = (
        "한국어로 네이버 블로그 포스팅을 작성해주세요.\n"
        f"- 문체: {tone_inst}\n"
        "- 소제목(##) 2~3개로 구조화, 해시태그 10개로 마무리\n"
        f"- 분량: 반드시 {length_map.get(length, length)} 분량으로 작성\n"
    )

    # 사진 배치 지시: 사진 위치를 '자리표시자'로 본문 흐름에 맞게 넣게 함
    n_photos = len(img_descs)
    if n_photos > 0:
        base += (
            f"- 첨부 사진이 {n_photos}장 있습니다. 각 사진 내용을 본문에 자연스럽게 녹이고,\n"
            "  사진이 들어갈 위치에 반드시 '[[PHOTO:번호]]' 형식의 자리표시자를 "
            "그 사진을 설명하는 문단 바로 뒤에 한 줄로 넣으세요.\n"
            f"  (예: 첫 사진 자리에는 [[PHOTO:1]], 둘째 사진 자리에는 [[PHOTO:2]] … "
            f"{n_photos}번까지)\n"
            "  · 자리표시자는 반드시 한 줄에 단독으로 두고, 1번부터 순서대로 모두 사용하세요.\n"
            "  · '(사진1)', '사진 1 참고' 같은 다른 표기는 쓰지 말고 오직 [[PHOTO:번호]]만 쓰세요.\n"
            "  · 사진을 글 맨 위에 몰아넣지 말고, 관련 내용이 나오는 흐름에 맞춰 분산 배치하세요.\n"
        )
    else:
        base += "- 사진은 없습니다. 텍스트 정보만으로 작성하세요.\n"

    # 웹에서 수집한 배경 정보를 참고 자료로 주입 (내용 보강용)
    if web_reference and web_reference.strip():
        base += (
            "\n[웹에서 찾은 참고 자료]\n"
            f"{web_reference}\n"
            "위 참고 자료의 사실 정보(위치·역사·특징·배경 등)를 본문에 자연스럽게 녹여 "
            "내용을 더 풍부하고 신뢰감 있게 작성하세요. 단, 참고 자료에 없는 가격·영업시간 "
            "같은 구체 수치는 임의로 지어내지 말고, 확실하지 않으면 일반적인 표현으로 쓰세요.\n"
        )
    if style == "🍽️ 맛집":
        return base + (
            f"\n[맛집 정보]\n가게명: {title} / 위치: {location} / 특징: {keywords}\n"
            f"추가 메모: {extra}\n[첨부 사진]\n{photos_text}\n\n"
            "제목(#)부터 시작한 뒤, 아래 9단계 순서를 '그대로' 따라 각 단계를 "
            "소제목(##)으로 나눠 작성하세요. 각 단계 제목에 어울리는 이모지를 하나씩 붙이세요.\n"
            "1) 인트로 — 방문 계기나 첫인상으로 자연스럽게 시작\n"
            "2) 가게 정보 — 상호명·주소·영업시간·주차장 여부를 리스트로 정리 "
            "(입력/참고자료에 없는 항목은 '확인 필요' 또는 일반적 표현으로, 지어내지 말 것)\n"
            "3) 가게 외관 & 위치 — 찾아가는 길, 건물 외관 느낌\n"
            "4) 웨이팅 — 대기 여부·대기 시간·대기 팁 (해당 없으면 '웨이팅 없이 입장' 식으로)\n"
            "5) 내부 분위기 — 인테리어, 좌석, 테이블 간격, 전체 무드\n"
            "6) 메뉴 소개 — 대표 메뉴와 가격대 전반 소개\n"
            "7) 기본 반찬 — 밑반찬/기본 제공 구성과 맛\n"
            "8) 주문한 메뉴 상세 — 내가 주문한 메뉴를 하나씩 설명하고 맛을 구체적으로 평가\n"
            "9) 마무리 — 총평과 추천 포인트로 마무리\n"
            "마지막에 해시태그 10개를 답니다. "
            "입력 정보가 부족한 단계는 억지로 늘리지 말고 자연스럽게 짧게 쓰되, "
            "단계 순서와 구성은 반드시 지키세요."
        )
    elif style == "✈️ 여행":
        return base + (
            f"\n[여행 정보]\n여행지: {title} / 위치: {location} / 특징: {keywords}\n"
            f"추가 메모: {extra}\n[첨부 사진]\n{photos_text}\n\n"
            "제목(#)부터 시작해서 소개→방문후기→여행팁 순서로 작성해주세요."
        )
    else:
        return base + (
            f"\n[제품 정보]\n제품명: {title} / 특징: {keywords}\n"
            f"추가 메모: {extra}\n[첨부 사진]\n{photos_text}\n\n"
            "제목(#)부터 시작해서 구매계기→사용후기→장단점(✅❌)→총평 순서로 작성해주세요."
        )


def analyze_images(images):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    results = []
    for i, img in enumerate(images):
        if not api_key:
            w, h = img.size
            results.append(f"사진{i+1}({w}x{h}px): 색감이 선명하고 구도가 좋은 사진입니다.")
            continue
        try:
            import google.genai as genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_text("이 사진을 블로그용으로 한국어 200자 이내로 생생하게 묘사해주세요."),
                    types.Part.from_image(img),
                ]
            )
            results.append(resp.text.strip())
        except Exception as e:
            w, h = img.size
            results.append(f"사진{i+1}({w}x{h}px) 분석 실패: {e}")
    return results


def stream_blog(prompt: str):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        key = ("🍽️ 맛집" if "가게명" in prompt
               else ("✈️ 여행" if "여행지" in prompt else "📦 제품"))
        demo = DEMO_BLOGS[key]
        for i in range(0, len(demo), 15):
            yield demo[i:i+15]
            time.sleep(0.02)
        return
    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        for chunk in client.models.generate_content_stream(
            model=GEMINI_MODEL, contents=prompt
        ):
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"\n⚠️ 오류: {e}"


def img_to_base64(img: Image.Image, max_width=800) -> str:
    w, h = img.size
    if w > max_width:
        img = img.resize((max_width, int(h * max_width / w)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _single_img_html(img: Image.Image) -> str:
    """사진 1장을 중앙 정렬된 블록 이미지 HTML로."""
    return (
        '<div style="margin:18px 0;text-align:center;">'
        f'<img src="{img_to_base64(img)}" '
        'style="width:100%;max-width:640px;border-radius:10px;" /></div>'
    )


def strip_photo_placeholders(text: str) -> str:
    """본문 미리보기/텍스트 저장용: 사진 자리표시자를 보기 좋은 표시로 정리."""
    import re
    # 먼저 (사진1)/(사진 1) 등 → 중립 토큰으로 (이미 📷 붙은 건 제외)
    text = re.sub(r"\(?\s*사진\s*(\d+)\s*\)?", r"[[PHOTO:\1]]", text)
    # [[PHOTO:1]] → (📷 사진 1) 로 최종 변환 (한 번만)
    text = re.sub(r"\[\[PHOTO:(\d+)\]\]", r"(📷 사진 \1)", text)
    return text


def build_html(blog_text: str, images: list, title: str) -> str:
    import re

    if not images:
        body = markdown.markdown(blog_text, extensions=["nl2br"])
        return _wrap_html(body, title)

    n = len(images)
    # 1) 본문에 [[PHOTO:n]] 자리표시자가 있으면 그 자리에 해당 사진을 배치
    # 슬롯 토큰은 markdown이 굵게/기울임으로 오인하지 않도록 밑줄·별표 없이 구성
    def _slot(idx):
        return f"\n\nIMGSLOTXX{idx}XX\n\n"

    used = set()
    def _repl(m):
        idx = int(m.group(1))
        if 1 <= idx <= n:
            used.add(idx)
            return _slot(idx)
        return ""  # 범위 밖 번호는 제거
    text_with_slots = re.sub(r"\[\[PHOTO:(\d+)\]\]", _repl, blog_text)
    # AI가 혹시 (사진1) 식으로 쓴 경우도 자리표시자로 흡수
    def _repl2(m):
        idx = int(m.group(1))
        if 1 <= idx <= n and idx not in used:
            used.add(idx)
            return _slot(idx)
        return m.group(0)
    text_with_slots = re.sub(r"\(?\s*사진\s*(\d+)\s*\)?", _repl2, text_with_slots)

    body = markdown.markdown(text_with_slots, extensions=["nl2br"])

    # 슬롯 토큰(markdown이 <p>로 감쌀 수 있음)을 실제 이미지로 치환
    for i in range(1, n + 1):
        token = f"IMGSLOTXX{i}XX"
        img_html = _single_img_html(images[i - 1])
        body = body.replace(f"<p>{token}</p>", img_html).replace(token, img_html)

    # 2) 자리표시자로 못 들어간 사진은 소제목(<h2>) 사이에 고르게 분산 배치
    leftover = [images[i - 1] for i in range(1, n + 1) if i not in used]
    if leftover:
        h2_positions = [m.start() for m in re.finditer(r"<h2[ >]", body)]
        if h2_positions:
            # 각 남은 사진을 서로 다른 h2 앞에 분산 삽입 (뒤에서부터 삽입해 위치 보존)
            insert_points = []
            for k, img in enumerate(leftover):
                pos_idx = h2_positions[(k + 1) % len(h2_positions)] if len(h2_positions) > 1 else h2_positions[0]
                insert_points.append((pos_idx, img))
            for pos_idx, img in sorted(insert_points, key=lambda x: x[0], reverse=True):
                body = body[:pos_idx] + _single_img_html(img) + body[pos_idx:]
        else:
            # 소제목이 없으면 본문 끝에 차례로
            for img in leftover:
                body += _single_img_html(img)

    return _wrap_html(body, title)


def _wrap_html(body: str, title: str) -> str:
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<title>{title}</title>
<style>
body{{font-family:'맑은 고딕',sans-serif;font-size:16px;line-height:1.9;
     color:#333;max-width:680px;margin:0 auto;padding:24px 16px;}}
h1{{font-size:1.6rem;font-weight:800;color:#111;}}
h2{{font-size:1.2rem;font-weight:700;border-left:4px solid #03C75A;
    padding-left:10px;color:#222;margin:1.4rem 0 .6rem;}}
blockquote{{background:#f0fdf4;border-left:4px solid #03C75A;
            padding:10px 16px;border-radius:6px;color:#555;}}
hr{{border:none;border-top:1px solid #eee;margin:16px 0;}}
</style></head><body>{body}
<p style="margin-top:32px;font-size:.8rem;color:#aaa;text-align:center;">
✍️ AI 블로그 작성기</p></body></html>"""


# ── 데모 텍스트 ────────────────────────────────────────────────────────────────
DEMO_BLOGS = {
    "🍽️ 맛집": """# 을지로 레전드 🍺 노가리골목 노포 맛집 솔직 후기

> 💡 **데모 모드** — 사이드바에 Gemini API 키를 넣으면 실제 AI가 작성합니다.

을지로3가역에서 나오면 고소한 냄새를 따라가다 발견한 진짜배기 노포예요 😆

## 🍽️ 메뉴 & 맛

노가리 한 마리가 단돈 천 원대! 짭조름하고 고소한 맛이 맥주랑 환상 케미예요.

## ✨ 분위기

낡은 나무 테이블, 형광등, 플라스틱 의자... 이게 진짜 을지로죠.

## 📊 총평

⭐⭐⭐⭐⭐ 가성비·맛·분위기 삼박자 완벽! 퇴근 후 한 잔 자리로 강추 🙌

---
#을지로맛집 #노가리골목 #을지로노포 #직장인회식 #서울맛집 #을지로감성 #가성비맛집 #노가리 #맥주안주 #퇴근후한잔""",

    "✈️ 여행": """# 제주 협재해수욕장 🌊 에메랄드 바다에 완전히 반해버렸어요

> 💡 **데모 모드** — 사이드바에 Gemini API 키를 넣으면 실제 AI가 작성합니다.

## 🌅 왜 협재인가요?

하얀 모래사장 + 에메랄드빛 바다 + 비양도 뷰. 이 조합이면 설명 끝이죠 👨‍👩‍👧

## 📸 방문 후기

오전 9시에 도착했는데 이미 사람이 꽤 있었어요. 일찍 가는 게 국룰!

## 💡 꿀팁

- 오전 일찍 or 해질 무렵 방문 (일몰이 진짜 장관)

---
#제주여행 #협재해수욕장 #제주바다 #제주핫플 #여름여행 #국내여행 #에메랄드바다 #제주추천 #협재카페 #제주감성""",

    "📦 제품": """# 다이슨 V15 무선청소기 6개월 후기 💨 솔직하게 다 말해드릴게요

> 💡 **데모 모드** — 사이드바에 Gemini API 키를 넣으면 실제 AI가 작성합니다.

## 🔍 실사용 후기

레이저 먼지 감지 기능이 진짜 신세계예요 😱

## ✅ 장점 & ❌ 단점

✅ 흡입력 강력 / 디자인 예쁨
❌ 가격 부담 / 강력 모드 배터리 짧음

## 💰 총평

비싸지만 후회 없는 선택. 반려동물 털·알레르기 있는 분께 강력 추천!

---
#다이슨V15 #무선청소기추천 #다이슨후기 #청소기리뷰 #생활가전 #가전추천 #청소기비교 #다이슨 #무선청소기 #리뷰"""
}


# ══════════════════════════════════════════════════════════════════════════════
# session_state 초기화
# ══════════════════════════════════════════════════════════════════════════════
for k, v in {
    "blog_result": None,
    "blog_html":   None,
    "blog_title":  "",
    "blog_style":  "",
    "view_hist":   None,   # 기록 조회 중인 항목 id
    "prefill":     None,   # 기록에서 '다시 수정하기'로 불러온 입력값
    "blog_inputs": None,   # 방금 생성한 결과의 입력 요약
    "history":     [],     # 작성 기록 (접속자별 세션 보관)
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# 사이드바: API 키
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔑 Gemini API 키")
    key = st.text_input("API 키 (없으면 데모 모드)", type="password", placeholder="AIza...")
    if key:
        os.environ["GEMINI_API_KEY"] = key
        st.success("✅ 설정됨")
        st.caption(f"모델: {GEMINI_MODEL}")
    else:
        st.info("키 없이도 데모 블로그를 볼 수 있어요.\n\n"
                "[무료 발급 →](https://aistudio.google.com/app/apikey)")

    st.divider()
    st.markdown("### 🔎 웹 검색 보강 (선택)")
    st.caption("키를 넣으면 네이버·구글 검색 결과까지 글에 반영됩니다. "
               "없으면 위키백과·DuckDuckGo만 사용합니다.")

    with st.expander("네이버 검색 API 키"):
        nid = st.text_input("Client ID", type="password", key="naver_id",
                            placeholder="네이버 개발자센터 발급")
        nsec = st.text_input("Client Secret", type="password", key="naver_secret")
        if nid and nsec:
            os.environ["NAVER_CLIENT_ID"] = nid
            os.environ["NAVER_CLIENT_SECRET"] = nsec
            st.success("✅ 네이버 검색 사용")
        st.caption("[발급 →](https://developers.naver.com/apps/#/register)")

    with st.expander("구글 검색 API 키"):
        gkey = st.text_input("API Key", type="password", key="google_key",
                             placeholder="AIza...")
        gcx = st.text_input("검색엔진 ID (cx)", type="password", key="google_cx")
        if gkey and gcx:
            os.environ["GOOGLE_CSE_KEY"] = gkey
            os.environ["GOOGLE_CSE_CX"] = gcx
            st.success("✅ 구글 검색 사용")
        st.caption("[키 발급 →](https://developers.google.com/custom-search/v1/introduction) · "
                   "[검색엔진(cx) 만들기 →](https://programmablesearchengine.google.com/)")


# ══════════════════════════════════════════════════════════════════════════════
# 메인 레이아웃: 왼쪽(입력) | 오른쪽(기록)
# ══════════════════════════════════════════════════════════════════════════════
col_main, col_hist = st.columns([3, 1], gap="large")

# ────────────────────────────────────────────────────────────────────────────
# 왼쪽: 입력 + 결과
# ────────────────────────────────────────────────────────────────────────────
with col_main:
    st.title("✍️ AI 블로그 작성기")
    st.caption("사진과 간단한 정보만 입력하면 네이버 스타일 블로그를 자동으로 써드려요")
    st.divider()

    # 기록 조회 모드
    if st.session_state.view_hist:
        hist = load_history()
        item = next((h for h in hist if h["id"] == st.session_state.view_hist), None)
        if item:
            st.markdown(f"### 📖 {item['title']}")
            st.caption(f"{item['style']} · {item['date']} · {item['chars']:,}자")

            # 내가 입력했던 내용(요청)을 함께 보여주기 → 결과와 비교하며 수정 포인트 찾기
            inp = item.get("inputs") or {}
            if inp:
                with st.expander("📝 이때 내가 입력한 내용 (요청 기록)", expanded=True):
                    rows = [
                        ("스타일",   inp.get("style", "")),
                        ("제목",     inp.get("title", "")),
                        ("위치",     inp.get("location", "")),
                        ("키워드/특징", inp.get("keywords", "")),
                        ("추가 메모", inp.get("extra", "")),
                        ("문체",     inp.get("tone", "")),
                        ("글자 수",  inp.get("length", "")),
                        ("웹 보강",  "사용" if inp.get("use_web") else "미사용"),
                        ("사진 수",  f"{inp.get('photo_count', 0)}장"),
                    ]
                    for label, val in rows:
                        if val not in ("", None):
                            st.markdown(f"- **{label}**: {val}")
                    if inp.get("web_reference"):
                        with st.expander("🌐 그때 반영한 웹 참고 정보"):
                            st.markdown(inp["web_reference"])
            else:
                st.caption("ℹ️ 이 기록에는 입력 내용이 저장돼 있지 않아요(이전 버전에서 생성됨).")

            st.divider()
            st.markdown("#### 📄 생성된 블로그")
            _disp = strip_photo_placeholders(item["content"])
            st.markdown(_disp)
            st.divider()
            fname = item["title"][:10]

            # 이 입력을 그대로 불러와 수정·재생성
            if inp:
                if st.button("✏️ 이 입력으로 다시 수정하기", type="primary",
                             key=f"edit_{item['id']}"):
                    st.session_state.prefill = inp          # 입력폼 자동 채움용
                    st.session_state.view_hist = None
                    st.session_state.blog_result = None
                    st.rerun()

            b1, b2, b3 = st.columns(3)
            with b1:
                st.download_button("💾 TXT", _disp.encode("utf-8"),
                                   f"blog_{fname}.txt", key=f"htxt_{item['id']}")
            with b2:
                st.download_button("📄 MD",  _disp.encode("utf-8"),
                                   f"blog_{fname}.md",  key=f"hmd_{item['id']}")
            with b3:
                st.download_button("🌐 HTML", item["html"].encode("utf-8"),
                                   f"blog_{fname}.html", key=f"hhtml_{item['id']}")
            if st.button("← 돌아가기"):
                st.session_state.view_hist = None
                st.rerun()
        st.stop()

    # ── 스타일 선택 ──────────────────────────────────────────────────────────
    # 기록에서 '다시 수정하기'로 불러온 입력값(있으면 폼 기본값으로 사용)
    pf = st.session_state.get("prefill") or {}
    if pf:
        st.info("✏️ 지난 기록의 입력을 불러왔어요. 아래에서 고친 뒤 다시 생성하세요.")

    _style_opts = ["🍽️ 맛집", "✈️ 여행", "📦 제품"]
    _style_idx = _style_opts.index(pf["style"]) if pf.get("style") in _style_opts else 0
    style = st.radio("블로그 스타일", _style_opts, horizontal=True, index=_style_idx)
    st.divider()

    # ── 사진 업로드 ──────────────────────────────────────────────────────────
    st.markdown("**📷 사진 업로드** (최대 10장, 선택)")
    uploaded_files = st.file_uploader(
        "사진 선택", type=["jpg","jpeg","png","webp"],
        accept_multiple_files=True, label_visibility="collapsed",
    )
    img_objects = []
    if uploaded_files:
        img_objects = [Image.open(f) for f in uploaded_files]
        n = len(img_objects)
        cols_per_row = 1 if n == 1 else (2 if n == 2 else 3)
        for row_start in range(0, n, cols_per_row):
            row_imgs = img_objects[row_start:row_start+cols_per_row]
            cols = st.columns(cols_per_row)
            for col, img in zip(cols, row_imgs):
                w, h = img.size
                img_show = img.crop((0, 0, w, min(int(w*1.2), h))) if h > w*1.5 else img
                col.image(img_show, use_container_width=True)
        st.caption(f"✅ {n}장 선택됨")
    else:
        st.caption("사진 없이도 블로그를 생성할 수 있어요")

    st.divider()

    # ── 옵션 + 정보 입력 ──────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    _tone_opts = [
        "친근하고 감성적인",
        "전문적이고 정보 중심",
        "유쾌하고 재미있는",
        "담백하고 솔직한",
        "📔 혼잣말 일기체",
        "🌙 데일리 문 스타일",
    ]
    _len_opts = ["짧게 (500자 내외)","보통 (800~1000자)","길게 (1500자 이상)","매우 길게 (2000자+)"]
    _tone_idx = _tone_opts.index(pf["tone"]) if pf.get("tone") in _tone_opts else 0
    _len_idx  = _len_opts.index(pf["length"]) if pf.get("length") in _len_opts else 1
    with c1:
        tone = st.selectbox("✏️ 문체", _tone_opts, index=_tone_idx)
    with c2:
        length = st.selectbox("📏 글자 수", _len_opts, index=_len_idx)

    # prefill의 제목/위치는 스타일이 같을 때만 채움(스타일 바꾸면 혼동 방지)
    _pf_same_style = (pf.get("style") == style)
    _pf_title    = pf.get("title", "")    if _pf_same_style else ""
    _pf_location = pf.get("location", "") if _pf_same_style else ""

    if style == "🍽️ 맛집":
        title    = st.text_input("가게명 *", value=_pf_title, placeholder="예: 을지로 OO노가리집")
        location = st.text_input("위치",     value=_pf_location, placeholder="예: 서울 중구 을지로")
    elif style == "✈️ 여행":
        title    = st.text_input("여행지/장소명 *", value=_pf_title, placeholder="예: 제주도 협재해수욕장")
        location = st.text_input("위치",            value=_pf_location, placeholder="예: 제주특별자치도")
    else:
        title    = st.text_input("제품명 *", value=_pf_title, placeholder="예: 다이슨 V15 무선청소기")
        location = ""

    keywords = st.text_input("키워드/특징", value=pf.get("keywords", ""),
                             placeholder="예: 가성비, 분위기 좋음, 웨이팅")
    extra    = st.text_area("추가 메모", value=pf.get("extra", ""),
                            placeholder="기억에 남는 점 등 자유롭게", height=80)

    use_web = st.toggle(
        "🌐 웹에서 정보 보강 (제목·요약 기반)",
        value=bool(pf.get("use_web", True)),
        help="제목과 위치·키워드로 웹(위키백과 등)에서 관련 배경 정보를 찾아 "
             "본문을 더 풍부하게 채웁니다. 키가 필요 없는 무료 기능입니다.",
    )

    st.divider()

    # ── 생성 버튼 ─────────────────────────────────────────────────────────────
    if st.button("🚀 블로그 생성하기"):
        if not title.strip():
            st.error("⚠️ 필수 항목(*)을 입력해주세요!")
            st.stop()

        img_descs = []
        if img_objects:
            with st.spinner(f"🔍 사진 {len(img_objects)}장 분석 중..."):
                img_descs = analyze_images(img_objects)
            st.success(f"📸 {len(img_objects)}장 분석 완료")

        # 웹에서 배경 정보 수집 (제목 + 요약 기반)
        web_reference = ""
        if use_web:
            with st.spinner("🌐 웹에서 관련 정보 수집 중..."):
                try:
                    from modules.web_research import research
                    rr = research(title, keywords=keywords, location=location,
                                  extra=extra, style=style)
                    web_reference = rr.to_reference_text()
                except Exception as e:
                    web_reference = ""
            if web_reference:
                st.success(f"🌐 웹 정보 {len(rr.snippets)}건 반영")
                with st.expander("🔎 참고한 웹 정보 보기"):
                    st.markdown(web_reference)
                    if rr.sources:
                        st.caption("출처: " + " · ".join(rr.sources[:4]))
            else:
                st.info("🌐 관련 웹 정보를 찾지 못해, 입력하신 내용만으로 작성합니다.")

        prompt = build_prompt(style, title, location, keywords, extra, tone, img_descs, length,
                              web_reference=web_reference)
        st.markdown("---")
        st.markdown("#### ✍️ 생성 중...")
        result = st.write_stream(stream_blog(prompt))

        html_content = build_html(result, img_objects, title)

        # session_state 저장
        st.session_state.blog_result = result
        st.session_state.blog_html   = html_content
        st.session_state.blog_title  = title
        st.session_state.blog_style  = style

        # 내가 입력한 내용(요청)을 기록에 함께 저장
        inputs = {
            "style":    style,
            "title":    title,
            "location": location,
            "keywords": keywords,
            "extra":    extra,
            "tone":     tone,
            "length":   length,
            "use_web":  use_web,
            "web_reference": web_reference,
            "photo_count":   len(img_objects),
        }
        st.session_state.blog_inputs = inputs   # 결과 화면에서 입력 요약 표시용
        add_to_history(title, style, result, html_content, inputs=inputs)
        st.session_state.prefill = None   # 불러온 입력값은 1회만 사용하고 비움
        st.rerun()

    # ── 결과 표시 ─────────────────────────────────────────────────────────────
    if st.session_state.blog_result:
        result       = st.session_state.blog_result
        display_result = strip_photo_placeholders(result)  # 화면·텍스트용(자리표시자 정리)
        html_content = st.session_state.blog_html
        fname        = st.session_state.blog_title[:10]

        st.markdown("---")

        # 이 결과를 만든 '내 입력'을 함께 보여주기 (결과와 비교하며 수정)
        bi = st.session_state.get("blog_inputs") or {}
        if bi:
            with st.expander("📝 이 글을 만든 내 입력 보기", expanded=False):
                summary = []
                for label, k in [("제목", "title"), ("위치", "location"),
                                 ("키워드/특징", "keywords"), ("추가 메모", "extra"),
                                 ("문체", "tone"), ("글자 수", "length")]:
                    v = bi.get(k)
                    if v:
                        summary.append(f"- **{label}**: {v}")
                summary.append(f"- **웹 보강**: {'사용' if bi.get('use_web') else '미사용'}")
                st.markdown("\n".join(summary))

        st.markdown("#### 📄 생성된 블로그")
        st.markdown(display_result)
        st.caption("💡 사진은 HTML 저장 파일에서 글 흐름에 맞춰 자동 배치됩니다.")

        chars = len(display_result.replace("\n","").replace(" ",""))
        st.caption(f"📊 총 {chars:,}자 (목표: {length})")

        if bi:
            if st.button("✏️ 입력 수정해서 다시 생성", key="edit_current"):
                st.session_state.prefill = bi
                st.session_state.blog_result = None
                st.session_state.blog_html = None
                st.rerun()
        st.divider()

        st.markdown("#### 📤 저장 & 네이버 블로그 붙여넣기")
        b1, b2, b3 = st.columns(3)
        with b1:
            st.download_button("💾 TXT 저장", display_result.encode("utf-8"),
                               f"blog_{fname}.txt", key="dl_txt")
        with b2:
            st.download_button("📄 MD 저장", display_result.encode("utf-8"),
                               f"blog_{fname}.md", key="dl_md")
        with b3:
            st.download_button("🌐 HTML 저장 (사진 포함)", html_content.encode("utf-8"),
                               f"blog_{fname}.html", key="dl_html")

        st.info(
            "**📋 네이버 블로그 붙여넣기**\n\n"
            "1. HTML 저장 → 크롬/엣지로 열기\n"
            "2. **Ctrl+A** → **Ctrl+C**\n"
            "3. 네이버 블로그 글쓰기 → **Ctrl+V**\n"
            "4. 사진 + 글 한번에 붙여넣기 완료 ✅"
        )

        if st.button("🔄 새 블로그 작성"):
            st.session_state.blog_result = None
            st.session_state.blog_html   = None
            st.rerun()


# ────────────────────────────────────────────────────────────────────────────
# 오른쪽: 작성 기록 패널
# ────────────────────────────────────────────────────────────────────────────
with col_hist:
    history = load_history()

    st.markdown("### 📋 작성 기록")
    st.caption(f"총 {len(history)}개")

    if not history:
        st.info("아직 작성된 블로그가 없어요.\n첫 번째 블로그를 만들어보세요!")
    else:
        # 전체 삭제 버튼
        if st.button("🗑️ 전체 삭제", type="secondary"):
            save_history([])
            st.rerun()

        st.divider()

        for item in history:
            # 스타일 이모지
            style_emoji = {"🍽️ 맛집": "🍽️", "✈️ 여행": "✈️", "📦 제품": "📦"}.get(item["style"], "📝")
            preview = item["content"][:80].replace("\n", " ").replace("#", "").strip()

            # 카드 형태로 표시
            with st.container():
                st.markdown(
                    f"""<div class="hist-card">
                    <div class="hist-title">{style_emoji} {item['title']}</div>
                    <div class="hist-meta">{item['date']} · {item['chars']:,}자</div>
                    <div class="hist-preview">{preview}...</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("보기", key=f"view_{item['id']}", use_container_width=True):
                        st.session_state.view_hist = item["id"]
                        st.session_state.blog_result = None
                        st.rerun()
                with c2:
                    st.download_button(
                        "HTML", item["html"].encode("utf-8"),
                        f"blog_{item['title'][:8]}.html",
                        key=f"dh_{item['id']}", use_container_width=True,
                    )

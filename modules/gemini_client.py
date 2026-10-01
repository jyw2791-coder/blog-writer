"""
Google Gemini API 연동 모듈
- 이미지 분석 (Vision)
- 블로그 텍스트 생성
- API 키 없을 때 데모 모드 지원
"""

import os
import time
from PIL import Image


def _is_api_available() -> bool:
    """Gemini API 사용 가능 여부를 확인합니다."""
    try:
        import google.generativeai as genai  # noqa
        api_key = os.environ.get("GEMINI_API_KEY", "")
        return bool(api_key and api_key.strip())
    except ImportError:
        return False


def analyze_image(image: Image.Image) -> str:
    """업로드된 이미지를 Gemini Vision으로 분석합니다."""
    if not _is_api_available():
        return _demo_image_description(image)

    try:
        import google.generativeai as genai

        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = """이 사진을 블로그 포스팅에 활용할 수 있도록 자세히 묘사해주세요.

다음 항목들을 포함하여 한국어로 설명해주세요:
1. 사진에 보이는 주요 피사체 (음식, 장소, 제품 등)
2. 색감, 분위기, 구도
3. 눈에 띄는 특징이나 디테일
4. 블로그 독자에게 어필할 수 있는 매력 포인트

간결하되 생생하게 묘사해주세요 (200자 내외)."""

        response = model.generate_content([prompt, image])
        return response.text.strip()

    except Exception as e:
        return f"[이미지 분석 실패: {str(e)}] 사용자가 업로드한 사진이 포함되어 있습니다."


def generate_blog(prompt: str, stream: bool = True):
    """Gemini API로 블로그 글을 스트리밍 생성합니다."""
    if not _is_api_available():
        demo_text = _get_demo_blog_text(prompt)
        for chunk in _fake_stream(demo_text):
            yield chunk
        return

    try:
        import google.generativeai as genai

        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.85,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )

        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        yield f"\n\n⚠️ 블로그 생성 중 오류가 발생했습니다: {str(e)}\n\nAPI 키를 확인하거나 잠시 후 다시 시도해주세요."


def _fake_stream(text: str):
    """데모 모드에서 스트리밍 효과를 위해 텍스트를 청크로 분할합니다."""
    chunk_size = 20
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        time.sleep(0.025)


def _demo_image_description(image: Image.Image) -> str:
    """API 키 없을 때 기본 이미지 설명을 반환합니다."""
    width, height = image.size
    return (
        f"업로드된 사진 ({width}x{height}px): "
        "선명하고 생동감 있는 사진으로, 블로그 독자들의 시선을 사로잡을 수 있는 매력적인 구도입니다. "
        "색감이 자연스럽고 피사체가 잘 부각되어 있어 포스팅의 완성도를 높여줄 것입니다."
    )


def _get_demo_blog_text(prompt: str) -> str:
    """API 키 없을 때 데모용 블로그 텍스트를 반환합니다."""
    if "가게명" in prompt or "맛집" in prompt:
        return _demo_restaurant_blog()
    elif "여행지" in prompt or "여행" in prompt:
        return _demo_travel_blog()
    else:
        return _demo_product_blog()


def _demo_restaurant_blog() -> str:
    return """# 을지로 감성 뿜뿜 🍺 노포 감성 가득한 노가리 맛집 솔직 후기

> ⚠️ **데모 모드**: 사이드바에서 Gemini API 키를 입력하면 실제 AI가 맞춤형 블로그를 생성합니다.

안녕하세요 여러분! 오늘은 을지로 골목 구석구석을 탐방하다 발견한 완전 찐 노포 맛집을 소개해드릴게요 🙌

## 🗺️ 첫인상 & 찾아가는 길

을지로3가역에서 내려서 골목골목 걷다 보면 어느 순간 시끌벅적한 소리와 함께 노란 조명이 반겨주는 곳이 나타나요. 처음엔 '여기가 맞나?' 싶었는데, 이미 자리가 꽉 찬 걸 보고 '아, 이곳이 맞구나' 확신했어요 😂

## 🍽️ 메뉴 & 맛 상세 리뷰

메뉴판을 보는 순간 가성비에 눈이 번쩍! 노가리 한 마리에 단돈 천 원대라니, 서울 물가가 맞나 싶었어요.

- 🐟 **노가리 구이**: 짭조름하면서도 고소한 맛이 맥주랑 환상 궁합
- 🍺 **생맥주**: 시원하고 거품이 풍성해서 목 넘김이 최고
- 🥜 **땅콩 안주**: 무한 리필 가능 (진짜 레전드)

## ✨ 분위기 & 서비스

오래된 나무 테이블, 형광등 불빛, 플라스틱 의자... 인스타 감성과는 거리가 멀지만 이게 을지로 노포의 진짜 매력 아닐까요? 사장님과 이모님들 모두 친절하시고 테이블 회전이 빨라서 웨이팅이 있어도 금방 들어갈 수 있어요.

## 📊 총평

⭐⭐⭐⭐⭐ **5점 만점에 5점!**

가성비, 맛, 분위기 삼박자가 딱 맞는 을지로 레전드 맛집이에요. 직장인 회식, 친구들과의 가벼운 한 잔 자리로 강력 추천합니다!

---
#을지로맛집 #노가리골목 #을지로노포 #직장인회식 #서울맛집 #을지로감성 #가성비맛집 #노가리 #맥주맛집 #퇴근후한잔"""


def _demo_travel_blog() -> str:
    return """# 제주 협재해수욕장 🌊 에메랄드빛 바다에 완전히 반해버렸어요

> ⚠️ **데모 모드**: 사이드바에서 Gemini API 키를 입력하면 실제 AI가 맞춤형 블로그를 생성합니다.

안녕하세요! 이번 여름 제주 여행의 하이라이트였던 협재해수욕장 방문기를 들고 왔어요 ✈️

## 🌅 협재해수욕장, 왜 유명한가요?

협재는 제주 서쪽에 위치한 해수욕장으로, 하얀 모래사장과 에메랄드빛 바다가 만나는 곳이에요. 앞에는 비양도가 떠 있어서 풍경이 한 폭의 그림 같아요. 물이 얕고 잔잔해서 아이들도 안전하게 즐길 수 있다는 게 큰 장점이에요 👨‍👩‍👧

## 📸 실제 방문 후기

오전 9시에 도착했는데도 이미 여행객들이 꽤 있더라고요. 성수기에는 주차가 어렵다고 하니 일찍 가는 걸 추천해요!

바다에 발을 담그는 순간 '아, 이래서 제주 오는구나' 싶었어요. 물이 엄청 맑고 시원해서 더위가 싹 날아가는 느낌이었어요.

## 💡 협재 여행 꿀팁

- ⏰ **방문 시간**: 오전 일찍 또는 오후 늦게 (혼잡 피하기)
- 🅿️ **주차**: 공영주차장 이용 (성수기 만차 주의)
- 🌄 **일몰**: 해질 무렵 풍경이 정말 환상적이에요

협재해수욕장은 제주에 간다면 꼭 들러야 하는 필수 코스예요 🥹

---
#제주여행 #협재해수욕장 #제주바다 #제주핫플 #여름여행 #국내여행 #제주도여행 #협재 #에메랄드바다 #제주추천"""


def _demo_product_blog() -> str:
    return """# 다이슨 V15 무선청소기 6개월 사용 후기 💨 진짜 살 만한가요?

> ⚠️ **데모 모드**: 사이드바에서 Gemini API 키를 입력하면 실제 AI가 맞춤형 블로그를 생성합니다.

안녕하세요! 오늘은 구매 고민을 정말 오래 했던 다이슨 V15 무선청소기 6개월 사용 후기를 솔직하게 써볼게요 👀

## 🛒 구매 계기 & 첫인상

매번 유선 청소기 코드와 씨름하다 지쳐서 무선 청소기로 넘어가기로 결심! 박스 오픈하는 순간부터 뭔가 다르다는 느낌, 역시 다이슨이구나 싶었죠.

## 🔍 상세 스펙 & 실사용 후기

레이저 먼지 감지 기능 덕분에 눈에 안 보이던 먼지까지 잡아냈어요. 필터 청소할 때 쌓인 먼지 양 보고 깜짝 놀랐답니다 😱

## ✅ 장점 & ❌ 단점

**✅ 장점**
- 흡입력이 정말 강력함 (레이저 먼지 감지 기능 짱)
- 거치대 디자인이 예쁨
- 다양한 헤드로 소파, 침대, 차량 청소까지 가능

**❌ 단점**
- 가격이 너무 비쌈
- 강력 모드에서 배터리 수명 짧음
- A/S 비용 부담

## 💰 총평

"비싸지만 후회 없는 선택, 한 번 쓰면 다른 청소기로 못 돌아간다" 반려동물 털, 알레르기 있는 분께 강력 추천!

---
#다이슨V15 #무선청소기추천 #다이슨청소기 #청소기리뷰 #가전제품추천 #생활가전 #청소기비교 #다이슨후기 #무선청소기 #가성비청소기"""

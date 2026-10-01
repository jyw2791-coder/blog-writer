"""
블로그 스타일별 프롬프트 템플릿 모듈
- 맛집 블로그
- 여행 블로그
- 제품 리뷰 블로그
"""

BLOG_STYLES = {
    "🍽️ 맛집 블로그": "restaurant",
    "✈️ 여행 블로그": "travel",
    "📦 제품 리뷰 블로그": "product",
}

TONE_OPTIONS = {
    "친근하고 감성적인": "friendly",
    "전문적이고 정보 중심": "professional",
    "유쾌하고 재미있는": "fun",
    "담백하고 솔직한": "honest",
}


def get_restaurant_prompt(user_input: dict, image_description: str) -> str:
    name = user_input.get("title", "")
    location = user_input.get("location", "")
    keywords = user_input.get("keywords", "")
    rating = user_input.get("rating", "")
    memo = user_input.get("memo", "")
    tone = user_input.get("tone", "친근하고 감성적인")

    return f"""
당신은 네이버 맛집 블로그를 전문적으로 작성하는 블로거입니다.
아래 정보를 바탕으로 실제 네이버 블로그처럼 자연스럽고 읽기 좋은 맛집 포스팅을 작성해주세요.

[작성 조건]
- 문체: {tone} 스타일로 작성
- 분량: 800~1200자 내외
- 이모지를 적절히 활용하여 가독성 높이기
- 소제목(##)을 2~3개 사용하여 구조화
- 마지막에 별점 및 총평으로 마무리

[가게 정보]
- 가게명: {name}
- 위치: {location}
- 키워드/특징: {keywords}
- 별점: {rating}
- 메모: {memo}

[사진 분석 결과]
{image_description}

[작성 형식]
1. 제목 (# 으로 시작, 클릭을 유도하는 매력적인 제목)
2. 방문 계기 & 첫인상 (## 소제목 포함)
3. 메뉴 & 맛 상세 리뷰 (## 소제목 포함, 사진 분석 내용 자연스럽게 녹여내기)
4. 분위기 & 서비스
5. 총평 & 별점 (⭐ 이모지 활용)
6. 해시태그 10개 (맛집 관련)

지금 바로 블로그 포스팅을 작성해주세요:
"""


def get_travel_prompt(user_input: dict, image_description: str) -> str:
    title = user_input.get("title", "")
    location = user_input.get("location", "")
    keywords = user_input.get("keywords", "")
    season = user_input.get("season", "")
    memo = user_input.get("memo", "")
    tone = user_input.get("tone", "친근하고 감성적인")

    return f"""
당신은 네이버 여행 블로그를 전문적으로 작성하는 여행 블로거입니다.
아래 정보를 바탕으로 독자가 직접 가고 싶어지는 생동감 넘치는 여행 포스팅을 작성해주세요.

[작성 조건]
- 문체: {tone} 스타일로 작성
- 분량: 1000~1500자 내외
- 이모지를 적절히 활용하여 감성적인 분위기 연출
- 소제목(##)을 3~4개 사용하여 여행 동선처럼 구성
- 실용적인 여행 팁도 포함

[여행 정보]
- 여행지/장소: {title}
- 위치: {location}
- 키워드/특징: {keywords}
- 방문 시기/계절: {season}
- 메모: {memo}

[사진 분석 결과]
{image_description}

[작성 형식]
1. 제목 (# 으로 시작, 감성적이고 클릭을 유도하는 제목)
2. 여행지 소개 & 가게 된 이유 (## 소제목 포함)
3. 실제 방문 후기 (## 소제목 포함, 사진 분석 내용 자연스럽게 녹여내기)
4. 주변 볼거리 & 먹거리 꿀팁 (## 소제목 포함)
5. 여행 정보 정리 (교통, 운영시간, 입장료 등)
6. 마무리 한 줄 소감
7. 해시태그 10개 (여행 관련)

지금 바로 블로그 포스팅을 작성해주세요:
"""


def get_product_prompt(user_input: dict, image_description: str) -> str:
    product_name = user_input.get("title", "")
    brand = user_input.get("brand", "")
    price = user_input.get("price", "")
    keywords = user_input.get("keywords", "")
    pros_cons = user_input.get("pros_cons", "")
    memo = user_input.get("memo", "")
    tone = user_input.get("tone", "전문적이고 정보 중심")

    return f"""
당신은 네이버 제품 리뷰 블로그를 전문적으로 작성하는 리뷰어입니다.
아래 정보를 바탕으로 실제 구매자가 신뢰할 수 있는 솔직한 제품 리뷰를 작성해주세요.

[작성 조건]
- 문체: {tone} 스타일로 작성
- 분량: 1000~1400자 내외
- 이모지와 체크리스트(✅/❌)를 활용하여 가독성 높이기
- 소제목(##)을 3~4개 사용하여 구조화
- 구매 전 궁금한 점들을 미리 해소해주는 구성

[제품 정보]
- 제품명: {product_name}
- 브랜드: {brand}
- 가격: {price}
- 키워드/특징: {keywords}
- 장단점 메모: {pros_cons}
- 추가 메모: {memo}

[사진 분석 결과]
{image_description}

[작성 형식]
1. 제목 (# 으로 시작, 구매 전 검색할 법한 키워드 포함)
2. 제품 구매 계기 & 첫인상 (## 소제목 포함)
3. 상세 스펙 & 실사용 후기 (## 소제목 포함, 사진 분석 내용 자연스럽게 녹여내기)
4. 장점 & 단점 (✅/❌ 아이콘 활용, ## 소제목 포함)
5. 가격 대비 만족도 & 추천 대상
6. 총평 한 줄 요약
7. 해시태그 10개 (제품 리뷰 관련)

지금 바로 블로그 포스팅을 작성해주세요:
"""


def build_prompt(style: str, user_input: dict, image_description: str) -> str:
    """스타일에 맞는 프롬프트를 빌드하여 반환합니다."""
    style_key = BLOG_STYLES.get(style, "restaurant")

    if style_key == "restaurant":
        return get_restaurant_prompt(user_input, image_description)
    elif style_key == "travel":
        return get_travel_prompt(user_input, image_description)
    elif style_key == "product":
        return get_product_prompt(user_input, image_description)
    else:
        return get_restaurant_prompt(user_input, image_description)


def get_input_fields(style: str) -> list:
    """스타일별 입력 필드 정의를 반환합니다."""
    style_key = BLOG_STYLES.get(style, "restaurant")

    common = [
        {"key": "tone", "label": "글 스타일/문체", "type": "select",
         "options": list(TONE_OPTIONS.keys()), "default": "친근하고 감성적인"},
        {"key": "keywords", "label": "키워드/특징", "type": "text",
         "placeholder": "예: 웨이팅 맛집, 파스타, 분위기 좋은"},
        {"key": "memo", "label": "추가 메모 (자유 작성)", "type": "textarea",
         "placeholder": "기억에 남는 점, 특이사항 등 자유롭게 적어주세요"},
    ]

    if style_key == "restaurant":
        return [
            {"key": "title", "label": "가게명 *", "type": "text", "placeholder": "예: 을지로 노가리골목 OO집"},
            {"key": "location", "label": "위치", "type": "text", "placeholder": "예: 서울 중구 을지로"},
            {"key": "rating", "label": "별점", "type": "select",
             "options": ["⭐⭐⭐⭐⭐ (5점)", "⭐⭐⭐⭐ (4점)", "⭐⭐⭐ (3점)", "⭐⭐ (2점)", "⭐ (1점)"],
             "default": "⭐⭐⭐⭐⭐ (5점)"},
        ] + common

    elif style_key == "travel":
        return [
            {"key": "title", "label": "여행지/장소명 *", "type": "text", "placeholder": "예: 제주도 협재해수욕장"},
            {"key": "location", "label": "위치", "type": "text", "placeholder": "예: 제주특별자치도 제주시"},
            {"key": "season", "label": "방문 시기", "type": "text", "placeholder": "예: 2024년 8월, 여름"},
        ] + common

    elif style_key == "product":
        return [
            {"key": "title", "label": "제품명 *", "type": "text", "placeholder": "예: 다이슨 V15 무선청소기"},
            {"key": "brand", "label": "브랜드", "type": "text", "placeholder": "예: 다이슨"},
            {"key": "price", "label": "가격", "type": "text", "placeholder": "예: 799,000원"},
            {"key": "pros_cons", "label": "장단점", "type": "textarea",
             "placeholder": "장점: 흡입력 강함, 가볍다\n단점: 가격이 비쌈, 배터리 수명"},
        ] + common

    return common

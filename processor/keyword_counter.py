"""게시글에서 제품 수준의 구체적 키워드를 추출하고 카운팅한다.

"필름시공", "턴키" 같은 범용 키워드가 아니라
"영림 PS170", "디아망 코튼화이트" 같은 제품/모델 수준의 시그널을 잡는다.
"""

import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# ── 브랜드 사전 ──────────────────────────────────────
# 브랜드명을 감지하면, 주변 텍스트에서 제품명/모델명을 함께 추출한다
BRANDS = [
    # 벽지
    "디아망", "신한", "LG벽지", "코스모스벽지", "제일벽지",
    # 바닥재
    "동화마루", "한화마루", "LG하우시스", "KCC마루", "영림",
    # 페인트/도장
    "벤자민무어", "노루페인트", "KCC페인트", "듀럭스", "조광페인트", "팬톤",
    # 타일/줄눈
    "케라폭시", "유니본드", "아펠", "이나비", "로하스",
    # 조명
    "필립스", "오스람", "착한조명", "호강조명", "DR조명",
    # 싱크대/주방
    "한샘", "에넥스", "리바트", "이케아", "백센", "체리쉬",
    # 욕실
    "대림바스", "로얄앤컴퍼니", "로얄", "아메리칸스탠다드", "코토",
    # 필름
    "벤타", "현대엘앤씨", "LX하우시스",
    # 에어컨/설비
    "삼성", "LG", "캐리어", "위닉스",
    # 창호/문
    "KCC창호", "LG창호", "현대창호", "영림도어",
    # 실링팬
    "시거스", "판도라",
    # 기타
    "휴젠트", "까사미아", "이마트", "다이소", "쿠팡",
]

# ── 알려진 구체적 제품/모델명 ────────────────────────
# 정확히 매칭되면 바로 카운팅
KNOWN_PRODUCTS = {
    # 벽지
    "디아망 코튼화이트": ["디아망 코튼화이트", "디아망코튼화이트"],
    "디아망 크림화이트": ["디아망 크림화이트", "디아망크림화이트"],
    "디아망 포그그레이": ["디아망 포그그레이", "디아망포그그레이"],
    "디아망 그레이쉬": ["디아망 그레이쉬", "디아망그레이쉬"],
    "디아망 루나화이트": ["디아망 루나화이트", "디아망루나화이트"],
    "디아망 루카화이트": ["디아망 루카화이트", "디아망루카화이트"],
    "신한 머스타드": ["신한 머스타드"],
    # 바닥재
    "영림 PS170": ["PS170", "ps170"],
    "영림 에코빌리프": ["에코빌리프"],
    "동화 나투스프리미엄": ["나투스프리미엄", "나투스 프리미엄"],
    "동화 에디션": ["동화 에디션"],
    "한화 리얼우드": ["리얼우드", "리얼 우드"],
    # 필름
    "벤타 인테리어필름": ["벤타 필름", "벤타필름"],
    "LX 인테리어필름": ["LX 필름", "LX필름", "하우시스 필름"],
    # 타일/줄눈
    "케라폭시 이지": ["케라폭시 이지", "케라폭시이지"],
    "케라폭시 실버": ["케라폭시 실버"],
    # 조명
    "COB 2인치": ["COB 2인치", "cob 2인치", "COB2인치"],
    "COB 3인치": ["COB 3인치", "cob 3인치", "COB3인치"],
    "필립스 LED": ["필립스 LED", "필립스LED"],
    # 싱크대
    "한샘 유로": ["한샘 유로"],
    "한샘 인터스": ["한샘 인터스"],
    "에넥스 싱크대": ["에넥스 싱크대"],
    # 욕실
    "대림바스 CC": ["대림바스 CC", "대림 CC"],
    "로얄 세라믹": ["로얄 세라믹"],
    # 에어컨
    "삼성 무풍": ["삼성 무풍", "무풍에어컨", "무풍 에어컨"],
    "LG 휘센": ["LG 휘센", "휘센", "LG휘센"],
    # 실링팬
    "시거스 실링팬": ["시거스", "시거스 실링팬"],
    # 기타
    "휴젠트 몰딩": ["휴젠트 몰딩"],
    "탄성코트": ["탄성코트"],
}

# ── 범용 키워드 (제외 대상) ──────────────────────────
BORING_KEYWORDS = {
    "거실", "안방", "욕실", "주방", "베란다", "현관",
    "도배", "바닥", "타일", "조명", "견적", "평수", "이사",
    "인테리어", "시공", "업체", "공사", "문의", "질문",
    "셀프", "후기", "추천",
}


def _extract_brand_context(text: str, brand: str, window: int = 15) -> list[str]:
    """브랜드명 주변 텍스트에서 제품명 후보를 추출한다."""
    contexts = []
    text_lower = text.lower()
    brand_lower = brand.lower()
    start = 0

    while True:
        idx = text_lower.find(brand_lower, start)
        if idx == -1:
            break
        # 브랜드 앞뒤 window 글자 추출
        ctx_start = max(0, idx - window)
        ctx_end = min(len(text), idx + len(brand) + window)
        context = text[ctx_start:ctx_end].strip()
        contexts.append(context)
        start = idx + len(brand)

    return contexts


def count_keywords(posts: list[dict], exclude_boring: bool = True) -> list[dict]:
    """게시글에서 제품 수준의 키워드를 카운팅한다."""
    product_counter = Counter()  # 알려진 제품명
    brand_context_counter = Counter()  # 브랜드+주변 텍스트

    for post in posts:
        text = post.get("title", "")
        text += " " + post.get("content", "")
        for comment in post.get("comments", []):
            text += " " + comment

        # 1. 알려진 제품명 매칭
        matched_products = set()
        for product, patterns in KNOWN_PRODUCTS.items():
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    matched_products.add(product)
                    break

        for product in matched_products:
            product_counter[product] += 1

        # 2. 브랜드 감지 → 주변 컨텍스트 추출
        for brand in BRANDS:
            if brand.lower() in text.lower():
                contexts = _extract_brand_context(text, brand)
                for ctx in contexts:
                    # 브랜드 + 컨텍스트를 키로 저장 (나중에 Claude가 해석)
                    # 여기서는 브랜드 단독 카운팅
                    brand_context_counter[brand] += 1
                    break  # 게시글당 1회만

    # 3. 결과 합산: 제품명 우선, 브랜드 보조
    final_counter = Counter()

    # 제품명 (가장 가치 있는 시그널)
    for product, count in product_counter.items():
        final_counter[product] = count

    # 브랜드 (제품명으로 잡히지 않은 것만)
    for brand, count in brand_context_counter.items():
        # 이미 이 브랜드의 제품이 잡혔으면 브랜드 단독은 제외
        brand_products = [p for p in product_counter if brand in p]
        if not brand_products and count >= 3:  # 최소 3회 이상만
            final_counter[brand] = count

    # 순위 정렬
    ranked = []
    for rank, (keyword, count) in enumerate(final_counter.most_common(15), 1):
        heat = "🔥🔥🔥" if count >= 30 else "🔥🔥" if count >= 10 else "🔥"
        ranked.append({
            "rank": rank,
            "keyword": keyword,
            "mention_count": count,
            "heat": heat,
        })

    logger.info(f"제품 키워드 카운팅 완료: {len(ranked)}개")

    return ranked


def get_keyword_summary(posts: list[dict]) -> str:
    """Claude에게 넘길 키워드 카운팅 결과 텍스트."""
    ranked = count_keywords(posts)

    lines = ["[제품/브랜드 수준 키워드 카운팅 결과 — 코드 기반 정확 카운팅 (게시글 단위)]"]
    for r in ranked:
        lines.append(f"  {r['rank']}위. {r['keyword']}: {r['mention_count']}회 {r['heat']}")

    return "\n".join(lines)


if __name__ == "__main__":
    import json
    from pathlib import Path

    data_file = Path(__file__).resolve().parent.parent / "data" / "crawl_full_20260401.json"
    with open(data_file, "r", encoding="utf-8") as f:
        posts = json.load(f)

    print(f"total: {len(posts)}")
    result = count_keywords(posts)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    Path(__file__).resolve().parent.parent.joinpath("data", "keyword_count_v3.json").write_text(out, encoding="utf-8")
    print("saved to keyword_count_v3.json")

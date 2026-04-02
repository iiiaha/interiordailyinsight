"""수집된 게시글 텍스트 전처리 모듈."""

import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 스팸 필터 패턴
SPAM_PATTERN = re.compile(r"홍보|광고|업체소개|분양|매물|상담문의|무료견적|카톡상담")


class TextProcessor:
    """수집된 게시글을 분석에 적합한 형태로 전처리한다."""

    def clean_posts(self, posts: list[dict]) -> list[dict]:
        """게시글에서 HTML 태그 제거, 스팸 필터링, 정제를 수행한다."""
        cleaned = []
        spam_count = 0
        short_count = 0

        for post in posts:
            # HTML 태그 제거
            title = BeautifulSoup(post.get("title", ""), "html.parser").get_text()
            description = BeautifulSoup(post.get("description", ""), "html.parser").get_text()

            # 공백 정규화
            title = re.sub(r"\s+", " ", title).strip()
            description = re.sub(r"\s+", " ", description).strip()

            # 짧은 게시글 필터 (설명 50자 미만)
            if len(description) < 50:
                short_count += 1
                continue

            # 스팸 필터
            combined = title + " " + description
            if SPAM_PATTERN.search(combined):
                spam_count += 1
                continue

            cleaned.append({
                **post,
                "title": title,
                "description": description,
            })

        logger.info(
            f"전처리 완료: {len(posts)}건 → {len(cleaned)}건 "
            f"(스팸 {spam_count}건, 짧은글 {short_count}건 제거)"
        )
        return cleaned

    def aggregate_for_analysis(self, posts: list[dict], max_chars: int = 12000) -> str:
        """게시글을 키워드별로 그룹화하여 분석용 텍스트로 집계한다."""
        # 키워드별 그룹화
        groups: dict[str, list[dict]] = {}
        for post in posts:
            keyword = post.get("keyword", "기타")
            groups.setdefault(keyword, []).append(post)

        # 구조화된 텍스트 생성
        lines: list[str] = []
        for keyword, group_posts in groups.items():
            lines.append(f"\n[키워드: {keyword}] ({len(group_posts)}건)")
            for p in group_posts:
                lines.append(f"- {p['title']}: {p['description']}")

        result = "\n".join(lines)

        # 최대 길이 제한 (Claude 컨텍스트 고려)
        if len(result) > max_chars:
            result = result[:max_chars] + "\n\n... (이하 생략)"
            logger.warning(f"집계 텍스트가 {max_chars}자로 잘렸습니다")

        logger.info(f"분석용 텍스트 생성: {len(result)}자, {len(posts)}건")
        return result

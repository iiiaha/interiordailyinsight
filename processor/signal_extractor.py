"""고인게이지먼트 게시글에서 비즈니스 시그널을 추출한다.

단순 키워드 카운팅이 아니라:
1. 댓글 20개 이상 게시글만 필터 (진짜 시그널)
2. 댓글 수 기준 정렬
3. Claude에게 넘길 고밀도 텍스트 구성
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def filter_high_engagement(posts: list[dict], min_comments: int = 15) -> list[dict]:
    """댓글이 많은 고인게이지먼트 게시글만 필터링한다."""
    high = []
    for p in posts:
        comment_count = len(p.get("comments", []))
        if comment_count >= min_comments:
            high.append({**p, "comment_count": comment_count})

    # 댓글 수 기준 내림차순 정렬
    high.sort(key=lambda x: x["comment_count"], reverse=True)
    logger.info(f"고인게이지먼트 필터: {len(posts)}건 → {len(high)}건 (댓글 {min_comments}개 이상)")
    return high


def build_analysis_text(posts: list[dict], high_engagement: list[dict], max_chars: int = 90000) -> str:
    """Claude에게 넘길 분석용 텍스트를 구성한다.

    구조:
    1. 전체 통계 요약
    2. 고인게이지먼트 게시글 (본문 + 댓글 전체) — 가장 많은 분량
    3. 나머지 게시글은 제목만
    """
    lines = []
    char_count = 0

    # 전체 통계
    total = len(posts)
    with_content = sum(1 for p in posts if p.get("content"))
    with_comments = sum(1 for p in posts if p.get("comments"))
    total_comments = sum(len(p.get("comments", [])) for p in posts)

    # 게시판별 분포
    board_counts = {}
    for p in posts:
        b = p.get("board", "기타")
        board_counts[b] = board_counts.get(b, 0) + 1

    lines.append(f"[전체 통계]")
    lines.append(f"총 게시글: {total}건, 본문 수집: {with_content}건, 총 댓글: {total_comments}개")
    lines.append(f"게시판별: {', '.join(f'{b}({c}건)' for b, c in sorted(board_counts.items(), key=lambda x: -x[1]))}")
    lines.append("")

    # 고인게이지먼트 게시글 (핵심 데이터)
    lines.append(f"{'='*60}")
    lines.append(f"[고인게이지먼트 게시글 — 댓글 15개 이상, {len(high_engagement)}건]")
    lines.append(f"이 게시글들이 시장의 핵심 시그널입니다.")
    lines.append(f"{'='*60}")

    for i, p in enumerate(high_engagement):
        entry_lines = []
        entry_lines.append(f"\n--- [{i+1}/{len(high_engagement)}] 댓글 {p['comment_count']}개 | {p.get('board', '')} ---")
        entry_lines.append(f"제목: {p['title']}")

        # 본문 (최대 500자)
        content = p.get("content", "")
        if content:
            if len(content) > 500:
                content = content[:500] + "..."
            entry_lines.append(f"본문: {content}")

        # 댓글 전체 (고인게이지먼트 글은 댓글이 핵심)
        comments = p.get("comments", [])
        if comments:
            entry_lines.append(f"댓글 ({len(comments)}개):")
            for c in comments[:30]:  # 최대 30개
                c_text = c[:150] if len(c) > 150 else c
                entry_lines.append(f"  · {c_text}")

        entry = "\n".join(entry_lines)

        if char_count + len(entry) > max_chars * 0.75:  # 75%는 고인게이지먼트에 할당
            lines.append(f"\n... (고인게이지먼트 {len(high_engagement) - i}건 생략)")
            break
        lines.append(entry)
        char_count += len(entry)

    # 나머지 게시글 — 본문 포함 (200자 제한)
    remaining = [p for p in posts if p not in high_engagement]
    lines.append(f"\n{'='*60}")
    lines.append(f"[일반 게시글 — {len(remaining)}건 (본문 포함)]")
    lines.append(f"{'='*60}")

    for p in remaining:
        entry = f"\n[{p.get('board', '')}] {p['title']}"
        content = p.get("content", "")
        if content:
            if len(content) > 200:
                content = content[:200] + "..."
            entry += f"\n{content}"
        comments = p.get("comments", [])
        if comments:
            entry += f"\n댓글: {' | '.join(c[:80] for c in comments[:3])}"
        if char_count + len(entry) > max_chars:
            lines.append(f"... (이하 생략)")
            break
        lines.append(entry)
        char_count += len(entry)

    result = "\n".join(lines)
    logger.info(f"분석용 텍스트 생성: {len(result):,}자 (고인게이지먼트 {len(high_engagement)}건 + 일반 제목)")
    return result


if __name__ == "__main__":
    data_file = Path(__file__).resolve().parent.parent / "data" / "crawl_full_20260401.json"
    with open(data_file, "r", encoding="utf-8") as f:
        posts = json.load(f)

    high = filter_high_engagement(posts, min_comments=15)
    print(f"total: {len(posts)}, high engagement: {len(high)}")
    for h in high[:10]:
        print(f"  [{h['comment_count']}] {h['title'][:50]}")

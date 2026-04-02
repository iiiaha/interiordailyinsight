"""유튜브 인테리어 채널에서 최근 영상의 자막을 수집한다.

1. YouTube Data API로 각 채널의 최근 영상 목록 가져오기
2. youtube-transcript-api로 한국어 자막 추출
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 채널 리스트
CHANNEL_URLS = [
    "https://www.youtube.com/@alepseoul",
    "https://www.youtube.com/@homefaber_design",
    "https://www.youtube.com/@designA3",
    "https://www.youtube.com/@OWL_DESIGN",
    "https://www.youtube.com/@dfrog_studio",
    "https://www.youtube.com/@%EC%97%90%ED%94%84%EC%95%8CTV",
    "https://www.youtube.com/@interior-show",
    "https://www.youtube.com/@Ilhadadesign",
    "https://www.youtube.com/@ha_design",
    "https://www.youtube.com/@logdesign",
    "https://www.youtube.com/@framdesign",
    "https://www.youtube.com/@polarbearjeon",
    "https://www.youtube.com/@thisis_jooan",
    "https://www.youtube.com/@carmine_design",
    "https://www.youtube.com/@Design_Share",
    "https://www.youtube.com/@romentor",
    "https://www.youtube.com/@STEVEZIPS",
    "https://www.youtube.com/@intelliunnie",
    "https://www.youtube.com/@golma_interior",
    "https://www.youtube.com/@lilsquare_official",
    "https://www.youtube.com/@%EC%95%88%EB%8F%84%ED%95%98%EB%8B%A4",
    "https://www.youtube.com/@%EB%8B%A4%EC%A0%95%ED%95%9C%EC%9E%84%EC%86%8C%EC%9E%A5",
    "https://www.youtube.com/@softcondesign",
    "https://www.youtube.com/@homeludens_interior",
    "https://www.youtube.com/@studiowe.interior",
    "https://www.youtube.com/@%EC%8A%A4%ED%8A%9C%EB%94%94%EC%98%A4%EA%B3%BD%EC%96%B8%EB%8B%88",
]


def _extract_handle(url: str) -> str:
    """URL에서 채널 핸들(@xxx)을 추출한다."""
    match = re.search(r"@([^/]+)", unquote(url))
    return match.group(1) if match else ""


def _get_channel_id(youtube, handle: str) -> str | None:
    """핸들로 채널 ID를 조회한다."""
    try:
        # @handle로 검색
        response = youtube.search().list(
            part="snippet",
            q=handle,
            type="channel",
            maxResults=1,
        ).execute()

        items = response.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
        return None
    except Exception as e:
        logger.warning(f"채널 ID 조회 실패 ({handle}): {e}")
        return None


def _get_recent_videos(youtube, channel_id: str, days_back: int = 1) -> list[dict]:
    """채널의 최근 N일간 영상 목록을 가져온다."""
    after = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

    try:
        response = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            order="date",
            publishedAfter=after,
            type="video",
            maxResults=10,
        ).execute()

        videos = []
        for item in response.get("items", []):
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "published": item["snippet"]["publishedAt"],
                "description": item["snippet"].get("description", "")[:200],
            })
        return videos
    except Exception as e:
        logger.warning(f"영상 목록 조회 실패 ({channel_id}): {e}")
        return []


def _get_transcript(video_id: str) -> str | None:
    """영상의 한국어 자막을 가져온다."""
    try:
        ytt_api = YouTubeTranscriptApi()
        entries = ytt_api.fetch(video_id, languages=["ko"])
        text = " ".join(entry.text for entry in entries)
        return text if text.strip() else None
    except Exception as e:
        logger.debug(f"자막 추출 실패 ({video_id}): {e}")
        return None


def collect_youtube(api_key: str, days_back: int = 1) -> list[dict]:
    """전체 채널에서 최근 영상 + 자막을 수집한다."""
    youtube = build("youtube", "v3", developerKey=api_key)

    all_videos = []
    total_channels = len(CHANNEL_URLS)

    for i, url in enumerate(CHANNEL_URLS):
        handle = _extract_handle(url)
        logger.info(f"[{i+1}/{total_channels}] @{handle} 수집 중...")

        # 채널 ID 조회
        channel_id = _get_channel_id(youtube, handle)
        if not channel_id:
            logger.warning(f"  채널 ID 못 찾음: @{handle}")
            continue

        # 최근 영상 목록
        videos = _get_recent_videos(youtube, channel_id, days_back=days_back)
        if not videos:
            logger.info(f"  최근 {days_back}일 내 영상 없음")
            continue

        logger.info(f"  영상 {len(videos)}건 발견")

        # 각 영상 자막 추출
        for video in videos:
            transcript = _get_transcript(video["video_id"])
            video["transcript"] = transcript or ""
            video["has_transcript"] = bool(transcript)

            if transcript:
                logger.info(f"    자막 수집: {video['title'][:40]}... ({len(transcript)}자)")
            else:
                logger.info(f"    자막 없음: {video['title'][:40]}...")

        all_videos.extend(videos)

    # 결과 저장
    DATA_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    output = DATA_DIR / f"youtube_{today}.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_videos, f, ensure_ascii=False, indent=2)

    with_transcript = sum(1 for v in all_videos if v.get("has_transcript"))
    logger.info(f"유튜브 수집 완료: {len(all_videos)}건 (자막 {with_transcript}건)")
    logger.info(f"저장: {output}")

    return all_videos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        print("YOUTUBE_API_KEY를 .env에 설정하세요.")
        sys.exit(1)

    # 최근 7일로 테스트 (오늘 올라온 게 없을 수 있으니)
    videos = collect_youtube(api_key, days_back=7)
    print(f"\ntotal: {len(videos)}")
    for v in videos[:5]:
        t = "O" if v.get("has_transcript") else "X"
        print(f"  [{t}] {v['channel']}: {v['title'][:50]}")

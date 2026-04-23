"""weekly_reports 백필 — data/report_YYYY-MM-DD.html 파일을 DB 로 import.

사용(VPS):
    cd /opt/idi && venv/bin/python db/backfill_reports.py

- report_YYYY-MM-DD.html 형식만 처리 (report_test.html 등 무시)
- 같은 날짜 week_start 가 이미 있으면 skip (멱등)
- sent_at / created_at 에 파일 mtime 입력 → 어드민 발송이력 순서 정상
- recipient_count 는 0 으로 기록 (과거 수신자 수 모름)
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from db.supabase_client import SupabaseClient

DATA_DIR = PROJECT_ROOT / "data"
PATTERN = re.compile(r"^report_(\d{4}-\d{2}-\d{2})\.html$")


def main():
    db = SupabaseClient()

    rows = db.client.table("weekly_reports").select("week_start").execute().data or []
    existing = {r["week_start"] for r in rows}

    files = sorted(DATA_DIR.glob("report_*.html"))
    inserted = 0
    skipped_exists = 0
    skipped_nonmatch = 0

    for f in files:
        m = PATTERN.match(f.name)
        if not m:
            skipped_nonmatch += 1
            continue
        date = m.group(1)
        if date in existing:
            print(f"skip (exists): {date}")
            skipped_exists += 1
            continue

        html = f.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()

        db.client.table("weekly_reports").insert({
            "week_start": date,
            "week_end": date,
            "html_content": html,
            "sent_at": mtime,
            "created_at": mtime,
            "recipient_count": 0,
        }).execute()
        print(f"inserted: {date}  ({len(html):,} chars)")
        inserted += 1

    print()
    print(f"Done. inserted={inserted}, exists_skip={skipped_exists}, nonmatch_skip={skipped_nonmatch}")


if __name__ == "__main__":
    main()

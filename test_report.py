"""분석 결과를 HTML 리포트로 생성하여 로컬 파일로 저장."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from report.generator import ReportGenerator

# 분석 결과 로드
data_dir = Path(__file__).resolve().parent / "data"
with open(data_dir / "analysis_20260401.json", "r", encoding="utf-8") as f:
    analysis = json.load(f)

# 테스트 구독자
subscriber = {
    "id": "test-001",
    "name": "테스터",
    "email": "test@test.com",
}

# HTML 리포트 생성
generator = ReportGenerator()
html = generator.generate_html(
    analysis=analysis,
    subscriber=subscriber,
    week_start="2026-04-01",
    week_end="2026-04-01",
)

# 파일로 저장
output = data_dir / "report_20260401.html"
with open(output, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML 리포트 생성 완료: {output}")
print(f"파일 크기: {len(html):,}자")
print(f"\n브라우저에서 열어보세요: {output}")

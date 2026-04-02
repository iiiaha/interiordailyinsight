"""v2 분석 결과를 새 HTML 템플릿으로 리포트 생성."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from jinja2 import Environment, FileSystemLoader
from config.settings import SERVICE_DOMAIN, PROJECT_ROOT

# 분석 결과 로드
data_dir = Path(__file__).resolve().parent / "data"
with open(data_dir / "analysis_v2_20260401.json", "r", encoding="utf-8") as f:
    analysis = json.load(f)

# Jinja2 환경
template_dir = PROJECT_ROOT / "report" / "templates"
env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
template = env.get_template("daily_report.html")

# 렌더링
html = template.render(
    analysis=analysis,
    report_date="2026-04-01 (화)",
    subscriber_name="테스터",
    unsubscribe_url=f"{SERVICE_DOMAIN}/unsubscribe?token=test-001",
)

# 저장
output = data_dir / "report_v2_20260401.html"
with open(output, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML 리포트 생성: {output}")
print(f"크기: {len(html):,}자")

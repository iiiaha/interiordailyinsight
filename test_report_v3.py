"""v3 분석 결과를 HTML 리포트로 생성."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
from jinja2 import Environment, FileSystemLoader
from config.settings import SERVICE_DOMAIN, PROJECT_ROOT

data_dir = Path(__file__).resolve().parent / "data"
with open(data_dir / "analysis_v3_20260401.json", "r", encoding="utf-8") as f:
    analysis = json.load(f)

template_dir = PROJECT_ROOT / "report" / "templates"
env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
template = env.get_template("daily_report.html")

html = template.render(
    analysis=analysis,
    report_date="2026-04-01 (화)",
    subscriber_name="테스터",
    unsubscribe_url=f"{SERVICE_DOMAIN}/unsubscribe?token=test-001",
)

output = data_dir / "report_v3_20260401.html"
with open(output, "w", encoding="utf-8") as f:
    f.write(html)
print(f"done: {output} ({len(html):,} chars)")

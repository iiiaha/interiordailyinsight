"""v4 리포트 생성."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
from jinja2 import Environment, FileSystemLoader
from config.settings import SERVICE_DOMAIN, PROJECT_ROOT

data_dir = Path(__file__).resolve().parent / "data"
with open(data_dir / "analysis_v4_20260401.json", "r", encoding="utf-8") as f:
    analysis = json.load(f)

env = Environment(loader=FileSystemLoader(str(PROJECT_ROOT / "report" / "templates")), autoescape=True)
template = env.get_template("daily_v4.html")

html = template.render(
    analysis=analysis,
    meta=analysis["meta"],
    report_date="2026-04-01 (화)",
    subscriber_name="테스터",
    unsubscribe_url=f"{SERVICE_DOMAIN}/unsubscribe?token=test",
)

output = data_dir / "report_v4_20260401.html"
with open(output, "w", encoding="utf-8") as f:
    f.write(html)
print(f"done: {output} ({len(html):,} chars)")

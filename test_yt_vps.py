import sys,json
sys.path.insert(0,'/opt/idi')
from youtube_transcript_api import YouTubeTranscriptApi
data=json.load(open('/opt/idi/data/youtube_2026-04-03.json'))
print(len(data),'videos')
ytt=YouTubeTranscriptApi()
for v in data[:3]:
    vid=v['video_id']
    print(f"\n--- {vid} ---")
    print(f"title: {v['title'][:40]}")
    try:
        r=ytt.fetch(vid,languages=['ko'])
        text=' '.join(e.text for e in r)
        print(f"OK: {len(text)} chars")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

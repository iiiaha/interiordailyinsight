import sys,json
sys.path.insert(0,'/opt/idi')
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
data=json.load(open('/opt/idi/data/youtube_2026-04-04.json'))
print(len(data),'videos')
ytt=YouTubeTranscriptApi(
    proxy_config=WebshareProxyConfig(
        proxy_username="sbodetrh",
        proxy_password="s0lwegl673gr",
    )
)
for v in data[:5]:
    vid=v['video_id']
    try:
        r=ytt.fetch(vid,languages=['ko'])
        text=' '.join(e.text for e in r)
        print(f"OK {vid}: {len(text)} chars")
    except Exception as e:
        print(f"FAIL {vid}: {type(e).__name__}")

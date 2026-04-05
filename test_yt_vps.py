import json
data=json.load(open('/opt/idi/data/youtube_2026-04-05.json'))
for v in data:
    t='O' if v.get('has_transcript') else 'X'
    print(f"[{t}] https://youtube.com/watch?v={v['video_id']}")
    print(f"    {v['channel']} | {v['title'][:50]}")

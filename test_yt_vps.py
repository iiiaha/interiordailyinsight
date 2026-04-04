import sys,json
sys.path.insert(0,'/opt/idi')
data=json.load(open('/opt/idi/data/youtube_2026-04-03.json'))
print(len(data),'videos')
for v in data:
    print(v['video_id'], v.get('has_transcript','?'), v['channel'][:15], v['title'][:30])

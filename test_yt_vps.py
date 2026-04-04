import sys,json
sys.path.insert(0,'/opt/idi')
from youtube_transcript_api import YouTubeTranscriptApi
data=json.load(open('/opt/idi/data/youtube_2026-04-03.json'))
print(len(data),'videos')
v=data[0]
print(v['video_id'],v['title'][:40])
try:
    ytt=YouTubeTranscriptApi()
    r=ytt.fetch(v['video_id'],languages=['ko'])
    print('transcript:',len(r))
except Exception as e:
    print('error:',e)

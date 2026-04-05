import json
data=json.load(open('/opt/idi/data/crawl_2026-04-04.json'))
comments=[len(d.get('comments',[])) for d in data]
print('total posts:', len(data))
print('with comments:', sum(1 for c in comments if c>0))
print('avg comments:', round(sum(comments)/len(comments),1) if comments else 0)
print('max comments:', max(comments))
print('top 10:', sorted(comments, reverse=True)[:10])
print('5+ comments:', sum(1 for c in comments if c>=5))
print('3+ comments:', sum(1 for c in comments if c>=3))
print('1+ comments:', sum(1 for c in comments if c>=1))

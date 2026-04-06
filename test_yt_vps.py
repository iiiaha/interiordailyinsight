import sys,json
sys.path.insert(0,'/opt/idi')
from dotenv import load_dotenv
load_dotenv('/opt/idi/.env')
from jinja2 import Environment, FileSystemLoader
from mailer.resend_mailer import ResendMailer

analysis=json.load(open('/opt/idi/data/analysis_2026-04-05.json'))
yt=None
try:
    yt=json.load(open('/opt/idi/data/youtube_analysis_2026-04-05.json'))
except:
    pass

env=Environment(loader=FileSystemLoader('/opt/idi/report/templates'),autoescape=True)
html=env.get_template('daily_v6.html').render(analysis=analysis,meta=analysis['meta'],youtube=yt,report_date='2026-04-05',unsubscribe_url='#')
open('/opt/idi/data/report_test.html','w').write(html)

m=ResendMailer(api_key='re_jWAT4Yhp_Et3gxfMRfVUtLdPf4PwoVFeR')
print('sent' if m.send('iiiaha@naver.com','[test] mobile responsive',html) else 'fail')

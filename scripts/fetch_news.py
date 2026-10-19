"""Fetch sports RSS feeds and write news/<league>.json (run by GitHub Actions)."""
import json,re,html,time,os,concurrent.futures as cf,urllib.request as U,xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime,timezone
FOX='https://api.foxsports.com/v2/content/optimized-rss?partnerKey=MB0Wehpmuj2lUhuRhQaafhBjAJqaPU244mlTDK1i&size=30&tags=fs/'
ATH='https://www.nytimes.com/athletic/rss/'
F={'nfl':[('CBS Sports','https://www.cbssports.com/rss/headlines/nfl/'),('Yahoo Sports','https://sports.yahoo.com/nfl/rss/'),('Fox Sports',FOX+'nfl'),('ProFootballTalk','https://profootballtalk.nbcsports.com/feed/'),('The Athletic',ATH+'nfl/'),('SB Nation','https://www.sbnation.com/rss/nfl/index.xml')],
'mlb':[('CBS Sports','https://www.cbssports.com/rss/headlines/mlb/'),('Yahoo Sports','https://sports.yahoo.com/mlb/rss/'),('Fox Sports',FOX+'mlb'),('NBC Sports','https://www.nbcsports.com/mlb.rss'),('The Athletic',ATH+'mlb/'),('SB Nation','https://www.sbnation.com/rss/mlb/index.xml'),('MLB.com','https://www.mlb.com/feeds/news/rss.xml')],
'nba':[('CBS Sports','https://www.cbssports.com/rss/headlines/nba/'),('Yahoo Sports','https://sports.yahoo.com/nba/rss/'),('Fox Sports',FOX+'nba'),('The Athletic',ATH+'nba/'),('SB Nation','https://www.sbnation.com/rss/nba/index.xml')],
'cfb':[('CBS Sports','https://www.cbssports.com/rss/headlines/college-football/'),('Yahoo Sports','https://sports.yahoo.com/college-football/rss/'),('Fox Sports',FOX+'cfb'),('The Athletic',ATH+'college-football/'),('SB Nation','https://www.sbnation.com/rss/college-football/index.xml'),('NCAA.com','https://www.ncaa.com/news/football/fbs/rss.xml')],
'cbb':[('CBS Sports','https://www.cbssports.com/rss/headlines/college-basketball/'),('Yahoo Sports','https://sports.yahoo.com/college-basketball/rss/'),('Fox Sports',FOX+'cbk'),('The Athletic',ATH+'college-basketball/'),('SB Nation','https://www.sbnation.com/rss/college-basketball/index.xml'),('NCAA.com','https://www.ncaa.com/news/basketball-men/d1/rss.xml')]}
def ln(t):return t.split('}')[-1]
def when(s):
  if not s:return None
  try:return parsedate_to_datetime(s).astimezone(timezone.utc).isoformat()
  except Exception:
    try:return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc).isoformat()
    except Exception:return None
def parse(src,data):
  root=ET.fromstring(data);out=[]
  for it in [e for e in root.iter() if ln(e.tag) in('item','entry')][:40]:
    d={};img=None
    for c in it:
      n=ln(c.tag);t=(c.text or '').strip()
      if n=='title':d['title']=html.unescape(re.sub('<[^>]+>','',t))
      elif n=='link':d.setdefault('url',t or c.get('href'))
      elif n in('pubDate','published','updated','date'):d.setdefault('pub',t)
      elif n in('content','thumbnail','enclosure') and (c.get('url') and (c.get('medium')=='image' or 'image' in (c.get('type') or 'image') or n=='thumbnail')):img=img or c.get('url')
      elif n in('description','encoded','summary') and not img:
        m=re.search(r'<img[^>]+src="([^"]+)"',html.unescape(t));img=m and m.group(1)
      if n=='group':
        for g in c:
          if g.get('url') and not img:img=g.get('url')
    if d.get('title') and d.get('url'):out.append({'title':d['title'],'url':d['url'].strip(),'source':src,'published':when(d.get('pub')),'image':img})
  return out
def get(src,url):
  try:
    r=U.urlopen(U.Request(url,headers={'User-Agent':'Mozilla/5.0 (LiveScores news fetcher)'}),timeout=20);return parse(src,r.read())
  except Exception as e:print('FAIL',src,url,e);return []
os.makedirs('news',exist_ok=True);status={}
with cf.ThreadPoolExecutor(12) as ex:
  for lg,fs in F.items():
    res=list(ex.map(lambda f:get(*f),fs));items=[i for r in res for i in r]
    status[lg]={f[0]:len(r) for f,r in zip(fs,res)}
    if not items and os.path.exists(f'news/{lg}.json'):continue
    items.sort(key=lambda i:i['published'] or '',reverse=True)
    json.dump({'updated':datetime.now(timezone.utc).isoformat(),'items':items[:150]},open(f'news/{lg}.json','w'),separators=(',',':'))
json.dump({'updated':datetime.now(timezone.utc).isoformat(),'sources':status},open('news/status.json','w'),indent=1)
print(json.dumps(status,indent=1))

import os, logging
from database import get_tokens, get_db
from datetime import date, timedelta
logger = logging.getLogger(__name__)

THRESHOLDS = {'ctr':{'good':5.0,'warn':3.0},'retention':{'good':50.0,'warn':35.0},'engagement':{'good':4.0,'warn':2.0}}

def _status(metric,value):
    t = THRESHOLDS[metric]
    return 'ok' if value>=t['good'] else 'warn' if value>=t['warn'] else 'bad'

async def run() -> dict:
    tokens = await get_tokens()
    if not tokens:
        logger.warning('Layer 13: No tokens')
        return None
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        creds = Credentials(token=tokens['access_token'],refresh_token=tokens['refresh_token'],token_uri='https://oauth2.googleapis.com/token',client_id=os.getenv('GOOGLE_CLIENT_ID'),client_secret=os.getenv('GOOGLE_CLIENT_SECRET'))
        youtube = build('youtube','v3',credentials=creds)
        yt_analytics = build('youtubeAnalytics','v2',credentials=creds)
        ch = youtube.channels().list(part='snippet,statistics',mine=True).execute()
        channel = ch['items'][0]
        ch_name = channel['snippet']['title']
        subs = int(channel['statistics'].get('subscriberCount',0))
        total = int(channel['statistics'].get('videoCount',0))
        ch_id = channel['id']
        end = date.today().isoformat()
        start = (date.today()-timedelta(days=90)).isoformat()
        analytics = yt_analytics.reports().query(ids=f'channel=={ch_id}',startDate=start,endDate=end,metrics='views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,subscribersGained,clickThroughRate',dimensions='').execute()
        rows = analytics.get('rows',[[0]*8])
        r = rows[0] if rows else [0]*8
        views,_,avg_dur,avg_pct,likes,comments,_,ctr = r
        engagement = ((likes+comments)/views*100) if views>0 else 0
        ctr_val = float(ctr)*100
        insights = [
            {'metric':'CTR','value':f'{ctr_val:.1f}%','status':_status('ctr',ctr_val),'note':'Below 4% avg' if ctr_val<4 else 'Above average'},
            {'metric':'Avg retention','value':f'{avg_pct:.0f}%','status':_status('retention',avg_pct),'note':f'{avg_dur:.0f}s avg watch time'},
            {'metric':'Engagement','value':f'{engagement:.1f}%','status':_status('engagement',engagement),'note':'Likes + comments / views'},
        ]
        reroutes = []
        if ctr_val<THRESHOLDS['ctr']['good']:
            reroutes.append({'issue':f'CTR {ctr_val:.1f}% below target','target_layer':11,'layer_name':'Thumbnail Artist','priority':'high','instruction':'High contrast thumbnail, shocked expression, bright colors, large text'})
        if avg_pct<THRESHOLDS['retention']['good']:
            reroutes.append({'issue':f'Retention {avg_pct:.0f}% needs improvement','target_layer':4,'layer_name':'Hook Architect','priority':'high','instruction':'More shocking hook, curiosity gap, impossible fact in first 3 seconds'})
        if engagement<THRESHOLDS['engagement']['good']:
            reroutes.append({'issue':f'Engagement {engagement:.1f}% low','target_layer':3,'layer_name':'SEO Planner','priority':'medium','instruction':'Add comment-bait keywords, CTA for likes and comments'})
        analysis = {'channel_name':ch_name,'subscriber_count':subs,'total_videos':total,'insights':insights,'reroutes':reroutes}
        db = get_db()
        db.table('channel_analysis').insert({'channel_name':ch_name,'ctr':ctr_val,'retention':float(avg_pct),'engagement':engagement,'reroutes':reroutes}).execute()
        logger.info(f'Layer 13 -> {len(reroutes)} improvements')
        return analysis
    except Exception as e:
        logger.error(f'Layer 13 error: {e}')
        return None

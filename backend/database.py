import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def get_db() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def init_db():
    pass

async def get_all_topics():
    db = get_db()
    res = db.table('videos').select('topic').execute()
    return [r['topic'] for r in res.data] if res.data else []

async def save_video(topic, title, keywords, status='draft'):
    db = get_db()
    db.table('videos').insert({'topic':topic,'title':title,'keywords':keywords,'status':status}).execute()

async def mark_published(topic, youtube_url):
    db = get_db()
    db.table('videos').update({'status':'published','youtube_url':youtube_url}).eq('topic',topic).execute()

async def save_tokens(access, refresh, expiry, channel_id, channel_name):
    db = get_db()
    db.table('oauth_tokens').delete().neq('id',0).execute()
    db.table('oauth_tokens').insert({'access_token':access,'refresh_token':refresh,'token_expiry':expiry,'channel_id':channel_id,'channel_name':channel_name}).execute()

async def get_tokens():
    db = get_db()
    res = db.table('oauth_tokens').select('*').limit(1).execute()
    return res.data[0] if res.data else None

async def save_run(run_id, topic, status, layers_done):
    db = get_db()
    db.table('pipeline_runs').upsert({'id':run_id,'topic':topic,'status':status,'layers_completed':','.join(map(str,layers_done))}).execute()

async def get_stats():
    db = get_db()
    videos = db.table('videos').select('*').execute()
    published = db.table('videos').select('*').eq('status','published').execute()
    return {'total_videos':len(videos.data) if videos.data else 0,'published':len(published.data) if published.data else 0}

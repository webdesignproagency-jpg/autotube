import os, logging
from models.schemas import SEOOutput, PipelineConfig
from db.vault import save_video, mark_published, get_tokens
logger = logging.getLogger(__name__)

async def package(config: PipelineConfig, seo: SEOOutput, video_path: str, thumbnail_path: str) -> dict:
    keywords_str = ', '.join(seo.seo_keywords)
    description = f'In this documentary, we explore {seo.primary_topic}.\n\nTopics: {keywords_str}\n\n#mystery #unsolved #documentary'
    payload = {'title':config.video_title,'description':description,'tags':seo.seo_keywords+['mystery','unsolved','documentary'],'category_id':'22','privacy_status':'public','video_path':video_path,'thumbnail_path':thumbnail_path,'topic':seo.primary_topic}
    await save_video(topic=seo.primary_topic, title=config.video_title, keywords=keywords_str, output_path=video_path, thumbnail_path=thumbnail_path)
    return payload

async def upload(payload: dict) -> str:
    tokens = await get_tokens()
    if not tokens: raise ValueError('No OAuth tokens. Connect your channel first.')
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=tokens[1],refresh_token=tokens[2],token_uri='https://oauth2.googleapis.com/token',client_id=os.getenv('GOOGLE_CLIENT_ID'),client_secret=os.getenv('GOOGLE_CLIENT_SECRET'))
    youtube = build('youtube','v3',credentials=creds)
    body = {'snippet':{'title':payload['title'],'description':payload['description'],'tags':payload['tags'],'categoryId':payload['category_id']},'status':{'privacyStatus':payload['privacy_status']}}
    media = MediaFileUpload(payload['video_path'],chunksize=-1,resumable=True)
    request = youtube.videos().insert(part='snippet,status',body=body,media_body=media)
    response = None
    while response is None: _,response = request.next_chunk()
    video_id = response.get('id')
    url = f'https://www.youtube.com/watch?v={video_id}'
    if os.path.exists(payload['thumbnail_path']):
        youtube.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(payload['thumbnail_path'])).execute()
    await mark_published(payload['topic'], url)
    return url

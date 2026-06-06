import asyncio, json, os, uuid, logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
load_dotenv()

from database import init_db, save_run, get_stats
import layer01_trends as L1
import layer02_auditor as L2
import layer03_seo as L3
import layer04_hook as L4
import layer05_script as L5
import layer06_prompts as L6
import layer07_video as L7
import layer08_voice as L8
import layer09_editor as L9
import layer10_qc as L10
import layer11_thumbnail as L11
import layer12_publisher as L12
import layer13_channel as L13

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

state = {
    'running':False,'run_id':None,'topic':'',
    'current_layer':0,'progress':0,
    'payload':None,'config':None,
    'image_paths':[],'audio_paths':[],
    'video_path':None,'thumbnail_path':None,
    'channel_analysis':None,'layers_done':[],
}

connections = []
scheduler = AsyncIOScheduler()

async def broadcast(msg):
    data = json.dumps(msg)
    dead = []
    for ws in connections:
        try: await ws.send_text(data)
        except: dead.append(ws)
    for ws in dead: connections.remove(ws)

async def emit(layer, status, message, data=None):
    await broadcast({'type':'layer_update','layer':layer,'status':status,'message':message,'data':data or {},'ts':datetime.utcnow().isoformat()})

async def run_pipeline():
    if state['running']: return
    state['running'] = True
    state['run_id'] = str(uuid.uuid4())[:8]
    state['layers_done'] = []
    state['payload'] = None
    await broadcast({'type':'pipeline_start','message':'Pipeline started'})
    try:
        await emit(13,'running','Analysing your channel...')
        analysis = await L13.run()
        state['channel_analysis'] = analysis
        reroutes = {r['target_layer']:r for r in analysis.get('reroutes',[])} if analysis else {}
        await emit(13,'done','Channel analysis complete',analysis or {})
        state['layers_done'].append(13)

        await emit(1,'running','Scraping trends...')
        topics = await L1.run()
        state['layers_done'].append(1)
        await emit(1,'done',f'{len(topics)} topics found',{'count':len(topics)})

        await emit(2,'running','Checking duplicates...')
        topic = await L2.run(topics)
        state['topic'] = topic
        state['layers_done'].append(2)
        await emit(2,'done',f'Selected: {topic}',{'topic':topic})

        await emit(3,'running','Building SEO keywords...')
        seo = await L3.run(topic, reroutes.get(3,{}).get('instruction',''))
        state['layers_done'].append(3)
        await emit(3,'done',f"{len(seo['seo_keywords'])} keywords",seo)
        state['progress'] = 25

        await emit(4,'running','Writing hook (Gemini)...')
        hook = await L4.run(seo, reroutes.get(4,{}).get('instruction',''))
        state['layers_done'].append(4)
        await emit(4,'done','Hook written',{'hook':hook[:80]})

        await emit(5,'running','Generating script (Gemini)...')
        script = await L5.run(hook,seo)
        state['layers_done'].append(5)
        await emit(5,'done',f'{len(script)} lines',{'lines':len(script)})

        await emit(6,'running','Engineering visual prompts...')
        config = await L6.run(hook,script,seo)
        state['config'] = config
        state['layers_done'].append(6)
        await emit(6,'done',f"{len(config['scenes'])} scenes",{'title':config['video_title']})
        state['progress'] = 50

        await emit(7,'running','Generating scene visuals...')
        image_paths = await L7.run(config)
        state['image_paths'] = image_paths
        state['layers_done'].append(7)
        await emit(7,'done',f'{len(image_paths)} scenes rendered')

        await emit(8,'running','Synthesising narration...')
        audio_paths = await L8.run(config)
        state['audio_paths'] = audio_paths
        state['layers_done'].append(8)
        await emit(8,'done',f'{len(audio_paths)} audio files')
        state['progress'] = 75

        await emit(9,'running','Stitching master video...')
        video_path = await L9.run(image_paths,audio_paths)
        state['video_path'] = video_path
        state['layers_done'].append(9)
        await emit(9,'done','output_draft.mp4 ready')

        await emit(10,'running','Running QC checks...')
        qc = await L10.run(video_path)
        state['layers_done'].append(10)
        await emit(10,'done' if qc['passed'] else 'error',qc['message'],qc)

        await emit(11,'running','Generating thumbnail...')
        thumb = await L11.run(seo, reroutes.get(11,{}).get('instruction',''))
        state['thumbnail_path'] = thumb
        state['layers_done'].append(11)
        await emit(11,'done','thumbnail.png ready')

        await emit(12,'running','Packaging for approval...')
        payload = await L12.package(config,seo,video_path,thumb)
        state['payload'] = payload
        state['layers_done'].append(12)
        await emit(12,'done','Ready for your approval',payload)

        state['progress'] = 100
        await broadcast({'type':'pipeline_complete','message':'All 13 layers complete — awaiting your approval','data':{'topic':topic,'title':config['video_title'],'reroutes_applied':list(reroutes.keys())}})
        await save_run(state['run_id'],topic,'awaiting_approval',state['layers_done'])
    except Exception as e:
        logger.error(f'Pipeline error: {e}',exc_info=True)
        await broadcast({'type':'pipeline_error','message':str(e)})
    finally:
        state['running'] = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    hours = int(os.getenv('CRON_INTERVAL_HOURS',12))
    scheduler.add_job(run_pipeline,'interval',hours=hours,id='auto_pipeline')
    scheduler.start()
    logger.info(f'AutoTube Cloud started')
    yield
    scheduler.shutdown()

app = FastAPI(title='AutoTube Cloud',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

@app.websocket('/ws')
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    await ws.send_text(json.dumps({'type':'state_sync','data':{'running':state['running'],'topic':state['topic'],'progress':state['progress'],'layers_done':state['layers_done'],'channel_analysis':state['channel_analysis']}}))
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect:
        if ws in connections: connections.remove(ws)

@app.post('/api/pipeline/start')
async def start(bg: BackgroundTasks):
    if state['running']: raise HTTPException(400,'Already running')
    bg.add_task(run_pipeline)
    return {'status':'started'}

@app.get('/api/pipeline/status')
async def status(): return state

@app.get('/api/stats')
async def stats(): return await get_stats()

class ApprovalBody(BaseModel):
    action: str
    scene_idx: Optional[int] = None

@app.post('/api/pipeline/approve')
async def approve(body: ApprovalBody, bg: BackgroundTasks):
    if body.action == 'upload':
        if not state['payload']: raise HTTPException(400,'No payload ready')
        async def do_upload():
            await emit(12,'running','Uploading to YouTube...')
            try:
                url = await L12.upload(state['payload'])
                await broadcast({'type':'uploaded','data':{'url':url}})
            except Exception as e:
                await broadcast({'type':'pipeline_error','message':str(e)})
        bg.add_task(do_upload)
        return {'status':'uploading'}
    elif body.action == 'save':
        return {'status':'saved','video':state['video_path'],'thumbnail':state['thumbnail_path']}
    elif body.action == 'redo':
        async def redo():
            if state['config']:
                img = await L7.run(state['config'])
                aud = await L8.run(state['config'])
                vid = await L9.run(img,aud)
                state['video_path'] = vid
                qc = await L10.run(vid)
                await broadcast({'type':'redo_complete','message':'Re-render complete'})
        bg.add_task(redo)
        return {'status':'redo_started'}
    elif body.action == 'cancel':
        state['payload'] = None
        state['running'] = False
        return {'status':'cancelled'}
    raise HTTPException(400,f'Unknown: {body.action}')

@app.get('/api/channel/analysis')
async def channel_analysis():
    return {'connected':bool(state['channel_analysis']),'analysis':state['channel_analysis']}

@app.get('/auth/youtube')
async def auth_youtube():
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config({'web':{'client_id':os.getenv('GOOGLE_CLIENT_ID'),'client_secret':os.getenv('GOOGLE_CLIENT_SECRET'),'redirect_uris':[os.getenv('GOOGLE_REDIRECT_URI')],'auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token'}},scopes=['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly','https://www.googleapis.com/auth/yt-analytics.readonly'])
    flow.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    auth_url,_ = flow.authorization_url(access_type='offline',include_granted_scopes='true')
    return {'auth_url':auth_url}

@app.get('/auth/callback')
async def auth_callback(code: str):
    from google_auth_oauthlib.flow import Flow
    from database import save_tokens
    from googleapiclient.discovery import build
    flow = Flow.from_client_config({'web':{'client_id':os.getenv('GOOGLE_CLIENT_ID'),'client_secret':os.getenv('GOOGLE_CLIENT_SECRET'),'redirect_uris':[os.getenv('GOOGLE_REDIRECT_URI')],'auth_uri':'https://accounts.google.com/o/oauth2/auth','token_uri':'https://oauth2.googleapis.com/token'}},scopes=['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly','https://www.googleapis.com/auth/yt-analytics.readonly'])
    flow.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    flow.fetch_token(code=code)
    creds = flow.credentials
    youtube = build('youtube','v3',credentials=creds)
    ch = youtube.channels().list(part='snippet',mine=True).execute()
    ch_name = ch['items'][0]['snippet']['title']
    ch_id = ch['items'][0]['id']
    await save_tokens(creds.token,creds.refresh_token,creds.expiry.isoformat() if creds.expiry else '',ch_id,ch_name)
    return {'status':'connected','channel':ch_name}

@app.get('/health')
async def health(): return {'status':'ok'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app',host='0.0.0.0',port=8000,reload=False)

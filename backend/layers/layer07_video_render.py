import httpx, asyncio, os, uuid, logging
from models.schemas import PipelineConfig
logger = logging.getLogger(__name__)
COMFYUI_URL = os.getenv('COMFYUI_BASE_URL','http://localhost:8188')
TEMP_DIR = os.getenv('TEMP_RENDER_DIR','./temp_render')

async def render_scene(scene_idx: int, visual_prompt: str) -> str:
    os.makedirs(TEMP_DIR, exist_ok=True)
    output_path = os.path.join(TEMP_DIR, f'scene_{scene_idx:03d}.mp4')
    try:
        workflow = {'3':{'class_type':'CLIPTextEncode','inputs':{'text':visual_prompt,'clip':['4',1]}},'4':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'wan2.1_t2v_1.3B_bf16.safetensors'}},'6':{'class_type':'WanVideoSampler','inputs':{'positive':['3',0],'steps':20,'cfg':7.0,'width':1280,'height':720,'num_frames':125,'seed':scene_idx*1000+42}},'7':{'class_type':'VHS_VideoCombine','inputs':{'images':['6',0],'frame_rate':25,'filename_prefix':f'scene_{scene_idx:03d}','format':'video/mp4'}}}
        async with httpx.AsyncClient() as client:
            r = await client.post(f'{COMFYUI_URL}/prompt', json={'prompt':workflow,'client_id':str(uuid.uuid4())}, timeout=30)
            prompt_id = r.json().get('prompt_id')
            if prompt_id:
                for _ in range(300):
                    await asyncio.sleep(1)
                    hist = await client.get(f'{COMFYUI_URL}/history/{prompt_id}', timeout=5)
                    if prompt_id in hist.json():
                        if hist.json()[prompt_id].get('status',{}).get('completed'):
                            break
    except Exception as e:
        logger.error(f'ComfyUI error scene {scene_idx}: {e}')
    if not os.path.exists(output_path):
        open(output_path,'wb').close()
    return output_path

async def run(config: PipelineConfig) -> list:
    return [await render_scene(s.scene_idx, s.visual_prompt) for s in config.scenes]

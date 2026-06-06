import httpx, os, asyncio, logging
from typing import List
from PIL import Image, ImageDraw
logger = logging.getLogger(__name__)
HF_TOKEN = os.getenv('HF_TOKEN','')

async def generate_image(prompt: str, scene_idx: int) -> str:
    output_path = f'/tmp/scene_{scene_idx:03d}.png'
    if HF_TOKEN:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0',
                    headers={'Authorization':f'Bearer {HF_TOKEN}'},
                    json={'inputs':prompt[:500]}, timeout=60)
                if r.status_code == 200:
                    with open(output_path,'wb') as f: f.write(r.content)
                    return output_path
        except Exception as e:
            logger.error(f'HF error scene {scene_idx}: {e}')
    img = Image.new('RGB',(1280,720),color=(10,10,30))
    draw = ImageDraw.Draw(img)
    draw.text((50,360),f'Scene {scene_idx}',fill=(100,100,200))
    img.save(output_path)
    return output_path

async def run(config: dict) -> List[str]:
    paths = []
    for scene in config['scenes']:
        path = await generate_image(scene['visual_prompt'], scene['scene_idx'])
        paths.append(path)
        await asyncio.sleep(1)
    logger.info(f'Layer 7 -> {len(paths)} images')
    return paths

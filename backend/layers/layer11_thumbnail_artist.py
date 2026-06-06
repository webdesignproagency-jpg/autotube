import httpx, asyncio, os, uuid, logging
from PIL import Image, ImageDraw, ImageFont
from models.schemas import SEOOutput
logger = logging.getLogger(__name__)
COMFYUI_URL = os.getenv('COMFYUI_BASE_URL','http://localhost:8188')
OUTPUT_DIR = os.getenv('OUTPUT_DIR','./output')

def _add_text(image_path, title, output_path):
    img = Image.open(image_path).convert('RGBA')
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    w,h = img.size
    for y in range(h//3):
        alpha = int(200*(y/(h//3)))
        draw.rectangle([(0,h-h//3+y),(w,h-h//3+y+1)],fill=(0,0,0,alpha))
    img = Image.alpha_composite(img,overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arial.ttf', 72)
    except:
        font = ImageFont.load_default()
    words = title.upper().split()
    lines,line = [],''
    for word in words:
        test = (line+' '+word).strip()
        bbox = draw.textbbox((0,0),test,font=font)
        if bbox[2]>w-80: lines.append(line); line=word
        else: line=test
    if line: lines.append(line)
    for i,ln in enumerate(lines[:3]):
        draw.text((40,h-h//3+20+i*80),ln,fill=(255,230,0),font=font,stroke_width=3,stroke_fill=(0,0,0))
    img.save(output_path,'PNG')

async def run(seo: SEOOutput, l13_instruction: str = '') -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    thumbnail_path = os.path.join(OUTPUT_DIR,'thumbnail.png')
    raw = os.path.join(OUTPUT_DIR,'_raw_thumb.png')
    prompt = f'Cinematic dramatic thumbnail for {seo.primary_topic}, dark atmospheric, mysterious, high contrast, photorealistic, 4k, no text'
    if l13_instruction: prompt = l13_instruction + ', ' + prompt
    try:
        workflow = {'1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'flux1-schnell-fp8.safetensors'}},'2':{'class_type':'CLIPTextEncode','inputs':{'text':prompt,'clip':['1',1]}},'3':{'class_type':'KSampler','inputs':{'model':['1',0],'positive':['2',0],'negative':['4',0],'latent_image':['5',0],'steps':4,'cfg':1.0,'sampler_name':'euler','scheduler':'simple','denoise':1.0,'seed':abs(hash(seo.primary_topic))%2**32}},'4':{'class_type':'CLIPTextEncode','inputs':{'text':'blurry, text, watermark','clip':['1',1]}},'5':{'class_type':'EmptyLatentImage','inputs':{'width':1280,'height':720,'batch_size':1}},'6':{'class_type':'VAEDecode','inputs':{'samples':['3',0],'vae':['1',2]}},'7':{'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':'thumbnail'}}}
        async with httpx.AsyncClient() as client:
            r = await client.post(f'{COMFYUI_URL}/prompt',json={'prompt':workflow,'client_id':str(uuid.uuid4())},timeout=30)
            pid = r.json().get('prompt_id')
            if pid:
                for _ in range(120):
                    await asyncio.sleep(1)
                    h = await client.get(f'{COMFYUI_URL}/history/{pid}',timeout=5)
                    if pid in h.json():
                        for out in h.json()[pid].get('outputs',{}).values():
                            imgs = out.get('images',[])
                            if imgs:
                                ir = await client.get(f'{COMFYUI_URL}/view?filename={imgs[0]["filename"]}',timeout=10)
                                with open(raw,'wb') as f: f.write(ir.content)
                                break
                        break
    except Exception as e:
        logger.error(f'ComfyUI thumbnail error: {e}')
    if not os.path.exists(raw):
        Image.new('RGB',(1280,720),(10,10,20)).save(raw)
    _add_text(raw, seo.primary_topic, thumbnail_path)
    return thumbnail_path

import httpx, os, logging
from PIL import Image, ImageDraw, ImageFont
logger = logging.getLogger(__name__)
HF_TOKEN = os.getenv('HF_TOKEN','')

async def run(seo: dict, l13_instruction: str = '') -> str:
    topic = seo['primary_topic']
    output_path = '/tmp/thumbnail.png'
    raw_path = '/tmp/raw_thumb.png'
    prompt = f'Cinematic dramatic close-up for {topic}, dark mysterious, high contrast, photorealistic, 4k, no text'
    if l13_instruction: prompt = l13_instruction + ', ' + prompt
    generated = False
    if HF_TOKEN:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0',
                    headers={'Authorization':f'Bearer {HF_TOKEN}'},
                    json={'inputs':prompt[:500]},timeout=60)
                if r.status_code==200:
                    with open(raw_path,'wb') as f: f.write(r.content)
                    generated = True
        except Exception as e:
            logger.error(f'HF thumbnail error: {e}')
    if not generated:
        img = Image.new('RGB',(1280,720),color=(8,8,20))
        draw = ImageDraw.Draw(img)
        for y in range(720):
            alpha = int(40*(y/720))
            draw.line([(0,y),(1280,y)],fill=(alpha,0,alpha))
        img.save(raw_path)
    _add_text(raw_path,topic,output_path)
    return output_path

def _add_text(raw_path,title,output_path):
    img = Image.open(raw_path).convert('RGBA')
    overlay = Image.new('RGBA',img.size,(0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    w,h = img.size
    for y in range(h//3):
        alpha = int(210*(y/(h//3)))
        draw.rectangle([(0,h-h//3+y),(w,h-h//3+y+1)],fill=(0,0,0,alpha))
    img = Image.alpha_composite(img,overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',80)
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
    y_start = h-h//3+20
    for i,ln in enumerate(lines[:3]):
        draw.text((40,y_start+i*90),ln,fill=(255,220,0),font=font,stroke_width=4,stroke_fill=(0,0,0))
    img.save(output_path,'PNG')

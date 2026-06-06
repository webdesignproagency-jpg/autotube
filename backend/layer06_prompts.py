from gemini_client import generate
from typing import List
import re, logging
logger = logging.getLogger(__name__)
STYLE = 'cinematic documentary, photorealistic, 4k, dramatic lighting, film grain --ar 16:9'

async def run(hook: str, script_lines: List[str], seo: dict) -> dict:
    topic = seo['primary_topic']
    all_lines = [hook] + script_lines
    prompt = f'''For each narration line about '{topic}', write ONE short visual scene description (max 30 words).
Output numbered list only. Example: 1. Dark radio observatory, flickering monitors, 1970s atmosphere
Lines:
''' + '\n'.join(f'{i+1}. {l}' for i,l in enumerate(all_lines))
    result = await generate(prompt)
    visual_prompts = []
    for line in result.split('\n'):
        line = re.sub(r'^\d+\.\s*','',line.strip())
        if line and len(line)>10:
            visual_prompts.append(f'{line}, {STYLE}')
    while len(visual_prompts) < len(all_lines):
        visual_prompts.append(f'Dark mysterious scene about {topic}, {STYLE}')
    scenes = [{'scene_idx':i,'narration':line,'visual_prompt':visual_prompts[i]} for i,line in enumerate(all_lines)]
    return {'video_title':f'The Mystery of {topic} — What They Never Told You','scenes':scenes}

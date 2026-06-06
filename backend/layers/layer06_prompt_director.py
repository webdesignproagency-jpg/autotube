import ollama, re
from models.schemas import SEOOutput, Scene, PipelineConfig
from typing import List
import logging
logger = logging.getLogger(__name__)
STYLE = 'cinematic documentary, photorealistic, 4k, volumetric lighting, film grain, dramatic shadows --ar 16:9'

async def run(hook: str, narration_lines: List[str], seo: SEOOutput) -> PipelineConfig:
    all_lines = [hook] + narration_lines
    prompt = f'Topic: {seo.primary_topic}\nFor each narration line, write one short visual scene description (under 40 words). Output numbered list only.\n' + '\n'.join(f'{i+1}. {l}' for i,l in enumerate(all_lines))
    visual_prompts = []
    try:
        response = ollama.chat(model='llama3:8b', messages=[{'role':'user','content':prompt}])
        for line in response['message']['content'].split('\n'):
            line = re.sub(r'^\d+\.\s*','',line.strip())
            if line and len(line) > 10:
                visual_prompts.append(f'{line}, {STYLE}')
    except Exception as e:
        logger.error(f'Ollama L6 error: {e}')
    while len(visual_prompts) < len(all_lines):
        visual_prompts.append(f'Dark atmospheric scene, {seo.primary_topic}, {STYLE}')
    scenes = [Scene(scene_idx=i, narration=l, visual_prompt=visual_prompts[i]) for i,l in enumerate(all_lines)]
    return PipelineConfig(video_title=f'The Mystery of {seo.primary_topic} — What They Never Told You', scenes=scenes)

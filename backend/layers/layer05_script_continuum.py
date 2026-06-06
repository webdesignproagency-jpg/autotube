import ollama
from models.schemas import SEOOutput
from typing import List
import logging
logger = logging.getLogger(__name__)

async def run(hook: str, seo: SEOOutput) -> List[str]:
    prompt = f'Topic: {seo.primary_topic}\nHook (already written): {hook}\nKeywords: {", ".join(seo.seo_keywords)}\nWrite a 4-act documentary script: [ACT 1: THE INCIDENT] [ACT 2: THE INVESTIGATION] [ACT 3: THE ANOMALIES] [ACT 4: THE UNRESOLVED THEORY]. Each act has 3-5 short narration lines. Output only script lines.'
    try:
        response = ollama.chat(model='llama3:8b', messages=[{'role':'user','content':prompt}])
        lines = [l.strip() for l in response['message']['content'].split('\n') if l.strip() and not l.startswith('[') and len(l.strip()) > 20]
        return lines if lines else [response['message']['content']]
    except Exception as e:
        logger.error(f'Ollama L5 error: {e}')
        return [f'The story of {seo.primary_topic} begins in a way no one could have predicted.', 'Investigators arrived to find evidence that defied all known logic.', 'Every expert walked away with more questions than answers.', 'The anomalies pointed to something far more disturbing.', 'To this day, no official explanation has ever been given.']

import ollama
from models.schemas import SEOOutput
import logging
logger = logging.getLogger(__name__)

async def run(seo: SEOOutput, l13_instruction: str = '') -> str:
    extra = f'Additional instruction: {l13_instruction}' if l13_instruction else ''
    prompt = f'Topic: {seo.primary_topic}\nKeywords: {", ".join(seo.seo_keywords[:3])}\n{extra}\nWrite a 2-3 sentence 5-second high-tension YouTube hook. Open-ended question. Never reveal the answer. Output hook text only.'
    try:
        response = ollama.chat(model='llama3:8b', messages=[{'role':'user','content':prompt}])
        return response['message']['content'].strip()
    except Exception as e:
        logger.error(f'Ollama L4 error: {e}')
        return f'In {seo.primary_topic}, something happened that science still cannot explain. What we found in the archives will change everything you thought you knew.'

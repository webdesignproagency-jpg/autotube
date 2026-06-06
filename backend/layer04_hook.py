from gemini_client import generate
import logging
logger = logging.getLogger(__name__)

async def run(seo: dict, l13_instruction: str = '') -> str:
    topic = seo['primary_topic']
    keywords = ', '.join(seo['seo_keywords'][:3])
    extra = f'Channel feedback: {l13_instruction}' if l13_instruction else ''
    prompt = f'''You are a YouTube documentary hook writer.
Topic: {topic}
Keywords: {keywords}
{extra}
Write 2-3 sentences for a 5-second hook. Maximum tension. Open unanswered question. Never reveal the answer. Output hook text only.'''
    hook = await generate(prompt)
    logger.info(f'Layer 4 -> hook written')
    return hook

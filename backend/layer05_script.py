from gemini_client import generate
from typing import List
import logging
logger = logging.getLogger(__name__)

async def run(hook: str, seo: dict) -> List[str]:
    topic = seo['primary_topic']
    keywords = ', '.join(seo['seo_keywords'])
    prompt = f'''You are a YouTube documentary scriptwriter.
Topic: {topic}
Hook already written: {hook}
Keywords to include: {keywords}
Write a 4-act script:
ACT 1 THE INCIDENT - 3 lines
ACT 2 THE INVESTIGATION - 3 lines
ACT 3 THE ANOMALIES - 3 lines
ACT 4 THE UNRESOLVED THEORY - 3 lines
Each line = one short paragraph for 5-8 seconds narration.
Output ONLY the narration lines, one per line, no headers.'''
    result = await generate(prompt)
    lines = [l.strip() for l in result.split('\n') if l.strip() and len(l.strip())>20]
    logger.info(f'Layer 5 -> {len(lines)} lines')
    return lines if lines else [result]

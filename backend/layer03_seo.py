import httpx, json, re
from gemini_client import generate
import logging
logger = logging.getLogger(__name__)

async def run(topic: str, l13_instruction: str = '') -> dict:
    keywords = []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get('https://suggestqueries.google.com/complete/search',
                params={'client':'youtube','ds':'yt','q':topic}, timeout=10)
            match = re.search(r'\[.*\]', r.text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if isinstance(data,list) and len(data)>1:
                    keywords = [s[0] for s in data[1][:10] if isinstance(s,list)]
    except Exception as e:
        logger.warning(f'Autocomplete error: {e}')
    if not keywords:
        result = await generate(f'Give 10 YouTube SEO keywords for mystery documentary about {topic}. Comma separated list only.')
        keywords = [k.strip() for k in result.split(',')][:10]
    return {'primary_topic': topic, 'seo_keywords': keywords}

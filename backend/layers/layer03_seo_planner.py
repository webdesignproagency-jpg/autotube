import httpx, json, re
from models.schemas import SEOOutput
import logging
logger = logging.getLogger(__name__)

async def run(topic: str, l13_instruction: str = '') -> SEOOutput:
    keywords = []
    try:
        params = {'client': 'youtube', 'ds': 'yt', 'q': topic}
        async with httpx.AsyncClient() as client:
            r = await client.get('https://suggestqueries.google.com/complete/search', params=params, timeout=10)
            match = re.search(r'\[.*\]', r.text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if isinstance(data, list) and len(data) > 1:
                    keywords = [s[0] for s in data[1][:10] if isinstance(s, list)]
    except Exception as e:
        logger.warning(f'Autocomplete error: {e}')
    if not keywords:
        base = topic.lower()
        keywords = [f'{base} explained', f'{base} documentary', f'{base} mystery', f'unsolved {base}', f'{base} truth', f'{base} evidence', f'what happened {base}', f'{base} 2024', f'real story {base}', f'{base} conspiracy']
    return SEOOutput(primary_topic=topic, seo_keywords=keywords[:10])

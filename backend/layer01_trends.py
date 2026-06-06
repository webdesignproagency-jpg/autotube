import httpx
from typing import List
import logging
logger = logging.getLogger(__name__)

FALLBACKS = [
    'The Wow Signal','D.B. Cooper','Dyatlov Pass Incident',
    'The Zodiac Cipher','Voynich Manuscript','The Tunguska Event',
    'Antikythera Device','The Tamam Shud Case','Roanoke Colony',
    'The Bermuda Triangle','Area 51 Declassified','Oak Island Mystery',
    'The Black Dahlia Case','Amelia Earhart Disappearance',
    'The Somerton Man','MH370 Disappearance','Nazca Lines Mystery',
    'The Dancing Plague','Spring Heeled Jack','Cicada 3301'
]

async def run() -> List[str]:
    topics = set(FALLBACKS)
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                'https://www.reddit.com/r/UnresolvedMysteries/top/.json?limit=20&t=week',
                headers={'User-Agent':'AutoTube/1.0'}, timeout=10)
            for post in r.json().get('data',{}).get('children',[]):
                title = post['data'].get('title','')
                if title: topics.add(title[:60].title())
    except Exception as e:
        logger.warning(f'Reddit error: {e}')
    return list(topics)[:20]

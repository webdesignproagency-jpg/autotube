from pytrends.request import TrendReq
import httpx
from bs4 import BeautifulSoup
from typing import List
import logging
logger = logging.getLogger(__name__)

async def run() -> List[str]:
    topics = set()
    fallbacks = [
        'The Wow Signal','D.B. Cooper','Dyatlov Pass Incident',
        'The Zodiac Cipher','Voynich Manuscript','The Tunguska Event',
        'Antikythera Device','The Tamam Shud Case','Roanoke Colony',
        'The Bermuda Triangle','Area 51 Declassified','Oak Island Mystery',
        'The Black Dahlia Case','Amelia Earhart Disappearance',
        'The Somerton Man','MH370 Disappearance','Nazca Lines Mystery',
        'The Dancing Plague','Spring Heeled Jack','Cicada 3301'
    ]
    for f in fallbacks:
        topics.add(f)
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload(['unsolved mystery'], timeframe='now 7-d')
        related = pytrends.related_queries()
        for val in related.values():
            if val and val.get('top') is not None:
                for _, row in val['top'].iterrows():
                    topics.add(row['query'].title())
    except Exception as e:
        logger.warning(f'pytrends error: {e}')
    result = list(topics)[:20]
    logger.info(f'Layer 1 -> {len(result)} topics found')
    return result

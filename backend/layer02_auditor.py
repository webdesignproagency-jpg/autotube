from thefuzz import fuzz
from typing import List
from database import get_all_topics
import logging
logger = logging.getLogger(__name__)

async def run(topics: List[str]) -> str:
    existing = await get_all_topics()
    fresh = []
    for topic in topics:
        if not existing:
            fresh.append((topic, 0))
            continue
        score = max(fuzz.token_sort_ratio(topic.lower(), ex.lower()) for ex in existing)
        if score < 75:
            fresh.append((topic, score))
    if not fresh:
        fresh = [(t, 0) for t in topics]
    return sorted(fresh, key=lambda x: x[1])[0][0]

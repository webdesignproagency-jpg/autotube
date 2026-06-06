from thefuzz import fuzz
from typing import List
from db.vault import topic_exists
import logging
logger = logging.getLogger(__name__)
SIMILARITY_THRESHOLD = 75

async def run(topics: List[str]) -> str:
    existing_topics = await topic_exists('')
    fresh = []
    for topic in topics:
        if not existing_topics:
            fresh.append((topic, 0))
            continue
        max_score = max(fuzz.token_sort_ratio(topic.lower(), ex.lower()) for ex in existing_topics)
        if max_score < SIMILARITY_THRESHOLD:
            fresh.append((topic, max_score))
    if not fresh:
        fresh = [(t, 0) for t in topics]
    best = sorted(fresh, key=lambda x: x[1])[0][0]
    logger.info(f'Layer 2 -> selected: {best}')
    return best

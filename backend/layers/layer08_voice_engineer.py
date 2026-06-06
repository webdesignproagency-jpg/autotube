import os, asyncio, logging
import soundfile as sf
import numpy as np
from models.schemas import PipelineConfig
logger = logging.getLogger(__name__)
TEMP_DIR = os.getenv('TEMP_RENDER_DIR','./temp_render')
VOICE = os.getenv('KOKORO_VOICE','am_michael')

def _synth(text, path):
    try:
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code='a')
        samples = [audio for _,_,audio in pipeline(text, voice=VOICE, speed=0.95)]
        if samples:
            sf.write(path, np.concatenate(samples), 24000)
            return
    except Exception as e:
        logger.error(f'Kokoro error: {e}')
    sf.write(path, np.zeros(44100*6, dtype=np.float32), 44100)

async def run(config: PipelineConfig) -> list:
    os.makedirs(TEMP_DIR, exist_ok=True)
    paths = []
    loop = asyncio.get_event_loop()
    for scene in config.scenes:
        path = os.path.join(TEMP_DIR, f'audio_{scene.scene_idx:03d}.wav')
        await loop.run_in_executor(None, _synth, scene.narration, path)
        paths.append(path)
    logger.info(f'Layer 8 -> {len(paths)} audio files')
    return paths

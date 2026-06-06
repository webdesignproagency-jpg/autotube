import os, subprocess, asyncio, logging
from typing import List
logger = logging.getLogger(__name__)

def _stitch(image_paths, audio_paths, output_path):
    try:
        clips = []
        for i,(img,aud) in enumerate(zip(image_paths,audio_paths)):
            clip = f'/tmp/clip_{i:03d}.mp4'
            if os.path.exists(img) and os.path.exists(aud):
                cmd = ['ffmpeg','-y','-loop','1','-i',img,'-i',aud,
                       '-c:v','libx264','-tune','stillimage',
                       '-c:a','aac','-b:a','128k',
                       '-pix_fmt','yuv420p','-shortest',clip]
                subprocess.run(cmd,capture_output=True)
                if os.path.exists(clip): clips.append(clip)
        if not clips:
            open(output_path,'wb').close()
            return output_path
        concat = '/tmp/concat.txt'
        with open(concat,'w') as f:
            for c in clips: f.write(f"file '{c}'\n")
        cmd = ['ffmpeg','-y','-f','concat','-safe','0','-i',concat,
               '-c:v','libx264','-crf','20','-preset','fast',
               '-c:a','aac','-b:a','192k',output_path]
        subprocess.run(cmd,capture_output=True)
        logger.info(f'Layer 9 -> video stitched')
        return output_path
    except Exception as e:
        logger.error(f'FFmpeg error: {e}')
        open(output_path,'wb').close()
        return output_path

async def run(image_paths: List[str], audio_paths: List[str]) -> str:
    output = '/tmp/output_draft.mp4'
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _stitch, image_paths, audio_paths, output)

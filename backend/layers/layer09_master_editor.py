import os, glob, asyncio, subprocess, logging
logger = logging.getLogger(__name__)
TEMP_DIR = os.getenv('TEMP_RENDER_DIR','./temp_render')
OUTPUT_DIR = os.getenv('OUTPUT_DIR','./output')
AMBIENT_DIR = os.getenv('AMBIENT_MUSIC_DIR','./ambient_music')

def _stitch(video_paths, audio_paths, output_path):
    concat = os.path.join(TEMP_DIR,'concat.txt')
    merged = os.path.join(TEMP_DIR,'merged_audio.wav')
    valid_audio = [p for p in audio_paths if os.path.exists(p) and os.path.getsize(p)>0]
    if valid_audio:
        n = len(valid_audio)
        inputs = []
        for p in valid_audio: inputs += ['-i', p]
        fc = ''.join(f'[{i}:a]' for i in range(n)) + f'concat=n={n}:v=0:a=1[m]'
        subprocess.run(['ffmpeg','-y']+inputs+['-filter_complex',fc,'-map','[m]',merged], capture_output=True)
    with open(concat,'w') as f:
        for p in video_paths:
            if os.path.exists(p): f.write(f"file '{os.path.abspath(p)}'\n")
    ambient = glob.glob(os.path.join(AMBIENT_DIR,'*.mp3')) + glob.glob(os.path.join(AMBIENT_DIR,'*.wav'))
    cmd = ['ffmpeg','-y','-f','concat','-safe','0','-i',concat]
    if os.path.exists(merged): cmd += ['-i',merged]
    if ambient: cmd += ['-i',ambient[0],'-filter_complex','[2:a]volume=0.15[amb];[1:a][amb]amix=inputs=2:duration=first[out]','-map','0:v','-map','[out]']
    elif os.path.exists(merged): cmd += ['-map','0:v','-map','1:a']
    cmd += ['-c:v','libx264','-crf','20','-preset','fast','-c:a','aac','-b:a','192k',output_path]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        logger.error(f'FFmpeg: {result.stderr.decode()}')
        open(output_path,'wb').close()
    return output_path

async def run(video_paths, audio_paths) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output = os.path.join(OUTPUT_DIR,'output_draft.mp4')
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _stitch, video_paths, audio_paths, output)

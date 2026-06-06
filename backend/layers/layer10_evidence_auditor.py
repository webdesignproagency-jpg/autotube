import os, subprocess, json, logging
from models.schemas import QCResult
logger = logging.getLogger(__name__)

async def run(video_path: str) -> QCResult:
    if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
        return QCResult(passed=False, video_duration=0, audio_duration=0, frame_rate=0, bad_scene_idx=0, message='File missing or empty')
    try:
        cmd = ['ffprobe','-v','quiet','-print_format','json','-show_streams','-show_format',video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        probe = json.loads(result.stdout)
        streams = probe.get('streams',[])
        fmt = probe.get('format',{})
        video_stream = next((s for s in streams if s.get('codec_type')=='video'), None)
        audio_stream = next((s for s in streams if s.get('codec_type')=='audio'), None)
        video_dur = float(fmt.get('duration',0))
        audio_dur = float(audio_stream.get('duration',0)) if audio_stream else 0
        fps = 0
        if video_stream:
            num,den = video_stream.get('r_frame_rate','0/1').split('/')
            fps = round(int(num)/int(den),2) if int(den)>0 else 0
        passed = os.path.getsize(video_path)>1024 and video_dur>0 and abs(video_dur-audio_dur)<2.0 and fps>0
        msg = 'QC PASSED' if passed else f'QC FAILED: dur_diff={abs(video_dur-audio_dur):.1f}s fps={fps}'
        logger.info(f'Layer 10 -> {msg}')
        return QCResult(passed=passed, video_duration=video_dur, audio_duration=audio_dur, frame_rate=fps, bad_scene_idx=None if passed else 0, message=msg)
    except Exception as e:
        logger.error(f'QC error: {e}')
        return QCResult(passed=False, video_duration=0, audio_duration=0, frame_rate=0, bad_scene_idx=0, message=str(e))

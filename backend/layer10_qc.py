import os, subprocess, json, logging
logger = logging.getLogger(__name__)

async def run(video_path: str) -> dict:
    if not os.path.exists(video_path) or os.path.getsize(video_path)==0:
        return {'passed':False,'message':'File missing or empty','bad_scene_idx':0}
    try:
        cmd = ['ffprobe','-v','quiet','-print_format','json','-show_streams','-show_format',video_path]
        result = subprocess.run(cmd,capture_output=True,text=True)
        probe = json.loads(result.stdout)
        fmt = probe.get('format',{})
        streams = probe.get('streams',[])
        video_dur = float(fmt.get('duration',0))
        audio_stream = next((s for s in streams if s.get('codec_type')=='audio'),None)
        audio_dur = float(audio_stream.get('duration',0)) if audio_stream else 0
        passed = video_dur>0 and os.path.getsize(video_path)>1024
        msg = 'QC PASSED' if passed else f'QC FAILED: duration={video_dur}'
        return {'passed':passed,'video_duration':video_dur,'audio_duration':audio_dur,'message':msg}
    except Exception as e:
        return {'passed':False,'message':str(e),'bad_scene_idx':0}

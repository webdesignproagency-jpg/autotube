"""
AutoTube — FastAPI Backend
Orchestrates all 13 layers and streams real-time status to the React frontend
via WebSocket.
"""
import asyncio
import json
import os
import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

from db.vault import init_db, save_run
from models.schemas import ApprovalPayload, ChannelAnalysis

import layers.layer01_trend_scraper as L1
import layers.layer02_duplicate_auditor as L2
import layers.layer03_seo_planner as L3
import layers.layer04_hook_architect as L4
import layers.layer05_script_continuum as L5
import layers.layer06_prompt_director as L6
import layers.layer07_video_render as L7
import layers.layer08_voice_engineer as L8
import layers.layer09_master_editor as L9
import layers.layer10_evidence_auditor as L10
import layers.layer11_thumbnail_artist as L11
import layers.layer12_publisher as L12
import layers.layer13_channel_analyzer as L13

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Global pipeline state ────────────────────────────────────────────────────
pipeline_state = {
    "running": False,
    "run_id": None,
    "current_layer": 0,
    "topic": "",
    "payload": None,         # L12 upload payload awaiting approval
    "qc_result": None,
    "config": None,          # PipelineConfig
    "video_paths": [],
    "audio_paths": [],
    "video_path": None,
    "thumbnail_path": None,
    "channel_analysis": None,
    "layers_done": [],
}

connections: list[WebSocket] = []
scheduler = AsyncIOScheduler()

# ── WebSocket broadcast ───────────────────────────────────────────────────────
async def broadcast(msg: dict):
    data = json.dumps(msg)
    dead = []
    for ws in connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)

async def emit(layer: int, status: str, message: str, data: dict = None):
    await broadcast({
        "type": "layer_update",
        "layer": layer,
        "status": status,
        "message": message,
        "data": data or {},
        "ts": datetime.utcnow().isoformat()
    })

# ── Core pipeline orchestrator ────────────────────────────────────────────────
async def run_pipeline():
    if pipeline_state["running"]:
        return

    pipeline_state["running"] = True
    pipeline_state["run_id"] = str(uuid.uuid4())[:8]
    pipeline_state["layers_done"] = []
    pipeline_state["payload"] = None

    await broadcast({"type": "pipeline_start", "message": "Pipeline started"})

    try:
        # ── Layer 13: Channel analysis (runs first) ──────────────────────────
        await emit(13, "running", "Analysing your channel...")
        analysis: Optional[ChannelAnalysis] = await L13.run()
        pipeline_state["channel_analysis"] = analysis
        reroutes = {r.target_layer: r for r in analysis.reroutes} if analysis else {}
        l13_data = analysis.dict() if analysis else {}
        await emit(13, "done", "Channel analysis complete", l13_data)
        pipeline_state["layers_done"].append(13)

        # ── Layer 1: Trend scraper ───────────────────────────────────────────
        await emit(1, "running", "Scraping Google Trends & Reddit...")
        topics = await L1.run()
        pipeline_state["layers_done"].append(1)
        await emit(1, "done", f"{len(topics)} topics found", {"count": len(topics)})

        # ── Layer 2: Duplicate auditor ───────────────────────────────────────
        await emit(2, "running", "Checking for duplicates...")
        topic = await L2.run(topics)
        pipeline_state["topic"] = topic
        pipeline_state["layers_done"].append(2)
        await emit(2, "done", f"Selected: {topic}", {"topic": topic})

        # ── Layer 3: SEO planner ─────────────────────────────────────────────
        l3_instruction = reroutes.get(3, {})
        l3_instr_str = l3_instruction.instruction if hasattr(l3_instruction, 'instruction') else ""
        await emit(3, "running", "Building SEO keyword plan...")
        seo = await L3.run(topic, l3_instr_str)
        pipeline_state["layers_done"].append(3)
        await emit(3, "done", f"{len(seo.seo_keywords)} keywords", seo.dict())

        # ── Layer 4: Hook architect ──────────────────────────────────────────
        l4_instr = reroutes.get(4, {})
        l4_instr_str = l4_instr.instruction if hasattr(l4_instr, 'instruction') else ""
        await emit(4, "running", "Writing 5-second hook (Qwen 2.5 14B)...")
        hook = await L4.run(seo, l4_instr_str)
        pipeline_state["layers_done"].append(4)
        await emit(4, "done", "Hook written", {"hook": hook[:80]})

        # ── Layer 5: Script continuum ────────────────────────────────────────
        await emit(5, "running", "Generating 4-act script (Llama 3 8B)...")
        script_lines = await L5.run(hook, seo)
        pipeline_state["layers_done"].append(5)
        await emit(5, "done", f"{len(script_lines)} narration lines", {"lines": len(script_lines)})

        # ── Layer 6: Prompt director ─────────────────────────────────────────
        await emit(6, "running", "Engineering visual prompts per scene...")
        config = await L6.run(hook, script_lines, seo)
        pipeline_state["config"] = config
        pipeline_state["layers_done"].append(6)
        await emit(6, "done", f"{len(config.scenes)} scenes configured", {"title": config.video_title})

        # ── Layer 7: Video render ────────────────────────────────────────────
        await emit(7, "running", "Rendering video clips via ComfyUI + Wan 2.1...")
        video_paths = await L7.run(config)
        pipeline_state["video_paths"] = video_paths
        pipeline_state["layers_done"].append(7)
        await emit(7, "done", f"{len(video_paths)} clips rendered")

        # ── Layer 8: Voice engineer ──────────────────────────────────────────
        await emit(8, "running", "Synthesising narration via Kokoro-82M...")
        audio_paths = await L8.run(config)
        pipeline_state["audio_paths"] = audio_paths
        pipeline_state["layers_done"].append(8)
        await emit(8, "done", f"{len(audio_paths)} audio files synthesised")

        # ── Layer 9: Master editor ───────────────────────────────────────────
        await emit(9, "running", "Stitching master video with FFmpeg...")
        video_path = await L9.run(video_paths, audio_paths)
        pipeline_state["video_path"] = video_path
        pipeline_state["layers_done"].append(9)
        await emit(9, "done", "output_draft.mp4 ready")

        # ── Layer 10: QC auditor ─────────────────────────────────────────────
        await emit(10, "running", "Running quality control checks...")
        qc = await L10.run(video_path)
        pipeline_state["qc_result"] = qc
        pipeline_state["layers_done"].append(10)

        if not qc.passed:
            await emit(10, "error", f"QC FAILED — re-rendering scene {qc.bad_scene_idx}")
            # Re-render bad scene and re-stitch
            if qc.bad_scene_idx is not None and config:
                bad_scene = config.scenes[qc.bad_scene_idx]
                new_clip = await L7.render_scene(bad_scene.scene_idx, bad_scene.visual_prompt)
                video_paths[qc.bad_scene_idx] = new_clip
                video_path = await L9.run(video_paths, audio_paths)
                pipeline_state["video_path"] = video_path
                qc = await L10.run(video_path)
                pipeline_state["qc_result"] = qc

        await emit(10, "done", qc.message, qc.dict())

        # ── Layer 11: Thumbnail artist ───────────────────────────────────────
        l11_instr = reroutes.get(11, {})
        l11_instr_str = l11_instr.instruction if hasattr(l11_instr, 'instruction') else ""
        await emit(11, "running", "Generating thumbnail (Flux.1 Schnell)...")
        thumbnail_path = await L11.run(seo, l11_instr_str)
        pipeline_state["thumbnail_path"] = thumbnail_path
        pipeline_state["layers_done"].append(11)
        await emit(11, "done", "thumbnail.png ready")

        # ── Layer 12: Package for approval ───────────────────────────────────
        await emit(12, "running", "Packaging assets for sign-off...")
        payload = await L12.package(config, seo, video_path, thumbnail_path)
        pipeline_state["payload"] = payload
        pipeline_state["layers_done"].append(12)
        await emit(12, "done", "Ready for your approval", payload)

        await broadcast({
            "type": "pipeline_complete",
            "message": "All 13 layers complete — awaiting your approval",
            "data": {
                "topic": topic,
                "title": config.video_title,
                "reroutes_applied": list(reroutes.keys()),
            }
        })

        await save_run(pipeline_state["run_id"], topic, "awaiting_approval",
                       pipeline_state["layers_done"])

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        await broadcast({"type": "pipeline_error", "message": str(e)})
    finally:
        pipeline_state["running"] = False

# ── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    interval = int(os.getenv("CRON_INTERVAL_HOURS", 12))
    scheduler.add_job(run_pipeline, "interval", hours=interval, id="auto_pipeline")
    scheduler.start()
    logger.info(f"AutoTube started — auto-run every {interval}h")
    yield
    scheduler.shutdown()

app = FastAPI(title="AutoTube API", lifespan=lifespan)

app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    # Send current state immediately on connect
    await ws.send_text(json.dumps({
        "type": "state_sync",
        "data": {
            "running": pipeline_state["running"],
            "topic": pipeline_state["topic"],
            "layers_done": pipeline_state["layers_done"],
            "channel_analysis": pipeline_state["channel_analysis"].dict()
                if pipeline_state["channel_analysis"] else None,
        }
    }))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        connections.remove(ws)

# ── REST Endpoints ────────────────────────────────────────────────────────────
@app.post("/api/pipeline/start")
async def start_pipeline(background_tasks: BackgroundTasks):
    if pipeline_state["running"]:
        raise HTTPException(400, "Pipeline already running")
    background_tasks.add_task(run_pipeline)
    return {"status": "started"}

@app.get("/api/pipeline/status")
async def pipeline_status():
    return pipeline_state

@app.post("/api/pipeline/approve")
async def approve(payload: ApprovalPayload, background_tasks: BackgroundTasks):
    if payload.action == "upload":
        if not pipeline_state["payload"]:
            raise HTTPException(400, "No payload ready for upload")
        async def do_upload():
            await emit(12, "running", "Uploading to YouTube...")
            url = await L12.upload(pipeline_state["payload"])
            await broadcast({"type": "uploaded", "data": {"url": url}})
        background_tasks.add_task(do_upload)
        return {"status": "uploading"}

    elif payload.action == "save":
        return {"status": "saved", "paths": {
            "video": pipeline_state["video_path"],
            "thumbnail": pipeline_state["thumbnail_path"]
        }}

    elif payload.action == "redo":
        if not pipeline_state["config"]:
            raise HTTPException(400, "No config to redo from")
        async def redo():
            config = pipeline_state["config"]
            video_paths = await L7.run(config)
            audio_paths = await L8.run(config)
            video_path = await L9.run(video_paths, audio_paths)
            pipeline_state["video_path"] = video_path
            pipeline_state["video_paths"] = video_paths
            pipeline_state["audio_paths"] = audio_paths
            qc = await L10.run(video_path)
            pipeline_state["qc_result"] = qc
            await emit(10, "done", qc.message, qc.dict())
            await broadcast({"type": "redo_complete", "message": "Re-render complete"})
        background_tasks.add_task(redo)
        return {"status": "redo_started"}

    elif payload.action == "cancel":
        pipeline_state["payload"] = None
        pipeline_state["running"] = False
        return {"status": "cancelled"}

    raise HTTPException(400, f"Unknown action: {payload.action}")

@app.get("/api/channel/analysis")
async def channel_analysis():
    analysis = pipeline_state["channel_analysis"]
    if not analysis:
        return {"connected": False}
    return {"connected": True, "analysis": analysis.dict()}

# YouTube OAuth flow
@app.get("/auth/youtube")
async def auth_youtube():
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/yt-analytics.readonly"
        ]
    )
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    return {"auth_url": auth_url}

@app.get("/auth/callback")
async def auth_callback(code: str):
    from google_auth_oauthlib.flow import Flow
    from db.vault import save_tokens
    from googleapiclient.discovery import build

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=["https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly",
                "https://www.googleapis.com/auth/yt-analytics.readonly"]
    )
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    flow.fetch_token(code=code)
    creds = flow.credentials

    youtube = build("youtube", "v3", credentials=creds)
    ch = youtube.channels().list(part="snippet", mine=True).execute()
    ch_name = ch["items"][0]["snippet"]["title"]
    ch_id = ch["items"][0]["id"]

    await save_tokens(
        creds.token, creds.refresh_token,
        creds.expiry.isoformat() if creds.expiry else "",
        ch_id, ch_name
    )

    return {"status": "connected", "channel": ch_name}

# Serve output files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class SEOOutput(BaseModel):
    primary_topic: str
    seo_keywords: List[str]

class Scene(BaseModel):
    scene_idx: int
    narration: str
    visual_prompt: str

class PipelineConfig(BaseModel):
    video_title: str
    scenes: List[Scene]

class ChannelInsight(BaseModel):
    metric: str
    value: str
    status: str
    note: str

class RerouteInstruction(BaseModel):
    issue: str
    target_layer: int
    layer_name: str
    priority: str
    instruction: str

class ChannelAnalysis(BaseModel):
    channel_name: str
    subscriber_count: int
    total_videos: int
    insights: List[ChannelInsight]
    reroutes: List[RerouteInstruction]

class QCResult(BaseModel):
    passed: bool
    video_duration: float
    audio_duration: float
    frame_rate: float
    bad_scene_idx: Optional[int] = None
    message: str

class ApprovalPayload(BaseModel):
    action: str
    scene_idx: Optional[int] = None

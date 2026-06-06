"""
Layer 13 — Channel Intelligence Analyzer
Connects to the user's YouTube channel via Google Data API v3.
Audits: CTR, avg view duration, engagement rate, top/bottom performers.
Auto-generates RerouteInstruction objects for underperforming areas,
which the pipeline orchestrator injects into the relevant layers.
"""
import os
import logging
from typing import List, Optional
from models.schemas import ChannelAnalysis, ChannelInsight, RerouteInstruction
from db.vault import get_tokens

logger = logging.getLogger(__name__)

THRESHOLDS = {
    "ctr": {"good": 5.0, "warn": 3.0},           # %
    "avg_view_pct": {"good": 50.0, "warn": 35.0}, # % of video watched
    "engagement": {"good": 4.0, "warn": 2.0},     # likes+comments/views %
}

async def run() -> Optional[ChannelAnalysis]:
    tokens = await get_tokens()
    if not tokens:
        logger.warning("Layer 13: No OAuth tokens — skipping channel analysis")
        return None

    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=tokens[1],
            refresh_token=tokens[2],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        )
        youtube = build("youtube", "v3", credentials=creds)
        yt_analytics = build("youtubeAnalytics", "v2", credentials=creds)

        # Get channel info
        ch_resp = youtube.channels().list(part="snippet,statistics", mine=True).execute()
        channel = ch_resp["items"][0]
        ch_name = channel["snippet"]["title"]
        subs = int(channel["statistics"].get("subscriberCount", 0))
        total_videos = int(channel["statistics"].get("videoCount", 0))
        ch_id = channel["id"]

        # Get analytics (last 90 days)
        from datetime import date, timedelta
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=90)).isoformat()

        analytics = yt_analytics.reports().query(
            ids=f"channel=={ch_id}",
            startDate=start, endDate=end,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,subscribersGained,clickThroughRate",
            dimensions="",
        ).execute()

        rows = analytics.get("rows", [[0]*8])
        r = rows[0] if rows else [0]*8
        views, _, avg_dur, avg_pct, likes, comments, _, ctr = r

        engagement = ((likes + comments) / views * 100) if views > 0 else 0
        ctr_val = float(ctr) * 100  # API returns decimal

        # Build insights
        def status(metric, value):
            t = THRESHOLDS[metric]
            if value >= t["good"]:
                return "ok"
            elif value >= t["warn"]:
                return "warn"
            return "bad"

        insights = [
            ChannelInsight(metric="CTR", value=f"{ctr_val:.1f}%",
                          status=status("ctr", ctr_val),
                          note="Below 4% average" if ctr_val < 4 else "Above average"),
            ChannelInsight(metric="Avg retention", value=f"{avg_pct:.0f}%",
                          status=status("avg_view_pct", avg_pct),
                          note=f"{avg_dur:.0f}s avg watch time"),
            ChannelInsight(metric="Engagement", value=f"{engagement:.1f}%",
                          status=status("engagement", engagement),
                          note="Likes + comments / views"),
        ]

        # Build reroute instructions
        reroutes: List[RerouteInstruction] = []

        if ctr_val < THRESHOLDS["ctr"]["good"]:
            reroutes.append(RerouteInstruction(
                issue=f"CTR is {ctr_val:.1f}% — below {THRESHOLDS['ctr']['good']}% target",
                target_layer=11,
                layer_name="Thumbnail Artist",
                priority="high",
                instruction=(
                    "Generate more extreme, high-contrast thumbnail with larger text, "
                    "brighter colors, and a shocked/mysterious expression. "
                    "Focus on faces or dramatic single objects."
                )
            ))

        if avg_pct < THRESHOLDS["avg_view_pct"]["good"]:
            reroutes.append(RerouteInstruction(
                issue=f"Avg retention {avg_pct:.0f}% — hooks need strengthening",
                target_layer=4,
                layer_name="Hook Architect",
                priority="high",
                instruction=(
                    "Make the hook even more shocking and unresolved. "
                    "Add a bold unanswered question in the first 3 seconds. "
                    "Use curiosity gap: state an impossible fact before explaining it."
                )
            ))

        if engagement < THRESHOLDS["engagement"]["good"]:
            reroutes.append(RerouteInstruction(
                issue=f"Engagement {engagement:.1f}% — SEO and CTAs need improvement",
                target_layer=3,
                layer_name="SEO Planner",
                priority="medium",
                instruction=(
                    "Prioritise keywords with high comment intent like 'what do you think', "
                    "'your opinion'. Add CTA lines to script for likes and comments."
                )
            ))

        analysis = ChannelAnalysis(
            channel_name=ch_name,
            subscriber_count=subs,
            total_videos=total_videos,
            insights=insights,
            reroutes=reroutes
        )
        logger.info(f"Layer 13 → {len(reroutes)} improvements routed for '{ch_name}'")
        return analysis

    except Exception as e:
        logger.error(f"Layer 13 error: {e}")
        return None

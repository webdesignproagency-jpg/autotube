import { useState, useEffect, useRef, useCallback } from "react";
import "./index.css";

const API = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

const LAYER_META = {
  13: { name: "Channel analyzer",   phase: 0, color: "special",  desc: "YouTube API → audit CTR, retention, engagement → auto-routes improvements" },
  1:  { name: "Trend scraper",      phase: 1, color: "red",      desc: "pytrends + BeautifulSoup4 → 20 hot topics every 12h" },
  2:  { name: "Duplicate auditor",  phase: 1, color: "red",      desc: "SQLite + TheFuzz fuzzy match → best fresh topic" },
  3:  { name: "SEO planner",        phase: 1, color: "red",      desc: "YouTube autocomplete → top 10 long-tail keywords" },
  4:  { name: "Hook architect",     phase: 2, color: "purple",   desc: "Qwen 2.5 14B → 5-second scroll-stopper hook" },
  5:  { name: "Script continuum",   phase: 2, color: "purple",   desc: "Llama 3 8B → 4-act documentary narration" },
  6:  { name: "Prompt director",    phase: 2, color: "purple",   desc: "Llama 3 → per-scene cinematic visual prompts JSON" },
  7:  { name: "Video render",       phase: 3, color: "teal",     desc: "ComfyUI + Wan 2.1 → GPU-rendered .mp4 scene clips" },
  8:  { name: "Voice engineer",     phase: 3, color: "teal",     desc: "Kokoro-82M (Apache) → studio .wav narration" },
  9:  { name: "Master editor",      phase: 3, color: "teal",     desc: "FFmpeg + MoviePy → stitched output_draft.mp4" },
  10: { name: "Evidence auditor",   phase: 4, color: "amber",    desc: "QC gate → flags & re-renders bad scenes automatically" },
  11: { name: "Thumbnail artist",   phase: 4, color: "amber",    desc: "Flux.1 Schnell + PIL → click-optimised thumbnail.png" },
  12: { name: "Publisher",          phase: 4, color: "amber",    desc: "Google API v3 → packages assets for your approval" },
};

const PHASE_LABELS = {
  0: "Phase 0 — Channel Intelligence",
  1: "Phase 1 — Market Intelligence & SEO",
  2: "Phase 2 — Narrative & Creative Architecture",
  3: "Phase 3 — Asset Generation & Compositing",
  4: "Phase 4 — Quality Control & Distribution",
};

const ORDER = [13, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

export default function App() {
  const [layerStatus, setLayerStatus] = useState({});
  const [pipelineState, setPipelineState] = useState("idle"); // idle|running|awaiting|done
  const [topic, setTopic] = useState("");
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({ produced: 0, scanned: 0, qcRate: "—", published: 0, routed: 0 });
  const [payload, setPayload] = useState(null);
  const [channelAnalysis, setChannelAnalysis] = useState(null);
  const [reroutedLayers, setReroutedLayers] = useState([]);
  const [countdown, setCountdown] = useState("—");
  const [currentLayer, setCurrentLayer] = useState(null);
  const [progress, setProgress] = useState(0);
  const ws = useRef(null);
  const logRef = useRef(null);

  // Countdown timer
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const next = new Date(now);
      next.setHours(now.getHours() < 12 ? 12 : 24, 0, 0, 0);
      const diff = Math.max(0, next - now);
      const h = String(Math.floor(diff / 3600000)).padStart(2, "0");
      const m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, "0");
      const s = String(Math.floor((diff % 60000) / 1000)).padStart(2, "0");
      setCountdown(`${h}:${m}:${s}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const addLog = useCallback((msg, type = "info") => {
    const t = new Date().toLocaleTimeString("en", { hour12: false });
    setLogs(l => [{ t, msg, type, id: Date.now() + Math.random() }, ...l].slice(0, 60));
  }, []);

  // WebSocket connection
  useEffect(() => {
    const connect = () => {
      const socket = new WebSocket(WS_URL);
      ws.current = socket;

      socket.onopen = () => addLog("Connected to AutoTube backend", "system");

      socket.onmessage = (e) => {
        const msg = JSON.parse(e.data);

        if (msg.type === "state_sync") {
          const d = msg.data;
          if (d.running) setPipelineState("running");
          setTopic(d.topic || "");
          if (d.channel_analysis) handleAnalysis(d.channel_analysis);
          d.layers_done?.forEach(n => {
            setLayerStatus(s => ({ ...s, [n]: "done" }));
          });
        }

        if (msg.type === "pipeline_start") {
          setPipelineState("running");
          setProgress(0);
          setLayerStatus({});
          setPayload(null);
          addLog("▶ Pipeline started", "start");
        }

        if (msg.type === "layer_update") {
          const { layer, status, message, data } = msg;
          setLayerStatus(s => ({ ...s, [layer]: status }));
          setCurrentLayer(status === "running" ? layer : null);

          const done = ORDER.filter((n, i) => i < ORDER.indexOf(layer) && status !== "idle").length;
          setProgress(Math.round((ORDER.indexOf(layer)) / ORDER.length * 100));

          addLog(`L${layer} ${LAYER_META[layer]?.name}: ${message}`,
                 status === "error" ? "error" : status === "done" ? "done" : "run");

          if (layer === 13 && status === "done" && data?.reroutes) {
            handleAnalysis(data);
          }
          if (layer === 1 && data?.count) {
            setStats(s => ({ ...s, scanned: data.count }));
          }
          if (layer === 2 && data?.topic) {
            setTopic(data.topic);
          }
          if (layer === 10 && status === "done") {
            setStats(s => ({ ...s, qcRate: "100%" }));
          }
          if (layer === 12 && data) {
            setPayload(data);
          }
        }

        if (msg.type === "pipeline_complete") {
          setPipelineState("awaiting");
          setProgress(100);
          setCurrentLayer(null);
          addLog("✅ All 13 layers complete — awaiting your approval", "complete");
        }

        if (msg.type === "pipeline_error") {
          setPipelineState("idle");
          addLog(`❌ Pipeline error: ${msg.message}`, "error");
        }

        if (msg.type === "uploaded") {
          setPipelineState("done");
          setStats(s => ({ ...s, published: s.published + 1, produced: s.produced + 1 }));
          addLog(`☑ Published: ${msg.data?.url}`, "complete");
        }

        if (msg.type === "redo_complete") {
          setPipelineState("awaiting");
          addLog("↩ Re-render complete — ready for approval", "done");
        }
      };

      socket.onclose = () => {
        addLog("Disconnected — reconnecting in 3s...", "system");
        setTimeout(connect, 3000);
      };

      socket.onerror = () => socket.close();
    };

    connect();
    return () => ws.current?.close();
  }, [addLog]);

  function handleAnalysis(data) {
    setChannelAnalysis(data);
    const layers = data.reroutes?.map(r => r.target_layer) || [];
    setReroutedLayers(layers);
    setStats(s => ({ ...s, routed: data.reroutes?.length || 0 }));
  }

  async function startPipeline() {
    if (pipelineState === "running") return;
    setPipelineState("running");
    setLayerStatus({});
    setLogs([]);
    setProgress(0);
    setTopic("");
    setPayload(null);
    try {
      await fetch(`${API}/api/pipeline/start`, { method: "POST" });
    } catch {
      addLog("Cannot reach backend — is it running on :8000?", "error");
      setPipelineState("idle");
    }
  }

  async function handleApproval(action) {
    try {
      await fetch(`${API}/api/pipeline/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });
      if (action === "save") {
        setStats(s => ({ ...s, produced: s.produced + 1 }));
        setPipelineState("done");
        addLog("💾 Files saved to local output folder", "done");
      }
      if (action === "cancel") {
        setPipelineState("idle");
        setLayerStatus({});
        setProgress(0);
        setCurrentLayer(null);
        addLog("✖ Pipeline cancelled", "system");
      }
    } catch {
      addLog("Backend request failed", "error");
    }
  }

  async function connectChannel() {
    try {
      const r = await fetch(`${API}/auth/youtube`);
      const { auth_url } = await r.json();
      window.open(auth_url, "_blank");
    } catch {
      addLog("Cannot reach backend for OAuth", "error");
    }
  }

  const layersByPhase = [0, 1, 2, 3, 4].map(phase =>
    ORDER.filter(n => LAYER_META[n].phase === phase)
  );

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-left">
          <div className="logo">
            <svg viewBox="0 0 24 24" fill="white" width="20" height="20">
              <path d="M21.8 8s-.2-1.4-.8-2c-.8-.8-1.7-.8-2.1-.9C16.3 5 12 5 12 5s-4.3 0-6.9.1c-.4 0-1.3.1-2.1.9-.6.6-.8 2-.8 2S2 9.6 2 11.2v1.5c0 1.6.2 3.2.2 3.2s.2 1.4.8 2c.8.8 1.8.8 2.3.8C6.7 18.9 12 19 12 19s4.3 0 6.9-.2c.4 0 1.3-.1 2.1-.9.6-.6.8-2 .8-2s.2-1.6.2-3.2v-1.5C22 9.6 21.8 8 21.8 8zM10 15V9l6 3-6 3z"/>
            </svg>
          </div>
          <div>
            <div className="app-title">AutoTube Pipeline</div>
            <div className="app-sub">13-layer AI video automation system</div>
          </div>
        </div>
        <div className="topbar-right">
          <span className={`global-badge badge-${pipelineState}`}>
            {pipelineState === "idle" ? "Idle"
             : pipelineState === "running" ? "Running"
             : pipelineState === "awaiting" ? "Awaiting sign-off"
             : "Complete"}
          </span>
          <button
            className="run-btn"
            onClick={startPipeline}
            disabled={pipelineState === "running"}
          >
            {pipelineState === "running" ? "Running..." : "▶ Run now"}
          </button>
        </div>
      </header>

      <div className="main">
        {/* Stats bar */}
        <div className="stats-row">
          {[
            ["Videos produced", stats.produced],
            ["Topics scanned", stats.scanned],
            ["QC pass rate", stats.qcRate],
            ["Published", stats.published],
            ["Improvements routed", stats.routed],
          ].map(([label, val]) => (
            <div className="stat" key={label}>
              <div className="stat-label">{label}</div>
              <div className="stat-value">{val}</div>
            </div>
          ))}
        </div>

        {/* Trigger bar */}
        <div className="trigger-bar">
          <div><div className="tinfo">Next auto-run (12h cron)</div><div className="tval mono">{countdown}</div></div>
          <div><div className="tinfo">Current topic</div><div className="tval">{topic || "—"}</div></div>
          <div className="prog-section">
            <div className="tinfo">Pipeline progress</div>
            <div className="prog-track"><div className="prog-fill" style={{ width: `${progress}%` }} /></div>
          </div>
          <div><div className="tinfo">Active layer</div>
            <div className="tval">{currentLayer ? `L${currentLayer} — ${LAYER_META[currentLayer]?.name}` : "—"}</div>
          </div>
        </div>

        {/* Layer grid */}
        <div className="layers-section">
          {layersByPhase.map((layerNums, phaseIdx) => (
            <div key={phaseIdx} className="phase-block">
              <div className="phase-label">{PHASE_LABELS[phaseIdx]}</div>
              <div className={`layers-grid ${phaseIdx === 0 ? "grid-1" : ""}`}>
                {layerNums.map(n => {
                  const meta = LAYER_META[n];
                  const status = layerStatus[n] || "idle";
                  const isRerouted = reroutedLayers.includes(n) && n !== 13;
                  return (
                    <div
                      key={n}
                      className={`lcard lcard-${meta.color} ${status === "running" ? "lcard-active" : ""} ${status === "done" ? "lcard-done" : ""}`}
                    >
                      <div className="lcard-head">
                        <span className={`lnum lnum-${meta.color}`}>L{n}</span>
                        <div className={`dot dot-${status}`} />
                        {isRerouted && <span className="reroute-tag">← L13</span>}
                      </div>
                      <div className="lcard-name">{meta.name}</div>
                      <div className="lcard-desc">{meta.desc}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Channel + Review panels */}
        <div className="bottom-grid">
          {/* Channel Intelligence Panel */}
          <div className="panel channel-panel">
            <div className="panel-title">
              <span className="ptitle-icon">📡</span> Channel Intelligence — Layer 13
            </div>
            <div className="ch-connect">
              <div className="ch-avatar">YT</div>
              <div>
                <div className="ch-name">{channelAnalysis?.channel_name || "Your YouTube Channel"}</div>
                <div className="ch-sub">
                  {channelAnalysis
                    ? `Connected · ${channelAnalysis.subscriber_count?.toLocaleString()} subs · ${channelAnalysis.total_videos} videos`
                    : "Not connected"}
                </div>
              </div>
              <button className={`connect-btn ${channelAnalysis ? "connected" : ""}`} onClick={connectChannel}>
                {channelAnalysis ? "✓ Connected" : "Connect channel"}
              </button>
            </div>

            {channelAnalysis ? (
              <>
                <div className="insights-grid">
                  {channelAnalysis.insights?.map(ins => (
                    <div key={ins.metric} className={`insight-card ic-${ins.status}`}>
                      <div className="ic-label">{ins.metric}</div>
                      <div className="ic-val">{ins.value}</div>
                      <div className="ic-note">{ins.note}</div>
                    </div>
                  ))}
                </div>
                <div className="reroutes-label">Auto-routed improvements</div>
                <div className="reroutes-list">
                  {channelAnalysis.reroutes?.map(r => (
                    <div key={r.target_layer} className="reroute-item">
                      <div className="ri-left">
                        <div className="ri-issue">{r.issue}</div>
                        <div className="ri-target">→ {r.layer_name} (L{r.target_layer})</div>
                      </div>
                      <span className={`priority-badge prio-${r.priority}`}>{r.priority}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="ch-placeholder">Connect your channel to enable automatic improvement routing across all layers.</div>
            )}
          </div>

          {/* Review + Log */}
          <div className="panel">
            <div className="panel-title"><span className="ptitle-icon">🎬</span> Media review & approval</div>

            <div className="media-row">
              <div className="media-box">
                <div className="play-circle">▶</div>
                <div className="file-tag">output_draft.mp4</div>
              </div>
              <div className="thumb-box">
                <div className="thumb-icon">🖼</div>
                <div className="file-tag">thumbnail.png</div>
              </div>
            </div>

            {payload && (
              <div className="meta-block">
                <div className="meta-row"><span className="mk">Title</span><span className="mv">{payload.title}</span></div>
                <div className="meta-row"><span className="mk">Topic</span><span className="mv">{payload.topic}</span></div>
                <div className="meta-row"><span className="mk">Tags</span><span className="mv">{payload.tags?.slice(0,4).join(" · ")}</span></div>
              </div>
            )}

            <div className="approval-btns">
              <button className="abtn abtn-primary" onClick={() => handleApproval("upload")} disabled={pipelineState !== "awaiting"}>
                ☁ Auto upload
              </button>
              <button className="abtn" onClick={() => handleApproval("save")} disabled={pipelineState !== "awaiting"}>
                💾 Save only
              </button>
              <button className="abtn abtn-warn" onClick={() => handleApproval("redo")} disabled={pipelineState !== "awaiting"}>
                ↩ Redo scene
              </button>
              <button className="abtn abtn-danger" onClick={() => handleApproval("cancel")}>
                ✕ Cancel
              </button>
            </div>

            <div className="panel-title" style={{ marginTop: "1rem" }}><span className="ptitle-icon">📋</span> Live pipeline log</div>
            <div className="log-list" ref={logRef}>
              {logs.length === 0 && <div className="log-empty">Waiting for run...</div>}
              {logs.map(l => (
                <div key={l.id} className={`log-item log-${l.type}`}>
                  <span className="log-time">{l.t}</span>
                  <span>{l.msg}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

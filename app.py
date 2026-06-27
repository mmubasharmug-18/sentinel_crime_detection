"""
SENTINEL — Crime Detection Dashboard  (Animated Edition)
Run:  python app.py
Open: http://127.0.0.1:8050
"""
import dash, dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx, no_update
import plotly.graph_objects as go
import base64, os, tempfile, time
from datetime import datetime
from collections import deque

from utils.video_stream  import VideoStream, ImageStream
from utils.alert_manager import alert_manager

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True,
    title="SENTINEL | Crime Detection AI",
    update_title=None,
)

<<<<<<< HEAD
server = app.server

=======
>>>>>>> 9a304d7c010b1d371ca0b30fdbb6c9a48458987f
BG      = "#030712"
PANEL   = "#080f1a"
CARD    = "#0a1628"
BORDER  = "#1a2744"
ACCENT  = "#00d4ff"
DANGER  = "#ff2244"
WARNING = "#ff8c00"
SUCCESS = "#00ff88"
MUTED   = "#4a6080"
TEXT    = "#e2e8f0"

_stream       = None
_motion_hist  = deque(maxlen=60)
_time_hist    = deque(maxlen=60)
_upload_path  = None


# ── UI helpers ─────────────────────────────────────────────────────────────

def stat_card(title, val_id, icon, color):
    return html.Div([
        html.Div([
            html.Span(icon, style={"fontSize":"30px"}),
            html.Div(title, style={
                "fontSize":"15px","color":TEXT,"letterSpacing":"2px",
                "fontFamily":"'Courier New',monospace","fontWeight":"700",
                "marginTop":"2px",
            }),
        ], style={"display":"flex","alignItems":"center","gap":"14px","marginBottom":"16px"}),
        html.Div("—", id=val_id, style={
            "fontSize":"52px","fontWeight":"900","color":color,
            "fontFamily":"'Courier New',monospace","lineHeight":"1",
            "textShadow":f"0 0 30px {color}88",
        }),
    ], style={
        "background":   f"linear-gradient(135deg, {CARD}, #0d1f3c)",
        "border":       f"1px solid {color}66",
        "borderRadius": "16px",
        "padding":      "28px 26px",
        "flex":         "1",
        "position":     "relative",
        "overflow":     "hidden",
        "boxShadow":    f"0 0 40px {color}18, inset 0 1px 0 {color}33",
    })

def sidebar_btn(label, btn_id, color):
    return html.Button(label, id=btn_id, n_clicks=0, style={
        "width":"100%","padding":"14px 16px","marginBottom":"10px",
        "background":f"linear-gradient(135deg,{color}22,{color}11)",
        "border":f"1px solid {color}66","borderRadius":"10px",
        "color":color,"cursor":"pointer",
        "fontSize":"15px","fontWeight":"800","letterSpacing":"2px",
        "fontFamily":"'Courier New',monospace",
        "transition":"all .2s",
        "boxShadow":f"0 0 20px {color}22",
    })

def nav_item(icon, label, active=False):
    return html.Div([
        html.Span(icon, style={"fontSize":"18px","color":ACCENT if active else "#8ab0cc","minWidth":"22px"}),
        html.Span(label, style={"fontSize":"16px","fontWeight":"700" if active else "500",
                                "color":TEXT if active else "#adc8e0","letterSpacing":"1px"}),
    ], style={
        "display":"flex","alignItems":"center","gap":"14px",
        "padding":"15px 22px","cursor":"pointer",
        "background":f"linear-gradient(90deg,{ACCENT}22,transparent)" if active else "transparent",
        "borderLeft":f"3px solid {ACCENT}" if active else "3px solid transparent",
        "marginBottom":"4px","transition":"all .2s",
    })


# ── Layout ─────────────────────────────────────────────────────────────────
app.layout = html.Div([

    dcc.Interval(id="tick",       interval=150,  n_intervals=0),
    dcc.Interval(id="chart-tick", interval=2000, n_intervals=0),
    dcc.Store(id="upload-store",  data={"path": None}),
    html.Div(id="sound-trigger",  style={"display":"none"}),

    # ── Particle canvas (fullscreen background) ───────────────────────────
    html.Canvas(id="particle-canvas", style={
        "position":"fixed","top":"0","left":"0",
        "width":"100vw","height":"100vh",
        "zIndex":"0","pointerEvents":"none",
    }),

    # ── Main UI ───────────────────────────────────────────────────────────
    html.Div([

        # ══ SIDEBAR ══════════════════════════════════════════════════════
        html.Div([

            # Logo
            html.Div([
                html.Div("⬡", style={
                    "fontSize":"40px","color":ACCENT,
                    "textShadow":f"0 0 20px {ACCENT}",
                    "lineHeight":"1",
                }),
                html.Div([
                    html.Div("SENTINEL", style={
                        "fontSize":"22px","fontWeight":"900","color":ACCENT,
                        "letterSpacing":"5px","fontFamily":"'Courier New',monospace",
                        "textShadow":f"0 0 20px {ACCENT}88",
                    }),
                    html.Div("CRIME DETECTION AI", style={
                        "fontSize":"9px","color":MUTED,"letterSpacing":"3px",
                        "fontFamily":"'Courier New',monospace",
                    }),
                ]),
            ], style={"display":"flex","alignItems":"center","gap":"14px",
                      "padding":"28px 22px 32px"}),

            # Nav
            nav_item("▣", "Dashboard", active=True),
            nav_item("◉", "Analytics"),
            nav_item("◈", "Alerts"),
            nav_item("◎", "Settings"),

            html.Hr(style={"border":f"1px solid {BORDER}","margin":"20px 16px"}),

            # Controls
            html.Div([
                html.Div("VIDEO SOURCE", style={
                    "fontSize":"13px","color":TEXT,"letterSpacing":"3px",
                    "marginBottom":"16px","fontFamily":"'Courier New',monospace","fontWeight":"700",
                }),
                sidebar_btn("◎  START WEBCAM",   "webcam-btn", ACCENT),
                sidebar_btn("⬛  STOP FEED",      "stop-btn",   DANGER),

                html.Div([
                    html.Div(style={"flex":"1","height":"1px","background":BORDER}),
                    html.Div("or upload video", style={
                        "fontSize":"11px","color":MUTED,"padding":"0 10px","whiteSpace":"nowrap"}),
                    html.Div(style={"flex":"1","height":"1px","background":BORDER}),
                ], style={"display":"flex","alignItems":"center","margin":"14px 0"}),

                dcc.Upload(
                    id="upload-video",
                    children=html.Div([
                        html.Div("⬆", style={"fontSize":"28px","color":ACCENT,
                                             "textShadow":f"0 0 15px {ACCENT}"}),
                        html.Div("Drop video file here", style={
                            "fontSize":"14px","color":TEXT,"marginTop":"6px","fontWeight":"600"}),
                        html.Div(".mp4  .avi  .mov  .mkv", style={
                            "fontSize":"12px","color":MUTED,"marginTop":"3px"}),
                        html.Div(".jpg  .png  .jpeg  .bmp", style={
                            "fontSize":"12px","color":WARNING,"marginTop":"2px"}),
                    ], style={"textAlign":"center","padding":"18px 0"}),
                    style={
                        "border":f"2px dashed {ACCENT}55","borderRadius":"12px",
                        "cursor":"pointer","background":f"{ACCENT}08",
                        "transition":"all .2s",
                    },
                    accept="video/*,image/*",
                ),

                html.Div(id="upload-status", style={
                    "marginTop":"8px","fontSize":"12px","color":SUCCESS,
                    "textAlign":"center","minHeight":"18px",
                }),

                sidebar_btn("▶  ANALYSE VIDEO", "analyse-btn", WARNING),

            ], style={"padding":"0 18px"}),

            html.Hr(style={"border":f"1px solid {BORDER}","margin":"20px 16px"}),

            # System status
            html.Div([
                html.Div("SYSTEM STATUS", style={
                    "fontSize":"13px","color":TEXT,"letterSpacing":"3px",
                    "marginBottom":"14px","fontFamily":"'Courier New',monospace","fontWeight":"700",
                }),
                *[html.Div([
                    html.Span(lbl, style={"fontSize":"15px","color":"#adc8e0","fontWeight":"500"}),
                    html.Span(val, id=vid, style={"fontSize":"15px","color":col,
                                                   "fontWeight":"700"}),
                ], style={"display":"flex","justifyContent":"space-between",
                          "marginBottom":"12px"})
                for lbl, val, vid, col in [
                    ("AI Engine", "READY",  "ai-status",    SUCCESS),
                    ("Camera",    "—",      "cam-status",   WARNING),
                    ("Alerts",    "0",      "alert-count-side", ACCENT),
                ]],
            ], style={"padding":"0 18px 24px"}),

        ], style={
            "width":"260px","minWidth":"260px",
            "background":f"linear-gradient(180deg,{PANEL},{BG})",
            "borderRight":f"1px solid {BORDER}",
            "display":"flex","flexDirection":"column",
            "height":"100vh","overflowY":"auto",
            "position":"relative","zIndex":"1",
        }),

        # ══ MAIN CONTENT ═════════════════════════════════════════════════
        html.Div([

            # Top bar
            html.Div([
                html.Div([
                    html.Div("SURVEILLANCE DASHBOARD", style={
                        "fontSize":"26px","fontWeight":"900","color":TEXT,
                        "letterSpacing":"6px","fontFamily":"'Courier New',monospace",
                        "textShadow":f"0 0 30px {ACCENT}44",
                    }),
                    html.Div("—", id="sys-time", style={
                        "fontSize":"15px","color":ACCENT,"marginTop":"6px",
                        "fontFamily":"'Courier New',monospace","fontWeight":"600",
                        "letterSpacing":"2px",
                    }),
                ], style={"textAlign":"left"}),
                html.Div([
                    html.Div("● OFFLINE", id="live-badge", style={
                        "fontSize":"16px","color":MUTED,
                        "fontFamily":"'Courier New',monospace","fontWeight":"700",
                    }),
                    html.Div("0 FPS", id="fps-disp", style={
                        "fontSize":"16px","color":ACCENT,
                        "fontFamily":"'Courier New',monospace","fontWeight":"700",
                    }),
                ], style={"display":"flex","gap":"28px","alignItems":"center"}),
            ], style={
                "display":"flex","justifyContent":"space-between","alignItems":"center",
                "padding":"22px 32px",
                "borderBottom":f"1px solid {BORDER}",
                "background":f"linear-gradient(90deg,{PANEL}ee,{BG}cc)",
                "position":"relative","zIndex":"1",
                "backdropFilter":"blur(10px)",
            }),

            # Stat cards
            html.Div([
                stat_card("TOTAL ALERTS",  "s-total",  "🚨", DANGER),
                stat_card("HIGH SEVERITY", "s-high",   "⚠",  DANGER),
                stat_card("MEDIUM",        "s-medium", "◉",  WARNING),
                stat_card("MOTION LEVEL",  "s-motion", "〜", ACCENT),
            ], style={"display":"flex","gap":"22px","padding":"26px 32px 0",
                      "position":"relative","zIndex":"1"}),

            # Video + Alerts row
            html.Div([

                # Video panel
                html.Div([
                    # Header
                    html.Div([
                        html.Div([
                            html.Span("◉", style={"color":ACCENT,"fontSize":"14px",
                                                   "animation":"pulse 1.5s infinite"}),
                            html.Span(" LIVE FEED", style={
                                "fontSize":"16px","color":ACCENT,"letterSpacing":"3px",
                                "fontFamily":"'Courier New',monospace","fontWeight":"700",
                            }),
                        ]),
                        html.Span("SCANNING…", id="det-badge", style={
                            "fontSize":"12px","padding":"5px 14px","borderRadius":"20px",
                            "background":f"{MUTED}22","color":MUTED,
                            "fontFamily":"'Courier New',monospace","fontWeight":"700",
                        }),
                    ], style={
                        "display":"flex","justifyContent":"space-between",
                        "alignItems":"center","padding":"18px 20px 12px",
                    }),

                    # Video
                    html.Div([
                        html.Img(id="video-img", src="", style={
                            "width":"100%","borderRadius":"10px","display":"none",
                        }),
                        html.Div([
                            html.Div("◎", style={"fontSize":"56px","color":BORDER}),
                            html.Div("No Feed Active", style={
                                "color":MUTED,"marginTop":"12px",
                                "fontFamily":"'Courier New',monospace",
                                "fontSize":"16px","letterSpacing":"2px",
                            }),
                            html.Div("Start webcam or upload a video", style={
                                "color":MUTED,"fontSize":"12px","marginTop":"6px",
                            }),
                        ], id="no-feed", style={
                            "display":"flex","flexDirection":"column",
                            "alignItems":"center","justifyContent":"center",
                            "height":"340px",
                        }),
                    ], style={"padding":"0 16px 12px"}),

                    # Threat bar
                    html.Div([
                        html.Div([
                            html.Span("THREAT LEVEL", style={
                                "fontSize":"11px","color":MUTED,
                                "letterSpacing":"2px","fontFamily":"'Courier New',monospace",
                            }),
                            html.Span(id="threat-pct", children="0%", style={
                                "fontSize":"11px","color":ACCENT,
                                "fontFamily":"'Courier New',monospace",
                            }),
                        ], style={"display":"flex","justifyContent":"space-between",
                                  "marginBottom":"8px"}),
                        html.Div(style={
                            "background":BORDER,"borderRadius":"6px",
                            "height":"8px","overflow":"hidden",
                        }, children=html.Div(id="threat-bar", style={
                            "height":"100%","width":"0%","borderRadius":"6px",
                            "background":f"linear-gradient(90deg,{SUCCESS},{WARNING},{DANGER})",
                            "transition":"width .4s ease",
                            "boxShadow":f"0 0 10px {ACCENT}88",
                        })),
                    ], style={"padding":"0 20px 20px"}),

                ], style={
                    "flex":"1.8",
                    "background":f"linear-gradient(135deg,{CARD},{PANEL})",
                    "border":f"1px solid {BORDER}","borderRadius":"16px",
                    "boxShadow":f"0 0 40px {ACCENT}08",
                }),

                # Alert log
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("⚠", style={"color":DANGER,"fontSize":"16px"}),
                            html.Span(" ALERT LOG", style={
                                "fontSize":"16px","color":DANGER,
                                "letterSpacing":"3px","fontWeight":"700",
                                "fontFamily":"'Courier New',monospace",
                            }),
                        ]),
                        html.Button("CLEAR", id="clear-btn", n_clicks=0, style={
                            "fontSize":"11px","padding":"5px 14px",
                            "background":"transparent",
                            "border":f"1px solid {BORDER}","borderRadius":"6px",
                            "color":MUTED,"cursor":"pointer","letterSpacing":"1px",
                            "fontFamily":"'Courier New',monospace",
                        }),
                    ], style={
                        "display":"flex","justifyContent":"space-between",
                        "alignItems":"center","padding":"18px 20px 12px",
                    }),
                    html.Div(id="alert-log", children=[
                        html.Div("No alerts yet…", style={
                            "color":MUTED,"fontSize":"14px","textAlign":"center",
                            "marginTop":"50px","fontFamily":"'Courier New',monospace",
                        }),
                    ], style={"overflowY":"auto","maxHeight":"400px",
                              "padding":"0 16px 16px"}),
                ], style={
                    "flex":"1",
                    "background":f"linear-gradient(135deg,{CARD},{PANEL})",
                    "border":f"1px solid {BORDER}","borderRadius":"16px",
                    "display":"flex","flexDirection":"column",
                    "boxShadow":f"0 0 40px {DANGER}08",
                }),

            ], style={"display":"flex","gap":"22px","padding":"22px 32px",
                      "flex":"1","position":"relative","zIndex":"1"}),

            # Charts row
            html.Div([
                html.Div([
                    html.Div("MOTION TIMELINE", style={
                        "fontSize":"16px","color":ACCENT,"letterSpacing":"3px",
                        "padding":"18px 20px 8px","fontFamily":"'Courier New',monospace",
                        "fontWeight":"800",
                    }),
                    dcc.Graph(id="motion-chart", config={"displayModeBar":False},
                              style={"height":"180px"}),
                ], style={
                    "flex":"2","background":f"linear-gradient(135deg,{CARD},{PANEL})",
                    "border":f"1px solid {BORDER}","borderRadius":"16px",
                }),
                html.Div([
                    html.Div("SEVERITY BREAKDOWN", style={
                        "fontSize":"16px","color":ACCENT,"letterSpacing":"3px",
                        "padding":"18px 20px 8px","fontFamily":"'Courier New',monospace",
                        "fontWeight":"800",
                    }),
                    dcc.Graph(id="sev-chart", config={"displayModeBar":False},
                              style={"height":"180px"}),
                ], style={
                    "flex":"1","background":f"linear-gradient(135deg,{CARD},{PANEL})",
                    "border":f"1px solid {BORDER}","borderRadius":"16px",
                }),
            ], style={"display":"flex","gap":"22px","padding":"0 32px 28px",
                      "position":"relative","zIndex":"1"}),

        ], style={
            "flex":"1","display":"flex","flexDirection":"column",
            "background":"transparent","overflowY":"auto",
        }),

    ], style={"display":"flex","height":"100vh","overflow":"hidden",
              "position":"relative","zIndex":"1"}),

], style={
    "fontFamily":"'Segoe UI',sans-serif","color":TEXT,
    "background":BG,"position":"relative",
})


# ── Callbacks ──────────────────────────────────────────────────────────────

@app.callback(
    Output("upload-status", "children"),
    Output("upload-store",  "data"),
    Input("upload-video",   "contents"),
    State("upload-video",   "filename"),
    prevent_initial_call=True,
)
def handle_upload(contents, filename):
    global _upload_path
    if not contents:
        return "", {"path": None}
    try:
        _, encoded = contents.split(",", 1)
        data      = base64.b64decode(encoded)
        ext       = os.path.splitext(filename)[1].lower() or ".mp4"
        fd, path  = tempfile.mkstemp(suffix=ext, dir=tempfile.gettempdir())
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        _upload_path = path
        size_mb = len(data) / 1_048_576
        is_img  = ext in [".jpg",".jpeg",".png",".bmp",".webp"]
        kind    = "IMAGE" if is_img else "VIDEO"
        return f"✓ [{kind}] {filename[:22]} ({size_mb:.1f} MB)", {"path": path}
    except Exception as e:
        return f"⚠ {e}", {"path": None}


@app.callback(
    Output("cam-status", "children"),
    Output("cam-status", "style"),
    Input("webcam-btn",  "n_clicks"),
    Input("stop-btn",    "n_clicks"),
    Input("analyse-btn", "n_clicks"),
    prevent_initial_call=True,
)
def source_control(wc, stop, analyse):
    global _stream, _upload_path
    triggered = ctx.triggered_id

    def stop_stream():
        global _stream
        if _stream and _stream.is_running:
            _stream.stop()
        _stream = None

    sty_ok  = {"fontSize":"13px","color":SUCCESS,"fontWeight":"600"}
    sty_err = {"fontSize":"13px","color":DANGER,  "fontWeight":"600"}
    sty_off = {"fontSize":"13px","color":MUTED,   "fontWeight":"600"}

    if triggered == "webcam-btn":
        stop_stream()
        for idx in [0, 1, 2]:
            try:
                s = VideoStream(source=idx)
                s.start()
                # Wait briefly then check if capture thread is running
                time.sleep(0.5)
                if s.is_running:
                    _stream = s
                    return "ACTIVE", sty_ok
                s.stop()
            except Exception as e:
                print(f"Webcam {idx} failed: {e}")
        return "NO CAMERA", sty_err

    elif triggered == "stop-btn":
        stop_stream()
        return "OFFLINE", sty_off

    elif triggered == "analyse-btn":
        if not _upload_path or not os.path.exists(_upload_path):
            return "NO FILE", sty_err
        stop_stream()
        # Check if image file
        ext = os.path.splitext(_upload_path)[1].lower()
        if ext in [".jpg",".jpeg",".png",".bmp",".webp"]:
            # Image mode: use ImageStream wrapper
            try:
                s = ImageStream(source=_upload_path)
                s.start()
                time.sleep(0.3)
                _stream = s
                return "IMAGE", sty_ok
            except Exception as e:
                print(f"Image stream error: {e}")
                return "ERROR", sty_err
        else:
            try:
                s = VideoStream(source=_upload_path)
                s.start()
                time.sleep(0.3)
                _stream = s
                return "ACTIVE", sty_ok
            except Exception as e:
                print(f"Upload stream error: {e}")
                return "ERROR", sty_err

    return no_update, no_update


@app.callback(
    Output("video-img",        "src"),
    Output("video-img",        "style"),
    Output("no-feed",          "style"),
    Output("det-badge",        "children"),
    Output("det-badge",        "style"),
    Output("threat-bar",       "style"),
    Output("threat-pct",       "children"),
    Output("s-total",          "children"),
    Output("s-high",           "children"),
    Output("s-medium",         "children"),
    Output("s-motion",         "children"),
    Output("fps-disp",         "children"),
    Output("live-badge",       "children"),
    Output("live-badge",       "style"),
    Output("alert-log",        "children"),
    Output("sys-time",         "children"),
    Output("alert-count-side", "children"),
    Input("tick",              "n_intervals"),
)
def tick(_):
    global _stream, _motion_hist, _time_hist
    now   = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    stats = alert_manager.stats()

    img_hide = {"display":"none"}
    ph_show  = {"display":"flex","flexDirection":"column",
                "alignItems":"center","justifyContent":"center","height":"340px"}
    ph_hide  = {"display":"none"}

    def badge(color, text):
        return text, {
            "fontSize":"13px","padding":"6px 16px","borderRadius":"20px",
            "background":f"{color}25","color":color,
            "fontFamily":"'Courier New',monospace","fontWeight":"700",
            "border":f"1px solid {color}66",
            "boxShadow":f"0 0 15px {color}44",
        }

    def bar(pct):
        pct_int = min(int(pct * 100), 100)
        return ({"height":"100%","width":f"{pct_int}%","borderRadius":"6px",
                 "background":f"linear-gradient(90deg,{SUCCESS},{WARNING},{DANGER})",
                 "transition":"width .4s ease","boxShadow":f"0 0 12px {ACCENT}88"},
                f"{pct_int}%")

    def alerts_html():
        items = alert_manager.get_recent(30)
        if not items:
            return [html.Div("No alerts yet…", style={
                "color":MUTED,"fontSize":"14px","textAlign":"center",
                "marginTop":"50px","fontFamily":"'Courier New',monospace",
            })]
        rows = []
        for a in items:
            c = {"HIGH":DANGER,"MEDIUM":WARNING,"LOW":ACCENT}.get(a["severity"], MUTED)
            rows.append(html.Div([
                html.Div([
                    html.Span(f"#{a['id']}", style={
                        "color":c,"fontWeight":"800",
                        "fontFamily":"'Courier New',monospace","fontSize":"14px",
                    }),
                    html.Span(a["severity"], style={
                        "fontSize":"11px","padding":"3px 10px","borderRadius":"10px",
                        "background":f"{c}22","color":c,"fontWeight":"700",
                        "letterSpacing":"1px",
                    }),
                    html.Span(a.get("reason",""), style={
                        "fontSize":"10px","color":MUTED,"fontStyle":"italic",
                    }),
                ], style={"display":"flex","gap":"8px","alignItems":"center"}),
                html.Div([
                    html.Span(a["time"],  style={"fontSize":"12px","color":MUTED}),
                    html.Span(f"Conf: {a['confidence']*100:.0f}%",
                              style={"fontSize":"12px","color":TEXT,"fontWeight":"600"}),
                    html.Span(a["source"],style={"fontSize":"11px","color":MUTED}),
                ], style={"display":"flex","gap":"10px","marginTop":"4px"}),
            ], style={
                "padding":"12px 14px","borderRadius":"10px","marginBottom":"8px",
                "background":f"{c}0d","border":f"1px solid {c}44",
                "boxShadow":f"0 0 20px {c}11",
            }))
        return rows

    # No stream
    if _stream is None or not _stream.is_running:
        bt, bs = badge(MUTED, "OFFLINE")
        bar_s, bar_p = bar(0)
        return ("", img_hide, ph_show, bt, bs, bar_s, bar_p,
                str(stats["total"]), str(stats["high"]), str(stats["medium"]), "0.0",
                "0 FPS", "● OFFLINE",
                {"fontSize":"14px","color":MUTED,"fontFamily":"'Courier New',monospace","fontWeight":"700"},
                alerts_html(), now, str(stats["total"]))

    b64, result = _stream.get_latest()

    if not b64:
        bt, bs = badge(WARNING, "CONNECTING…")
        bar_s, bar_p = bar(0)
        return ("", img_hide, ph_show, bt, bs, bar_s, bar_p,
                str(stats["total"]), str(stats["high"]), str(stats["medium"]), "0.0",
                f"{_stream.fps:.0f} FPS", "● CONNECTING",
                {"fontSize":"14px","color":WARNING,"fontFamily":"'Courier New',monospace","fontWeight":"700"},
                alerts_html(), now, str(stats["total"]))

    _time_hist.append(datetime.now().strftime("%H:%M:%S"))
    _motion_hist.append(result.get("motion", 0))

    if result.get("new_alert"):
        src = "webcam" if isinstance(_stream.source, int) else "upload"
        alert_manager.add(result, source=src)

    violent    = result.get("violent", False)
    confidence = result.get("confidence", 0.0)
    motion     = result.get("motion", 0.0)

    if violent:
        bt, bs = badge(DANGER, "⚠ VIOLENCE DETECTED")
    elif motion > 1.500:
        bt, bs = badge(WARNING, "◉ MOTION DETECTED")
    else:
        bt, bs = badge(SUCCESS, "✓ NORMAL")

    img_style = {
        "width":"100%","borderRadius":"10px","display":"block",
        "border":   f"3px solid {DANGER}" if violent else "3px solid transparent",
        "boxShadow":f"0 0 40px {DANGER}88" if violent else "none",
        "transition":"box-shadow .3s",
    }

    bar_s, bar_p = bar(confidence)
    stats = alert_manager.stats()
    return (b64, img_style, ph_hide, bt, bs, bar_s, bar_p,
            str(stats["total"]), str(stats["high"]), str(stats["medium"]),
            f"{motion:.3f}", f"{_stream.fps:.0f} FPS",
            "● LIVE",
            {"fontSize":"14px","color":SUCCESS,"fontFamily":"'Courier New',monospace","fontWeight":"700"},
            alerts_html(), now, str(stats["total"]))


@app.callback(
    Output("motion-chart", "figure"),
    Output("sev-chart",    "figure"),
    Input("chart-tick",    "n_intervals"),
)
def update_charts(_):
    times   = list(_time_hist)
    motions = list(_motion_hist)
    if times:
        mfig = go.Figure()
        mfig.add_trace(go.Scatter(
            x=times, y=motions, mode="lines",
            fill="tozeroy", fillcolor="rgba(0,212,255,0.10)",
            line=dict(color=ACCENT, width=2.5),
        ))
        mfig.add_hline(y=1.4, line=dict(color=DANGER, dash="dash", width=1.5),
                       annotation_text="Violence Threshold",
                       annotation_font=dict(color=DANGER, size=10))
    else:
        mfig = go.Figure()

    mfig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=16, t=10, b=32), showlegend=False,
        xaxis=dict(showgrid=False, color=MUTED, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor=BORDER, color=MUTED, tickfont=dict(size=10)),
        font=dict(color=MUTED, family="Courier New"),
    )

    st = alert_manager.stats()
    if st["total"] > 0:
        sfig = go.Figure(go.Pie(
            labels=["HIGH", "MEDIUM", "LOW"],
            values=[st["high"], st["medium"], st["low"]],
            hole=0.60,
            marker=dict(colors=[DANGER, WARNING, ACCENT],
                        line=dict(color=BG, width=3)),
            textfont=dict(size=13, color=TEXT),
        ))
    else:
        sfig = go.Figure()

    sfig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=10, b=10),
        showlegend=True, font=dict(color=MUTED, family="Courier New"),
        legend=dict(font=dict(color=TEXT, size=12), bgcolor="rgba(0,0,0,0)"),
    )
    return mfig, sfig


@app.callback(
    Output("alert-log", "children", allow_duplicate=True),
    Input("clear-btn",  "n_clicks"),
    prevent_initial_call=True,
)
def clear_alerts(_):
    alert_manager.clear()
    _motion_hist.clear()
    _time_hist.clear()
    return [html.Div("No alerts yet…", style={
        "color":MUTED,"fontSize":"14px","textAlign":"center",
        "marginTop":"50px","fontFamily":"'Courier New',monospace",
    })]


# ── Sound + Particle Animation (clientside) ────────────────────────────────
app.clientside_callback(
    """
    function(badge_text) {
        /* ── Particle network animation ── */
        if (!window._particleInit) {
            window._particleInit = true;
            var canvas = document.getElementById('particle-canvas');
            if (canvas) {
                var ctx = canvas.getContext('2d');
                var W = window.innerWidth, H = window.innerHeight;
                canvas.width = W; canvas.height = H;
                window.addEventListener('resize', function() {
                    W = canvas.width  = window.innerWidth;
                    H = canvas.height = window.innerHeight;
                });

                var DOTS = 90;
                var mouse = {x: W/2, y: H/2};
                document.addEventListener('mousemove', function(e) {
                    mouse.x = e.clientX; mouse.y = e.clientY;
                });

                var dots = [];
                for (var i = 0; i < DOTS; i++) {
                    dots.push({
                        x: Math.random()*W, y: Math.random()*H,
                        vx: (Math.random()-0.5)*0.5,
                        vy: (Math.random()-0.5)*0.5,
                        r: Math.random()*2.5+1
                    });
                }

                function draw() {
                    ctx.clearRect(0,0,W,H);
                    /* move */
                    dots.forEach(function(d) {
                        d.x += d.vx; d.y += d.vy;
                        if (d.x<0||d.x>W) d.vx*=-1;
                        if (d.y<0||d.y>H) d.vy*=-1;
                    });
                    /* lines between close dots */
                    for (var i=0;i<dots.length;i++) {
                        for (var j=i+1;j<dots.length;j++) {
                            var dx=dots[i].x-dots[j].x, dy=dots[i].y-dots[j].y;
                            var dist=Math.sqrt(dx*dx+dy*dy);
                            if (dist<160) {
                                ctx.beginPath();
                                ctx.moveTo(dots[i].x,dots[i].y);
                                ctx.lineTo(dots[j].x,dots[j].y);
                                ctx.strokeStyle='rgba(255,255,255,'+(0.20*(1-dist/160))+')';
                                ctx.lineWidth=0.8;
                                ctx.stroke();
                            }
                        }
                        /* lines to mouse */
                        var mx=dots[i].x-mouse.x, my=dots[i].y-mouse.y;
                        var mdist=Math.sqrt(mx*mx+my*my);
                        if (mdist<220) {
                            ctx.beginPath();
                            ctx.moveTo(dots[i].x,dots[i].y);
                            ctx.lineTo(mouse.x,mouse.y);
                            ctx.strokeStyle='rgba(255,255,255,'+(0.40*(1-mdist/220))+')';
                            ctx.lineWidth=1;
                            ctx.stroke();
                        }
                    }
                    /* dots */
                    dots.forEach(function(d) {
                        ctx.beginPath();
                        ctx.arc(d.x,d.y,d.r,0,Math.PI*2);
                        ctx.fillStyle='rgba(255,255,255,0.7)';
                        ctx.fill();
                    });
                    requestAnimationFrame(draw);
                }
                draw();
            }
        }

        /* ── Violence sound ── */
        if (!badge_text) return "";
        if (badge_text.indexOf("VIOLENCE") !== -1) {
            try {
                if (!window._sCtx) {
                    window._sCtx = new (window.AudioContext||window.webkitAudioContext)();
                }
                var now = Date.now();
                if (!window._sLast || now - window._sLast > 3000) {
                    window._sLast = now;
                    var c = window._sCtx;
                    [0, 0.38, 0.76].forEach(function(delay) {
                        var osc=c.createOscillator(), g=c.createGain();
                        osc.connect(g); g.connect(c.destination);
                        osc.type='square'; osc.frequency.value=880;
                        var t=c.currentTime+delay;
                        g.gain.setValueAtTime(0.5,t);
                        g.gain.exponentialRampToValueAtTime(0.001,t+0.3);
                        osc.start(t); osc.stop(t+0.32);
                    });
                }
            } catch(e) {}
        }
        return "";
    }
    """,
    Output("sound-trigger", "children"),
    Input("det-badge", "children"),
    prevent_initial_call=False,
)


# ── Global CSS ─────────────────────────────────────────────────────────────
app.index_string = """<!DOCTYPE html>
<html>
<head>
    {%metas%}<title>{%title%}</title>{%favicon%}{%css%}
    <style>
        * { box-sizing:border-box; margin:0; padding:0; }
        body { background:#030712; overflow:hidden; }
        ::-webkit-scrollbar { width:5px; }
        ::-webkit-scrollbar-track { background:#080f1a; }
        ::-webkit-scrollbar-thumb { background:#1a2744; border-radius:3px; }
        @keyframes pulse {
            0%,100% { opacity:1; text-shadow:0 0 10px #00d4ff; }
            50%      { opacity:0.4; text-shadow:0 0 3px #00d4ff; }
        }
        @keyframes fadeInUp {
            from { opacity:0; transform:translateY(10px); }
            to   { opacity:1; transform:translateY(0); }
        }
        button:hover { filter:brightness(1.2) !important; transform:translateY(-1px); }
        button { transition: all .2s !important; }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>"""


# ── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  SENTINEL — Crime Detection AI Dashboard")
    print("  http://127.0.0.1:7860")
    print("="*55 + "\n")
    app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 7860)),
    debug=False
)

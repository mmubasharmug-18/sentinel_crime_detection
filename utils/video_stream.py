"""
Smooth Video Stream — 2-Thread Architecture
============================================
Thread 1 (CAPTURE): reads frames at full camera speed, never waits for YOLO
Thread 2 (DETECT):  runs YOLO on latest frame at its own pace

Key fix: YOLO runs in detect thread, capture thread is NEVER blocked.
Video plays smooth at 25-30 FPS. YOLO updates boxes at ~8-10 FPS separately.
"""
import cv2, base64, threading, time, numpy as np
from utils.detector import CrimeDetector, annotate_frame

DISPLAY_W = 800
DISPLAY_H = 480
DETECT_W  = 320   # smaller = faster YOLO
DETECT_H  = 320
JPEG_Q    = 72


class VideoStream:
    def __init__(self, source=0):
        self.source      = source
        self.detector    = CrimeDetector()
        self._cap        = None
        self._stop_evt   = threading.Event()
        self._running    = False

        # Latest display frame (written by capture, read by detect+UI)
        self._frame_lock = threading.Lock()
        self._disp_frame = None   # latest display-size frame
        self._frame_id   = 0      # increments each new frame

        # Latest detection result (written by detect, read by UI)
        self._result_lock = threading.Lock()
        self._last_result = {}
        self._last_boxes  = []    # cached boxes from last YOLO run

        # Output for UI (written by capture after drawing cached boxes)
        self._out_lock = threading.Lock()
        self._out_b64  = ""
        self._out_res  = {}

        self._fps        = 0.0
        self._last_fid   = -1    # frame_id last processed by detect thread

    def start(self):
        if self._running:
            return
        self._stop_evt.clear()
        self.detector.reset()
        self._last_result = {}
        self._last_boxes  = []
        self._out_b64     = ""
        self._frame_id    = 0

        if isinstance(self.source, int):
            self._cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._cap.set(cv2.CAP_PROP_FPS, 30)
        else:
            self._cap = cv2.VideoCapture(self.source)

        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open: {self.source}")

        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._running = True

        threading.Thread(target=self._capture_loop, daemon=True).start()
        threading.Thread(target=self._detect_loop,  daemon=True).start()

    def stop(self):
        self._stop_evt.set()
        self._running = False
        time.sleep(0.3)
        if self._cap:
            self._cap.release()
            self._cap = None
        with self._out_lock:
            self._out_b64 = ""
            self._out_res = {}

    def get_latest(self):
        with self._out_lock:
            return self._out_b64, dict(self._out_res)

    @property
    def is_running(self):
        return self._running

    @property
    def fps(self):
        return self._fps

    # ── Thread 1: CAPTURE + ANNOTATE ─────────────────────────────────
    # Reads every frame. Draws CACHED boxes from last YOLO result.
    # Encodes and stores output. Never waits for YOLO.

    def _capture_loop(self):
        t0 = time.time()
        fc = 0

        while not self._stop_evt.is_set():
            ok, raw = self._cap.read()
            if not ok:
                if isinstance(self.source, int):
                    time.sleep(0.005)
                    continue
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            fc += 1

            # Resize for display
            disp = cv2.resize(raw, (DISPLAY_W, DISPLAY_H),
                              interpolation=cv2.INTER_LINEAR)

            # Store latest frame for detect thread
            with self._frame_lock:
                self._disp_frame = disp
                self._frame_id  += 1

            # Get latest detection result (non-blocking)
            with self._result_lock:
                result = dict(self._last_result)

            # If no result yet, create a basic one with just optical flow
            if not result:
                result = {
                    "motion": 0.0, "confidence": 0.0,
                    "violent": False, "new_alert": False,
                    "detections": [], "reason": "",
                    "yolo_status": "LOADING...",
                    "timestamp": "",
                    "date": "",
                }

            # Draw cached boxes on current frame (smooth — no YOLO wait)
            annotated = annotate_frame(disp.copy(), result)
            b64       = _enc(annotated)

            with self._out_lock:
                self._out_b64 = b64
                self._out_res = result

            # FPS counter
            elapsed = time.time() - t0
            if elapsed >= 1.0:
                self._fps = fc / elapsed
                fc = 0
                t0 = time.time()

    # ── Thread 2: DETECT ─────────────────────────────────────────────
    # Waits for a new frame, runs YOLO+flow, stores result.
    # Runs at YOLO speed (~8-10fps). Does NOT block capture thread.

    def _detect_loop(self):
        while not self._stop_evt.is_set():
            # Get latest frame
            with self._frame_lock:
                frame    = self._disp_frame
                frame_id = self._frame_id

            # Skip if no new frame since last detection
            if frame is None or frame_id == self._last_fid:
                time.sleep(0.02)
                continue

            self._last_fid = frame_id

            # Resize smaller for faster YOLO
            small = cv2.resize(frame, (DETECT_W, DETECT_H),
                               interpolation=cv2.INTER_LINEAR)

            # Run detection (this is the slow part — ~80-120ms)
            result = self.detector.process_frame(small)

            # Scale boxes back to display size
            result = _scale_boxes(result, DETECT_W, DETECT_H,
                                  DISPLAY_W, DISPLAY_H)

            with self._result_lock:
                self._last_result = result


# ── helpers ───────────────────────────────────────────────────────────────

def _scale_boxes(result, sw, sh, dw, dh):
    sx = dw / sw
    sy = dh / sh
    scaled = [(lbl, cf, int(x1*sx), int(y1*sy), int(x2*sx), int(y2*sy))
              for (lbl, cf, x1, y1, x2, y2) in result.get("detections", [])]
    r = dict(result)
    r["detections"] = scaled
    return r


def _enc(frame):
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_Q])
    return ("data:image/jpeg;base64," +
            base64.b64encode(buf).decode()) if ok else ""


# ── ImageStream — shows a single image with detection ─────────────────────

class ImageStream:
    """Wraps a single image file so the dashboard treats it like a video."""

    def __init__(self, source):
        self.source   = source
        self._b64     = ""
        self._result  = {}
        self._running = False
        self._fps     = 0.0

    def start(self):
        import cv2, numpy as np
        from utils.detector import detect_image

        img = cv2.imread(self.source)
        if img is None:
            raise RuntimeError(f"Cannot read image: {self.source}")

        annotated, result = detect_image(img)
        self._b64     = _enc(annotated)
        self._result  = result
        self._running = True
        self._fps     = 0.0

    def stop(self):
        self._running = False
        self._b64     = ""
        self._result  = {}

    def get_latest(self):
        return self._b64, dict(self._result)

    @property
    def is_running(self):
        return self._running

    @property
    def fps(self):
        return self._fps
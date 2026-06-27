"""
SENTINEL Crime Detection Engine — Final
========================================
Models used:
  yolov8n.pt  — persons, cars, knife, scissors (COCO 80 classes)
  weapon.pt   — pistol, rifle (class 0 and 1 only, conf >= 0.75)
  fight.pt    — fight detection (place in project folder to activate)

Motion rules:
  Normal     : motion < 1.50
  Suspicious : 1.50 <= motion < 3.50
  Violence   : motion >= 3.50
"""
import cv2, numpy as np, time, os, threading
from datetime import datetime
from collections import deque

COCO_DANGER       = {"knife", "scissors", "baseball bat"}
MOTION_SUSPICIOUS = 1.50
MOTION_VIOLENT    = 3.50
HISTORY_FRAMES    = 8
ALERT_COOLDOWN    = 5

_HERE            = os.path.dirname(os.path.abspath(__file__))
_PROJ            = os.path.dirname(_HERE)
_MODEL_PT        = os.path.join(_PROJ, "yolov8n.pt")
_WEAPON_MODEL_PT = os.path.join(_PROJ, "weapon.pt")
_FIGHT_MODEL_PT  = os.path.join(_PROJ, "fight.pt")

_model        = None   # yolov8n
_weapon_model = None   # weapon.pt
_fight_model  = None   # fight.pt
_model_ready  = False
_weapon_ready = False
_fight_ready  = False
_fight_classes = {}    # {class_id: name} from fight.pt
_fight_violence_ids = set()  # class ids that mean "fight/violence"

_WEAPON_CLASS_MAP = {
    "0": "Pistol", "1": "Rifle", "2": "Knife",
    "3": "Grenade", "4": "Weapon", "5": "Weapon",
}


def _load_models():
    global _model, _weapon_model, _fight_model
    global _model_ready, _weapon_ready, _fight_ready
    global _fight_classes, _fight_violence_ids

    # ── yolov8n ────────────────────────────────────────────────────────
    try:
        from ultralytics import YOLO
        print(f"[SENTINEL] Loading {_MODEL_PT}")
        m = YOLO(_MODEL_PT)
        m(np.zeros((320,320,3), dtype=np.uint8), verbose=False, conf=0.25)
        _model       = m
        _model_ready = True
        print("[SENTINEL] yolov8n ready ✓")
    except Exception as e:
        print(f"[SENTINEL] yolov8n error: {e}")

    # ── weapon.pt ──────────────────────────────────────────────────────
    if os.path.exists(_WEAPON_MODEL_PT):
        try:
            from ultralytics import YOLO
            print(f"[SENTINEL] Loading {_WEAPON_MODEL_PT}")
            wm = YOLO(_WEAPON_MODEL_PT)
            wm(np.zeros((320,320,3), dtype=np.uint8), verbose=False, conf=0.25)
            _weapon_model = wm
            _weapon_ready = True
            print(f"[SENTINEL] weapon.pt ready ✓  classes: {list(wm.names.values())}")
        except Exception as e:
            print(f"[SENTINEL] weapon.pt error: {e}")

    # ── fight.pt ───────────────────────────────────────────────────────
    if os.path.exists(_FIGHT_MODEL_PT):
        try:
            from ultralytics import YOLO
            print(f"[SENTINEL] Loading {_FIGHT_MODEL_PT}")
            fm = YOLO(_FIGHT_MODEL_PT)
            fm(np.zeros((320,320,3), dtype=np.uint8), verbose=False, conf=0.25)
            _fight_model  = fm
            _fight_ready  = True
            _fight_classes = fm.names
            print(f"[SENTINEL] fight.pt ready ✓  classes: {list(fm.names.values())}")

            # Class mapping from fight.pt (ayaz dataset):
            # Class 0 = 'No Fight' → no alert
            # Class 1 = 'fight'    → VIOLENCE alert
            for cid, cname in fm.names.items():
                cname_lower = cname.lower().strip()
                # Any class with fight/violence word = alert
                # Any class with no/normal/safe word = skip
                FIGHT_WORDS  = {"fight","violen","attack","brawl","assault","combat"}
                NORMAL_WORDS = {"no fight","nofight","no-fight","normal",
                                "peaceful","safe","non"}
                is_normal = any(w in cname_lower for w in NORMAL_WORDS)
                is_fight  = any(w in cname_lower for w in FIGHT_WORDS)
                if is_fight and not is_normal:
                    _fight_violence_ids.add(cid)
                    print(f"[SENTINEL] ✓ Fight class {cid}='{cname}' → VIOLENCE alert")
                else:
                    print(f"[SENTINEL]   Normal class {cid}='{cname}' → no alert")

        except Exception as e:
            print(f"[SENTINEL] fight.pt error: {e}")
    else:
        print(f"[SENTINEL] fight.pt not found — place fight.pt in {_PROJ}")


threading.Thread(target=_load_models, daemon=True).start()


def _boxes_overlap(b1, b2):
    ax1,ay1,ax2,ay2 = b1
    bx1,by1,bx2,by2 = b2
    return ax2 > bx1 and bx2 > ax1 and ay2 > by1 and by2 > ay1


def detect_image(img_bgr):
    """Single image detection for image uploads."""
    frame  = cv2.resize(img_bgr, (800, 480))
    result = {
        "motion": 0.0, "confidence": 0.0, "violent": False,
        "new_alert": False, "detections": [], "reason": "",
        "yolo_status": _status_str(),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    detections   = []
    yolo_violent = False
    yolo_conf    = 0.0
    reason       = ""

    if _model is not None:
        try:
            res = _model(frame, verbose=False, conf=0.25, iou=0.4)[0]
            for box in res.boxes:
                lbl          = _model.names[int(box.cls[0])]
                cf           = float(box.conf[0])
                x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                detections.append((lbl, cf, x1, y1, x2, y2))
                if lbl in COCO_DANGER:
                    yolo_violent = True
                    yolo_conf    = max(yolo_conf, cf)
                    reason       = f"WEAPON:{lbl}"
        except Exception as e:
            print(f"[SENTINEL] Image yolo error: {e}")

    if _weapon_model is not None:
        try:
            wres = _weapon_model(frame, verbose=False, conf=0.65, iou=0.4)[0]
            for box in wres.boxes:
                raw_lbl      = _weapon_model.names[int(box.cls[0])]
                cls_id       = int(box.cls[0])
                if cls_id not in [0, 1]:
                    continue
                real_lbl     = _WEAPON_CLASS_MAP.get(raw_lbl, raw_lbl)
                cf           = float(box.conf[0])
                x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                detections.append((real_lbl, cf, x1, y1, x2, y2))
                yolo_violent = True
                yolo_conf    = max(yolo_conf, cf)
                reason       = f"WEAPON:{real_lbl}"
        except Exception as e:
            print(f"[SENTINEL] Image weapon error: {e}")

    if _fight_model is not None:
        try:
            fres = _fight_model(frame, verbose=False, conf=0.50, iou=0.4)[0]
            for box in fres.boxes:
                cls_id       = int(box.cls[0])
                lbl          = _fight_classes.get(cls_id, str(cls_id))
                cf           = float(box.conf[0])
                x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                detections.append((lbl, cf, x1, y1, x2, y2))
                if cls_id in _fight_violence_ids:
                    yolo_violent = True
                    yolo_conf    = max(yolo_conf, cf)
                    reason       = f"FIGHT:{lbl}"
        except Exception as e:
            print(f"[SENTINEL] Image fight error: {e}")

    result["detections"] = detections
    result["violent"]    = yolo_violent
    result["confidence"] = yolo_conf
    result["reason"]     = reason
    result["new_alert"]  = yolo_violent
    annotated = annotate_frame(frame.copy(), result)
    return annotated, result


class CrimeDetector:
    def __init__(self):
        self.prev_gray    = None
        self.flow_hist    = deque(maxlen=HISTORY_FRAMES)
        self.last_alert_t = 0.0
        self._frame_n     = 0

    def reset(self):
        self.prev_gray    = None
        self.flow_hist.clear()
        self.last_alert_t = 0.0
        self._frame_n     = 0

    def process_frame(self, frame):
        self._frame_n += 1

        # Optical flow
        gray = cv2.GaussianBlur(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (15,15), 0)
        mag = 0.0
        if self.prev_gray is not None and self.prev_gray.shape == gray.shape:
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray, None, 0.5, 2, 13, 2, 5, 1.1, 0)
            m, _ = cv2.cartToPolar(flow[...,0], flow[...,1])
            mag  = float(np.mean(m))
        self.prev_gray = gray
        self.flow_hist.append(mag)
        smoothed = float(np.mean(self.flow_hist))

        detections   = []
        yolo_violent = False
        yolo_conf    = 0.0
        reason       = ""

        # ── yolov8n: persons, cars, knives ────────────────────────────
        if _model is not None:
            try:
                res = _model(frame, verbose=False, conf=0.25, iou=0.4)[0]
                for box in res.boxes:
                    lbl          = _model.names[int(box.cls[0])]
                    cf           = float(box.conf[0])
                    x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                    detections.append((lbl, cf, x1, y1, x2, y2))
                    if lbl in COCO_DANGER:
                        yolo_violent = True
                        yolo_conf    = max(yolo_conf, min(cf+0.10, 1.0))
                        reason       = f"WEAPON:{lbl}"
            except Exception as e:
                print(f"[SENTINEL] YOLO error: {e}")

        # ── weapon.pt: pistol and rifle only ──────────────────────────
        if _weapon_model is not None:
            try:
                wres = _weapon_model(frame, verbose=False, conf=0.75, iou=0.4)[0]
                for box in wres.boxes:
                    raw_lbl      = _weapon_model.names[int(box.cls[0])]
                    cls_id       = int(box.cls[0])
                    if cls_id not in [0, 1]:
                        continue
                    real_lbl     = _WEAPON_CLASS_MAP.get(raw_lbl, raw_lbl)
                    cf           = float(box.conf[0])
                    x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                    detections.append((real_lbl, cf, x1, y1, x2, y2))
                    yolo_violent = True
                    yolo_conf    = max(yolo_conf, min(cf+0.10, 1.0))
                    reason       = f"WEAPON:{real_lbl}"
            except Exception as e:
                print(f"[SENTINEL] Weapon error: {e}")

        # ── fight.pt: dedicated fight detection ───────────────────────
        if _fight_model is not None:
            try:
                fres = _fight_model(frame, verbose=False, conf=0.55, iou=0.4)[0]
                for box in fres.boxes:
                    cls_id       = int(box.cls[0])
                    lbl          = _fight_classes.get(cls_id, str(cls_id))
                    cf           = float(box.conf[0])
                    x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                    detections.append((lbl, cf, x1, y1, x2, y2))
                    if cls_id in _fight_violence_ids:
                        yolo_violent = True
                        yolo_conf    = max(yolo_conf, min(cf+0.05, 1.0))
                        reason       = f"FIGHT:{lbl}"
            except Exception as e:
                print(f"[SENTINEL] Fight model error: {e}")

        # ── Apply rules ───────────────────────────────────────────────
        motion_conf = min(smoothed / MOTION_VIOLENT, 1.0)
        if yolo_violent:
            violent    = True
            confidence = min(max(yolo_conf, motion_conf), 1.0)
        elif smoothed >= MOTION_VIOLENT:
            violent    = True
            confidence = motion_conf
            reason     = f"HIGH-MOTION:{smoothed:.2f}"
        else:
            violent    = False
            confidence = motion_conf

        now       = time.time()
        new_alert = violent and (now - self.last_alert_t) >= ALERT_COOLDOWN
        if new_alert:
            self.last_alert_t = now

        return {
            "motion":      smoothed,
            "confidence":  confidence,
            "violent":     violent,
            "new_alert":   new_alert,
            "detections":  detections,
            "reason":      reason,
            "yolo_status": _status_str(),
            "timestamp":   datetime.now().strftime("%H:%M:%S"),
            "date":        datetime.now().strftime("%Y-%m-%d"),
        }


def _status_str():
    parts = []
    if _model_ready:   parts.append("YOLO")
    if _weapon_ready:  parts.append("GUN")
    if _fight_ready:   parts.append("FIGHT")
    return "+".join(parts) if parts else "LOADING..."


# ── Colours BGR ────────────────────────────────────────────────────────────
_C = {
    "person":       (  0, 220, 255),
    "car":          ( 80, 255, 128),
    "truck":        ( 60, 220,  80),
    "motorcycle":   ( 60, 255,  60),
    "bicycle":      (100, 255, 100),
    "bus":          ( 40, 180,  60),
    "knife":        (  0,   0, 255),
    "scissors":     (  0,   0, 220),
    "baseball bat": (  0,   0, 200),
    "Pistol":       (  0,   0, 255),
    "Rifle":        (  0,   0, 220),
    "Knife":        (  0,   0, 200),
    "Grenade":      (  0,  50, 255),
    "Weapon":       (  0,   0, 200),
    "fight":        (  0,   0, 255),
    "violence":     (  0,   0, 255),
    "fighting":     (  0,   0, 255),
    "normal":       (  0, 220,  80),
    "cell phone":   (255, 100, 200),
    "backpack":     (255, 180, 100),
    "umbrella":     (200, 200, 200),
}
_DEF = (160, 160, 160)


def annotate_frame(frame, result):
    h, w = frame.shape[:2]

    for (lbl, cf, x1, y1, x2, y2) in result.get("detections", []):
        color = _C.get(lbl, _C.get(lbl.lower(), _DEF))
        is_danger = any(d in lbl.lower() for d in
                        ["knife","gun","pistol","rifle","weapon",
                         "scissors","bat","fight","violen","attack"])
        thick = 3 if is_danger else 2
        cv2.rectangle(frame, (x1,y1), (x2,y2), color, thick)
        tag = f"{lbl} {cf*100:.0f}%"
        (tw,th),_ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        ty = max(y1-4, th+6)
        cv2.rectangle(frame, (x1,ty-th-4), (x1+tw+8,ty+2), color, -1)
        cv2.putText(frame, tag, (x1+4,ty-2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,0,0), 1, cv2.LINE_AA)

    ov = frame.copy()
    cv2.rectangle(ov, (0,0), (w,48), (0,0,0), -1)
    cv2.addWeighted(ov, 0.65, frame, 0.35, 0, frame)

    violent = result.get("violent", False)
    motion  = result.get("motion",  0.0)
    n_obj   = len(result.get("detections", []))
    reason  = result.get("reason", "")
    status  = result.get("yolo_status", "")

    if violent:
        sc = (0, 0, 255)
        st = f"!! VIOLENCE !! {reason}" if reason else "!! VIOLENCE DETECTED !!"
    elif motion >= MOTION_SUSPICIOUS:
        sc, st = (0,160,255), "SUSPICIOUS MOTION"
    else:
        sc, st = (0,220,80), "NORMAL"

    cv2.putText(frame, st, (10,33),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, sc, 2, cv2.LINE_AA)
    info = f"Motion:{motion:.3f}  Objects:{n_obj}  [{status}]"
    cv2.putText(frame, info, (10,h-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180,180,180), 1, cv2.LINE_AA)
    cv2.putText(frame, result["timestamp"], (w-90,33),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (160,160,160), 1, cv2.LINE_AA)
    if violent:
        cv2.rectangle(frame, (0,0), (w-1,h-1), (0,0,255), 5)
    return frame
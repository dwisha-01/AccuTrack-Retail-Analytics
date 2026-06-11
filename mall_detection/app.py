#  ACUTRACK — ID-Persistent Retail Analytics Platform
#  app.py — StrongSort + OSNet Version
#  Real Re-ID generalization using OSNet weights trained on Market-1501
#  9+ FPS on CPU — usable for real-time demo

from flask import Flask, render_template, Response, request, jsonify
from flask_socketio import SocketIO
from ultralytics import YOLO
from boxmot.trackers.strongsort.strongsort import StrongSort
from pathlib import Path
import cv2
import time
import threading
import numpy as np
import torch

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ── YOLO for detection only ────────────────────────────────────────────────────
model = YOLO("yolov8n.pt")

# ── FRAME RESOLUTION ───────────────────────────────────────────────────────────
FRAME_W = 1060
FRAME_H = 660

# ── STRONGSORT TRACKER + OSNET RE-ID ──────────────────────────────────────────
print("Loading StrongSort tracker with OSNet Re-ID...")
tracker = StrongSort(
    reid_weights=Path("osnet_x0_25_msmt17.pt"),
    device=torch.device("cpu"),
    half=False,
    max_age=90,
    cmc_off=True,
    max_cos_dist=0.4,
)
print("StrongSort + OSNet loaded!")

# ── RE-ID ACCURACY TRACKING ────────────────────────────────────────────────────
known_ids       = set()   # all unique IDs ever assigned
id_switch_count = 0       # proxy for ID switches (new IDs appearing)
reid_lock       = threading.Lock()

# ── VIDEO SOURCES ──────────────────────────────────────────────────────────────
VIDEO_SOURCES = {
    "cam1": {"file": "crowd_video.mp4",    "label": "Camera 1",   "desc": "Mall Dataset — Indoor retail environment"},
    "cam2": {"file": "moderate_video.mp4", "label": "Camera 2",   "desc": "Moderate Crowd — Outdoor pedestrian walkway"},
    "cam3": {"file": "lowlight_video.mp4", "label": "Camera 3",   "desc": "Low Light — Poor visibility conditions"},
    "live": {"file": 0,                    "label": "Live Camera", "desc": "Live webcam feed"},
}

# ── ZONES ──────────────────────────────────────────────────────────────────────
ZONES = {
    "Zone A": {"coords": (10,  80, 390, 660), "color": (74,  144, 217), "label": "Store Entrance"},
    "Zone B": {"coords": (390, 80, 720, 660), "color": (56,  161, 105), "label": "Food Court"},
    "Zone C": {"coords": (720, 80, 1050, 660), "color": (221, 107, 32),  "label": "Exit Corridor"},
}

ZONE_CAPACITY = {
    "Zone A": 8,
    "Zone B": 10,
    "Zone C": 8,
}

# ── GLOBAL STATE ───────────────────────────────────────────────────────────────
state_lock          = threading.Lock()
current_video       = "cam2"
switch_video        = False
flow_enabled        = True
zone_counts         = {z: 0    for z in ZONES}
zone_footfall       = {z: 0    for z in ZONES}
zone_avg_dwell      = {z: 0.0  for z in ZONES}
zone_dwell_samples  = {z: []   for z in ZONES}
prev_zone_ids       = {z: set() for z in ZONES}
zone_alerts         = {z: False for z in ZONES}
dwell_entry_times   = {}
total_people        = 0
latest_frame        = None
prev_gray           = None


# ── HELPERS ────────────────────────────────────────────────────────────────────

def point_in_zone(px, py, zone_name):
    x1, y1, x2, y2 = ZONES[zone_name]["coords"]
    return x1 < px < x2 and y1 < py < y2


def apply_optical_flow(frame, prev_gray, curr_gray):
    flow    = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
    )
    h, w    = frame.shape[:2]
    step    = 40
    overlay = frame.copy()
    for y in range(step // 2, h, step):
        for x in range(step // 2, w, step):
            dx, dy    = flow[y, x]
            magnitude = np.sqrt(dx**2 + dy**2)
            if magnitude < 1.5:
                continue
            scale = 3.0
            x_end = int(np.clip(x + dx * scale, 0, w - 1))
            y_end = int(np.clip(y + dy * scale, 0, h - 1))
            speed_norm = min(magnitude / 10.0, 1.0)
            color = (int(255*(1-speed_norm)), int(200*speed_norm), int(255*speed_norm))
            cv2.arrowedLine(overlay, (x, y), (x_end, y_end), color, 1, tipLength=0.4)
    return cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)


def draw_alert_banner(frame, zone_name, zone_data):
    x1, y1, x2, y2 = zone_data["coords"]
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 220), -1)
    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
    cx = (x1 + x2) // 2
    cv2.putText(frame, "! OVERCROWDED",
                (cx - 80, y2 - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return frame


def reset_stats():
    global prev_gray
    global known_ids, id_switch_count
    prev_gray       = None
    known_ids       = set()
    id_switch_count = 0
    tracker.reset()
    for z in ZONES:
        zone_counts[z]        = 0
        zone_footfall[z]      = 0
        zone_avg_dwell[z]     = 0.0
        zone_dwell_samples[z] = []
        prev_zone_ids[z]      = set()
        zone_alerts[z]        = False
    dwell_entry_times.clear()


# ── MAIN DETECTION LOOP ────────────────────────────────────────────────────────

def detection_loop():
    global latest_frame, total_people, zone_counts, zone_footfall
    global zone_avg_dwell, prev_zone_ids, dwell_entry_times
    global current_video, switch_video
    global zone_alerts, prev_gray
    global known_ids, id_switch_count

    source = VIDEO_SOURCES[current_video]["file"]
    cap    = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    frame_count = 0

    while True:

        # ── Handle video switch ──────────────────────────────────────────────
        with state_lock:
            should_switch = switch_video
            new_video     = current_video

        if should_switch:
            cap.release()
            source = VIDEO_SOURCES[new_video]["file"]
            cap    = cv2.VideoCapture(source)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
            with state_lock:
                switch_video = False
                reset_stats()
            frame_count = 0

        ret, frame = cap.read()
        if not ret:
            if isinstance(source, int):
                continue
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            with state_lock:
                reset_stats()
            continue

        frame = cv2.resize(frame, (FRAME_W, FRAME_H))
        frame_count += 1

        # ── Optical flow ─────────────────────────────────────────────────────
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        with state_lock:
            show_flow = flow_enabled
        if show_flow and prev_gray is not None:
            frame = apply_optical_flow(frame, prev_gray, curr_gray)
        prev_gray = curr_gray

        # ── YOLO detection only (no tracking) ────────────────────────────────
        results = model(
            frame,
            classes=[0],
            verbose=False,
            conf=0.2,
            iou=0.45
        )

        # ── Convert to BoxMOT format [x1,y1,x2,y2,conf,class] ────────────────
        dets = np.empty((0, 6))
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes_xyxy = results[0].boxes.xyxy.cpu().numpy()
            confs      = results[0].boxes.conf.cpu().numpy()
            classes    = results[0].boxes.cls.cpu().numpy()
            dets       = np.column_stack([boxes_xyxy, confs, classes])

        # ── StrongSort tracking + OSNet Re-ID ────────────────────────────────
        tracks = tracker.update(dets, frame)

        # ── Zone overlays ────────────────────────────────────────────────────
        for zone_name, zone_data in ZONES.items():
            x1, y1, x2, y2 = zone_data["coords"]
            color = zone_data["color"]
            bgr   = (int(color[2]), int(color[1]), int(color[0]))
            overlay = frame.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), bgr, -1)
            cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
            cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, 2)
            cv2.putText(frame, zone_name,
                        (x1 + 8, y1 + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, bgr, 2)
            cv2.putText(frame, zone_data["label"],
                        (x1 + 8, y1 + 52),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, bgr, 1)

        # ── Process tracks ───────────────────────────────────────────────────
        detection_data     = []
        current_zone_ids   = {z: set() for z in ZONES}
        frame_people_count = 0

        if len(tracks) > 0:
            for track in tracks:
                x1       = int(track[0])
                y1       = int(track[1])
                x2       = int(track[2])
                y2       = int(track[3])
                track_id = int(track[4])

                frame_people_count += 1

                # Count unique IDs for metrics
                with reid_lock:
                    if track_id not in known_ids:
                        known_ids.add(track_id)

                foot_x   = (x1 + x2) // 2
                foot_y   = y2
                center_x = foot_x
                center_y = (y1 + y2) // 2

                detection_data.append({
                    "track_id": track_id,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "foot_x": foot_x, "foot_y": foot_y
                })

                for zone_name in ZONES:
                    if point_in_zone(foot_x, foot_y, zone_name):
                        current_zone_ids[zone_name].add(track_id)
                        if track_id not in dwell_entry_times:
                            dwell_entry_times[track_id] = {}
                        if zone_name not in dwell_entry_times[track_id]:
                            dwell_entry_times[track_id][zone_name] = time.time()

        # ── Bounding boxes ────────────────────────────────────────────────────
        for d in detection_data:
            track_id = d["track_id"]
            x1, y1   = d["x1"], d["y1"]
            x2, y2   = d["x2"], d["y2"]
            foot_x   = d["foot_x"]
            foot_y   = d["foot_y"]
            color    = (50, 200, 50)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"ID:{track_id}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.circle(frame, (foot_x, foot_y), 5, (255, 255, 255), -1)

        # ── Update zone stats ─────────────────────────────────────────────────
        with state_lock:
            total_people = frame_people_count
            for zone_name in ZONES:
                curr_ids  = current_zone_ids[zone_name]
                prev_ids  = prev_zone_ids[zone_name]
                count     = len(curr_ids)
                zone_counts[zone_name] = count
                threshold = ZONE_CAPACITY.get(zone_name, 10)
                zone_alerts[zone_name] = (count >= threshold)
                new_entries = curr_ids - prev_ids
                zone_footfall[zone_name] += len(new_entries)
                left_ids = prev_ids - curr_ids
                for tid in left_ids:
                    if tid in dwell_entry_times and zone_name in dwell_entry_times[tid]:
                        duration = time.time() - dwell_entry_times[tid][zone_name]
                        zone_dwell_samples[zone_name].append(duration)
                        zone_dwell_samples[zone_name] = zone_dwell_samples[zone_name][-20:]
                        zone_avg_dwell[zone_name] = round(
                            sum(zone_dwell_samples[zone_name]) /
                            len(zone_dwell_samples[zone_name]), 1)
                        del dwell_entry_times[tid][zone_name]
            prev_zone_ids = {z: set(current_zone_ids[z]) for z in ZONES}

        # ── Alert banners ─────────────────────────────────────────────────────
        for zone_name, zone_data in ZONES.items():
            if zone_alerts[zone_name]:
                frame = draw_alert_banner(frame, zone_name, zone_data)

        # ── HUD ───────────────────────────────────────────────────────────────
        with reid_lock:
            unique_ids = len(known_ids)
        cv2.rectangle(frame, (0, 0), (FRAME_W, 60), (245, 247, 250), -1)
        cv2.putText(frame,
                    f"AcuTrack  |  People: {frame_people_count}  |  Unique IDs: {unique_ids}  |  OSNet Re-ID: ON",
                    (14, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
        cv2.putText(frame, VIDEO_SOURCES[current_video]["label"],
                    (FRAME_W - 160, 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 80, 80), 2)
        if isinstance(VIDEO_SOURCES[current_video]["file"], int):
            cv2.circle(frame, (FRAME_W - 20, 30), 8, (0, 0, 220), -1)

        # ── Terminal metrics every 100 frames ─────────────────────────────────
        if frame_count % 100 == 0:
            with reid_lock:
                uid = len(known_ids)
            print("\n" + "="*55)
            print(f"  FRAME          : {frame_count}")
            print(f"  ACTIVE PEOPLE  : {frame_people_count}")
            print(f"  UNIQUE IDs     : {uid}")
            print(f"  TRACKER        : StrongSort + OSNet Re-ID")
            print(f"  RE-ID MODEL    : osnet_x0_25_msmt17 (Market-1501)")
            print("-"*55)
            for z in ZONES:
                alert_str = "  ⚠ ALERT" if zone_alerts[z] else ""
                print(f"  {z} | Now: {zone_counts[z]:>2} | "
                      f"Footfall: {zone_footfall[z]:>4} | "
                      f"Dwell: {zone_avg_dwell[z]}s{alert_str}")
            print("="*55 + "\n")

        # ── Encode + emit ─────────────────────────────────────────────────────
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with state_lock:
            latest_frame = buffer.tobytes()

        stats = {"total": frame_people_count, "video": current_video, "zones": {}}
        for zone_name in ZONES:
            stats["zones"][zone_name] = {
                "count":    zone_counts[zone_name],
                "footfall": zone_footfall[zone_name],
                "dwell":    zone_avg_dwell[zone_name],
                "label":    ZONES[zone_name]["label"],
                "alert":    zone_alerts[zone_name],
                "capacity": ZONE_CAPACITY.get(zone_name, 10),
            }
        socketio.emit("stats", stats)

    cap.release()


# ── ROUTES ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/switch_video', methods=['POST'])
def switch_video_route():
    global current_video, switch_video
    data    = request.get_json()
    new_vid = data.get("video")
    if new_vid in VIDEO_SOURCES:
        with state_lock:
            current_video = new_vid
            switch_video  = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400


@app.route('/toggle_flow', methods=['POST'])
def toggle_flow():
    global flow_enabled
    with state_lock:
        flow_enabled = not flow_enabled
        state = flow_enabled
    return jsonify({"flow": state})


def generate_frames():
    while True:
        with state_lock:
            frame = latest_frame
        if frame is None:
            time.sleep(0.05)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    cam_thread = threading.Thread(target=detection_loop, daemon=True)
    cam_thread.start()
    print("=" * 55)
    print("  AcuTrack Running — StrongSort + OSNet Re-ID!")
    print("  Open browser → http://localhost:5000")
    print("=" * 55)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
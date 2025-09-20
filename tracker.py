import cv2
import logging
from ultralytics import YOLO
import config as cfg
from utils import format_mmss, is_center_inside_roi, compute_speed_pixels_per_second, remove_id_from_dicts

class WaitTimeTracker:
    def __init__(self, roi, logger=None):
        self.roi = roi
        self.model = YOLO(cfg.MODEL_NAME)
        self.class_names = self.model.names
        self.logger = logger or logging.getLogger("ROI-Logger")
        self.positions_by_id = {}
        self.inside_roi_flag = {}
        self.resting_flag = {}
        self.rest_start_time = {}
        self.accumulated_wait_seconds = {}
        self.last_increment_time = {}
        self.last_seen_time = {}

    def process_video(self):
        cap = cv2.VideoCapture(cfg.VIDEO_PATH)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(cfg.OUTPUT_VIDEO, cv2.VideoWriter_fourcc(*"mp4v"), fps,(fw, fh))
        self.logger.info("Loading YOLO model")
        try:
            stream = self.model.track(
                cfg.VIDEO_PATH,
                stream=True,
                tracker=cfg.TRACKER_CONFIG,
                persist=True,
                conf=cfg.CONFIDENCE_THRESHOLD
            )
        except TypeError:
            stream = self.model.track(
                cfg.VIDEO_PATH,
                stream=True,
                tracker=cfg.TRACKER_CONFIG,
                conf=cfg.CONFIDENCE_THRESHOLD
            )
        self.logger.info("Starting frame processing with ByteTrack")
        frame_idx = 0
        for result in stream:
            frame_idx += 1
            current_time = frame_idx / fps
            frame = result.orig_img.copy()
            try:
                boxes = result.boxes.xyxy.cpu().numpy()
                ids = result.boxes.id.int().cpu().numpy()
                clses = result.boxes.cls.cpu().numpy().astype(int)
            except Exception:
                continue
            for j, box in enumerate(boxes):
                track_id = int(ids[j])
                class_label = self.class_names[clses[j]].lower()
                if class_label not in cfg.VEHICLE_CLASSES:
                    continue
                x1, y1, x2, y2 = map(int, box)
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                if track_id not in self.positions_by_id:
                    self.positions_by_id[track_id] = []
                    self.logger.info(f"New ID {track_id} detected at {current_time:.2f}s")
                self.last_seen_time[track_id] = current_time
                self.positions_by_id[track_id].append((current_time, (cx, cy)))
                while len(self.positions_by_id[track_id]) > cfg.MAX_HISTORY_LEN:
                    self.positions_by_id[track_id].pop(0)
                now_inside = is_center_inside_roi((x1, y1, x2, y2), self.roi)
                self.inside_roi_flag[track_id] = now_inside
                speed_pixels_per_sec = compute_speed_pixels_per_second(
                    self.positions_by_id[track_id],
                    current_time,
                    cfg.SPEED_WINDOW_SEC
                )
                now_resting = False
                if speed_pixels_per_sec <= cfg.SPEED_THRESHOLD_PX_PER_SEC:
                    now_resting = True
                self.resting_flag[track_id] = now_resting
                if now_inside and now_resting:
                    if track_id not in self.rest_start_time:
                        self.rest_start_time[track_id] = current_time
                        self.logger.info(f"ID {track_id} entered ROI and became resting at {current_time:.2f}s")
                    rest_elapsed = current_time - self.rest_start_time[track_id]
                    if rest_elapsed >= cfg.MIN_STILL_TIME:
                        if track_id not in self.last_increment_time:
                            counting_start_time = self.rest_start_time[track_id] + cfg.MIN_STILL_TIME
                            initial_added = current_time - counting_start_time
                            existing = 0.0
                            if track_id in self.accumulated_wait_seconds:
                                existing = self.accumulated_wait_seconds[track_id]
                            self.accumulated_wait_seconds[track_id] = existing + initial_added
                            self.last_increment_time[track_id] = current_time
                            self.logger.info(f"Started counting wait time for ID {track_id} at {current_time:.2f}s")
                        else:
                            previous_time = self.last_increment_time[track_id]
                            delta_time = current_time - previous_time
                            if delta_time > 0.0:
                                existing = 0.0
                                if track_id in self.accumulated_wait_seconds:
                                    existing = self.accumulated_wait_seconds[track_id]
                                self.accumulated_wait_seconds[track_id] = existing + delta_time
                                self.last_increment_time[track_id] = current_time
                else:
                    if track_id in self.rest_start_time:
                        self.logger.info(f"ID {track_id} moved inside ROI at {current_time:.2f}s, stopping rest count")
                        self.rest_start_time.pop(track_id)
                    if track_id in self.last_increment_time:
                        self.last_increment_time.pop(track_id)
                label = f"{class_label.upper()} ID:{track_id}"
                if track_id in self.accumulated_wait_seconds:
                    label += " " + format_mmss(self.accumulated_wait_seconds[track_id])
                is_actively_counted = False
                if track_id in self.rest_start_time:
                    elapsed_for_display = current_time - self.rest_start_time[track_id]
                    if elapsed_for_display >= cfg.MIN_STILL_TIME and now_inside and now_resting:
                        is_actively_counted = True
                color = cfg.COLORS["active_box"] if is_actively_counted else cfg.COLORS["inactive_box"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, cfg.COLORS["text"], 2)
                cv2.circle(frame, (int(cx), int(cy)), 3, cfg.COLORS["centroid"], -1)
                speed_text = f"{speed_pixels_per_sec:.1f}px/s"
                cv2.putText(frame, speed_text, (int(cx) + 6, int(cy) + 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, cfg.COLORS["speed_text"], 1)
            cv2.rectangle(frame, (self.roi[0], self.roi[1]), (self.roi[2], self.roi[3]), cfg.COLORS["roi"], 2)
            cv2.putText(frame, "ROI", (self.roi[0] + 6, self.roi[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, cfg.COLORS["roi"], 2)
            writer.write(frame)
            expired_ids = []
            for tid_key in list(self.last_seen_time.keys()):
                time_last = self.last_seen_time[tid_key]
                if current_time - time_last > cfg.ID_EXPIRY_SECONDS:
                    expired_ids.append(tid_key)
            for expired_id in expired_ids:
                remove_id_from_dicts(
                    expired_id,
                    self.positions_by_id,
                    self.inside_roi_flag,
                    self.resting_flag,
                    self.rest_start_time,
                    self.last_increment_time,
                    self.last_seen_time
                )
                self.logger.info(f"Expired ID {expired_id} at {current_time:.2f}s")
        cap.release()
        writer.release()
        cv2.destroyAllWindows()
        self.logger.info("Finished processing.")
        self.logger.info("Final accumulated wait time :")
        for tid, secs in sorted(self.accumulated_wait_seconds.items()):
            self.logger.info(f"ID {tid}: {format_mmss(secs)}")
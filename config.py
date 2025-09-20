VIDEO_PATH = "input_video.mp4"
OUTPUT_VIDEO = "output_video.mp4"
MODEL_NAME = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.25
TRACKER_CONFIG = "bytetrack.yaml"
VEHICLE_CLASSES = ["car"]
SPEED_THRESHOLD_PX_PER_SEC = 15.0
MIN_STILL_TIME = 0.5
SPEED_WINDOW_SEC = 0.8
MAX_HISTORY_LEN = 60
ID_EXPIRY_SECONDS = 5.0

COLORS = {
    "roi": (0, 0, 255),           # red
    "active_box": (255, 0, 0),    # blue
    "inactive_box": (0, 255, 0),  # green
    "text": (255, 255, 255),      # white
    "centroid": (255, 255, 0),    # cyan
    "speed_text": (200, 200, 200) # gray
}

LOG_FILE = "log_file.log"
LOG_LEVEL = "INFO" 

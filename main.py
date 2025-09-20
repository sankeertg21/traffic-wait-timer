import cv2
import logging
import config as cfg
from utils import select_roi_on_first_frame
from tracker import WaitTimeTracker

def setup_logger():
    logging.basicConfig(
        level=getattr(logging, cfg.LOG_LEVEL),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(cfg.LOG_FILE, mode="w"),  logging.StreamHandler()
        ]
    )
    return logging.getLogger("ROI-Logger")

def main(): 
    logger = setup_logger()
    cap = cv2.VideoCapture(cfg.VIDEO_PATH)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("Could not open video.")
    roi = select_roi_on_first_frame(frame, logger)
    tracker = WaitTimeTracker(roi, logger)
    tracker.process_video()

if __name__ == "__main__":
    main()

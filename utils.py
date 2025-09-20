import cv2
import math

def format_mmss(seconds_value): # used this to convert float seconds to mm:ss format    
    rounded = int(round(seconds_value))
    minutes = rounded // 60
    seconds_remain = rounded % 60
    return f"{minutes:02d}:{seconds_remain:02d}"

def is_center_inside_roi(box_xyxy, roi_box): # this function basically checks if center of detected car is inside roi or not     
    x1, y1, x2, y2 = box_xyxy
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    rx1, ry1, rx2, ry2 = roi_box
    return rx1 <= cx <= rx2 and ry1 <= cy <= ry2

def compute_speed_pixels_per_second(history_list, current_time, window_seconds): # this function does is that it calculates speed of car in pixels per second so that i can use it to check if car is stationary or not.
    if len(history_list) < 2:
        return float("inf")
    start_time = current_time - window_seconds
    index = 0
    while index < len(history_list) and history_list[index][0] < start_time:
        index += 1
    if index >= len(history_list):
        index = 0
    t0, (cx0, cy0) = history_list[index]
    t1, (cx1, cy1) = history_list[-1]
    dt = t1 - t0
    if dt <= 0:
        return float("inf")
    distance = math.hypot(cx1 - cx0, cy1 - cy0)
    return distance / dt

#below function is used to remove id from all the dictionaries when id expires
def remove_id_from_dicts(track_id,
                         positions_by_id,
                         inside_roi_flag,
                         resting_flag,
                         rest_start_time,
                         last_increment_time,
                         last_seen_time):
    for d in [positions_by_id, inside_roi_flag, resting_flag, rest_start_time, last_increment_time, last_seen_time]:
        if track_id in d:
            d.pop(track_id)

def select_roi_on_first_frame(first_frame, logger): # this functino is  used to select roi on using first frame of video. Drag the area using mouse and press enter once done . 
    while True:
        window_name = "Draw ROI"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, first_frame)
        rect = cv2.selectROI(window_name, first_frame, showCrosshair=True, fromCenter=False)
        cv2.destroyWindow(window_name)
        x, y, w, h = rect
        if w == 0 or h == 0:
            logger.warning("Empty ROI. Please draw again.")
            continue
        x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
        logger.info(f"ROI confirmed: ({x1},{y1}) - ({x2},{y2})")
        return (x1, y1, x2, y2)

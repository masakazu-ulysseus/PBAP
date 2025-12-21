"""
Assembly Number Image Extraction PoC v2
Extracts assembly number images from assembly page images.

Detection method:
- Detect red/black horizontal and vertical lines using HSV color filtering
- Find rectangles formed by intersecting lines
- Filter by:
  - Has quantity labels (x1, x2, etc.) inside
  - Has assembly number nearby (outside the frame)
  - Not connected to arrow lines (must be independent frame)
  - Not blue frame
"""

import argparse
import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict


def get_color_mask(img, color='red'):
    """
    Create a mask for specific color (red or black lines).
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    if color == 'red':
        # Red color range (wraps around 0/180)
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
    elif color == 'black':
        # Black/dark gray range - expanded to catch more dark lines
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 80, 100])
        mask = cv2.inRange(hsv, lower_black, upper_black)
    elif color == 'blue':
        # Blue color range
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
    else:
        mask = np.zeros(img.shape[:2], dtype=np.uint8)

    return mask


def detect_blue_frames(img, min_line_length=50):
    """
    Detect blue frames to exclude them and any frames inside them.
    Returns list of blue frame bboxes.
    """
    mask = get_color_mask(img, 'blue')

    # Detect lines
    h_lines, v_lines = detect_lines_hough(mask, min_line_length=min_line_length)

    # Merge nearby lines
    h_lines = merge_nearby_lines(h_lines, is_horizontal=True)
    v_lines = merge_nearby_lines(v_lines, is_horizontal=False)

    # Find rectangles
    img_h, img_w = img.shape[:2]
    rectangles = find_rectangles_from_lines(
        h_lines, v_lines,
        min_width=60, min_height=40,
        img_width=img_w, img_height=img_h
    )

    return [r['bbox'] for r in rectangles]


def is_inside_blue_frame(frame_bbox, blue_frames, margin=10):
    """
    Check if a frame is inside any blue frame.
    """
    x, y, w, h = frame_bbox
    frame_center_x = x + w // 2
    frame_center_y = y + h // 2

    for bx, by, bw, bh in blue_frames:
        # Check if the frame's center is inside the blue frame
        if (bx - margin <= frame_center_x <= bx + bw + margin and
            by - margin <= frame_center_y <= by + bh + margin):
            return True

        # Also check if there's significant overlap
        ix1 = max(x, bx)
        iy1 = max(y, by)
        ix2 = min(x + w, bx + bw)
        iy2 = min(y + h, by + bh)

        if ix1 < ix2 and iy1 < iy2:
            intersection = (ix2 - ix1) * (iy2 - iy1)
            frame_area = w * h
            # If more than 50% of the frame is inside blue frame, exclude it
            if intersection / frame_area > 0.5:
                return True

    return False


def validate_extracted_frame(frame_img, debug=False):
    """
    Validate that the extracted image contains exactly ONE rectangular frame.

    This validation focuses on detecting MULTIPLE frames (false positives where
    two adjacent frames were detected as one).

    Returns: (is_valid, reason)
    """
    if frame_img is None or frame_img.size == 0:
        return False, "empty_image"

    img_h, img_w = frame_img.shape[:2]

    if debug:
        print(f"    [VALIDATE DEBUG] Image size: {img_w}x{img_h}")

    # Use color-based detection to find frame border lines (more reliable than edge detection)
    # Look for black or red lines that could be frame separators

    # Get masks for frame colors
    black_mask = get_color_mask(frame_img, 'black')
    red_mask = get_color_mask(frame_img, 'red')
    combined_mask = cv2.bitwise_or(black_mask, red_mask)

    # Detect horizontal lines in the combined mask
    min_line_length = max(30, img_w // 4)
    h_lines, _ = detect_lines_hough(combined_mask, min_line_length=min_line_length, max_line_gap=10)

    if not h_lines:
        # No significant lines detected - might be okay, continue
        return True, "valid"

    # Merge nearby horizontal lines
    h_lines = merge_nearby_lines(h_lines, is_horizontal=True, merge_threshold=15)

    if debug:
        print(f"    [VALIDATE DEBUG] Horizontal lines detected: {len(h_lines)}")

    # Sort by y position
    h_lines_sorted = sorted(h_lines, key=lambda l: l[2])

    # Find the top and bottom frame borders
    # The topmost and bottommost long lines are likely frame borders
    long_h_lines = [l for l in h_lines_sorted if (l[1] - l[0]) > img_w * 0.5]

    if len(long_h_lines) < 2:
        # Can't determine frame borders, assume valid
        return True, "valid"

    # Top border is the first long line, bottom border is the last
    top_border_y = long_h_lines[0][2]
    bottom_border_y = long_h_lines[-1][2]
    frame_height = bottom_border_y - top_border_y

    if debug:
        print(f"    [VALIDATE DEBUG] Frame borders: top={top_border_y}, bottom={bottom_border_y}, height={frame_height}")

    # Check for HORIZONTAL separators BETWEEN the top and bottom borders
    min_separator_length = img_w * 0.7

    for h_line in long_h_lines[1:-1]:  # Exclude first (top) and last (bottom) lines
        line_start, line_end, y_pos = h_line
        line_length = line_end - line_start

        # Check if this line is in the middle of the frame (not near borders)
        dist_from_top = y_pos - top_border_y
        dist_from_bottom = bottom_border_y - y_pos

        if debug and line_length > img_w * 0.5:
            print(f"    [VALIDATE DEBUG] Middle h-line at y={y_pos}: length={line_length}, dist_top={dist_from_top}, dist_bottom={dist_from_bottom}")

        # If this line is far from both borders and long, it's likely a separator
        if dist_from_top > frame_height * 0.2 and dist_from_bottom > frame_height * 0.2:
            if line_length > min_separator_length:
                if debug:
                    print(f"    [VALIDATE DEBUG] Horizontal separator detected at y={y_pos}")
                return False, "multiple_frames_horizontal"

    # Note: Vertical separator detection was attempted but caused too many false positives
    # (rejecting valid single frames). Keeping only horizontal separator detection for now.

    return True, "valid"


def count_frames_in_image(frame_img, color='red'):
    """
    Count how many LARGE rectangular frames exist in the image.
    This is used to detect cases where multiple assembly frames were
    incorrectly detected as one.

    Returns the count of detected frames.
    """
    if frame_img is None or frame_img.size == 0:
        return 0

    img_h, img_w = frame_img.shape[:2]

    # Use longer minimum line length to only detect significant frame borders
    min_line_length = max(50, min(img_w, img_h) // 4)

    # Get color mask
    mask = get_color_mask(frame_img, color)

    # Detect lines
    h_lines, v_lines = detect_lines_hough(mask, min_line_length=min_line_length)

    if not h_lines or not v_lines:
        return 0

    # Merge nearby lines
    h_lines = merge_nearby_lines(h_lines, is_horizontal=True, merge_threshold=15)
    v_lines = merge_nearby_lines(v_lines, is_horizontal=False, merge_threshold=15)

    # Find rectangles with larger minimum size
    # Only count frames that are at least 30% of the image size
    min_width = max(80, int(img_w * 0.25))
    min_height = max(60, int(img_h * 0.25))

    rectangles = find_rectangles_from_lines(
        h_lines, v_lines,
        min_width=min_width, min_height=min_height,
        img_width=img_w, img_height=img_h,
        tolerance=20
    )

    # Remove duplicates
    rectangles = remove_duplicate_rectangles(rectangles, iou_threshold=0.5)

    return len(rectangles)


def detect_lines_hough(mask, min_line_length=50, max_line_gap=10):
    """
    Detect lines using Hough Line Transform.
    Returns horizontal and vertical lines separately.
    """
    # Apply morphological operations to clean up the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Detect lines using probabilistic Hough transform
    lines = cv2.HoughLinesP(mask, 1, np.pi/180, threshold=50,
                            minLineLength=min_line_length, maxLineGap=max_line_gap)

    horizontal_lines = []
    vertical_lines = []

    if lines is None:
        return horizontal_lines, vertical_lines

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Calculate angle
        if x2 - x1 == 0:
            angle = 90
        else:
            angle = abs(np.degrees(np.arctan((y2 - y1) / (x2 - x1))))

        # Classify as horizontal or vertical (with 10-degree tolerance)
        if angle < 10:
            # Horizontal line
            horizontal_lines.append((min(x1, x2), max(x1, x2), (y1 + y2) // 2))
        elif angle > 80:
            # Vertical line
            vertical_lines.append((min(y1, y2), max(y1, y2), (x1 + x2) // 2))

    return horizontal_lines, vertical_lines


def detect_all_lines_hough(mask, min_line_length=30, max_line_gap=5):
    """
    Detect ALL lines (including diagonal/arrow lines) using Hough Line Transform.
    Returns list of (x1, y1, x2, y2, angle) tuples.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    lines = cv2.HoughLinesP(mask, 1, np.pi/180, threshold=30,
                            minLineLength=min_line_length, maxLineGap=max_line_gap)

    all_lines = []
    if lines is None:
        return all_lines

    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:
            angle = 90
        else:
            angle = abs(np.degrees(np.arctan((y2 - y1) / (x2 - x1))))
        all_lines.append((x1, y1, x2, y2, angle))

    return all_lines


def merge_nearby_lines(lines, is_horizontal=True, merge_threshold=15):
    """
    Merge lines that are close together.
    """
    if not lines:
        return []

    # Sort by position (y for horizontal, x for vertical)
    if is_horizontal:
        lines = sorted(lines, key=lambda l: l[2])  # Sort by y
    else:
        lines = sorted(lines, key=lambda l: l[2])  # Sort by x

    merged = []
    current_group = [lines[0]]

    for line in lines[1:]:
        if is_horizontal:
            # Compare y positions
            if abs(line[2] - current_group[-1][2]) < merge_threshold:
                current_group.append(line)
            else:
                # Merge current group
                min_start = min(l[0] for l in current_group)
                max_end = max(l[1] for l in current_group)
                avg_pos = sum(l[2] for l in current_group) // len(current_group)
                merged.append((min_start, max_end, avg_pos))
                current_group = [line]
        else:
            # Compare x positions
            if abs(line[2] - current_group[-1][2]) < merge_threshold:
                current_group.append(line)
            else:
                min_start = min(l[0] for l in current_group)
                max_end = max(l[1] for l in current_group)
                avg_pos = sum(l[2] for l in current_group) // len(current_group)
                merged.append((min_start, max_end, avg_pos))
                current_group = [line]

    # Don't forget the last group
    if current_group:
        min_start = min(l[0] for l in current_group)
        max_end = max(l[1] for l in current_group)
        avg_pos = sum(l[2] for l in current_group) // len(current_group)
        merged.append((min_start, max_end, avg_pos))

    return merged


def find_rectangles_from_lines(horizontal_lines, vertical_lines,
                                min_width=80, min_height=60,
                                max_width_ratio=0.9, max_height_ratio=0.9,
                                img_width=None, img_height=None,
                                tolerance=20):
    """
    Find rectangles formed by intersecting horizontal and vertical lines.
    """
    rectangles = []

    if img_width is None or img_height is None:
        return rectangles

    max_width = img_width * max_width_ratio
    max_height = img_height * max_height_ratio

    # For each pair of horizontal lines (top and bottom)
    for i, h_top in enumerate(horizontal_lines):
        for h_bottom in horizontal_lines[i+1:]:
            top_y = h_top[2]
            bottom_y = h_bottom[2]
            height = bottom_y - top_y

            if height < min_height or height > max_height:
                continue

            # Find vertical lines that could form left and right edges
            # They should span from top_y to bottom_y (with tolerance)
            matching_verticals = []
            for v_line in vertical_lines:
                v_start, v_end, v_x = v_line
                # Check if vertical line spans the height
                if v_start <= top_y + tolerance and v_end >= bottom_y - tolerance:
                    matching_verticals.append(v_x)

            matching_verticals = sorted(matching_verticals)

            # For each pair of vertical lines
            for j, left_x in enumerate(matching_verticals):
                for right_x in matching_verticals[j+1:]:
                    width = right_x - left_x

                    if width < min_width or width > max_width:
                        continue

                    # Check if horizontal lines span this width
                    h_top_start, h_top_end, _ = h_top
                    h_bottom_start, h_bottom_end, _ = h_bottom

                    # Top line should cover the rectangle width
                    if h_top_start > left_x + tolerance or h_top_end < right_x - tolerance:
                        continue
                    # Bottom line should cover the rectangle width
                    if h_bottom_start > left_x + tolerance or h_bottom_end < right_x - tolerance:
                        continue

                    # Valid rectangle found
                    rectangles.append({
                        'bbox': (left_x, top_y, width, height),
                        'area': width * height
                    })

    return rectangles


def remove_duplicate_rectangles(rectangles, iou_threshold=0.5):
    """
    Remove duplicate/overlapping rectangles.
    """
    if not rectangles:
        return []

    # Sort by area (largest first)
    rectangles = sorted(rectangles, key=lambda r: r['area'], reverse=True)

    result = []
    for rect in rectangles:
        x1, y1, w1, h1 = rect['bbox']
        is_duplicate = False

        for existing in result:
            x2, y2, w2, h2 = existing['bbox']

            # Calculate IoU
            ix1 = max(x1, x2)
            iy1 = max(y1, y2)
            ix2 = min(x1 + w1, x2 + w2)
            iy2 = min(y1 + h1, y2 + h2)

            if ix1 < ix2 and iy1 < iy2:
                intersection = (ix2 - ix1) * (iy2 - iy1)
                union = w1 * h1 + w2 * h2 - intersection
                iou = intersection / union

                if iou > iou_threshold:
                    is_duplicate = True
                    break

        if not is_duplicate:
            result.append(rect)

    return result


def has_quantity_labels(img, frame_bbox):
    """
    Check if the frame contains quantity labels like 'x1', 'x2', etc.
    These appear as small red text below parts.
    """
    x, y, w, h = frame_bbox
    img_h, img_w = img.shape[:2]

    # Extract frame region
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(img_w, x + w)
    y2 = min(img_h, y + h)
    frame_img = img[y1:y2, x1:x2]

    if frame_img.size == 0:
        return False

    # Look for red text (quantity labels are often red)
    hsv = cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV)

    # Red color mask - more lenient thresholds
    lower_red1 = np.array([0, 30, 30])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([160, 30, 30])
    upper_red2 = np.array([180, 255, 255])

    mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    # Count red pixels ratio
    fh, fw = frame_img.shape[:2]
    red_pixel_count = np.count_nonzero(mask_red)
    red_ratio = red_pixel_count / (fh * fw)

    # Also check for absolute number of red pixels (for larger frames)
    # Quantity labels typically have at least some minimum red pixels
    min_red_pixels = 50

    # If there's a reasonable amount of red text, likely has quantity labels
    # Use either ratio OR absolute count
    return red_ratio > 0.0003 or red_pixel_count > min_red_pixels


def find_nearby_number(img, frame_bbox, search_margin=100):
    """
    Find assembly numbers near the frame (outside the frame).
    """
    x, y, w, h = frame_bbox
    img_h, img_w = img.shape[:2]

    regions = []

    # Below the frame (most common)
    if y + h + 20 < img_h:
        regions.append(('below', img[y+h:min(y+h+search_margin, img_h), max(0,x-20):min(x+w+20, img_w)]))

    # Above the frame
    if y > 20:
        regions.append(('above', img[max(0, y-search_margin):y, max(0,x-20):min(x+w+20, img_w)]))

    # Left of the frame
    if x > 20:
        regions.append(('left', img[max(0,y-20):min(y+h+20, img_h), max(0, x-search_margin):x]))

    # Right of the frame
    if x + w + 20 < img_w:
        regions.append(('right', img[max(0,y-20):min(y+h+20, img_h), x+w:min(x+w+search_margin, img_w)]))

    for position, region in regions:
        if region.size == 0 or region.shape[0] < 10 or region.shape[1] < 10:
            continue

        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 200 < area < 50000:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                aspect = bw / bh if bh > 0 else 0
                if 0.2 < aspect < 4.0 and bh > 12:
                    return position, True

    return None, False


def is_connected_to_arrow(img, frame_bbox, all_lines, tolerance=10):
    """
    Check if the frame is connected to arrow/diagonal lines.

    Arrow-connected frames typically have:
    - A diagonal line that starts AT the frame edge and extends OUTWARD
    - The line should be significant (not just noise)

    Returns True if connected to arrow (should be excluded).
    """
    x, y, w, h = frame_bbox

    # Define frame edges
    left_edge = x
    right_edge = x + w
    top_edge = y
    bottom_edge = y + h

    # Minimum line length to be considered an arrow
    min_arrow_length = 30

    arrow_connections = 0

    for line in all_lines:
        x1, y1, x2, y2, angle = line

        # Only consider diagonal lines (20-70 degrees - more strict)
        if not (20 <= angle <= 70):
            continue

        # Calculate line length
        line_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if line_length < min_arrow_length:
            continue

        # Check if one endpoint is ON the frame edge and the other is OUTSIDE
        for (px, py), (ox, oy) in [((x1, y1), (x2, y2)), ((x2, y2), (x1, y1))]:
            # Check if point (px, py) is on frame edge
            on_left = abs(px - left_edge) < tolerance and top_edge < py < bottom_edge
            on_right = abs(px - right_edge) < tolerance and top_edge < py < bottom_edge
            on_top = abs(py - top_edge) < tolerance and left_edge < px < right_edge
            on_bottom = abs(py - bottom_edge) < tolerance and left_edge < px < right_edge

            if on_left or on_right or on_top or on_bottom:
                # Check if the OTHER endpoint is OUTSIDE the frame
                other_outside = (ox < left_edge - tolerance or ox > right_edge + tolerance or
                                oy < top_edge - tolerance or oy > bottom_edge + tolerance)

                if other_outside:
                    arrow_connections += 1
                    break

    # Need at least 2 arrow connections to be considered an arrow-connected frame
    # (arrows typically come in pairs or have arrowhead + line)
    return arrow_connections >= 2


def detect_colored_frames(img, color='red', min_line_length=50, debug_img=None):
    """
    Detect frames of a specific color using line detection.
    """
    # Get color mask
    mask = get_color_mask(img, color)

    # Detect lines
    h_lines, v_lines = detect_lines_hough(mask, min_line_length=min_line_length)

    # Merge nearby lines
    h_lines = merge_nearby_lines(h_lines, is_horizontal=True)
    v_lines = merge_nearby_lines(v_lines, is_horizontal=False)

    # Debug: draw detected lines
    if debug_img is not None:
        line_color = (0, 0, 255) if color == 'red' else (100, 100, 100)
        for start, end, y in h_lines:
            cv2.line(debug_img, (start, y), (end, y), line_color, 2)
        for start, end, x in v_lines:
            cv2.line(debug_img, (x, start), (x, end), line_color, 2)

    # Find rectangles
    img_h, img_w = img.shape[:2]
    rectangles = find_rectangles_from_lines(
        h_lines, v_lines,
        min_width=80, min_height=60,
        img_width=img_w, img_height=img_h
    )

    # Add color info
    for rect in rectangles:
        rect['color'] = color

    return rectangles


def extract_assembly_numbers(image_path, output_dir, debug=False):
    """
    Main function to extract assembly number images.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Failed to read image: {image_path}")

    img_h, img_w = img.shape[:2]

    # Adjust min_line_length based on image size
    min_line_length = max(50, min(img_w, img_h) // 20)

    print(f"[Step 1] Detecting colored lines (min_length={min_line_length})...")

    debug_img = img.copy() if debug else None

    # Detect red frames
    red_frames = detect_colored_frames(img, 'red', min_line_length, debug_img)
    print(f"  -> Red frames: {len(red_frames)}")

    # Detect black frames
    black_frames = detect_colored_frames(img, 'black', min_line_length, debug_img)
    print(f"  -> Black frames: {len(black_frames)}")

    # Combine all frames
    all_frames = red_frames + black_frames

    print(f"[Step 2] Removing duplicates...")
    all_frames = remove_duplicate_rectangles(all_frames)
    print(f"  -> Unique frames: {len(all_frames)}")

    # Detect blue frames (to exclude frames inside them)
    print(f"[Step 3] Detecting blue frames...")
    blue_frames = detect_blue_frames(img, min_line_length)
    print(f"  -> Blue frames: {len(blue_frames)}")

    # Detect ALL lines (including diagonal) for arrow detection
    print(f"[Step 4] Detecting arrow/diagonal lines...")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    all_lines = detect_all_lines_hough(edges, min_line_length=30)
    print(f"  -> Total lines detected: {len(all_lines)}")

    print(f"[Step 5] Filtering frames...")
    valid_frames = []
    rejected_frames = []

    for frame in all_frames:
        bbox = frame['bbox']

        # Check 0: Is inside a blue frame (should be excluded)
        inside_blue = is_inside_blue_frame(bbox, blue_frames)
        frame['inside_blue_frame'] = inside_blue

        # Check 1: Has quantity labels (x1, x2, etc.)
        has_qty = has_quantity_labels(img, bbox)
        frame['has_quantity_labels'] = has_qty

        # Check 2: Has nearby assembly number
        num_pos, has_number = find_nearby_number(img, bbox)
        frame['has_nearby_number'] = has_number
        frame['number_position'] = num_pos

        # Check 3: Is connected to arrow lines
        is_arrow_connected = is_connected_to_arrow(img, bbox, all_lines)
        frame['is_arrow_connected'] = is_arrow_connected

        # Apply rejection criteria (order matters - check blue first)
        if inside_blue:
            frame['reject_reason'] = 'inside_blue_frame'
            rejected_frames.append(frame)
        elif not has_qty:
            frame['reject_reason'] = 'no_quantity_labels'
            rejected_frames.append(frame)
        elif not has_number:
            frame['reject_reason'] = 'no_nearby_number'
            rejected_frames.append(frame)
        elif is_arrow_connected:
            frame['reject_reason'] = 'connected_to_arrow'
            rejected_frames.append(frame)
        else:
            valid_frames.append(frame)

    print(f"  -> Valid: {len(valid_frames)}, Rejected: {len(rejected_frames)}")

    for frame in rejected_frames:
        x, y, w, h = frame['bbox']
        print(f"    [REJECT] {w}x{h} at ({x},{y}) - {frame.get('reject_reason', 'unknown')}")

    # Sort by position (top-to-bottom, left-to-right)
    valid_frames.sort(key=lambda f: (f['bbox'][1], f['bbox'][0]))

    # Debug visualization
    if debug:
        # Draw diagonal lines in yellow for debugging
        for line in all_lines:
            x1, y1, x2, y2, angle = line
            if 15 <= angle <= 75:  # Diagonal
                cv2.line(debug_img, (x1, y1), (x2, y2), (0, 255, 255), 1)

        for frame in valid_frames:
            x, y, w, h = frame['bbox']
            color_bgr = (0, 255, 0)  # Green for valid
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), color_bgr, 3)
            cv2.putText(debug_img, frame['color'], (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_bgr, 2)

        for frame in rejected_frames:
            x, y, w, h = frame['bbox']
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
            # Show rejection reason
            reason = frame.get('reject_reason', '')[:15]
            cv2.putText(debug_img, reason, (x, y+h+15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        debug_path = output_dir / "debug_frames.png"
        cv2.imwrite(str(debug_path), debug_img)
        print(f"  -> Debug image saved: {debug_path}")

    # Extract and save valid frames
    print(f"[Step 6] Extracting {len(valid_frames)} assembly number images...")

    base_name = image_path.stem
    extracted = []
    validation_rejected = []

    for i, frame in enumerate(valid_frames):
        x, y, w, h = frame['bbox']

        # Add margin
        margin = 15
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(img_w, x + w + margin)
        y2 = min(img_h, y + h + margin)

        # Extend downward to capture assembly number
        y2_extended = min(img_h, y + h + 80)

        frame_img = img[y1:y2_extended, x1:x2]

        # Post-extraction validation: check that extracted image has exactly ONE valid frame
        is_valid, validation_reason = validate_extracted_frame(frame_img, debug=False)

        if not is_valid:
            validation_rejected.append({
                'bbox': (x, y, w, h),
                'color': frame['color'],
                'validation_reason': validation_reason
            })
            print(f"  [VALIDATION REJECT] {w}x{h} at ({x},{y}) - {validation_reason}")
            continue

        # Additional check: count frames using color detection
        # Only reject if there are clearly multiple LARGE frames (not small internal boxes)
        frame_count_red = count_frames_in_image(frame_img, 'red')
        frame_count_black = count_frames_in_image(frame_img, 'black')
        total_frame_count = frame_count_red + frame_count_black

        # Only reject if we detect more than 2 frames (to avoid false positives from
        # internal content that looks like small frames)
        if total_frame_count > 2:
            validation_rejected.append({
                'bbox': (x, y, w, h),
                'color': frame['color'],
                'validation_reason': f'multiple_frames_count_{total_frame_count}'
            })
            print(f"  [VALIDATION REJECT] {w}x{h} at ({x},{y}) - multiple frames detected (count={total_frame_count})")
            continue

        out_filename = f"{base_name}_assembly_{len(extracted)+1:02d}.jpg"
        out_path = output_dir / out_filename

        cv2.imwrite(str(out_path), frame_img)
        print(f"  Saved: {out_filename} ({w}x{h}, color={frame['color']})")

        extracted.append({
            'filename': out_filename,
            'bbox': (x, y, w, h),
            'color': frame['color']
        })

    print(f"[Step 7] Post-extraction validation results:")
    print(f"  -> Valid: {len(extracted)}, Validation rejected: {len(validation_rejected)}")

    return extracted


def main():
    parser = argparse.ArgumentParser(description="Extract assembly number images (v2 - line detection)")
    parser.add_argument("input_path", help="Path to the assembly page image")
    parser.add_argument("--output", "-o", default=None, help="Output directory")
    parser.add_argument("--debug", "-d", action="store_true", help="Save debug visualization")

    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path(__file__).parent / "output" / "assembly_numbers_v2"

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input: {input_path}")
    print(f"Output: {output_dir}")
    print()

    extracted = extract_assembly_numbers(input_path, output_dir, debug=args.debug)

    print(f"\n[DONE] Extracted {len(extracted)} assembly number images")


if __name__ == "__main__":
    main()

"""
Assembly Number Image Extraction PoC
Extracts assembly number images from assembly page images.

Detection criteria:
- Frame color: Red or Black (NOT blue)
- Contains parts with quantity labels (x1, x2, etc.)
- Has assembly number near the frame
"""

import argparse
import cv2
import numpy as np
from pathlib import Path
from PIL import Image


def detect_frame_color(frame_img):
    """
    Detect the dominant color of a frame border.
    Returns: 'red', 'black', 'blue', or 'unknown'
    """
    h, w = frame_img.shape[:2]

    # Sample border pixels with adaptive width
    border_width = max(3, min(15, h // 8, w // 8))

    # Collect border pixels from all edges
    border_regions = []
    # Top edge
    border_regions.append(frame_img[0:border_width, :])
    # Bottom edge
    border_regions.append(frame_img[h-border_width:h, :])
    # Left edge
    border_regions.append(frame_img[:, 0:border_width])
    # Right edge
    border_regions.append(frame_img[:, w-border_width:w])

    # Combine and convert to HSV
    border_pixels = np.vstack([r.reshape(-1, 3) for r in border_regions])
    hsv_border = cv2.cvtColor(border_pixels.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV)
    hsv_border = hsv_border.reshape(-1, 3)

    # Count color categories
    red_count = 0
    blue_count = 0
    black_count = 0
    gray_count = 0

    for pixel in hsv_border:
        hue, sat, val = pixel

        # Red (hue wraps around 0/180) - more lenient thresholds
        if (hue < 15 or hue > 165) and sat > 30 and val > 40:
            red_count += 1
        # Blue - standard range
        elif 90 <= hue <= 135 and sat > 40 and val > 40:
            blue_count += 1
        # Black (low value, low saturation)
        elif val < 100 and sat < 60:
            black_count += 1
        # Gray (medium value, low saturation) - often part of frames
        elif 100 <= val < 180 and sat < 40:
            gray_count += 1

    total = len(hsv_border)
    red_ratio = red_count / total
    blue_ratio = blue_count / total
    black_ratio = black_count / total
    gray_ratio = gray_count / total

    # Determine dominant color
    # Red detection is prioritized with lower threshold
    if red_ratio > 0.02 and red_ratio > blue_ratio:
        return 'red', red_ratio
    elif blue_ratio > 0.03 and blue_ratio > red_ratio:
        return 'blue', blue_ratio
    elif black_ratio > 0.08:
        return 'black', black_ratio
    elif gray_ratio > 0.3:
        # Gray frames are often black/dark gray outlines
        return 'black', gray_ratio
    else:
        return 'unknown', 0


def has_quantity_labels(frame_img):
    """
    Check if the frame contains quantity labels like 'x1', 'x2', etc.
    These appear as small text below parts.
    """
    # Convert to grayscale and threshold
    gray = cv2.cvtColor(frame_img, cv2.COLOR_BGR2GRAY)

    # Look for red 'x' characters (quantity labels are often red)
    hsv = cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV)

    # Red color mask - expanded range
    lower_red1 = np.array([0, 40, 40])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([165, 40, 40])
    upper_red2 = np.array([180, 255, 255])

    mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    # Also check for black text (some diagrams use black for quantity)
    _, mask_dark = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

    # Count red pixels ratio
    h, w = frame_img.shape[:2]
    red_ratio = np.count_nonzero(mask_red) / (h * w)

    # If there's a reasonable amount of red text, likely has quantity labels
    # Parts list frames typically have more red text (x1, x2, etc.)
    return red_ratio > 0.0005  # At least 0.05% red pixels


def find_nearby_number(img, frame_bbox, search_margin=120):
    """
    Find assembly numbers near the frame (outside the frame).
    Returns the number if found, None otherwise.
    """
    x, y, w, h = frame_bbox
    img_h, img_w = img.shape[:2]

    # Define search regions around the frame
    regions = []

    # Below the frame (most common position for assembly numbers)
    if y + h + 20 < img_h:
        regions.append(('below', img[y+h:min(y+h+search_margin, img_h), max(0,x-30):min(x+w+30, img_w)]))

    # Above the frame
    if y > 20:
        regions.append(('above', img[max(0, y-search_margin):y, max(0,x-30):min(x+w+30, img_w)]))

    # Left of the frame
    if x > 20:
        regions.append(('left', img[max(0,y-30):min(y+h+30, img_h), max(0, x-search_margin):x]))

    # Right of the frame
    if x + w + 20 < img_w:
        regions.append(('right', img[max(0,y-30):min(y+h+30, img_h), x+w:min(x+w+search_margin, img_w)]))

    for position, region in regions:
        if region.size == 0 or region.shape[0] < 10 or region.shape[1] < 10:
            continue

        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)

        # Look for dark text (numbers)
        _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)

        # Find contours that could be numbers
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Numbers are typically medium-sized - adjusted range
            if 200 < area < 80000:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                aspect = bw / bh if bh > 0 else 0
                # Numbers have reasonable aspect ratio
                if 0.2 < aspect < 4.0 and bh > 15:
                    return position, True

    return None, False


def detect_frames(img, min_area=8000, max_area_ratio=0.4):
    """
    Detect rectangular frames in the image.
    Returns list of (x, y, w, h, color, has_number) tuples.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_h, img_w = img.shape[:2]
    max_area = img_h * img_w * max_area_ratio

    # Edge detection with adjusted thresholds
    edges = cv2.Canny(gray, 20, 80)

    # Dilate to connect gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    frames = []

    for cnt in contours:
        # Approximate to polygon
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        # Check if it's roughly rectangular (4+ vertices)
        if len(approx) >= 4:
            area = cv2.contourArea(cnt)

            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect = w / h if h > 0 else 0

                # Reasonable aspect ratio for assembly diagrams
                if 0.2 < aspect < 5.0:
                    # Extract frame region with small margin
                    margin = 2
                    y1 = max(0, y - margin)
                    y2 = min(img_h, y + h + margin)
                    x1 = max(0, x - margin)
                    x2 = min(img_w, x + w + margin)
                    frame_roi = img[y1:y2, x1:x2]

                    if frame_roi.size > 0:
                        # Detect frame color
                        color, color_ratio = detect_frame_color(frame_roi)

                        # Check for quantity labels
                        has_qty = has_quantity_labels(frame_roi)

                        # Check for nearby assembly number
                        num_pos, has_number = find_nearby_number(img, (x, y, w, h))

                        frames.append({
                            'bbox': (x, y, w, h),
                            'area': area,
                            'color': color,
                            'color_ratio': color_ratio,
                            'has_quantity_labels': has_qty,
                            'has_nearby_number': has_number,
                            'number_position': num_pos
                        })

    # Sort by area (largest first)
    frames.sort(key=lambda f: f['area'], reverse=True)

    return frames


def filter_valid_frames(frames):
    """
    Filter frames based on detection criteria.
    Valid frames: red/black, has quantity labels, has nearby number
    Invalid frames: blue, no number nearby
    """
    valid_frames = []
    rejected_frames = []

    for frame in frames:
        color = frame['color']
        has_qty = frame['has_quantity_labels']
        has_num = frame['has_nearby_number']

        # Rejection criteria
        if color == 'blue':
            frame['reject_reason'] = 'blue_frame'
            rejected_frames.append(frame)
        elif not has_num:
            frame['reject_reason'] = 'no_nearby_number'
            rejected_frames.append(frame)
        # Accept red/black frames with nearby number
        elif color in ['red', 'black'] and has_num:
            valid_frames.append(frame)
        # Also accept unknown color if it has quantity labels and number
        elif color == 'unknown' and has_qty and has_num:
            # Likely a thin-bordered frame we couldn't classify
            frame['color'] = 'inferred_valid'
            valid_frames.append(frame)
        else:
            frame['reject_reason'] = f'criteria_not_met (color={color}, qty={has_qty}, num={has_num})'
            rejected_frames.append(frame)

    return valid_frames, rejected_frames


def remove_nested_frames(frames, overlap_threshold=0.7):
    """
    Remove frames that are mostly contained within larger frames.
    """
    if len(frames) <= 1:
        return frames

    # Sort by area descending
    sorted_frames = sorted(frames, key=lambda f: f['area'], reverse=True)

    result = []

    for frame in sorted_frames:
        x1, y1, w1, h1 = frame['bbox']
        is_nested = False

        for existing in result:
            x2, y2, w2, h2 = existing['bbox']

            # Calculate intersection
            ix1 = max(x1, x2)
            iy1 = max(y1, y2)
            ix2 = min(x1 + w1, x2 + w2)
            iy2 = min(y1 + h1, y2 + h2)

            if ix1 < ix2 and iy1 < iy2:
                intersection = (ix2 - ix1) * (iy2 - iy1)
                frame_area = w1 * h1

                if intersection / frame_area > overlap_threshold:
                    is_nested = True
                    break

        if not is_nested:
            result.append(frame)

    return result


def extract_assembly_numbers(image_path, output_dir, debug=False):
    """
    Main function to extract assembly number images from an assembly page.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Failed to read image: {image_path}")

    print(f"[Step 1] Detecting frames...")
    all_frames = detect_frames(img)
    print(f"  -> Found {len(all_frames)} potential frames")

    print(f"[Step 2] Filtering valid frames...")
    valid_frames, rejected_frames = filter_valid_frames(all_frames)
    print(f"  -> Valid: {len(valid_frames)}, Rejected: {len(rejected_frames)}")

    for frame in rejected_frames:
        x, y, w, h = frame['bbox']
        print(f"    [REJECT] {w}x{h} at ({x},{y}) - {frame.get('reject_reason', 'unknown')}")

    print(f"[Step 3] Removing nested frames...")
    valid_frames = remove_nested_frames(valid_frames)
    print(f"  -> Final: {len(valid_frames)} frames")

    # Sort by position (top-to-bottom, left-to-right)
    valid_frames.sort(key=lambda f: (f['bbox'][1], f['bbox'][0]))

    # Debug visualization
    if debug:
        debug_img = img.copy()
        for frame in valid_frames:
            x, y, w, h = frame['bbox']
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(debug_img, frame['color'], (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        for frame in rejected_frames:
            x, y, w, h = frame['bbox']
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 255), 2)

        debug_path = output_dir / "debug_frames.png"
        cv2.imwrite(str(debug_path), debug_img)
        print(f"  -> Debug image saved: {debug_path}")

    # Extract and save valid frames
    print(f"[Step 4] Extracting {len(valid_frames)} assembly number images...")

    base_name = image_path.stem
    extracted = []

    for i, frame in enumerate(valid_frames):
        x, y, w, h = frame['bbox']

        # Add margin around the frame
        margin = 20
        img_h, img_w = img.shape[:2]
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(img_w, x + w + margin)
        y2 = min(img_h, y + h + margin)

        # Also include area below for assembly number
        # Extend downward to capture the number
        y2_extended = min(img_h, y + h + 100)

        frame_img = img[y1:y2_extended, x1:x2]

        out_filename = f"{base_name}_assembly_{i+1:02d}.jpg"
        out_path = output_dir / out_filename

        cv2.imwrite(str(out_path), frame_img)
        print(f"  Saved: {out_filename} ({w}x{h}, color={frame['color']})")

        extracted.append({
            'filename': out_filename,
            'bbox': (x, y, w, h),
            'color': frame['color']
        })

    return extracted


def main():
    parser = argparse.ArgumentParser(description="Extract assembly number images from assembly page")
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
        output_dir = Path(__file__).parent / "output" / "assembly_numbers"

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input: {input_path}")
    print(f"Output: {output_dir}")
    print()

    extracted = extract_assembly_numbers(input_path, output_dir, debug=args.debug)

    print(f"\n[DONE] Extracted {len(extracted)} assembly number images")


if __name__ == "__main__":
    main()

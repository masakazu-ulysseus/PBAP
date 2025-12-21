"""
Part Extraction PoC v2
- Transparent background (Alpha channel)
- Improved crop positioning
"""

import argparse
import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image


def find_largest_frame(gray_img, min_area=1000):
    """Detect the largest rectangular frame in the image."""
    edges = cv2.Canny(gray_img, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects = []
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            area = cv2.contourArea(cnt)
            if area >= min_area:
                x, y, w, h = cv2.boundingRect(approx)
                rects.append((x, y, w, h, area))

    if not rects:
        return None

    # Return largest by area
    rects.sort(key=lambda r: r[4], reverse=True)
    return rects[0][:4]


def is_blue_indicator(frame_img, contour, bbox):
    """
    Check if the contour is a blue indicator (quantity indicator like ③ or size label like 2x3).
    """
    x, y, w, h = bbox

    # Check if it's predominantly blue
    roi = frame_img[y:y+h, x:x+w]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Blue color range in HSV
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    blue_ratio = np.count_nonzero(mask_blue) / (w * h) if (w * h) > 0 else 0

    # If more than 20% is blue, it's likely a blue indicator (circle or label)
    return blue_ratio > 0.2


def is_red_text(frame_img, contour, bbox, max_size=100):
    """
    Check if the contour is red text (quantity labels like x2, x1).
    """
    x, y, w, h = bbox

    # Size filter - text is typically small
    if w > max_size or h > max_size:
        return False

    # Check if it's predominantly red
    roi = frame_img[y:y+h, x:x+w]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Red color range in HSV (red wraps around 0/180)
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    red_ratio = np.count_nonzero(mask_red) / (w * h) if (w * h) > 0 else 0

    # If more than 30% is red, it's likely red text
    return red_ratio > 0.3


def extract_parts_with_mask(frame_img, debug_dir=None, min_size=20, max_size=2000, min_area=1800):
    """
    Extract parts with contour masks for transparent background.

    Args:
        frame_img: BGR image of the enhanced frame
        debug_dir: optional debug output directory
        min_size: minimum width/height (default: 20, lowered from 30 for thin parts)
        max_size: maximum width/height
        min_area: minimum contour area (default: 1500, lowered from 2000 for thin parts)

    Returns:
        list of dict: [{'bbox': (x,y,w,h), 'contour': np.array, 'mask': np.array}, ...]
    """
    # Noise reduction
    frame_denoised = cv2.medianBlur(frame_img, 7)
    gray = cv2.cvtColor(frame_denoised, cv2.COLOR_BGR2GRAY)

    # Otsu's Binarization (Inverse - parts are white)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    if debug_dir:
        cv2.imwrite(str(debug_dir / "01_threshold.png"), thresh)

    # Find external contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    parts = []
    rejected_parts = []

    for i, cnt in enumerate(contours):
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        aspect = w / h if h > 0 else 0

        # Filtering criteria
        reject_reason = None

        # Blue indicator filter (quantity indicators like ③ or size labels like 2x3)
        if is_blue_indicator(frame_img, cnt, (x, y, w, h)):
            reject_reason = "blue_indicator"
        # Red text filter (quantity labels like x2, x1)
        elif is_red_text(frame_img, cnt, (x, y, w, h)):
            reject_reason = "red_text"
        elif w < min_size or h < min_size:
            reject_reason = f"too_small ({w}x{h})"
        elif w > max_size or h > max_size:
            reject_reason = f"too_large ({w}x{h})"
        elif area < min_area:
            reject_reason = f"area_small ({area})"
        elif aspect < 0.15 or aspect > 6.0:  # Relaxed for thin parts (rods)
            reject_reason = f"aspect ({aspect:.2f})"
        else:
            # Object count check - avoid multiple objects merged together
            part_crop = frame_img[y:y+h, x:x+w]
            obj_count = count_significant_objects(part_crop)
            if obj_count > 1:
                # Exception: very thin/elongated parts (rods) - aspect < 0.35 or > 3.0
                # These often get merged with nearby text/symbols but are valid parts
                if aspect < 0.35 or aspect > 3.0:
                    print(f"    -> EXCEPTION: Thin part (aspect={aspect:.2f}), allowing despite multi_objects")
                else:
                    reject_reason = f"multi_objects ({obj_count})"

        info = {
            'idx': i,
            'bbox': (x, y, w, h),
            'area': area,
            'aspect': aspect,
            'contour': cnt,
        }

        if reject_reason:
            info['reject_reason'] = reject_reason
            rejected_parts.append(info)
            print(f"  [REJECT] Part {i}: {w}x{h}, area={area:.0f}, aspect={aspect:.2f} -> {reject_reason}")
        else:
            parts.append(info)
            print(f"  [ACCEPT] Part {i}: {w}x{h}, area={area:.0f}, aspect={aspect:.2f}")

    # Sort by x position
    parts.sort(key=lambda p: p['bbox'][0])

    # Debug visualization
    if debug_dir:
        debug_img = frame_img.copy()
        for p in parts:
            x, y, w, h = p['bbox']
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.drawContours(debug_img, [p['contour']], -1, (0, 255, 0), 1)
        for p in rejected_parts:
            x, y, w, h = p['bbox']
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 255), 1)
        cv2.imwrite(str(debug_dir / "02_detected_parts.png"), debug_img)

    return parts


def count_significant_objects(image_crop, min_area=50, significant_ratio=0.5):
    """Count significant objects in a crop (to detect merged parts)."""
    if image_crop.size == 0:
        return 0

    gray = cv2.cvtColor(image_crop, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    areas = [cv2.contourArea(cnt) for cnt in contours if cv2.contourArea(cnt) >= min_area]
    if not areas:
        return 0

    max_area = max(areas)
    significant = [a for a in areas if a > max_area * significant_ratio]
    return len(significant)


def create_part_with_transparent_bg(frame_img, part_info, margin=5, debug_dir=None, part_idx=0):
    """
    Create a part image with transparent background.
    Only the detected object pixels are visible; everything else is transparent.

    Args:
        frame_img: BGR image of the frame
        part_info: dict with 'bbox' and 'contour'
        margin: margin around the bounding box
        debug_dir: optional debug output directory
        part_idx: part index for debug filenames

    Returns:
        PIL.Image: RGBA image with transparent background
    """
    x, y, w, h = part_info['bbox']
    contour = part_info['contour']

    h_img, w_img = frame_img.shape[:2]

    # Add margin to bbox
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(w_img, x + w + margin)
    y2 = min(h_img, y + h + margin)

    crop_w = x2 - x1
    crop_h = y2 - y1

    # Create a mask using convex hull to ensure entire object is covered
    # This prevents issues with light-colored areas being excluded
    full_mask = np.zeros((h_img, w_img), dtype=np.uint8)

    # Use convex hull for more robust filling
    hull = cv2.convexHull(contour)
    cv2.drawContours(full_mask, [hull], -1, 255, thickness=cv2.FILLED)

    # Also draw the original contour to capture any concave details
    cv2.drawContours(full_mask, [contour], -1, 255, thickness=cv2.FILLED)

    # Dilate mask to include edge pixels and fill small gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    full_mask = cv2.dilate(full_mask, kernel, iterations=2)

    # Crop the mask and image
    mask_crop = full_mask[y1:y2, x1:x2]
    img_crop = frame_img[y1:y2, x1:x2].copy()

    # Convert BGR to RGBA
    img_rgb = cv2.cvtColor(img_crop, cv2.COLOR_BGR2RGB)
    img_rgba = np.dstack([img_rgb, mask_crop])

    if debug_dir:
        # Save mask for debugging
        cv2.imwrite(str(debug_dir / f"part_{part_idx:02d}_mask.png"), mask_crop)
        # Save RGBA
        pil_img = Image.fromarray(img_rgba, mode='RGBA')
        pil_img.save(str(debug_dir / f"part_{part_idx:02d}_rgba.png"))

    return Image.fromarray(img_rgba, mode='RGBA')


def create_part_tight_crop(frame_img, part_info, padding=10, debug_dir=None, part_idx=0):
    """
    Create a tightly cropped part image (no transparent background).
    Uses contour bounding rect with padding.

    Args:
        frame_img: BGR image of the frame
        part_info: dict with 'bbox' and 'contour'
        padding: padding around the tight bounding box

    Returns:
        PIL.Image: RGB image with tight crop
    """
    contour = part_info['contour']

    # Get the tight bounding rect (potentially rotated)
    # For simplicity, use axis-aligned bounding rect
    x, y, w, h = cv2.boundingRect(contour)

    h_img, w_img = frame_img.shape[:2]

    # Add padding
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(w_img, x + w + padding)
    y2 = min(h_img, y + h + padding)

    img_crop = frame_img[y1:y2, x1:x2].copy()

    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img_crop, cv2.COLOR_BGR2RGB)

    return Image.fromarray(img_rgb, mode='RGB')


def main():
    parser = argparse.ArgumentParser(description="Part Extraction PoC v2 - Transparent Background")
    parser.add_argument("input_path", help="Path to the assembly diagram image")
    parser.add_argument("--output", "-o", default=None, help="Output directory (default: poc/output/parts_v2)")
    parser.add_argument("--transparent", "-t", action="store_true", default=True,
                        help="Enable transparent background (default: True)")
    parser.add_argument("--no-transparent", dest="transparent", action="store_false",
                        help="Disable transparent background")
    parser.add_argument("--margin", "-m", type=int, default=5, help="Margin around parts (default: 5)")
    parser.add_argument("--debug", "-d", action="store_true", help="Save debug images")

    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    # Setup output directories
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path(__file__).parent / "output" / "parts_v2"

    output_dir.mkdir(parents=True, exist_ok=True)

    debug_dir = None
    if args.debug:
        debug_dir = output_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input: {input_path}")
    print(f"Output: {output_dir}")
    print(f"Transparent: {args.transparent}")
    print(f"Margin: {args.margin}")
    print()

    # Load image
    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"Failed to read image: {input_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Find largest frame (red box with parts list)
    print("[Step 1] Detecting frames...")
    frame_bbox = find_largest_frame(gray)

    if frame_bbox is None:
        print("[ERROR] No rectangular frame detected!")
        return

    fx, fy, fw, fh = frame_bbox
    print(f"  -> Found frame: ({fx}, {fy}) {fw}x{fh}")

    if debug_dir:
        debug_frame = img.copy()
        cv2.rectangle(debug_frame, (fx, fy), (fx+fw, fy+fh), (0, 0, 255), 3)
        cv2.imwrite(str(debug_dir / "00_detected_frame.png"), debug_frame)

    # 2. Crop frame with margin to exclude border
    margin_frame = 10
    frame_roi = img[fy+margin_frame : fy+fh-margin_frame,
                    fx+margin_frame : fx+fw-margin_frame]

    # 3. Super-resolution (2x) + Sharpening
    print("[Step 2] Enhancing frame (2x upscale + sharpen)...")
    frame_upscaled = cv2.resize(frame_roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    blurred = cv2.GaussianBlur(frame_upscaled, (0, 0), 3)
    frame_enhanced = cv2.addWeighted(frame_upscaled, 1.5, blurred, -0.5, 0)

    if debug_dir:
        cv2.imwrite(str(debug_dir / "00_frame_enhanced.png"), frame_enhanced)

    # 4. Extract parts with contour information
    print("[Step 3] Extracting parts...")
    parts = extract_parts_with_mask(frame_enhanced, debug_dir=debug_dir)

    print(f"\n[Step 4] Saving {len(parts)} parts...")

    base_name = input_path.stem

    for i, part_info in enumerate(parts):
        if args.transparent:
            # Create with transparent background
            part_img = create_part_with_transparent_bg(
                frame_enhanced, part_info,
                margin=args.margin,
                debug_dir=debug_dir if args.debug else None,
                part_idx=i+1
            )
            ext = "png"  # PNG for transparency
        else:
            # Create tight crop without transparency
            part_img = create_part_tight_crop(
                frame_enhanced, part_info,
                padding=args.margin,
                debug_dir=debug_dir if args.debug else None,
                part_idx=i+1
            )
            ext = "webp"

        out_path = output_dir / f"{base_name}_part_{i+1:02d}.{ext}"
        part_img.save(str(out_path))
        print(f"  Saved: {out_path.name}")

    print(f"\n[DONE] Extracted {len(parts)} parts from {input_path.name}")


if __name__ == "__main__":
    main()

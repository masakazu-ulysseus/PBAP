import argparse
import os
import cv2
import numpy as np
from pathlib import Path


def find_rectangular_contours(gray_img, min_area=1000):
    """Detect rectangular contours (frames) in the image.
    Returns a list of bounding boxes (x, y, w, h)."""
    # Edge detection
    edges = cv2.Canny(gray_img, 50, 150)
    # Dilate to close gaps in the frame lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=1)
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects = []
    for cnt in contours:
        # Approximate polygon
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            area = cv2.contourArea(cnt)
            if area >= min_area:
                x, y, w, h = cv2.boundingRect(approx)
                rects.append((x, y, w, h))
    # Sort by x coordinate for deterministic order
    rects.sort(key=lambda r: r[0])
    print(f"[DEBUG] Detected {len(rects)} rectangular frame(s) with min_area={min_area}")
    return rects


def extract_parts_from_frame(frame_img, debug_dir=None, frame_idx=0, min_size=30, max_size=1000):
    """Extract part bounding boxes inside a given frame image.
    Returns a list of (x, y, w, h) relative to the frame image.
    """
    # Apply noise reduction (median filter is good for scanned images)
    # Kernel size must be odd (3, 5, 7, etc.)
    frame_img_denoised = cv2.medianBlur(frame_img, 7)
    
    gray = cv2.cvtColor(frame_img_denoised, cv2.COLOR_BGR2GRAY)
    
    # Strategy 1: Otsu's Binarization (Global) - Good for high contrast parts on white bg
    # Invert so parts are white, bg is black
    _, thresh_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Minimal morphological operations to remove noise but NOT merge parts
    # DISABLED: This may be merging parts together
    # kernel_noise = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    # thresh_otsu = cv2.morphologyEx(thresh_otsu, cv2.MORPH_OPEN, kernel_noise, iterations=1)
    
    # Debug: Print threshold statistics
    white_pixels = np.count_nonzero(thresh_otsu == 255)
    total_pixels = thresh_otsu.size
    white_ratio = white_pixels / total_pixels
    print(f"[DEBUG] Threshold: {white_pixels}/{total_pixels} white pixels ({white_ratio*100:.1f}%)")
    
    if debug_dir:
        cv2.imwrite(str(debug_dir / f"frame_{frame_idx:02d}_thresh_otsu.jpg"), thresh_otsu)

    # Find contours
    contours, hierarchy = cv2.findContours(thresh_otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    parts = []
    print(f"[DEBUG] Frame {frame_idx} (Otsu): found {len(contours)} contours")
    
    if debug_dir:
        debug_cnt_img = frame_img.copy()
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        
        # Filter logic
        is_part = True
        if w < min_size or h < min_size: is_part = False
        if w > max_size or h > max_size: is_part = False
        # Minimum area filter (to exclude small symbols like ×)
        # For 2x upscaled images, this filters out objects < 2000 pixels
        if area < 2000: is_part = False
        # Aspect ratio filter (parts shouldn't be extremely thin lines)
        aspect = w / h
        if aspect < 0.2 or aspect > 5.0: is_part = False
        
        print(f"  - Contour: {w}x{h}, Area: {area:.0f}, Aspect: {aspect:.2f} -> {'KEEP' if is_part else 'SKIP'}")
        
        if debug_dir:
            color = (0, 255, 0) if is_part else (0, 0, 255)
            cv2.rectangle(debug_cnt_img, (x, y), (x+w, y+h), color, 2)
        
        if is_part:
            parts.append((x, y, w, h))

    if debug_dir:
        cv2.imwrite(str(debug_dir / f"frame_{frame_idx:02d}_contours_otsu.jpg"), debug_cnt_img)

    # Strategy 2: Adaptive Threshold (if Otsu failed or found too few?)
    # For now, let's stick to Otsu as primary. If parts are merged, Adaptive might help but 
    # usually Otsu is cleaner for "scanned document" type images with clear background.
    
    # Sort by x for stable naming
    parts.sort(key=lambda r: r[0])
    return parts


def count_objects_in_crop(image_crop, min_area=50):
    """
    Count distinct objects in a cropped image.
    Returns a list of dicts: [{'area': area, 'bbox': (x,y,w,h)}, ...]
    """
    if image_crop.size == 0:
        return []
        
    gray = cv2.cvtColor(image_crop, cv2.COLOR_BGR2GRAY)
    
    # Otsu's binarization
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find external contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    objects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            objects.append({'area': area, 'bbox': (x, y, w, h)})
            
    return objects



def save_part(image, bbox, out_path, margin_top=0, margin_bottom=20, margin_left=0, margin_right=20):
    x, y, w, h = bbox
    
    # Add asymmetric margins
    h_img, w_img = image.shape[:2]
    y_start = max(0, y - margin_top)
    y_end = min(h_img, y + h + margin_bottom)
    x_start = max(0, x - margin_left)
    x_end = min(w_img, x + w + margin_right)
    
    crop = image[y_start:y_end, x_start:x_end]
    # Ensure output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Encode as WEBP (lossless for PoC clarity)
    cv2.imwrite(out_path, crop, [cv2.IMWRITE_WEBP_QUALITY, 95])


def main():
    parser = argparse.ArgumentParser(description="Extract part images from an assembly diagram image.")
    parser.add_argument("input_path", help="Path to the assembly diagram image (JPEG/PNG).")
    parser.add_argument("--output", "-o", default="c:/develop/Antigravity/PPBA/poc/output/parts", help="Directory to store extracted part images.")
    parser.add_argument("--filter-objects", action="store_true", default=True, help="Filter out regions with multiple objects (default: True).")

    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    # Load image (BGR)
    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"Failed to read image: {input_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1️⃣ Detect outer frames (rectangular containers)
    frames = find_rectangular_contours(gray)
    if not frames:
        print("[INFO] No rectangular frames detected. Trying fallback Canny+contour method.")
        # Fallback: treat the whole image as a single frame
        frames = [(0, 0, img.shape[1], img.shape[0])]
    
    # Select only the largest frame (by area) when multiple frames are detected
    if len(frames) > 1:
        print(f"[INFO] {len(frames)} frames detected. Selecting the largest frame (by area).")
        # Calculate area for each frame and sort by area (descending)
        frames_with_area = [(fx, fy, fw, fh, fw * fh) for fx, fy, fw, fh in frames]
        frames_with_area.sort(key=lambda x: x[4], reverse=True)
        
        # Select only the largest frame
        largest_frame = frames_with_area[0]
        frames = [(largest_frame[0], largest_frame[1], largest_frame[2], largest_frame[3])]
        print(f"[INFO] Selected frame with area: {largest_frame[4]} pixels ({largest_frame[2]}x{largest_frame[3]})")
    else:
        print(f"[INFO] {len(frames)} frame detected.")

    # --- Debug: Save image with detected frames drawn ---
    debug_img = img.copy()
    for i, (fx, fy, fw, fh) in enumerate(frames):
        cv2.rectangle(debug_img, (fx, fy), (fx + fw, fy + fh), (0, 0, 255), 3)
        cv2.putText(debug_img, f"Frame {i+1}", (fx, fy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    
    debug_dir = Path(args.output).parent / "debug"
    os.makedirs(debug_dir, exist_ok=True)
    debug_path = debug_dir / f"{input_path.stem}_debug_frames.jpg"
    cv2.imwrite(str(debug_path), debug_img)
    print(f"[DEBUG] Saved frame visualization to: {debug_path}")
    # ----------------------------------------------------

    base_name = input_path.stem  # e.g. AssemblyDiagram_no31
    part_counter = 1
    for frame_idx, (fx, fy, fw, fh) in enumerate(frames, start=1):
        # Crop INSIDE the frame to avoid the border line
        margin = 10  # Increased from 5 to avoid frame borders
        if fw > 2 * margin and fh > 2 * margin:
            frame_roi = img[fy+margin : fy+fh-margin, fx+margin : fx+fw-margin]
        else:
            frame_roi = img[fy:fy+fh, fx:fx+fw]
        
        # --- Debug: Save the cropped frame image with super-resolution ---
        # Apply 2x super-resolution (upscale to 2x width and 2x height)
        frame_roi_upscaled = cv2.resize(frame_roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Apply sharpening (unsharp mask)
        # Create a Gaussian blur
        blurred = cv2.GaussianBlur(frame_roi_upscaled, (0, 0), 3)
        # Sharpen using weighted difference
        frame_roi_sharpened = cv2.addWeighted(frame_roi_upscaled, 1.5, blurred, -0.5, 0)
        
        frame_crop_path = debug_dir / f"{base_name}_frame_{frame_idx:02d}.webp"
        cv2.imwrite(str(frame_crop_path), frame_roi_sharpened)
        print(f"[DEBUG] Saved enhanced frame (2x upscaled + sharpened) to: {frame_crop_path}")
        # -------------------------------------------

        # Use the enhanced (upscaled + sharpened) frame for part extraction
        # This ensures parts are also high-resolution
        parts = extract_parts_from_frame(frame_roi_sharpened, debug_dir=debug_dir, frame_idx=frame_idx)
        if not parts:
            print(f"[WARN] No parts found in frame {frame_idx}.")
            continue
            
        for part_bbox in parts:
            x, y, w, h = part_bbox
            
            # Object Count Filtering
            if args.filter_objects:
                part_crop = frame_roi_sharpened[y:y+h, x:x+w]
                objects = count_objects_in_crop(part_crop)
                
                if not objects:
                     print(f"    -> REJECTED (No objects detected)")
                     continue

                # Sort objects by area (descending)
                objects.sort(key=lambda x: x['area'], reverse=True)
                max_area = objects[0]['area']
                
                # Count "significant" objects (area > 50% of max_area)
                # Increased from 40% to 50% to account for 2x upscaling
                significant_objects = [obj for obj in objects if obj['area'] > (max_area * 0.5)]
                obj_count = len(significant_objects)
                
                print(f"  - Candidate at ({x},{y}): Significant Objects = {obj_count} (Total: {len(objects)})")
                
                if obj_count > 1:
                    print(f"    -> REJECTED (Multiple significant objects detected)")
                    for i, obj in enumerate(significant_objects):
                        print(f"       Obj {i+1}: Area={obj['area']:.1f}, BBox={obj['bbox']}")
                    continue

            # Save part from the enhanced frame (not from original image)
            # Coordinates are relative to the enhanced frame
            part_bbox_for_save = (x, y, w, h)
            out_filename = f"{base_name}_part_{part_counter:02d}.webp"
            out_path = Path(args.output) / out_filename
            save_part(frame_roi_sharpened, part_bbox_for_save, str(out_path))
            print(f"Saved part {part_counter} -> {out_path}")
            part_counter += 1

    print(f"[DONE] Extracted {part_counter - 1} part(s) from {input_path.name}.")

if __name__ == "__main__":
    main()

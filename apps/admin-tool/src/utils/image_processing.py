import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Optional

class NumberExtractor:
    """
    アセンブリ番号（数字）の特徴量マッチングによる抽出クラス
    """
    def __init__(self, debug=False):
        self.debug = debug
        
    def analyze_template(self, image: np.ndarray, template_bbox: tuple) -> dict:
        """
        テンプレート（ユーザー指定の数字領域）を分析して特徴を抽出する
        
        Args:
            image: 元画像 (BGR)
            template_bbox: ユーザー指定枠 (x, y, w, h)
            
        Returns:
            dict: 抽出された特徴パラメータ
        """
        x, y, w, h = template_bbox
        
        # 画像範囲チェック
        h_img, w_img = image.shape[:2]
        x = max(0, min(x, w_img - 1))
        y = max(0, min(y, h_img - 1))
        w = max(1, min(w, w_img - x))
        h = max(1, min(h, h_img - y))
        
        roi = image[y:y+h, x:x+w]
        
        # 1. 色特徴（HSV）
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # 黒の割合
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 100])
        mask_black = cv2.inRange(hsv, lower_black, upper_black)
        black_ratio = np.count_nonzero(mask_black) / (w * h)
        
        # 赤の割合
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
        red_ratio = np.count_nonzero(mask_red) / (w * h)
        
        target_color = 'black'
        if red_ratio > black_ratio:
            target_color = 'red'
            
        # 2. サイズ特徴（文字の塊の平均サイズ）
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        if target_color == 'black':
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            binary = mask_red
            
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        char_heights = []
        char_areas = []
        
        for cnt in contours:
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            if ch < 5 or cw < 5:
                continue
            char_heights.append(ch)
            char_areas.append(cw * ch)
            
        if not char_heights:
            avg_height = h
            avg_area = w * h
        else:
            avg_height = np.mean(char_heights)
            avg_area = np.mean(char_areas)
            
        return {
            'color': target_color,
            'height': avg_height,
            'area': avg_area
        }

    def extract(self, image: np.ndarray, template_bbox: tuple) -> dict:
        """
        特徴に基づいて数字（アセンブリ番号）を抽出
        
        Args:
            image: 元画像 (BGR)
            template_bbox: ユーザー指定枠 (x, y, w, h)
            
        Returns:
            dict: 抽出結果 {'regions': list, 'params': dict, 'candidates_count': int}
        """
        # 1. 特徴抽出
        params = self.analyze_template(image, template_bbox)
        
        # 2. 候補検索
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if params['color'] == 'black':
            lower = np.array([0, 0, 0])
            upper = np.array([180, 255, 100])
            mask = cv2.inRange(hsv, lower, upper)
        else: # red
            lower1 = np.array([0, 70, 50])
            upper1 = np.array([10, 255, 255])
            lower2 = np.array([170, 70, 50])
            upper2 = np.array([180, 255, 255])
            mask = cv2.inRange(hsv, lower1, upper1) + cv2.inRange(hsv, lower2, upper2)
            
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        
        # 許容誤差を少し緩める（厳しすぎると何も検出されない）
        h_tol = 0.30  # 高さ ±30%
        a_tol = 0.40  # 面積 ±40%
        
        min_h = params['height'] * (1 - h_tol)
        max_h = params['height'] * (1 + h_tol)
        min_a = params['area'] * (1 - a_tol)
        max_a = params['area'] * (1 + a_tol)
        
        filtered_by_height = 0
        filtered_by_area = 0
        filtered_by_aspect = 0
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # サイズフィルタ
            if not (min_h <= h <= max_h):
                filtered_by_height += 1
                continue
            
            # 面積フィルタ
            if not (min_a <= area <= max_a):
                filtered_by_area += 1
                continue
            
            # アスペクト比チェック（少し緩める）
            aspect = w / h if h > 0 else 999
            if not (0.2 <= aspect <= 3.0):  # 0.3-2.5 から 0.2-3.0 に緩和
                filtered_by_aspect += 1
                continue
                
            candidates.append({'bbox': (x, y, w, h), 'center': (x + w/2, y + h/2)})
            
        # 3. グルーピング
        dist_thresh = params['height'] * 1.5
        grouped_regions = []
        used_indices = set()
        
        candidates.sort(key=lambda c: c['bbox'][0])
        
        for i, c1 in enumerate(candidates):
            if i in used_indices:
                continue
                
            group = [c1]
            used_indices.add(i)
            
            current_right = c1['bbox'][0] + c1['bbox'][2]
            current_y_center = c1['center'][1]
            
            for j, c2 in enumerate(candidates):
                if j in used_indices:
                    continue
                
                if abs(c2['center'][1] - current_y_center) > (params['height'] * 0.5):
                    continue
                
                dist = c2['bbox'][0] - current_right
                if 0 <= dist <= dist_thresh:
                    group.append(c2)
                    used_indices.add(j)
                    current_right = c2['bbox'][0] + c2['bbox'][2]
            
            min_x = min(c['bbox'][0] for c in group)
            min_y = min(c['bbox'][1] for c in group)
            max_x = max(c['bbox'][0] + c['bbox'][2] for c in group)
            max_y = max(c['bbox'][1] + c['bbox'][3] for c in group)
            
            # マージンを追加して少し広めに取る
            margin = 5
            h_img, w_img = image.shape[:2]
            
            final_x = max(0, min_x - margin)
            final_y = max(0, min_y - margin)
            final_w = min(w_img - final_x, (max_x - min_x) + margin * 2)
            final_h = min(h_img - final_y, (max_y - min_y) + margin * 2)
            
            grouped_regions.append({
                'bbox': (final_x, final_y, final_w, final_h),
                'count': len(group)
            })
            
        return {
            'regions': grouped_regions,
            'params': params,
            'candidates_count': len(candidates)
        }

# --- Part Extraction Logic (v2 - Transparent Background) ---

def find_rectangular_contours(gray_img, min_area=1000):
    """
    Find rectangular contours in a grayscale image.
    Returns a list of (x, y, w, h) tuples sorted by x-coordinate.
    """
    edges = cv2.Canny(gray_img, 50, 150)

    # Dilate to connect gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects = []
    for cnt in contours:
        # Approximate contour to polygon
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        # Check if it has 4 vertices and is convex
        if len(approx) == 4 and cv2.isContourConvex(approx):
            area = cv2.contourArea(cnt)
            if area >= min_area:
                x, y, w, h = cv2.boundingRect(approx)
                rects.append((x, y, w, h))

    # Sort by x coordinate (left to right)
    rects.sort(key=lambda r: r[0])
    return rects


def _is_blue_indicator(frame_img, bbox):
    """
    Check if the region is a blue indicator (quantity indicator like ③ or size label like 2x3).
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


def _is_red_text(frame_img, bbox, max_size=100):
    """
    Check if the region is red text (quantity labels like x2, x1).
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


def _detect_black_text_mask(img):
    """
    Detect black text regions (like "x1", "x2" quantity labels) in an image.
    Returns a mask where black text regions are white (255).

    Args:
        img: BGR image

    Returns:
        Binary mask of black text regions
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Black color detection in HSV
    # Low saturation, low value = black
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 100, 80])
    mask_black = cv2.inRange(hsv, lower_black, upper_black)

    # Find contours in black mask
    contours, _ = cv2.findContours(mask_black, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h_img, w_img = img.shape[:2]
    text_mask = np.zeros((h_img, w_img), dtype=np.uint8)

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)

        # Text characteristics:
        # - Small to medium size (not too large)
        # - Reasonable aspect ratio for text
        # - Located typically in corners or edges
        if area < 50:  # Too small, noise
            continue
        if w > w_img * 0.4 or h > h_img * 0.4:  # Too large, not text
            continue

        aspect = w / h if h > 0 else 0

        # "x1", "x2" text is typically wider than tall or roughly square
        if 0.3 < aspect < 4.0:
            # Check if this looks like text (high density of black pixels)
            roi_mask = mask_black[y:y+h, x:x+w]
            density = np.count_nonzero(roi_mask) / (w * h) if (w * h) > 0 else 0

            # Text typically has 20-70% fill density
            if 0.15 < density < 0.8:
                # Mark this region as text
                cv2.rectangle(text_mask, (x, y), (x+w, y+h), 255, -1)

    # Dilate to cover the text fully
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    text_mask = cv2.dilate(text_mask, kernel, iterations=2)

    return text_mask


def _count_significant_objects(image_crop, min_area=50, significant_ratio=0.5):
    """
    Count significant objects in a crop (to detect merged parts).
    """
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


def _extract_parts_with_contours(frame_img, min_size=20, max_size=2000, min_area=1800):
    """
    Extract parts with contour information for transparent background.
    Enhanced to detect gray parts using edge detection and adaptive thresholding.

    Returns:
        list of dict: [{'bbox': (x,y,w,h), 'contour': np.array}, ...]
    """
    # Noise reduction
    frame_denoised = cv2.medianBlur(frame_img, 7)
    gray = cv2.cvtColor(frame_denoised, cv2.COLOR_BGR2GRAY)
    img_h, img_w = frame_img.shape[:2]

    # 1. Otsu's Binarization (Inverse - parts are white)
    _, thresh_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 2. Edge detection for gray parts (low contrast parts)
    edges = cv2.Canny(gray, 30, 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges_dilated = cv2.dilate(edges, kernel, iterations=2)
    edges_closed = cv2.morphologyEx(edges_dilated, cv2.MORPH_CLOSE, kernel, iterations=2)

    # 3. Adaptive thresholding for local contrast detection
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5
    )

    # 4. Combine all masks
    combined_mask = cv2.bitwise_or(thresh_otsu, edges_closed)
    combined_mask = cv2.bitwise_or(combined_mask, adaptive_thresh)

    # 5. Remove edge noise (clear 10 pixels from image borders)
    border_margin = 10
    combined_mask[:border_margin, :] = 0  # Top
    combined_mask[-border_margin:, :] = 0  # Bottom
    combined_mask[:, :border_margin] = 0  # Left
    combined_mask[:, -border_margin:] = 0  # Right

    # 6. Morphological cleanup
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_small)

    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_close)

    # Find external contours
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Maximum allowed area (30% of image to prevent frame detection)
    max_allowed_area = img_h * img_w * 0.3

    parts = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        aspect = w / h if h > 0 else 0

        # Filtering criteria
        is_valid = True

        # Exclude regions that are too large (frame misdetection prevention)
        if w * h > max_allowed_area:
            is_valid = False
        # Exclude large regions touching image edges (boundary noise)
        elif (x <= 5 or y <= 5) and (w * h > img_h * img_w * 0.1):
            is_valid = False
        # Blue indicator filter (quantity indicators like ③ or size labels like 2x3)
        elif _is_blue_indicator(frame_img, (x, y, w, h)):
            is_valid = False
        # Red text filter (quantity labels like x2, x1)
        elif _is_red_text(frame_img, (x, y, w, h)):
            is_valid = False
        elif w < min_size or h < min_size:
            is_valid = False
        elif w > max_size or h > max_size:
            is_valid = False
        elif area < min_area:
            is_valid = False
        elif aspect < 0.15 or aspect > 6.0:  # Relaxed for thin parts (rods)
            is_valid = False
        else:
            # Object count check - avoid multiple objects merged together
            part_crop = frame_img[y:y+h, x:x+w]
            obj_count = _count_significant_objects(part_crop)
            if obj_count > 1:
                # Exception: very thin/elongated parts (rods)
                if not (aspect < 0.35 or aspect > 3.0):
                    is_valid = False

        if is_valid:
            parts.append({
                'bbox': (x, y, w, h),
                'contour': cnt,
            })

    # Sort by x position
    parts.sort(key=lambda p: p['bbox'][0])
    return parts


def _create_part_with_transparent_bg(frame_img, part_info, margin=10):
    """
    Create a part image with transparent background.
    Only the detected object pixels are visible; everything else is transparent.

    Args:
        frame_img: BGR image of the frame
        part_info: dict with 'bbox' and 'contour'
        margin: margin around the bounding box

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
    mask_crop = full_mask[y1:y2, x1:x2].copy()
    img_crop = frame_img[y1:y2, x1:x2].copy()

    # Note: Black text removal (x1, x2) was disabled because it causes
    # false detection issues with black-colored parts.
    # If text labels are included, use manual cropping for precise selection.

    # Convert BGR to RGBA
    img_rgb = cv2.cvtColor(img_crop, cv2.COLOR_BGR2RGB)
    img_rgba = np.dstack([img_rgb, mask_crop])

    return Image.fromarray(img_rgba, mode='RGBA')


def create_transparent_crop(image, left: int, top: int, width: int, height: int, margin: int = 10):
    """
    Create a cropped image with transparent background from a manually selected region.
    Simply crops the selected area and makes white/light background transparent.
    Object detection is disabled - user selects exact region manually.
    Fine adjustments can be made using the eraser (edit) function.

    Args:
        image: PIL Image or numpy array (RGB/BGR)
        left, top, width, height: Crop coordinates
        margin: Not used (kept for API compatibility)

    Returns:
        PIL.Image: RGBA image with transparent background
    """

    # Convert PIL to numpy array
    if isinstance(image, Image.Image):
        img = np.array(image)
        if len(img.shape) == 3 and img.shape[2] == 3:
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img
    else:
        img_bgr = image.copy()

    # Crop the region exactly as selected
    crop_img = img_bgr[top:top+height, left:left+width]

    if crop_img.size == 0:
        # Return empty RGBA image if crop is invalid
        return Image.new('RGBA', (1, 1), (0, 0, 0, 0))

    h_crop, w_crop = crop_img.shape[:2]

    # Convert to RGB for output
    crop_rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)

    # Create alpha mask - make white/light background transparent
    # Use grayscale to detect light areas
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)

    # Threshold to find white/near-white pixels (background)
    # Pixels with value > 240 are considered background
    _, white_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

    # Also check if pixels are close to pure white in color
    # (to handle slightly off-white backgrounds)
    b, g, r = cv2.split(crop_img)
    color_diff = np.maximum(np.abs(b.astype(int) - g.astype(int)),
                           np.abs(g.astype(int) - r.astype(int)))
    near_white = (gray > 230) & (color_diff < 15)

    # Combine masks
    background_mask = cv2.bitwise_or(white_mask, near_white.astype(np.uint8) * 255)

    # Alpha channel: 255 for object, 0 for background
    alpha = 255 - background_mask

    # Create RGBA image
    img_rgba = np.dstack([crop_rgb, alpha])

    return Image.fromarray(img_rgba, mode='RGBA')


def extract_parts(image) -> list:
    """
    Extract part images from an assembly diagram image.
    Parts are extracted with transparent backgrounds.

    Args:
        image: PIL Image or numpy array (BGR)

    Returns:
        list: List of PIL Images (RGBA) containing extracted parts with transparent backgrounds
    """
    # Convert PIL to BGR if necessary
    if isinstance(image, Image.Image):
        img = np.array(image)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img = image.copy()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Detect Frames
    frames = find_rectangular_contours(gray)

    if not frames:
        return []

    # 2. Select Largest Frame
    frames_with_area = [(fx, fy, fw, fh, fw * fh) for fx, fy, fw, fh in frames]
    frames_with_area.sort(key=lambda x: x[4], reverse=True)

    fx, fy, fw, fh = frames_with_area[0][:4]

    # Crop INSIDE the frame to avoid the border line
    frame_margin = 10
    if fw > 2 * frame_margin and fh > 2 * frame_margin:
        frame_roi = img[fy+frame_margin : fy+fh-frame_margin, fx+frame_margin : fx+fw-frame_margin]
    else:
        frame_roi = img[fy:fy+fh, fx:fx+fw]

    # 3. Super-resolution (2x) and Sharpening
    frame_roi_upscaled = cv2.resize(frame_roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    blurred = cv2.GaussianBlur(frame_roi_upscaled, (0, 0), 3)
    frame_enhanced = cv2.addWeighted(frame_roi_upscaled, 1.5, blurred, -0.5, 0)

    # 4. Extract Parts with contour information
    parts_info = _extract_parts_with_contours(frame_enhanced)

    # 5. Create transparent background images
    extracted_images = []
    part_margin = 10  # Margin around each part

    for part_info in parts_info:
        part_img = _create_part_with_transparent_bg(frame_enhanced, part_info, margin=part_margin)
        extracted_images.append(part_img)

    return extracted_images


# --- Assembly Number Image Extraction (v2 - Line Detection) ---

def _get_color_mask(img: np.ndarray, color: str) -> np.ndarray:
    """
    Create a mask for specific color (red, black, or blue lines).

    Args:
        img: BGR image
        color: 'red', 'black', or 'blue'

    Returns:
        Binary mask
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    if color == 'red':
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
    elif color == 'black':
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 80, 100])
        mask = cv2.inRange(hsv, lower_black, upper_black)
    elif color == 'blue':
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
    else:
        mask = np.zeros(img.shape[:2], dtype=np.uint8)

    return mask


def _detect_lines_hough(mask: np.ndarray, min_line_length: int = 50, max_line_gap: int = 10) -> Tuple[List, List]:
    """
    Detect lines using Hough Line Transform.

    Returns:
        Tuple of (horizontal_lines, vertical_lines)
        Each line is (start, end, position) where position is y for horizontal, x for vertical
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    lines = cv2.HoughLinesP(mask, 1, np.pi/180, threshold=50,
                            minLineLength=min_line_length, maxLineGap=max_line_gap)

    horizontal_lines = []
    vertical_lines = []

    if lines is None:
        return horizontal_lines, vertical_lines

    for line in lines:
        x1, y1, x2, y2 = line[0]

        if x2 - x1 == 0:
            angle = 90
        else:
            angle = abs(np.degrees(np.arctan((y2 - y1) / (x2 - x1))))

        if angle < 10:
            horizontal_lines.append((min(x1, x2), max(x1, x2), (y1 + y2) // 2))
        elif angle > 80:
            vertical_lines.append((min(y1, y2), max(y1, y2), (x1 + x2) // 2))

    return horizontal_lines, vertical_lines


def _detect_all_lines_hough(mask: np.ndarray, min_line_length: int = 30, max_line_gap: int = 5) -> List:
    """
    Detect ALL lines (including diagonal/arrow lines) using Hough Line Transform.

    Returns:
        List of (x1, y1, x2, y2, angle) tuples
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


def _merge_nearby_lines(lines: List, is_horizontal: bool = True, merge_threshold: int = 15) -> List:
    """
    Merge lines that are close together.
    """
    if not lines:
        return []

    lines = sorted(lines, key=lambda l: l[2])

    merged = []
    current_group = [lines[0]]

    for line in lines[1:]:
        if abs(line[2] - current_group[-1][2]) < merge_threshold:
            current_group.append(line)
        else:
            min_start = min(l[0] for l in current_group)
            max_end = max(l[1] for l in current_group)
            avg_pos = sum(l[2] for l in current_group) // len(current_group)
            merged.append((min_start, max_end, avg_pos))
            current_group = [line]

    if current_group:
        min_start = min(l[0] for l in current_group)
        max_end = max(l[1] for l in current_group)
        avg_pos = sum(l[2] for l in current_group) // len(current_group)
        merged.append((min_start, max_end, avg_pos))

    return merged


def _find_rectangles_from_lines(horizontal_lines: List, vertical_lines: List,
                                 min_width: int = 80, min_height: int = 60,
                                 max_width_ratio: float = 0.9, max_height_ratio: float = 0.9,
                                 img_width: int = None, img_height: int = None,
                                 tolerance: int = 20) -> List[Dict]:
    """
    Find rectangles formed by intersecting horizontal and vertical lines.
    """
    rectangles = []

    if img_width is None or img_height is None:
        return rectangles

    max_width = img_width * max_width_ratio
    max_height = img_height * max_height_ratio

    for i, h_top in enumerate(horizontal_lines):
        for h_bottom in horizontal_lines[i+1:]:
            top_y = h_top[2]
            bottom_y = h_bottom[2]
            height = bottom_y - top_y

            if height < min_height or height > max_height:
                continue

            matching_verticals = []
            for v_line in vertical_lines:
                v_start, v_end, v_x = v_line
                if v_start <= top_y + tolerance and v_end >= bottom_y - tolerance:
                    matching_verticals.append(v_x)

            matching_verticals = sorted(matching_verticals)

            for j, left_x in enumerate(matching_verticals):
                for right_x in matching_verticals[j+1:]:
                    width = right_x - left_x

                    if width < min_width or width > max_width:
                        continue

                    h_top_start, h_top_end, _ = h_top
                    h_bottom_start, h_bottom_end, _ = h_bottom

                    if h_top_start > left_x + tolerance or h_top_end < right_x - tolerance:
                        continue
                    if h_bottom_start > left_x + tolerance or h_bottom_end < right_x - tolerance:
                        continue

                    rectangles.append({
                        'bbox': (left_x, top_y, width, height),
                        'area': width * height
                    })

    return rectangles


def _remove_duplicate_rectangles(rectangles: List[Dict], iou_threshold: float = 0.5) -> List[Dict]:
    """
    Remove duplicate/overlapping rectangles.
    """
    if not rectangles:
        return []

    rectangles = sorted(rectangles, key=lambda r: r['area'], reverse=True)

    result = []
    for rect in rectangles:
        x1, y1, w1, h1 = rect['bbox']
        is_duplicate = False

        for existing in result:
            x2, y2, w2, h2 = existing['bbox']

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


def _detect_blue_frames(img: np.ndarray, min_line_length: int = 50) -> List[Tuple]:
    """
    Detect blue frames to exclude them and any frames inside them.
    """
    mask = _get_color_mask(img, 'blue')
    h_lines, v_lines = _detect_lines_hough(mask, min_line_length=min_line_length)
    h_lines = _merge_nearby_lines(h_lines, is_horizontal=True)
    v_lines = _merge_nearby_lines(v_lines, is_horizontal=False)

    img_h, img_w = img.shape[:2]
    rectangles = _find_rectangles_from_lines(
        h_lines, v_lines,
        min_width=60, min_height=40,
        img_width=img_w, img_height=img_h
    )

    return [r['bbox'] for r in rectangles]


def _is_inside_blue_frame(frame_bbox: Tuple, blue_frames: List[Tuple], margin: int = 10) -> bool:
    """
    Check if a frame is inside any blue frame.
    """
    x, y, w, h = frame_bbox
    frame_center_x = x + w // 2
    frame_center_y = y + h // 2

    for bx, by, bw, bh in blue_frames:
        if (bx - margin <= frame_center_x <= bx + bw + margin and
            by - margin <= frame_center_y <= by + bh + margin):
            return True

        ix1 = max(x, bx)
        iy1 = max(y, by)
        ix2 = min(x + w, bx + bw)
        iy2 = min(y + h, by + bh)

        if ix1 < ix2 and iy1 < iy2:
            intersection = (ix2 - ix1) * (iy2 - iy1)
            frame_area = w * h
            if intersection / frame_area > 0.5:
                return True

    return False


def _has_quantity_labels(img: np.ndarray, frame_bbox: Tuple) -> bool:
    """
    Check if the frame contains quantity labels like 'x1', 'x2', etc.
    """
    x, y, w, h = frame_bbox
    img_h, img_w = img.shape[:2]

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(img_w, x + w)
    y2 = min(img_h, y + h)
    frame_img = img[y1:y2, x1:x2]

    if frame_img.size == 0:
        return False

    hsv = cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 30, 30])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([160, 30, 30])
    upper_red2 = np.array([180, 255, 255])

    mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    fh, fw = frame_img.shape[:2]
    red_pixel_count = np.count_nonzero(mask_red)
    red_ratio = red_pixel_count / (fh * fw)

    min_red_pixels = 50
    return red_ratio > 0.0003 or red_pixel_count > min_red_pixels


def _find_nearby_number(img: np.ndarray, frame_bbox: Tuple, search_margin: int = 100) -> Tuple[Optional[str], bool]:
    """
    Find assembly numbers near the frame (outside the frame).
    """
    x, y, w, h = frame_bbox
    img_h, img_w = img.shape[:2]

    regions = []

    if y + h + 20 < img_h:
        regions.append(('below', img[y+h:min(y+h+search_margin, img_h), max(0,x-20):min(x+w+20, img_w)]))
    if y > 20:
        regions.append(('above', img[max(0, y-search_margin):y, max(0,x-20):min(x+w+20, img_w)]))
    if x > 20:
        regions.append(('left', img[max(0,y-20):min(y+h+20, img_h), max(0, x-search_margin):x]))
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


def _is_connected_to_arrow(img: np.ndarray, frame_bbox: Tuple, all_lines: List, tolerance: int = 10) -> bool:
    """
    Check if the frame is connected to arrow/diagonal lines.
    """
    x, y, w, h = frame_bbox

    left_edge = x
    right_edge = x + w
    top_edge = y
    bottom_edge = y + h

    min_arrow_length = 30
    arrow_connections = 0

    for line in all_lines:
        x1, y1, x2, y2, angle = line

        if not (20 <= angle <= 70):
            continue

        line_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if line_length < min_arrow_length:
            continue

        for (px, py), (ox, oy) in [((x1, y1), (x2, y2)), ((x2, y2), (x1, y1))]:
            on_left = abs(px - left_edge) < tolerance and top_edge < py < bottom_edge
            on_right = abs(px - right_edge) < tolerance and top_edge < py < bottom_edge
            on_top = abs(py - top_edge) < tolerance and left_edge < px < right_edge
            on_bottom = abs(py - bottom_edge) < tolerance and left_edge < px < right_edge

            if on_left or on_right or on_top or on_bottom:
                other_outside = (ox < left_edge - tolerance or ox > right_edge + tolerance or
                                oy < top_edge - tolerance or oy > bottom_edge + tolerance)

                if other_outside:
                    arrow_connections += 1
                    break

    return arrow_connections >= 2


def _detect_colored_frames(img: np.ndarray, color: str = 'red', min_line_length: int = 50) -> List[Dict]:
    """
    Detect frames of a specific color using line detection.
    """
    mask = _get_color_mask(img, color)
    h_lines, v_lines = _detect_lines_hough(mask, min_line_length=min_line_length)
    h_lines = _merge_nearby_lines(h_lines, is_horizontal=True)
    v_lines = _merge_nearby_lines(v_lines, is_horizontal=False)

    img_h, img_w = img.shape[:2]
    rectangles = _find_rectangles_from_lines(
        h_lines, v_lines,
        min_width=80, min_height=60,
        img_width=img_w, img_height=img_h
    )

    for rect in rectangles:
        rect['color'] = color

    return rectangles


def _validate_extracted_frame(frame_img: np.ndarray) -> Tuple[bool, str]:
    """
    Validate that the extracted image contains exactly ONE rectangular frame.
    """
    if frame_img is None or frame_img.size == 0:
        return False, "empty_image"

    img_h, img_w = frame_img.shape[:2]

    black_mask = _get_color_mask(frame_img, 'black')
    red_mask = _get_color_mask(frame_img, 'red')
    combined_mask = cv2.bitwise_or(black_mask, red_mask)

    min_line_length = max(30, img_w // 4)
    h_lines, _ = _detect_lines_hough(combined_mask, min_line_length=min_line_length, max_line_gap=10)

    if not h_lines:
        return True, "valid"

    h_lines = _merge_nearby_lines(h_lines, is_horizontal=True, merge_threshold=15)
    h_lines_sorted = sorted(h_lines, key=lambda l: l[2])

    long_h_lines = [l for l in h_lines_sorted if (l[1] - l[0]) > img_w * 0.5]

    if len(long_h_lines) < 2:
        return True, "valid"

    top_border_y = long_h_lines[0][2]
    bottom_border_y = long_h_lines[-1][2]
    frame_height = bottom_border_y - top_border_y

    min_separator_length = img_w * 0.7

    for h_line in long_h_lines[1:-1]:
        line_start, line_end, y_pos = h_line
        line_length = line_end - line_start

        dist_from_top = y_pos - top_border_y
        dist_from_bottom = bottom_border_y - y_pos

        if dist_from_top > frame_height * 0.2 and dist_from_bottom > frame_height * 0.2:
            if line_length > min_separator_length:
                return False, "multiple_frames_horizontal"

    return True, "valid"


def _count_frames_in_image(frame_img: np.ndarray, color: str = 'red') -> int:
    """
    Count how many LARGE rectangular frames exist in the image.
    """
    if frame_img is None or frame_img.size == 0:
        return 0

    img_h, img_w = frame_img.shape[:2]
    min_line_length = max(50, min(img_w, img_h) // 4)

    mask = _get_color_mask(frame_img, color)
    h_lines, v_lines = _detect_lines_hough(mask, min_line_length=min_line_length)

    if not h_lines or not v_lines:
        return 0

    h_lines = _merge_nearby_lines(h_lines, is_horizontal=True, merge_threshold=15)
    v_lines = _merge_nearby_lines(v_lines, is_horizontal=False, merge_threshold=15)

    min_width = max(80, int(img_w * 0.25))
    min_height = max(60, int(img_h * 0.25))

    rectangles = _find_rectangles_from_lines(
        h_lines, v_lines,
        min_width=min_width, min_height=min_height,
        img_width=img_w, img_height=img_h,
        tolerance=20
    )

    rectangles = _remove_duplicate_rectangles(rectangles, iou_threshold=0.5)
    return len(rectangles)


def extract_assembly_images(image, return_coords: bool = False) -> List:
    """
    組立ページ画像から組立番号ごとの部品一覧枠を検出・抽出する。

    Args:
        image: PIL Image または numpy array (BGR)
        return_coords: Trueの場合、座標情報も一緒に返す

    Returns:
        return_coords=False: List[PIL.Image]: 抽出された組立番号画像のリスト（RGB形式）
        return_coords=True: List[dict]: {'image': PIL.Image, 'region_x': int, 'region_y': int, 'region_width': int, 'region_height': int}
    """
    # Convert PIL to BGR if necessary
    if isinstance(image, Image.Image):
        img = np.array(image)
        if len(img.shape) == 3 and img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img = image.copy()

    img_h, img_w = img.shape[:2]
    min_line_length = max(50, min(img_w, img_h) // 20)

    # Detect red frames
    red_frames = _detect_colored_frames(img, 'red', min_line_length)

    # Detect black frames
    black_frames = _detect_colored_frames(img, 'black', min_line_length)

    # Combine all frames
    all_frames = red_frames + black_frames
    all_frames = _remove_duplicate_rectangles(all_frames)

    # Detect blue frames (to exclude frames inside them)
    blue_frames = _detect_blue_frames(img, min_line_length)

    # Detect ALL lines (including diagonal) for arrow detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    all_lines = _detect_all_lines_hough(edges, min_line_length=30)

    # Filter frames
    valid_frames = []

    for frame in all_frames:
        bbox = frame['bbox']

        # Check 0: Is inside a blue frame
        if _is_inside_blue_frame(bbox, blue_frames):
            continue

        # Check 1: Has quantity labels
        if not _has_quantity_labels(img, bbox):
            continue

        # Check 2: Has nearby assembly number
        _, has_number = _find_nearby_number(img, bbox)
        if not has_number:
            continue

        # Check 3: Is connected to arrow lines
        if _is_connected_to_arrow(img, bbox, all_lines):
            continue

        valid_frames.append(frame)

    # Sort by position (top-to-bottom, left-to-right)
    valid_frames.sort(key=lambda f: (f['bbox'][1], f['bbox'][0]))

    # Extract valid frames with post-extraction validation
    extracted_images = []

    for frame in valid_frames:
        x, y, w, h = frame['bbox']

        # Add margin
        margin = 30
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(img_w, x + w + margin)

        # Extend downward to capture assembly number
        y2_extended = min(img_h, y + h + 80)

        frame_img = img[y1:y2_extended, x1:x2]

        # Post-extraction validation
        is_valid, _ = _validate_extracted_frame(frame_img)
        if not is_valid:
            continue

        # Additional check: count frames using color detection
        frame_count_red = _count_frames_in_image(frame_img, 'red')
        frame_count_black = _count_frames_in_image(frame_img, 'black')
        total_frame_count = frame_count_red + frame_count_black

        if total_frame_count > 2:
            continue

        # Convert BGR to RGB and create PIL Image
        frame_rgb = cv2.cvtColor(frame_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)

        if return_coords:
            # 座標情報も含めて返す（Pythonのint型に変換）
            extracted_images.append({
                'image': pil_img,
                'region_x': int(x1),
                'region_y': int(y1),
                'region_width': int(x2 - x1),
                'region_height': int(y2_extended - y1)
            })
        else:
            extracted_images.append(pil_img)

    return extracted_images

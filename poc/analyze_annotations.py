"""
アノテーション画像から34と35の位置を特定し、検出結果と比較する分析スクリプト
"""

import cv2
import numpy as np
from pathlib import Path
import json


def find_green_circles(image_path):
    """
    緑の円を検出してその中心座標を返す
    """
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    # HSV色空間に変換
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 緑色の範囲
    lower_green = np.array([40, 40, 40])
    upper_green = np.array([80, 255, 255])
    
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # 輪郭検出
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    circles = []
    for cnt in contours:
        # 面積が一定以上のものだけ
        area = cv2.contourArea(cnt)
        if area < 1000:
            continue
        
        # 外接矩形を取得
        x, y, w, h = cv2.boundingRect(cnt)
        
        # 中心座標
        center_x = x + w // 2
        center_y = y + h // 2
        
        circles.append({
            'center': (center_x, center_y),
            'bbox': (x, y, w, h),
            'area': area
        })
    
    return circles, mask


def check_overlap(bbox1, bbox2):
    """
    2つの矩形が重なっているかチェック
    """
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    
    # 矩形1の範囲
    x1_min, y1_min = x1, y1
    x1_max, y1_max = x1 + w1, y1 + h1
    
    # 矩形2の範囲
    x2_min, y2_min = x2, y2
    x2_max, y2_max = x2 + w2, y2 + h2
    
    # 重なり判定
    return not (x1_max < x2_min or x2_max < x1_min or
                y1_max < y2_min or y2_max < y1_min)


def point_in_bbox(point, bbox):
    """
    点が矩形内にあるかチェック
    """
    px, py = point
    x, y, w, h = bbox
    return x <= px <= x + w and y <= py <= y + h


def main():
    # アノテーション画像から緑の円を検出
    annotated_image = Path('docs/AssemblyDiagram_sample/AssemblyDiagram_annotated.jpg')
    print(f"Analyzing: {annotated_image}")
    
    circles, mask = find_green_circles(annotated_image)
    print(f"\nGreen circles detected: {len(circles)}")
    
    for i, circle in enumerate(circles):
        center = circle['center']
        bbox = circle['bbox']
        print(f"  Circle {i+1}: center={center}, bbox={bbox}")
    
    # 検出結果を読み込み
    detection_result = Path('poc/output/detection_result.json')
    with open(detection_result, 'r', encoding='utf-8') as f:
        detected_regions = json.load(f)
    
    print(f"\nDetected regions: {detected_regions['total_regions']}")
    
    # 各緑円が検出領域のどれに含まれるかチェック
    print("\n=== Analysis ===")
    for i, circle in enumerate(circles):
        center = circle['center']
        circle_bbox = circle['bbox']
        
        print(f"\nCircle {i+1} (Assembly number 34 or 35):")
        print(f"  Position: {center}")
        
        matched_regions = []
        for region in detected_regions['regions']:
            region_id = region['id']
            region_bbox = tuple(region['bbox'])
            
            # 緑円の中心が検出領域に含まれるか
            if point_in_bbox(center, region_bbox):
                matched_regions.append(region_id)
                print(f"  ✅ Contained in Region {region_id}")
            # 緑円と検出領域が重なっているか
            elif check_overlap(circle_bbox, region_bbox):
                matched_regions.append(region_id)
                print(f"  ⚠️ Overlaps with Region {region_id}")
        
        if not matched_regions:
            print(f"  ❌ NOT DETECTED in any region!")
            print(f"     This is why assembly number 34 or 35 is missing.")
    
    # デバッグ用: 緑円マスクを保存
    output_dir = Path('poc/output')
    cv2.imwrite(str(output_dir / 'debug_green_circles.jpg'), mask)
    print(f"\nGreen circle mask saved: {output_dir / 'debug_green_circles.jpg'}")


if __name__ == '__main__':
    main()

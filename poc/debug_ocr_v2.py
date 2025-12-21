"""
OCRデバッグ用スクリプト v2
OCRフィルタ前の領域でテストする
"""

import cv2
import numpy as np
from pathlib import Path
import pytesseract
import re

# Tesseractパス設定
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# assembly_detection_poc.pyから検出器をインポート
import sys
sys.path.insert(0, 'poc')
from assembly_detection_poc import AssemblyNumberDetector

# 画像読み込み
image_path = Path('poc/imput/パンターG型_001.jpg')
n = np.fromfile(str(image_path), np.uint8)
image = cv2.imdecode(n, cv2.IMREAD_COLOR)

print(f"Image loaded: {image.shape}")

# 検出器で処理（OCRなし）
detector = AssemblyNumberDetector(debug=False, use_ocr=False)
result = detector.detect(image_path)

print(f"\nMerged regions (before OCR): {len(result['regions'])}")

# 各領域でOCRテスト
for i, region in enumerate(result['regions']):
    x, y, w, h = region['bbox']
    
    print(f"\n=== Region {i+1} ===")
    print(f"bbox: {region['bbox']}")
    
    # 検索範囲
    search_h = min(int(h * 0.5), 300)
    search_w = min(int(w * 0.5), 300)
    
    # 画像境界チェック
    if y + search_h > image.shape[0]:
        search_h = image.shape[0] - y
    if x + search_w > image.shape[1]:
        search_w = image.shape[1] - x
    
    if search_h <= 0 or search_w <= 0:
        print("Invalid search area")
        continue
    
    print(f"Search area: {search_w}x{search_h}")
    
    roi = image[y:y+search_h, x:x+search_w]
    
    # OCR設定テスト
    psm_modes = [6, 7, 11, 13]
    scales = [1.0, 2.0]
    
    print(f"\n--- Testing OCR configurations for Region {i+1} ---")
    
    for scale in scales:
        if scale != 1.0:
            roi_scaled = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        else:
            roi_scaled = roi
            
        # 前処理バリエーション
        preprocessed_images = {}
        
        # 1. Gray
        gray = cv2.cvtColor(roi_scaled, cv2.COLOR_BGR2GRAY)
        preprocessed_images['Gray'] = gray
        
        # 2. Binary (Adaptive)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        preprocessed_images['Binary'] = binary
        
        # 3. Inverted Binary
        binary_inv = cv2.bitwise_not(binary)
        preprocessed_images['BinaryInv'] = binary_inv
        
        # 4. Otsu
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_images['Otsu'] = otsu

        for name, img in preprocessed_images.items():
            for psm in psm_modes:
                custom_config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist=0123456789'
                try:
                    text = pytesseract.image_to_string(img, config=custom_config).strip()
                    if text:
                        print(f"Scale={scale}, Prep={name}, PSM={psm} -> Text='{text}'")
                        # 数字抽出
                        numbers = re.findall(r'\d+', text)
                        for num_str in numbers:
                            if 1 <= int(num_str) <= 200:
                                print(f"  ✅ FOUND VALID NUMBER: {num_str}")
                except Exception as e:
                    pass

print("\nDebug images saved in poc/output/")

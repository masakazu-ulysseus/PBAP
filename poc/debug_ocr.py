"""
OCRデバッグ用スクリプト
パンターG型_001.jpgの最初の領域でOCRをテストする
"""

import cv2
import numpy as np
from pathlib import Path
import pytesseract

# Tesseractパス設定
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 画像読み込み
image_path = Path('poc/imput/パンターG型_001.jpg')
n = np.fromfile(str(image_path), np.uint8)
image = cv2.imdecode(n, cv2.IMREAD_COLOR)

print(f"Image loaded: {image.shape}")

# 検出結果JSONから領域情報を読み込み
import json
result_path = Path('poc/output/パンターG型_001/detection_result.json')
with open(result_path, 'r', encoding='utf-8') as f:
    result = json.load(f)

print(f"Total regions: {result['total_regions']}")

# 最初の領域でOCRテスト
if result['total_regions'] > 0:
    region = result['regions'][0]
    x, y, w, h = region['bbox']
    
    print(f"\nRegion 1: bbox={region['bbox']}")
    
    # 検索範囲
    search_h = min(int(h * 0.5), 300)
    search_w = min(int(w * 0.5), 300)
    
    print(f"Search area: {search_w}x{search_h}")
    
    roi = image[y:y+search_h, x:x+search_w]
    
    # グレースケール
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # 二値化
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    
    # デバッグ用に画像保存
    cv2.imwrite('poc/output/debug_roi.jpg', roi)
    cv2.imwrite('poc/output/debug_gray.jpg', gray)
    cv2.imwrite('poc/output/debug_binary.jpg', binary)
    
    print("Debug images saved: debug_roi.jpg, debug_gray.jpg, debug_binary.jpg")
    
    # OCR実行
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
    
    text = pytesseract.image_to_string(binary, config=custom_config)
    
    print(f"\nOCR result: '{text}'")
    print(f"OCR result (repr): {repr(text)}")
    
    # 数字抽出
    import re
    numbers = re.findall(r'\d+', text)
    print(f"Numbers found: {numbers}")
    
    for num_str in numbers:
        num = int(num_str)
        if 1 <= num <= 200:
            print(f"Valid assembly number: {num}")
else:
    print("No regions detected")

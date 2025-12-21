"""
アセンブリ番号領域検出 PoC - メインスクリプト

アプローチ1: 枠検出ベース
1. 赤枠・黒枠を検出（青枠を除外）
2. 輪郭抽出で枠で囲まれた領域を検出
3. 各領域の左上にアセンブリ番号があるか確認
4. 領域を矩形で囲む
"""

import cv2
import numpy as np
from pathlib import Path
import json
import re

# OCR
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    
    # Windows環境でのTesseractパス設定
    import platform
    if platform.system() == 'Windows':
        # 一般的なインストールパス
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        for path in tesseract_paths:
            from pathlib import Path as PathLib
            if PathLib(path).exists():
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"Tesseract path set: {path}")
                break
        
except ImportError:
    TESSERACT_AVAILABLE = False
    print("WARNING: pytesseract not installed. OCR will be disabled.")

class AssemblyNumberDetector:
    def __init__(self, debug=True, use_ocr=True):
        self.debug = debug
        self.use_ocr = use_ocr and TESSERACT_AVAILABLE
        
        if self.use_ocr:
            print("OCR enabled (Tesseract)")
        else:
            print("OCR disabled")
    
    def check_assembly_number_ocr(self, image, bbox):
        """
        OCRを使って、領域の左上付近にアセンブリ番号（1〜200の数字）があるかチェック
        
        Args:
            image: 元画像
            bbox: 領域の座標 (x, y, w, h)
            
        Returns:
            int or None: 検出されたアセンブリ番号（1〜200）、見つからなければNone
        """
        if not self.use_ocr:
            return None
        
        x, y, w, h = bbox
        
        # 領域の左上部分（アセンブリ番号がある場所）を切り出し
        # 範囲を広げる: 上から50%、左から50%
        search_h = min(int(h * 0.5), 300)
        search_w = min(int(w * 0.5), 300)
        
        # 画像境界チェック
        if y + search_h > image.shape[0]:
            search_h = image.shape[0] - y
        if x + search_w > image.shape[1]:
            search_w = image.shape[1] - x
        
        if search_h <= 0 or search_w <= 0:
            return None
        
        roi = image[y:y+search_h, x:x+search_w]
        
        # グレースケール化
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # 画像の前処理を改善
        # 1. アップスケーリング (2倍) - 小さな文字の認識率向上
        roi_scaled = cv2.resize(roi, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        
        # 2. グレースケール化
        gray = cv2.cvtColor(roi_scaled, cv2.COLOR_BGR2GRAY)
        
        # 3. 二値化（適応的閾値処理）
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        
        # OCR実行（数字のみ、PSM 6: 単一ブロック）
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        
        try:
            text = pytesseract.image_to_string(binary, config=custom_config)
            
            # 数字を抽出
            numbers = re.findall(r'\d+', text)
            
            # 1〜200の範囲の数字を探す
            for num_str in numbers:
                num = int(num_str)
                if 1 <= num <= 200:
                    if self.debug:
                        print(f"    OCR detected assembly number: {num}")
                    return num
            
            if self.debug:
                print(f"    OCR: No valid assembly number found (text: {text.strip()})")
            
        except Exception as e:
            if self.debug:
                print(f"    OCR error: {e}")
        
        return None
        
    def detect_colored_boxes(self, image):
        """
        赤枠・黒枠を検出し、青枠を除外する
        
        Returns:
            list: 検出された輪郭のリスト
        """
        # HSV色空間に変換
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 赤色の範囲（2つの範囲で検出）
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = mask_red1 + mask_red2
        
        # 黒色の範囲
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 50])
        mask_black = cv2.inRange(hsv, lower_black, upper_black)
        
        # 赤または黒のマスク
        mask_combined = cv2.bitwise_or(mask_red, mask_black)
        
        # 青色の範囲（除外用）
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # 青を除外
        mask_final = cv2.bitwise_and(mask_combined, cv2.bitwise_not(mask_blue))
        
        if self.debug:
            cv2.imwrite('poc/output/debug_mask_red.jpg', mask_red)
            cv2.imwrite('poc/output/debug_mask_black.jpg', mask_black)
            cv2.imwrite('poc/output/debug_mask_combined.jpg', mask_combined)
            cv2.imwrite('poc/output/debug_mask_final.jpg', mask_final)
        
        # 輪郭検出
        contours, _ = cv2.findContours(mask_final, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return contours
    
    def filter_box_contours(self, contours, image_shape):
        """
        検出された輪郭から部品リストの枠らしいものをフィルタリング
        
        条件:
        - 一定以上のサイズ（幅・高さ）
        - 矩形に近い形状
        - 一定以上の面積
        """
        filtered = []
        height, width = image_shape[:2]
        image_area = width * height
        
        for cnt in contours:
            # 矩形で近似
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h  # バウンディングボックスの面積
            
            # サイズフィルタ（画像の短辺の10%以上）
            min_dimension = min(width, height)
            min_size = min_dimension * 0.10  # 10% (約200px)
            
            if w < min_size or h < min_size:
                continue
            
            # 面積フィルタ（画像全体の1%以上）
            if area < (image_area * 0.01):
                continue

            # 最大サイズフィルタ（画像全体の90%以下 - 枠自体が画像全体ではないこと）
            if w > (width * 0.95) and h > (height * 0.95):
                continue
            
            # アスペクト比フィルタ（削除: 縦長の枠もあるため）
            # aspect_ratio = max(w, h) / min(w, h)
            # if aspect_ratio > 8:
            #     continue
            
            filtered.append({
                'contour': cnt,
                'bbox': (x, y, w, h),
                'area': area
            })
        
        return filtered
    
    def find_assembly_regions(self, image, box_contours):
        """
        部品リストの枠からアセンブリ番号領域を推定
        
        修正: 枠の「周囲」を含める（上下左右）
        """
        regions = []
        h_img, w_img = image.shape[:2]
        
        for box_info in box_contours:
            x, y, w, h = box_info['bbox']
            
            # 枠の周囲を含める（マージン）
            margin = 100  # 上下左右に100px
            
            region_x = max(0, x - margin)
            region_y = max(0, y - margin)
            region_w = min(w_img - region_x, w + (margin * 2))
            region_h = min(h_img - region_y, h + (margin * 2))
            
            regions.append({
                'bbox': (region_x, region_y, region_w, region_h),
                'box_bbox': box_info['bbox']
            })
        
        return regions
    
    def merge_overlapping_regions(self, regions):
        """
        重複する領域をマージ
        """
        if len(regions) <= 1:
            return regions
        
        merged = []
        used = set()
        
        for i, region1 in enumerate(regions):
            if i in used:
                continue
            
            x1, y1, w1, h1 = region1['bbox']
            rect1 = (x1, y1, x1 + w1, y1 + h1)
            
            merged_rect = list(rect1)
            used.add(i)
            
            for j, region2 in enumerate(regions):
                if j <= i or j in used:
                    continue
                
                x2, y2, w2, h2 = region2['bbox']
                rect2 = (x2, y2, x2 + w2, y2 + h2)
                
                # 重複判定
                if self._rectangles_overlap(rect1, rect2):
                    # マージ
                    merged_rect[0] = min(merged_rect[0], rect2[0])
                    merged_rect[1] = min(merged_rect[1], rect2[1])
                    merged_rect[2] = max(merged_rect[2], rect2[2])
                    merged_rect[3] = max(merged_rect[3], rect2[3])
                    used.add(j)
            
            x, y, x2, y2 = merged_rect
            merged.append({
                'bbox': (x, y, x2 - x, y2 - y)
            })
        
        return merged
    
    def _rectangles_overlap(self, rect1, rect2):
        """2つの矩形が重複しているか判定"""
        x1_min, y1_min, x1_max, y1_max = rect1
        x2_min, y2_min, x2_max, y2_max = rect2
        
        return not (x1_max < x2_min or x2_max < x1_min or
                   y1_max < y2_min or y2_max < y1_min)
    
    def detect(self, image_path):
        """
        メイン検出関数
        
        Args:
            image_path: 組立図ページ画像のパス
            
        Returns:
            dict: 検出結果
        """
        # 画像読み込み (日本語パス対応)
        try:
            # np.fromfileでバイナリとして読み込み
            n = np.fromfile(str(image_path), np.uint8)
            image = cv2.imdecode(n, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"Error loading image with numpy: {e}")
            image = None

        if image is None:
            # フォールバック (通常のimread)
            image = cv2.imread(str(image_path))
            
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        print(f"Image loaded: {image.shape}")
        
        # 1. 枠検出
        contours = self.detect_colored_boxes(image)
        print(f"Contours detected: {len(contours)}")
        
        # 2. 枠フィルタリング
        box_contours = self.filter_box_contours(contours, image.shape)
        print(f"Filtered boxes: {len(box_contours)}")
        
        # 3. アセンブリ番号領域推定
        regions = self.find_assembly_regions(image, box_contours)
        print(f"Assembly regions found: {len(regions)}")
        
        # 4. 重複領域のマージ（削除: 枠が分割されていることはないため）
        # merged_regions = self.merge_overlapping_regions(regions)
        # print(f"Merged regions: {len(merged_regions)}")
        
        # 5. OCRでアセンブリ番号を確認（一旦無効化）
        # if self.use_ocr:
        #     ...
        
        return {
            'image': image,
            'regions': regions,  # マージせずそのまま返す
            'box_contours': box_contours
        }


def main():
    """メイン実行"""
    # 入力ディレクトリ
    input_dir = Path('poc/imput')
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return

    # 出力ディレクトリベース
    base_output_dir = Path('poc/output')
    base_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 検出器初期化
    detector = AssemblyNumberDetector(debug=False)
    
    # 画像ファイルを取得
    image_files = list(input_dir.glob('*.jpg'))
    print(f"Found {len(image_files)} images in {input_dir}")

    for input_image in image_files:
        print(f"\nProcessing: {input_image.name}")
        
        # ファイルごとの出力ディレクトリ
        output_dir = base_output_dir / input_image.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = detector.detect(input_image)
            
            # 結果を画像に描画
            image_with_boxes = result['image'].copy()
            
            for i, region in enumerate(result['regions']):
                x, y, w, h = region['bbox']
                # 緑の枠で描画
                cv2.rectangle(image_with_boxes, (x, y), (x + w, y + h), (0, 255, 0), 3)
                # 番号を描画
                cv2.putText(image_with_boxes, f"#{i+1}", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 結果保存 (日本語パス対応)
            output_path = output_dir / 'detected_regions.jpg'
            try:
                extension = output_path.suffix
                save_success, encoded_img = cv2.imencode(extension, image_with_boxes)
                if save_success:
                    with open(output_path, "wb") as f:
                        encoded_img.tofile(f)
                    print(f"  Result saved: {output_path}")
            except Exception as e:
                print(f"  Error saving result image: {e}")
            
            # 各領域を個別に保存
            for i, region in enumerate(result['regions']):
                x, y, w, h = region['bbox']
                region_img = result['image'][y:y+h, x:x+w]
                region_path = output_dir / f'region_{i+1}.jpg'
                try:
                    extension = region_path.suffix
                    save_success, encoded_img = cv2.imencode(extension, region_img)
                    if save_success:
                        with open(region_path, "wb") as f:
                            encoded_img.tofile(f)
                except Exception as e:
                    print(f"  Error saving region image {i+1}: {e}")
            
            # 結果をJSONで保存
            result_json = {
                'filename': input_image.name,
                'total_regions': len(result['regions']),
                'regions': [
                    {
                        'id': i + 1,
                        'bbox': region['bbox']
                    }
                    for i, region in enumerate(result['regions'])
                ]
            }
            
            json_path = output_dir / 'detection_result.json'
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result_json, f, indent=2, ensure_ascii=False)
            
            print(f"  Total regions detected: {len(result['regions'])}")

        except Exception as e:
            print(f"  Error processing {input_image.name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n=== Batch Processing Complete ===")

if __name__ == '__main__':
    main()

"""
アセンブリ番号領域検出 PoC - テンプレートマッチング（パラメータキャリブレーション）版

ユーザーが指定した「正解の枠」を分析し、その特徴（サイズ、色、面積）に基づいて
画像全体から類似した枠を検出する。
"""

import cv2
import numpy as np
from pathlib import Path
import json

class TemplateMatchingDetector:
    def __init__(self, debug=True):
        self.debug = debug
        
    def analyze_template(self, image, template_bbox):
        """
        テンプレート（ユーザー指定領域）を分析して特徴を抽出する
        
        Args:
            image: 元画像
            template_bbox: ユーザー指定枠 (x, y, w, h)
            
        Returns:
            dict: 抽出された特徴パラメータ
        """
        x, y, w, h = template_bbox
        roi = image[y:y+h, x:x+w]
        
        # 1. 基本サイズ特徴
        area = w * h
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
        
        # 2. 色特徴（赤か黒か？）
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # 赤色の割合
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
        red_ratio = np.count_nonzero(mask_red) / area
        
        # 黒色の割合
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 50])
        mask_black = cv2.inRange(hsv, lower_black, upper_black)
        black_ratio = np.count_nonzero(mask_black) / area
        
        dominant_color = 'red' if red_ratio > black_ratio else 'black'
        
        if self.debug:
            print(f"Template Analysis:")
            print(f"  Size: {w}x{h}")
            print(f"  Area: {area}")
            print(f"  Aspect Ratio: {aspect_ratio:.2f}")
            print(f"  Red Ratio: {red_ratio:.2f}")
            print(f"  Black Ratio: {black_ratio:.2f}")
            print(f"  Dominant Color: {dominant_color}")
            
        return {
            'width': w,
            'height': h,
            'area': area,
            'aspect_ratio': aspect_ratio,
            'dominant_color': dominant_color,
            'red_ratio': red_ratio,
            'black_ratio': black_ratio
        }

    def detect(self, image_path, template_bbox):
        """
        テンプレートの特徴に基づいて類似領域を検出
        """
        # パスを絶対パスに変換して確認
        abs_path = Path(image_path).resolve()
        print(f"Loading image from: {abs_path}")
        if not abs_path.exists():
            raise FileNotFoundError(f"Image file not found: {abs_path}")
            
        # 画像読み込み
        try:
            n = np.fromfile(str(abs_path), np.uint8)
            image = cv2.imdecode(n, cv2.IMREAD_COLOR)
        except Exception as e:
            raise ValueError(f"Failed to load image with numpy: {e}")
        
        if image is None:
            raise ValueError(f"Failed to decode image: {abs_path}")
            
        # 1. テンプレート分析
        params = self.analyze_template(image, template_bbox)
        
        # 2. 色検出（テンプレートの主要色に合わせる）
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        if params['dominant_color'] == 'red':
            # 赤のみ検出
            lower_red1 = np.array([0, 70, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 70, 50])
            upper_red2 = np.array([180, 255, 255])
            mask = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
        else:
            # 黒のみ検出（赤と青を除く）
            # ここでは簡単のため、以前の「赤+黒 - 青」ロジックを再利用しつつ、
            # テンプレートが黒なら黒の重みを増やす等の調整が可能だが、
            # まずは既存の「赤+黒」ロジックで候補を出し、サイズで絞るのが安全
            
            # 既存ロジック再利用
            lower_red1 = np.array([0, 70, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 70, 50])
            upper_red2 = np.array([180, 255, 255])
            mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
            
            lower_black = np.array([0, 0, 0])
            upper_black = np.array([180, 255, 50])
            mask_black = cv2.inRange(hsv, lower_black, upper_black)
            
            mask_combined = cv2.bitwise_or(mask_red, mask_black)
            
            lower_blue = np.array([100, 50, 50])
            upper_blue = np.array([130, 255, 255])
            mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
            
            mask = cv2.bitwise_and(mask_combined, cv2.bitwise_not(mask_blue))

        # 3. 輪郭検出
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 4. 動的フィルタリング（テンプレートとの類似度判定）
        detected_regions = []
        h_img, w_img = image.shape[:2]
        
        # 許容誤差（±30%）
        tolerance = 0.3
        
        min_w = params['width'] * (1 - tolerance)
        max_w = params['width'] * (1 + tolerance)
        min_h = params['height'] * (1 - tolerance)
        max_h = params['height'] * (1 + tolerance)
        min_area = params['area'] * (1 - tolerance)
        max_area = params['area'] * (1 + tolerance)
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # サイズチェック
            if not (min_w <= w <= max_w):
                continue
            if not (min_h <= h <= max_h):
                continue
            if not (min_area <= area <= max_area):
                continue
                
            # アスペクト比チェック（±0.5程度）
            aspect = max(w, h) / min(w, h)
            if abs(aspect - params['aspect_ratio']) > 0.5:
                continue
            
            # 領域拡張（周囲100px）
            margin = 100
            region_x = max(0, x - margin)
            region_y = max(0, y - margin)
            region_w = min(w_img - region_x, w + (margin * 2))
            region_h = min(h_img - region_y, h + (margin * 2))
            
            detected_regions.append({
                'bbox': (region_x, region_y, region_w, region_h),
                'box_bbox': (x, y, w, h),
                'match_score': 1.0 # 簡易スコア
            })
            
        return {
            'image': image,
            'regions': detected_regions,
            'template_params': params
        }

def main():
    # テスト用: パンターG型_001.jpg の既知の正解枠を「ユーザー入力」として使用
    # 以前の検出結果から座標を取得（例: 最初の検出領域のbox_bbox）
    # ここでは手動で設定（仮の値、後で調整）
    
    # パンターG型_001.jpgのパス
    image_path = Path('poc/input/パンターG型_001.jpg')
    
    # 仮のテンプレート座標 (x, y, w, h) - 以前のログから推定
    # Region 1: bbox=(37, 0, 1583, 1167) <- これは拡張後の領域
    # 実際の枠はもっと小さいはず。
    # ここでは、以前の検出結果JSONがあればそれを読み込んで「1つ目」を使うのが確実
    
    json_path = Path('poc/output/パンターG型_001/detection_result.json')
    if not json_path.exists():
        print("Error: Previous detection result not found. Run assembly_detection_poc.py first.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    if not data['regions']:
        print("Error: No regions in previous result.")
        return
        
    # 最初の領域の「元の枠（box_bbox）」を取得したいが、JSONには拡張後のbboxしかない可能性がある
    # assembly_detection_poc.py の出力JSONを確認する必要がある
    # もしbox_bboxがなければ、拡張後bboxから逆算するか、適当な値を設定する
    
    # JSONの中身を確認
    print(f"Loaded JSON keys: {data['regions'][0].keys()}")
    
    # box_bboxキーがあるか確認（直近の修正で追加したはず）
    if 'box_bbox' in data['regions'][0]:
        template_bbox = data['regions'][0]['box_bbox']
    else:
        # なければ拡張後bboxから推定（マージン100pxを引く）
        rx, ry, rw, rh = data['regions'][0]['bbox']
        template_bbox = (rx+100, ry+100, rw-200, rh-200)
    
    print(f"Simulated User Selection (Template): {template_bbox}")
    
    detector = TemplateMatchingDetector(debug=True)
    result = detector.detect(image_path, template_bbox)
    
    print(f"Detected Regions: {len(result['regions'])}")
    
    # 結果保存
    output_dir = Path('poc/output/template_matching_test')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 描画
    img_draw = result['image'].copy()
    
    # テンプレート枠（青）
    tx, ty, tw, th = template_bbox
    cv2.rectangle(img_draw, (tx, ty), (tx+tw, ty+th), (255, 0, 0), 5)
    
    # 検出枠（緑）
    for region in result['regions']:
        x, y, w, h = region['bbox']
        cv2.rectangle(img_draw, (x, y), (x+w, y+h), (0, 255, 0), 3)
        
        # 元の枠（黄色）
        bx, by, bw, bh = region['box_bbox']
        cv2.rectangle(img_draw, (bx, by), (bx+bw, by+bh), (0, 255, 255), 2)
        
    cv2.imwrite(str(output_dir / 'result_001.jpg'), img_draw)
    print(f"Saved result to {output_dir / 'result_001.jpg'}")

if __name__ == "__main__":
    main()

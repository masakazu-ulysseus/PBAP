"""
アセンブリ番号抽出 PoC - 特徴量マッチング版

ユーザーが指定した「数字（文字）」の特徴（色、サイズ）を分析し、
画像全体から類似した文字の塊を検出し、グルーピングしてアセンブリ番号として抽出する。
"""

import cv2
import numpy as np
from pathlib import Path

class NumberExtractor:
    def __init__(self, debug=True):
        self.debug = debug
        
    def analyze_template(self, image, template_bbox):
        """
        テンプレート（ユーザー指定の数字領域）を分析して特徴を抽出する
        
        Args:
            image: 元画像
            template_bbox: ユーザー指定枠 (x, y, w, h)
            
        Returns:
            dict: 抽出された特徴パラメータ
        """
        x, y, w, h = template_bbox
        roi = image[y:y+h, x:x+w]
        
        # 1. 色特徴（HSV）
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # 文字は通常「黒」または「濃い色」
        # ここでは簡易的に、ROI内の「最も多い色」ではなく「文字らしい色（黒）」を検出する
        # ただし、ユーザーが「赤文字」を指定する場合もあるため、ROI内の分布を見る
        
        # 黒の割合
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 100]) # 明度100以下を黒とみなす
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
        # ROI内で二値化して輪郭を抽出し、文字1つ分のサイズを推定する
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        if target_color == 'black':
            # 黒文字抽出 (白背景前提)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            # 赤文字抽出
            # 赤マスクをそのまま使う
            binary = mask_red
            
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        char_heights = []
        char_areas = []
        
        for cnt in contours:
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            # 小さすぎるノイズは除外
            if ch < 5 or cw < 5:
                continue
            char_heights.append(ch)
            char_areas.append(cw * ch)
            
        if not char_heights:
            # 輪郭が見つからない場合はROI全体を1文字とみなす
            avg_height = h
            avg_area = w * h
        else:
            avg_height = np.mean(char_heights)
            avg_area = np.mean(char_areas)
            
        if self.debug:
            print(f"Template Analysis:")
            print(f"  Target Color: {target_color}")
            print(f"  Avg Char Height: {avg_height:.1f}")
            print(f"  Avg Char Area: {avg_area:.1f}")
            
        return {
            'color': target_color,
            'height': avg_height,
            'area': avg_area
        }

    def extract(self, image_path, template_bbox):
        """
        特徴に基づいて数字（アセンブリ番号）を抽出
        """
        # 画像読み込み
        abs_path = Path(image_path).resolve()
        if not abs_path.exists():
            raise FileNotFoundError(f"Image not found: {abs_path}")
            
        n = np.fromfile(str(abs_path), np.uint8)
        image = cv2.imdecode(n, cv2.IMREAD_COLOR)
        
        # 1. 特徴抽出
        params = self.analyze_template(image, template_bbox)
        
        # 2. 候補検索（全体から類似ブロブを探す）
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
            
        # 輪郭抽出
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        
        # 許容誤差
        h_tol = 0.4 # 高さ ±40%
        a_tol = 0.5 # 面積 ±50%
        
        min_h = params['height'] * (1 - h_tol)
        max_h = params['height'] * (1 + h_tol)
        min_a = params['area'] * (1 - a_tol)
        max_a = params['area'] * (1 + a_tol)
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # サイズフィルタ
            if not (min_h <= h <= max_h):
                continue
            # 面積フィルタ（文字の太さも考慮される）
            # if not (min_a <= area <= max_a):
            #     continue
            
            # アスペクト比チェック（極端に横長なものは除外、数字は縦長か正方形に近い）
            if w / h > 3.0:
                continue
                
            candidates.append({'bbox': (x, y, w, h), 'center': (x + w/2, y + h/2)})
            
        # 3. グルーピング（近接する文字をまとめる）
        # 距離閾値: 文字の高さの1.5倍以内
        dist_thresh = params['height'] * 1.5
        
        grouped_regions = []
        used_indices = set()
        
        # x座標でソート（左から右へ処理するため）
        candidates.sort(key=lambda c: c['bbox'][0])
        
        for i, c1 in enumerate(candidates):
            if i in used_indices:
                continue
                
            # 新しいグループ
            group = [c1]
            used_indices.add(i)
            
            # 近接する他の候補を探す
            # 簡易的な実装: 既にグループ化されたもの以外で、距離が近いものを探す
            # 本来は再帰的あるいはクラスタリングすべきだが、ここでは単純な走査
            
            # c1の右側にあるものを探す
            current_right = c1['bbox'][0] + c1['bbox'][2]
            current_y_center = c1['center'][1]
            
            for j, c2 in enumerate(candidates):
                if j in used_indices:
                    continue
                
                # Y軸のずれチェック（同じ行にあるか）
                if abs(c2['center'][1] - current_y_center) > (params['height'] * 0.5):
                    continue
                
                # X軸の距離チェック（すぐ右にあるか）
                dist = c2['bbox'][0] - current_right
                if 0 <= dist <= dist_thresh:
                    group.append(c2)
                    used_indices.add(j)
                    current_right = c2['bbox'][0] + c2['bbox'][2] # 右端を更新
            
            # グループのバウンディングボックスを計算
            min_x = min(c['bbox'][0] for c in group)
            min_y = min(c['bbox'][1] for c in group)
            max_x = max(c['bbox'][0] + c['bbox'][2] for c in group)
            max_y = max(c['bbox'][1] + c['bbox'][3] for c in group)
            
            # 1文字だけでも登録する（"1"とかあるので）
            grouped_regions.append({
                'bbox': (min_x, min_y, max_x - min_x, max_y - min_y),
                'count': len(group)
            })
            
        return {
            'image': image,
            'regions': grouped_regions,
            'params': params,
            'candidates_count': len(candidates)
        }

def main():
    image_path = Path('poc/input/パンターG型_001.jpg')
    
    # シミュレーション: ユーザーが「数字」を選択する
    # ここでは、画像内の適当な「文字らしい」場所を自動探索してテンプレートとする
    # （実際のアプリではユーザーがドラッグする）
    
    print("Simulating user input...")
    
    # 画像を一時読み込みして、テンプレートを探す
    n = np.fromfile(str(image_path), np.uint8)
    img = cv2.imdecode(n, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    template_bbox = None
    
    # 適当なサイズの輪郭を探す（高さ30〜100pxくらい）
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if 30 < h < 100 and 10 < w < 100:
            # アスペクト比が文字っぽい（極端に細長くない）
            if 0.2 < w/h < 1.5:
                template_bbox = (x, y, w, h)
                print(f"Found simulated template at: {template_bbox}")
                break
    
    if template_bbox is None:
        print("Could not find a suitable template for simulation. Using fallback.")
        template_bbox = (100, 100, 50, 50) # 適当
        
    extractor = NumberExtractor(debug=True)
    result = extractor.extract(image_path, template_bbox)
    
    print(f"\nDetected Number Regions: {len(result['regions'])}")
    
    # 結果保存
    output_dir = Path('poc/output/number_extraction_test')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    img_draw = result['image'].copy()
    
    # テンプレート（青）
    tx, ty, tw, th = template_bbox
    cv2.rectangle(img_draw, (tx, ty), (tx+tw, ty+th), (255, 0, 0), 3)
    cv2.putText(img_draw, "Template", (tx, ty-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
    
    # 検出結果（緑）
    for region in result['regions']:
        x, y, w, h = region['bbox']
        cv2.rectangle(img_draw, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
    cv2.imwrite(str(output_dir / 'result_numbers.jpg'), img_draw)
    print(f"Saved result to {output_dir / 'result_numbers.jpg'}")

if __name__ == "__main__":
    main()

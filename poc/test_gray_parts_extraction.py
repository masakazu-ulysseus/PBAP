"""
灰色部品の抽出テスト用スクリプト

目的：
- 現在のアルゴリズムと改善版アルゴリズムを比較
- 灰色部品が正しく抽出できるか確認
- 他の色の部品への影響がないか確認

使用方法：
    cd /home/masakazu/develop/claude-code/PBAP/poc
    python test_gray_parts_extraction.py
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import sys

# image_processing.py のパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'apps' / 'admin-tool' / 'src' / 'utils'))

from image_processing import (
    find_rectangular_contours,
    _is_blue_indicator,
    _is_red_text,
    _count_significant_objects,
)


def extract_parts_original(frame_img, min_size=20, max_size=2000, min_area=1800):
    """
    現在のアルゴリズム（オリジナル）
    """
    frame_denoised = cv2.medianBlur(frame_img, 7)
    gray = cv2.cvtColor(frame_denoised, cv2.COLOR_BGR2GRAY)

    # Otsu's Binarization (Inverse - parts are white)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    parts = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        aspect = w / h if h > 0 else 0

        is_valid = True
        if _is_blue_indicator(frame_img, (x, y, w, h)):
            is_valid = False
        elif _is_red_text(frame_img, (x, y, w, h)):
            is_valid = False
        elif w < min_size or h < min_size:
            is_valid = False
        elif w > max_size or h > max_size:
            is_valid = False
        elif area < min_area:
            is_valid = False
        elif aspect < 0.15 or aspect > 6.0:
            is_valid = False
        else:
            part_crop = frame_img[y:y+h, x:x+w]
            obj_count = _count_significant_objects(part_crop)
            if obj_count > 1:
                if not (aspect < 0.35 or aspect > 3.0):
                    is_valid = False

        if is_valid:
            parts.append({'bbox': (x, y, w, h), 'contour': cnt})

    parts.sort(key=lambda p: p['bbox'][0])
    return parts, thresh


def extract_parts_improved(frame_img, min_size=20, max_size=2000, min_area=1800):
    """
    改善版アルゴリズム（灰色部品対応）
    - オリジナルのOtsu二値化
    - 追加：エッジ検出ベースの抽出
    - 追加：適応的閾値処理（灰色部品用）
    """
    frame_denoised = cv2.medianBlur(frame_img, 7)
    gray = cv2.cvtColor(frame_denoised, cv2.COLOR_BGR2GRAY)
    img_h, img_w = frame_img.shape[:2]

    # 1. オリジナルのOtsu二値化
    _, thresh_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 2. エッジ検出ベースの追加抽出（灰色部品用）
    edges = cv2.Canny(gray, 30, 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges_dilated = cv2.dilate(edges, kernel, iterations=2)
    edges_closed = cv2.morphologyEx(edges_dilated, cv2.MORPH_CLOSE, kernel, iterations=2)

    # 3. 適応的閾値処理（局所的なコントラストを利用）
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5
    )

    # 4. 3つのマスクを結合
    combined_mask = cv2.bitwise_or(thresh_otsu, edges_closed)
    combined_mask = cv2.bitwise_or(combined_mask, adaptive_thresh)

    # 画像端のノイズを除去（端から10ピクセルは黒にする）
    border_margin = 10
    combined_mask[:border_margin, :] = 0  # 上端
    combined_mask[-border_margin:, :] = 0  # 下端
    combined_mask[:, :border_margin] = 0  # 左端
    combined_mask[:, -border_margin:] = 0  # 右端

    # ノイズ除去（小さな点を除去）
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_small)

    # 穴埋め（部品内部の穴を埋める）
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_close)

    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 画像サイズの30%を超える輪郭は除外（フレーム全体の誤検出防止）
    max_allowed_area = img_h * img_w * 0.3

    parts = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        aspect = w / h if h > 0 else 0

        is_valid = True
        # 大きすぎる領域は除外
        if w * h > max_allowed_area:
            is_valid = False
        # 画像の端に接している大きな領域は除外（境界の誤検出防止）
        elif (x <= 5 or y <= 5) and (w * h > img_h * img_w * 0.1):
            is_valid = False
        elif _is_blue_indicator(frame_img, (x, y, w, h)):
            is_valid = False
        elif _is_red_text(frame_img, (x, y, w, h)):
            is_valid = False
        elif w < min_size or h < min_size:
            is_valid = False
        elif w > max_size or h > max_size:
            is_valid = False
        elif area < min_area:
            is_valid = False
        elif aspect < 0.15 or aspect > 6.0:
            is_valid = False
        else:
            part_crop = frame_img[y:y+h, x:x+w]
            obj_count = _count_significant_objects(part_crop)
            if obj_count > 1:
                if not (aspect < 0.35 or aspect > 3.0):
                    is_valid = False

        if is_valid:
            parts.append({'bbox': (x, y, w, h), 'contour': cnt})

    parts.sort(key=lambda p: p['bbox'][0])
    return parts, combined_mask


def draw_parts_on_image(img, parts, color=(0, 255, 0), thickness=2):
    """
    画像上に検出された部品の枠を描画
    """
    result = img.copy()
    for i, part in enumerate(parts):
        x, y, w, h = part['bbox']
        cv2.rectangle(result, (x, y), (x+w, y+h), color, thickness)
        cv2.putText(result, str(i+1), (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return result


def main():
    # テスト画像のパス
    test_image_path = Path(__file__).parent.parent / '38(t)-007-12.png'

    if not test_image_path.exists():
        print(f"テスト画像が見つかりません: {test_image_path}")
        return

    print(f"テスト画像: {test_image_path}")

    # 画像を読み込み
    img = cv2.imread(str(test_image_path))
    if img is None:
        print("画像の読み込みに失敗しました")
        return

    print(f"画像サイズ: {img.shape}")

    # 赤い枠を検出して、その中の部品を抽出
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    frames = find_rectangular_contours(gray)

    print(f"検出されたフレーム数: {len(frames)}")

    if not frames:
        print("フレームが検出されませんでした")
        return

    # 最大のフレームを選択
    frames_with_area = [(fx, fy, fw, fh, fw * fh) for fx, fy, fw, fh in frames]
    frames_with_area.sort(key=lambda x: x[4], reverse=True)
    fx, fy, fw, fh = frames_with_area[0][:4]

    print(f"選択されたフレーム: x={fx}, y={fy}, w={fw}, h={fh}")

    # フレーム内部を切り出し
    frame_margin = 10
    frame_roi = img[fy+frame_margin:fy+fh-frame_margin, fx+frame_margin:fx+fw-frame_margin]

    # Super-resolution (2x) and Sharpening
    frame_roi_upscaled = cv2.resize(frame_roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    blurred = cv2.GaussianBlur(frame_roi_upscaled, (0, 0), 3)
    frame_enhanced = cv2.addWeighted(frame_roi_upscaled, 1.5, blurred, -0.5, 0)

    # オリジナルアルゴリズムでテスト
    print("\n=== オリジナルアルゴリズム ===")
    parts_original, mask_original = extract_parts_original(frame_enhanced)
    print(f"検出された部品数: {len(parts_original)}")
    for i, part in enumerate(parts_original):
        x, y, w, h = part['bbox']
        print(f"  部品{i+1}: x={x}, y={y}, w={w}, h={h}")

    # 改善版アルゴリズムでテスト
    print("\n=== 改善版アルゴリズム ===")
    parts_improved, mask_improved = extract_parts_improved(frame_enhanced)
    print(f"検出された部品数: {len(parts_improved)}")
    for i, part in enumerate(parts_improved):
        x, y, w, h = part['bbox']
        print(f"  部品{i+1}: x={x}, y={y}, w={w}, h={h}")

    # 結果を画像として保存
    output_dir = Path(__file__).parent / 'output_gray_test'
    output_dir.mkdir(exist_ok=True)

    # マスク画像を保存
    cv2.imwrite(str(output_dir / 'mask_original.png'), mask_original)
    cv2.imwrite(str(output_dir / 'mask_improved.png'), mask_improved)

    # 検出結果を描画して保存
    result_original = draw_parts_on_image(frame_enhanced, parts_original, color=(0, 255, 0))
    result_improved = draw_parts_on_image(frame_enhanced, parts_improved, color=(255, 0, 0))

    cv2.imwrite(str(output_dir / 'result_original.png'), result_original)
    cv2.imwrite(str(output_dir / 'result_improved.png'), result_improved)

    # 比較画像（両方を並べて表示）
    comparison = np.hstack([result_original, result_improved])
    cv2.imwrite(str(output_dir / 'comparison.png'), comparison)

    print(f"\n結果を保存しました: {output_dir}")
    print("  - mask_original.png: オリジナルの二値化マスク")
    print("  - mask_improved.png: 改善版のマスク")
    print("  - result_original.png: オリジナルの検出結果（緑枠）")
    print("  - result_improved.png: 改善版の検出結果（青枠）")
    print("  - comparison.png: 比較画像（左:オリジナル、右:改善版）")


if __name__ == '__main__':
    main()

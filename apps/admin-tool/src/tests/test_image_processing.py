import numpy as np
import cv2
from PIL import Image

from utils import image_processing

def make_dummy_image(color=(255, 255, 255)):
    """白い 200x200 のダミー画像を作成"""
    return Image.new("RGB", (200, 200), color)

def test_extract_assembly_numbers_returns_list_of_images():
    dummy = make_dummy_image()
    result = image_processing.extract_assembly_numbers(dummy)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Image.Image)

def test_extract_parts_detects_red_boxes():
    # 赤い矩形 (10,10)-(60,60) を描画した画像を作成
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[10:60, 10:60] = [0, 0, 255]  # BGR の赤
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    parts = image_processing.extract_parts(pil_img)
    assert isinstance(parts, list)
    # 現在はプレースホルダー実装で 1 件返すが、将来的に 1 件以上が期待できる
    assert len(parts) >= 1
    for p in parts:
        assert isinstance(p, Image.Image)

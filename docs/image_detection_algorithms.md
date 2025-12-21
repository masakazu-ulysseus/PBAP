# 画像検出アルゴリズム仕様書

管理ツールで使用する画像検出アルゴリズムの技術仕様です。

## 目次

1. [組立番号画像検出 (extract_assembly_numbers_v2)](#1-組立番号画像検出)
2. [部品画像検出 (extract_parts_v2)](#2-部品画像検出)

---

## 1. 組立番号画像検出

### 1.1 概要

組立ページ画像から、組立番号ごとの部品一覧枠（赤枠/黒枠）を検出・抽出します。

**入力**: 組立ページ画像（PNG/JPG）
**出力**: 組立番号ごとの切り出し画像（JPG）

### 1.2 検出フロー

```
[入力画像]
    ↓
[Step 1] 色マスク生成（赤/黒/青）
    ↓
[Step 2] Hough変換による線検出
    ↓
[Step 3] 矩形フレーム形成検出
    ↓
[Step 4] フィルタリング
    ├── 青枠除外
    ├── 矢印接続検出
    ├── 数量ラベルチェック
    └── 近接番号チェック
    ↓
[Step 5] 抽出後バリデーション
    ↓
[出力画像]
```

### 1.3 色検出パラメータ

HSV色空間を使用した色マスク生成：

| 色 | Hue範囲 | Saturation範囲 | Value範囲 |
|---|---------|----------------|-----------|
| 赤 | 0-10, 170-180 | 50-255 | 50-255 |
| 黒 | 0-180 | 0-80 | 0-100 |
| 青 | 90-130 | 50-255 | 50-255 |

```python
# 赤色マスク
lower_red1 = [0, 50, 50], upper_red1 = [10, 255, 255]
lower_red2 = [170, 50, 50], upper_red2 = [180, 255, 255]

# 黒色マスク
lower_black = [0, 0, 0], upper_black = [180, 80, 100]

# 青色マスク
lower_blue = [90, 50, 50], upper_blue = [130, 255, 255]
```

### 1.4 線検出アルゴリズム

**Hough変換パラメータ:**
- threshold: 50
- minLineLength: max(50, min(img_w, img_h) // 20)
- maxLineGap: 10

**線分類:**
- 水平線: 角度 < 10度
- 垂直線: 角度 > 80度
- 斜め線（矢印）: 20-70度

**近接線のマージ:**
- merge_threshold: 15ピクセル

### 1.5 矩形検出アルゴリズム

水平線と垂直線の交点から矩形を形成：

```python
# 矩形形成条件
min_width = 80px
min_height = 60px
max_width = img_width * 0.9
max_height = img_height * 0.9
tolerance = 20px  # 線端の許容誤差
```

**重複除去:**
- IoU > 0.5 で重複と判定
- 面積の大きい方を優先

### 1.6 フィルタリング条件

検出されたフレームに対して以下の条件でフィルタリング：

#### 1.6.1 青枠除外
- フレームの中心が青枠内にある場合は除外
- フレーム面積の50%以上が青枠と重なる場合は除外

#### 1.6.2 数量ラベルチェック
フレーム内に赤色の数量ラベル（x1, x2等）が存在するかチェック：
- 赤色ピクセル比率 > 0.0003 または
- 赤色ピクセル数 > 50

#### 1.6.3 近接番号チェック
フレーム外側（上下左右、検索範囲100px）に組立番号が存在するかチェック：
- コントア面積: 200-50000px
- アスペクト比: 0.2-4.0
- 高さ: > 12px

#### 1.6.4 矢印接続検出
フレームが矢印線に接続されている場合は除外：
- 斜め線（20-70度）がフレーム端から外側に延びている
- 接続数 >= 2 の場合に除外

### 1.7 抽出後バリデーション

抽出した画像に対して追加検証：

#### 1.7.1 水平セパレーター検出
複数フレームが1つとして検出されるケースを防止：
- フレーム上辺・下辺以外に長い水平線があれば拒否
- 条件:
  - 位置: top_y + height*0.25 < y < bottom_y - height*0.25
  - 長さ: > frame_width * 0.7

#### 1.7.2 フレーム数カウント
色検出ベースでフレーム数をカウント：
- min_width: max(80, img_w * 0.25)
- min_height: max(60, img_h * 0.25)
- count > 2 の場合に拒否

### 1.8 出力仕様

- 形式: JPEG
- マージン: 上下左右15px + 下部80px（組立番号を含めるため）
- ファイル名: `{入力ファイル名}_assembly_{番号:02d}.jpg`

### 1.9 既知の制限事項

- 横に並んだ2つのフレームが1つとして検出されるケースがある
- 垂直セパレーター検出を試みたが、誤検出が多く無効化

---

## 2. 部品画像検出

### 2.1 概要

組立番号画像から個々の部品を検出・抽出します。

**入力**: 組立番号画像（JPG/PNG）
**出力**: 部品画像（PNG/透過背景）

### 2.2 検出フロー

```
[入力画像]
    ↓
[Step 1] 最大矩形フレーム検出
    ↓
[Step 2] フレーム切り出し + 前処理
    ├── 2x超解像（INTER_CUBIC）
    └── シャープニング（Unsharp Mask）
    ↓
[Step 3] コントア検出
    ├── メディアンフィルタ（kernel=7）
    └── Otsu二値化
    ↓
[Step 4] フィルタリング
    ├── 青インジケーター除外
    ├── 赤テキスト除外
    ├── サイズフィルタ
    ├── アスペクト比フィルタ
    └── マルチオブジェクト検出
    ↓
[Step 5] 透過背景で出力
    ↓
[出力画像]
```

### 2.3 フレーム検出

Canny エッジ検出 + コントア検出で最大矩形を特定：

```python
edges = cv2.Canny(gray_img, 50, 150)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
edges = cv2.dilate(edges, kernel, iterations=1)
contours = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 矩形判定
approx = cv2.approxPolyDP(cnt, 0.02 * perimeter, True)
is_rect = len(approx) == 4 and cv2.isContourConvex(approx)
```

### 2.4 画像前処理

#### 2.4.1 超解像（2x）
```python
frame_upscaled = cv2.resize(frame_roi, None, fx=2, fy=2,
                            interpolation=cv2.INTER_CUBIC)
```

#### 2.4.2 シャープニング（Unsharp Mask）
```python
blurred = cv2.GaussianBlur(frame_upscaled, (0, 0), 3)
frame_enhanced = cv2.addWeighted(frame_upscaled, 1.5, blurred, -0.5, 0)
```

### 2.5 コントア検出

```python
# ノイズ除去
frame_denoised = cv2.medianBlur(frame_img, 7)

# Otsu二値化（反転）
_, thresh = cv2.threshold(gray, 0, 255,
                          cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# 外部コントア検出
contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                            cv2.CHAIN_APPROX_SIMPLE)
```

### 2.6 フィルタリング条件

| フィルタ | 条件 | 説明 |
|---------|------|------|
| 青インジケーター | blue_ratio > 0.2 | 数量表示（③等）を除外 |
| 赤テキスト | red_ratio > 0.3, size < 100 | 数量ラベル（x2等）を除外 |
| 最小サイズ | w >= 20, h >= 20 | 小さすぎるノイズを除外 |
| 最大サイズ | w <= 2000, h <= 2000 | 大きすぎる領域を除外 |
| 最小面積 | area >= 1800 | 小さすぎる領域を除外 |
| アスペクト比 | 0.15 <= aspect <= 6.0 | 極端な形状を除外 |
| マルチオブジェクト | obj_count <= 1 | 複数部品が結合した領域を除外 |

#### 2.6.1 青インジケーター検出
```python
# HSV青色範囲
lower_blue = [90, 50, 50]
upper_blue = [130, 255, 255]
blue_ratio = count_nonzero(mask_blue) / (w * h)
is_blue = blue_ratio > 0.2
```

#### 2.6.2 赤テキスト検出
```python
# HSV赤色範囲
lower_red1 = [0, 70, 50], upper_red1 = [10, 255, 255]
lower_red2 = [170, 70, 50], upper_red2 = [180, 255, 255]
red_ratio = count_nonzero(mask_red) / (w * h)
is_red_text = red_ratio > 0.3 and max(w, h) < 100
```

#### 2.6.3 マルチオブジェクト検出
```python
def count_significant_objects(crop, min_area=50, significant_ratio=0.5):
    # 切り出し領域内で二値化・コントア検出
    # 最大面積の50%以上のオブジェクト数をカウント
    areas = [contourArea(cnt) for cnt in contours if area >= min_area]
    max_area = max(areas)
    significant = [a for a in areas if a > max_area * significant_ratio]
    return len(significant)
```

**例外処理:**
- 細長い部品（aspect < 0.35 or aspect > 3.0）は、マルチオブジェクト検出をバイパス

### 2.7 透過背景生成

```python
# Convex Hullでマスク作成（光沢面も含める）
hull = cv2.convexHull(contour)
cv2.drawContours(mask, [hull], -1, 255, thickness=cv2.FILLED)

# 膨張処理でエッジを含める
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask = cv2.dilate(mask, kernel, iterations=2)

# RGBA画像生成
img_rgba = np.dstack([img_rgb, mask])
```

### 2.8 出力仕様

- 形式: PNG（透過背景）
- マージン: 5px
- ファイル名: `{入力ファイル名}_part_{番号:02d}.png`

---

## 3. 使用ライブラリ

- OpenCV (cv2): 画像処理全般
- NumPy: 配列操作
- Pillow (PIL): 画像入出力

## 4. 関連ファイル

- `/poc/extract_assembly_numbers_v2.py`: 組立番号検出PoC
- `/poc/extract_parts_v2.py`: 部品検出PoC

## 5. 更新履歴

| 日付 | 内容 |
|-----|------|
| 2024-12-14 | 初版作成 |

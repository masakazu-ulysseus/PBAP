# Tesseract OCR インストール手順

## WSL/Linux環境の場合

以下のコマンドを実行してください：

```bash
sudo apt update
sudo apt install tesseract-ocr
```

インストール確認：
```bash
tesseract --version
```

## Windows環境の場合（参考）

1. [Tesseract-OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki) からインストーラーをダウンロード
2. インストーラーを実行
3. 環境変数PATHに `C:\Program Files\Tesseract-OCR` を追加

## インストール後

Tesseractがインストールされたら、以下のコマンドでPoCスクリプトを実行してください：

```bash
poc_venv/Scripts/python.exe poc/assembly_detection_poc.py
```

OCRによる数字検出が有効になり、精度が向上します。

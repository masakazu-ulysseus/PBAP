import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from dotenv import load_dotenv
import requests
from io import BytesIO
from PIL import Image

load_dotenv()

# SMTP設定
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM")
SMTP_BCC = os.getenv("SMTP_BCC")  # 社内同報用BCCアドレス

# デフォルトの件名
DEFAULT_SUBJECT = "【パンツァーブロックス】不足部品の発送について"

# デフォルトの本文テンプレート
DEFAULT_BODY_TEMPLATE = """{recipient_name} 様

この度は、部品が不足していたことにより、せっかくの組立体験を
損なう結果となり、大変申し訳ありません。

{request_date}にご依頼いただいた不足品について、準備が完了
しましたので、添付写真のとおり、送付致します。

発送は、普通郵便となりますのであらかじめご容赦ください。

------------------------
パンツァーブロックス サポート部門 佐藤
"""


def get_default_body(recipient_name: str, request_date: str) -> str:
    """デフォルトの本文を生成する"""
    return DEFAULT_BODY_TEMPLATE.format(
        recipient_name=recipient_name,
        request_date=request_date
    )


def download_image_from_url(url: str) -> bytes:
    """URLから画像をダウンロードしてバイト列で返す"""
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"画像のダウンロードに失敗しました: {response.status_code}")


def convert_to_jpeg(image_data: bytes) -> bytes:
    """画像をJPEG形式に変換する（WEBPなど他形式からの変換用）"""
    img = Image.open(BytesIO(image_data))
    # RGBAの場合はRGBに変換（JPEG非対応のため）
    if img.mode in ('RGBA', 'LA', 'P'):
        # 白い背景を追加
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # JPEG形式でバイト列に変換
    output = BytesIO()
    img.save(output, format='JPEG', quality=90)
    return output.getvalue()


def send_email(
    to_email: str,
    subject: str,
    body: str,
    image_url: str = None
) -> dict:
    """
    メールを送信する

    Args:
        to_email: 送信先メールアドレス
        subject: 件名
        body: 本文
        image_url: 添付する画像のURL（オプション）

    Returns:
        dict: 結果 {"success": bool, "message": str}
    """
    print(f"[EMAIL DEBUG] Sending email to: {to_email}")
    print(f"[EMAIL DEBUG] SMTP_HOST: {SMTP_HOST}, SMTP_PORT: {SMTP_PORT}")
    print(f"[EMAIL DEBUG] SMTP_USER: {SMTP_USER}, SMTP_FROM: {SMTP_FROM}")
    print(f"[EMAIL DEBUG] SMTP_BCC: {SMTP_BCC}")

    try:
        # メッセージ作成
        msg = MIMEMultipart()
        # 送信元に表示名を付加
        msg['From'] = "PANZER BLOCKS<" + SMTP_FROM + ">"
        msg['To'] = to_email
        msg['Subject'] = subject
        # BCCはヘッダーには含めない（送信時に指定）

        # 本文追加
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # 画像を添付（URLがある場合）- JPEG形式に変換
        if image_url:
            try:
                print(f"[EMAIL DEBUG] Downloading image from: {image_url}")
                image_data = download_image_from_url(image_url)
                print(f"[EMAIL DEBUG] Image downloaded, size: {len(image_data)} bytes")

                # JPEG形式に変換
                print("[EMAIL DEBUG] Converting to JPEG...")
                jpeg_data = convert_to_jpeg(image_data)
                print(f"[EMAIL DEBUG] Converted to JPEG, size: {len(jpeg_data)} bytes")

                image = MIMEImage(jpeg_data, _subtype='jpeg')
                image.add_header('Content-Disposition', 'attachment', filename='shipment.jpg')
                msg.attach(image)
            except Exception as e:
                print(f"[EMAIL DEBUG] Image attachment failed: {e}")
                return {
                    "success": False,
                    "message": f"画像の添付に失敗しました: {str(e)}"
                }

        # 送信先リスト（BCC含む）
        recipients = [to_email]
        if SMTP_BCC:
            recipients.append(SMTP_BCC)
            print(f"[EMAIL DEBUG] Adding BCC: {SMTP_BCC}")

        # SMTP接続して送信
        print("[EMAIL DEBUG] Connecting to SMTP server...")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.set_debuglevel(1)  # SMTPデバッグ出力を有効化
            print("[EMAIL DEBUG] Connected, starting TLS...")
            server.starttls()  # TLS暗号化
            print("[EMAIL DEBUG] TLS started, logging in...")
            server.login(SMTP_USER, SMTP_PASSWORD)
            print(f"[EMAIL DEBUG] Logged in, sending message to: {recipients}")
            server.sendmail(SMTP_FROM, recipients, msg.as_string())
            print("[EMAIL DEBUG] Message sent successfully!")

        return {
            "success": True,
            "message": "メールを送信しました"
        }

    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL DEBUG] Authentication error: {e}")
        return {
            "success": False,
            "message": "SMTP認証エラー: ユーザー名またはパスワードが正しくありません"
        }
    except smtplib.SMTPConnectError as e:
        print(f"[EMAIL DEBUG] Connection error: {e}")
        return {
            "success": False,
            "message": "SMTPサーバーへの接続に失敗しました"
        }
    except Exception as e:
        print(f"[EMAIL DEBUG] General error: {e}")
        import traceback
        print(f"[EMAIL DEBUG] Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"メール送信エラー: {str(e)}"
        }

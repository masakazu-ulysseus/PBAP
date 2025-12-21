import os
import time
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client
from io import BytesIO

# Load environment variables
# Try to find .env file
load_dotenv(find_dotenv(usecwd=True))


def check_db_response(response, operation: str = "DB operation"):
    """
    Supabase DBレスポンスを検証し、エラーがあれば例外を発生させる

    Args:
        response: Supabase execute()の戻り値
        operation: 操作の説明（エラーメッセージ用）

    Returns:
        response.data（成功時）

    Raises:
        Exception: エラー発生時
    """
    # APIResponseオブジェクトの場合
    if hasattr(response, 'data'):
        # エラーチェック（Supabase v2では error 属性がない場合もある）
        if hasattr(response, 'error') and response.error:
            raise Exception(f"{operation} failed: {response.error}")

        # データが空でINSERT/UPDATEの場合は警告（SELECTで空は正常）
        if response.data is None:
            print(f"[WARNING] {operation}: response.data is None")

        return response.data
    else:
        # 予期しないレスポンス形式
        raise Exception(f"{operation} returned unexpected response: {type(response)}")

_supabase: Client = None

def get_supabase_client() -> Client:
    global _supabase
    if _supabase:
        return _supabase

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        # Try loading from specific path if find_dotenv failed (e.g. running from src)
        # Assuming .env is in apps/admin-tool
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # apps/admin-tool/src/utils -> apps/admin-tool/.env
        env_path = os.path.join(current_dir, '..', '..', '.env')
        load_dotenv(env_path)

        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Supabase URL and Key must be set in .env file")

    _supabase = create_client(url, key)
    return _supabase

def upload_image_to_supabase(image, filename: str) -> str:
    """
    画像をSupabase Storageにアップロードし、公開URLを返す

    Args:
        image: PIL Imageオブジェクト（RGB or RGBA）
        filename: 保存するファイル名

    Returns:
        公開URL
    """
    supabase = get_supabase_client()

    # 画像をWebP形式に変換してバッファに保存
    buffer = BytesIO()

    # 画像のサイズを調整（最大2000px）
    max_size = 2000
    width, height = image.size
    if max(width, height) > max_size:
        ratio = max_size / max(width, height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        image = image.resize((new_width, new_height))

    # WebP形式で保存（RGBAの場合は透明度を保持）
    # WebPはアルファチャンネルをサポート
    if image.mode == 'RGBA':
        # 透明度付きの場合はlosslessで保存して透明度を確実に保持
        image.save(buffer, format='WebP', lossless=True)
    else:
        image.save(buffer, format='WebP', quality=85)
    buffer.seek(0)

    # Supabase Storageにアップロード
    try:
        # BytesIOをbytesに変換
        buffer.seek(0)
        file_data = buffer.getvalue()

        # upsert: "true" で既存ファイルを上書き
        response = supabase.storage.from_("product-images").upload(
            filename,
            file_data,
            {"content-type": "image/webp", "upsert": "true"}
        )

        # レスポンス検証
        if response is None:
            raise Exception("Storage upload returned None")

        # エラーレスポンスのチェック（dict形式でerrorが返る場合）
        if isinstance(response, dict):
            if 'error' in response and response['error']:
                raise Exception(f"Storage upload error: {response['error']}")
            if 'path' in response:
                public_url = supabase.storage.from_("product-images").get_public_url(filename)
                print(f"[INFO] Storage upload success: {filename}")
                return public_url

        # UploadResponseオブジェクトが返ってきたら成功
        if hasattr(response, 'path'):
            # 公開URLを取得
            public_url = supabase.storage.from_("product-images").get_public_url(filename)
            print(f"[INFO] Storage upload success: {filename}")
            return public_url
        elif hasattr(response, 'error') and response.error:
            raise Exception(f"Storage upload error: {response.error}")
        else:
            # 予期しないレスポンス形式だが、ファイルがアップロードされた可能性を確認
            print(f"[WARNING] Unexpected upload response type: {type(response)}, value: {response}")
            # URLを取得して返す（アップロードは成功している可能性）
            public_url = supabase.storage.from_("product-images").get_public_url(filename)
            return public_url

    except Exception as e:
        print(f"[ERROR] Storage upload failed: {filename}, error: {e}")
        raise Exception(f"Failed to upload image '{filename}': {e}")

def add_cache_buster(url: str) -> str:
    """
    URLにキャッシュ破棄用のタイムスタンプを追加する

    Args:
        url: 元のURL

    Returns:
        タイムスタンプ付きURL
    """
    if '?' in url:
        return f"{url}&_t={int(time.time())}"
    else:
        return f"{url}?_t={int(time.time())}"

def upload_image_to_supabase_with_cache_buster(image, filename: str) -> str:
    """
    画像をSupabase Storageにアップロードし、キャッシュ破棄用URLを返す

    Args:
        image: PIL Imageオブジェクト
        filename: 保存するファイル名

    Returns:
        キャッシュ破棄用付き公開URL
    """
    base_url = upload_image_to_supabase(image, filename)
    return add_cache_buster(base_url)

def get_supabase_image_url(filename: str) -> str:
    """
    Supabase Storageの画像URLを取得する（認証付きURLを試みる）

    Args:
        filename: ファイル名

    Returns:
        画像URL
    """
    supabase = get_supabase_client()

    # まず公開URLを試す
    try:
        public_url = supabase.storage.from_("product-images").get_public_url(filename)
        return public_url
    except:
        # 公開URLがダメな場合は認証付きURLを試す
        try:
            signed_url = supabase.storage.from_("product-images").create_signed_url(filename, expires_in=3600)
            if signed_url:
                return signed_url['signedURL']
        except:
            pass

    # どちらもダメな場合は直接URLを構成
    return f"https://fatsrmydhyyyragtmhaw.supabase.co/storage/v1/object/public/product-images/{filename}"


def delete_storage_file(file_url: str) -> bool:
    """
    Supabase Storageからファイルを削除する

    Args:
        file_url: 削除するファイルのURL

    Returns:
        削除成功時True
    """
    if not file_url:
        return True

    try:
        supabase = get_supabase_client()
        # URLからファイルパスを抽出
        # 例: https://xxx.supabase.co/storage/v1/object/public/product-images/assembly_pages/xxx.webp
        if 'product-images/' in file_url:
            file_path = file_url.split('product-images/')[-1].split('?')[0]
            supabase.storage.from_("product-images").remove([file_path])
            print(f"[INFO] Storage file deleted: {file_path}")
            return True
    except Exception as e:
        print(f"[WARNING] Failed to delete storage file: {file_url}, error: {e}")
        return False


def delete_part(part_id: str) -> dict:
    """
    部品を削除する（画像とDBレコード）

    Args:
        part_id: 部品ID

    Returns:
        削除結果 {"success": bool, "deleted_images": int}
    """
    supabase = get_supabase_client()
    deleted_images = 0

    try:
        # 部品情報を取得
        part_response = supabase.table("parts").select("*").eq("id", part_id).execute()
        if part_response.data:
            part = part_response.data[0]
            # 画像を削除
            if part.get('parts_url'):
                if delete_storage_file(part['parts_url']):
                    deleted_images += 1

        # DBから削除（assembly_image_partsのpart_idはCASCADEでNULLになる）
        supabase.table("parts").delete().eq("id", part_id).execute()

        return {"success": True, "deleted_images": deleted_images}
    except Exception as e:
        print(f"[ERROR] Failed to delete part {part_id}: {e}")
        return {"success": False, "deleted_images": deleted_images, "error": str(e)}


def delete_assembly_image(assembly_image_id: str) -> dict:
    """
    組立番号を削除する（配下の部品も含めて削除）

    Args:
        assembly_image_id: 組立番号画像ID

    Returns:
        削除結果 {"success": bool, "deleted_parts": int, "deleted_images": int}
    """
    supabase = get_supabase_client()
    deleted_parts = 0
    deleted_images = 0

    try:
        # 1. 配下の部品を取得して削除
        parts_response = supabase.table("assembly_image_parts").select(
            "*, parts(*)"
        ).eq("assembly_image_id", assembly_image_id).execute()

        if parts_response.data:
            for part_data in parts_response.data:
                part = part_data.get('parts')
                if part:
                    result = delete_part(part['id'])
                    if result['success']:
                        deleted_parts += 1
                        deleted_images += result.get('deleted_images', 0)

        # 2. assembly_image_partsを削除（CASCADEで自動削除されるが明示的に）
        supabase.table("assembly_image_parts").delete().eq("assembly_image_id", assembly_image_id).execute()

        # 3. 組立番号画像を削除
        assembly_response = supabase.table("assembly_images").select("*").eq("id", assembly_image_id).execute()
        if assembly_response.data:
            assembly = assembly_response.data[0]
            if assembly.get('image_url'):
                if delete_storage_file(assembly['image_url']):
                    deleted_images += 1

        # 4. 組立番号レコードを削除
        supabase.table("assembly_images").delete().eq("id", assembly_image_id).execute()

        return {"success": True, "deleted_parts": deleted_parts, "deleted_images": deleted_images}
    except Exception as e:
        print(f"[ERROR] Failed to delete assembly_image {assembly_image_id}: {e}")
        return {"success": False, "deleted_parts": deleted_parts, "deleted_images": deleted_images, "error": str(e)}


def delete_assembly_page(page_id: str) -> dict:
    """
    組立ページを削除する（配下の組立番号、部品も含めて削除）

    Args:
        page_id: 組立ページID

    Returns:
        削除結果 {"success": bool, "deleted_assembly_images": int, "deleted_parts": int, "deleted_images": int}
    """
    supabase = get_supabase_client()
    deleted_assembly_images = 0
    deleted_parts = 0
    deleted_images = 0

    try:
        # 1. 配下の組立番号を取得して削除
        assembly_response = supabase.table("assembly_images").select("*").eq("page_id", page_id).execute()

        if assembly_response.data:
            for assembly in assembly_response.data:
                result = delete_assembly_image(assembly['id'])
                if result['success']:
                    deleted_assembly_images += 1
                    deleted_parts += result.get('deleted_parts', 0)
                    deleted_images += result.get('deleted_images', 0)

        # 2. 組立ページ画像を削除
        page_response = supabase.table("assembly_pages").select("*").eq("id", page_id).execute()
        if page_response.data:
            page = page_response.data[0]
            if page.get('image_url'):
                if delete_storage_file(page['image_url']):
                    deleted_images += 1

        # 3. 組立ページレコードを削除
        supabase.table("assembly_pages").delete().eq("id", page_id).execute()

        return {
            "success": True,
            "deleted_assembly_images": deleted_assembly_images,
            "deleted_parts": deleted_parts,
            "deleted_images": deleted_images
        }
    except Exception as e:
        print(f"[ERROR] Failed to delete assembly_page {page_id}: {e}")
        return {
            "success": False,
            "deleted_assembly_images": deleted_assembly_images,
            "deleted_parts": deleted_parts,
            "deleted_images": deleted_images,
            "error": str(e)
        }


def get_deletion_impact(level: str, id: str) -> dict:
    """
    削除による影響範囲を取得する

    Args:
        level: 削除レベル ("assembly_page", "assembly_image", "part")
        id: 対象ID

    Returns:
        影響範囲 {"assembly_images": int, "parts": int, "images": int}
    """
    supabase = get_supabase_client()
    result = {"assembly_images": 0, "parts": 0, "images": 0}

    try:
        if level == "assembly_page":
            # 組立ページ配下の組立番号を取得
            assembly_response = supabase.table("assembly_images").select("id, image_url").eq("page_id", id).execute()
            if assembly_response.data:
                result["assembly_images"] = len(assembly_response.data)
                result["images"] += sum(1 for a in assembly_response.data if a.get('image_url'))

                # 各組立番号配下の部品を取得
                for assembly in assembly_response.data:
                    parts_response = supabase.table("assembly_image_parts").select(
                        "parts(id, parts_url)"
                    ).eq("assembly_image_id", assembly['id']).execute()

                    if parts_response.data:
                        for p in parts_response.data:
                            if p.get('parts'):
                                result["parts"] += 1
                                if p['parts'].get('parts_url'):
                                    result["images"] += 1

            # ページ画像も含める
            page_response = supabase.table("assembly_pages").select("image_url").eq("id", id).execute()
            if page_response.data and page_response.data[0].get('image_url'):
                result["images"] += 1

        elif level == "assembly_image":
            # 組立番号画像
            assembly_response = supabase.table("assembly_images").select("image_url").eq("id", id).execute()
            if assembly_response.data and assembly_response.data[0].get('image_url'):
                result["images"] += 1

            # 配下の部品を取得
            parts_response = supabase.table("assembly_image_parts").select(
                "parts(id, parts_url)"
            ).eq("assembly_image_id", id).execute()

            if parts_response.data:
                for p in parts_response.data:
                    if p.get('parts'):
                        result["parts"] += 1
                        if p['parts'].get('parts_url'):
                            result["images"] += 1

        elif level == "part":
            result["parts"] = 1
            part_response = supabase.table("parts").select("parts_url").eq("id", id).execute()
            if part_response.data and part_response.data[0].get('parts_url'):
                result["images"] = 1

    except Exception as e:
        print(f"[ERROR] Failed to get deletion impact: {e}")

    return result

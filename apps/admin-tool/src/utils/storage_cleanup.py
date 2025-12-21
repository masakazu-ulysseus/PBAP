"""
Supabase Storageの不要なファイルを削除するユーティリティ
"""

from utils.supabase_client import get_supabase_client

def cleanup_orphaned_assembly_page_images():
    """
    【安全対策】DBに存在しないassembly_pages画像ファイルを確認する（削除しない）

    Returns:
        孤立しているファイルのリスト
    """
    print("⚠️  安全モード: 削除は実行されず、確認のみ行います")

    # Supabase Storage APIのlist()は信頼性が低いため、手動確認を推奨
    print("❌ 自動クリーニングは無効化されています")
    print("💡 手動でSupabaseダッシュボードから確認してください")
    print("   URL: https://supabase.com/dashboard/project/fatsrmydhyyyragtmhaw/storage/product-images")

    return []  # 削除しない

def get_storage_usage_info():
    """
    Storageの使用量情報を取得する（実装例）
    """
    supabase = get_supabase_client()

    try:
        # assembly_pagesフォルダのファイル一覧
        files_response = supabase.storage.from_("product-images").list("assembly_pages/")

        if hasattr(files_response, 'data') and files_response.data:
            file_count = len(files_response.data)
            print(f"assembly_pages フォルダ内のファイル数: {file_count}")
            return file_count
        else:
            print("ファイル情報の取得に失敗しました")
            return 0

    except Exception as e:
        print(f"Storage情報取得エラー: {e}")
        return 0
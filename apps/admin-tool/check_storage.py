#!/usr/bin/env python3
"""
【安全版】Storageの状態を確認するスクリプト（自動削除なし）
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.supabase_client import get_supabase_client
from utils.storage_cleanup import get_storage_usage_info, cleanup_orphaned_assembly_page_images

def main():
    print("=== Supabase Storage 安全状態確認 ===")

    print("\n⚠️  重要: 自動削除機能は無効化されています")
    print("💡 以下の手順で手動確認してください:")

    print("\n1. Supabaseダッシュボードにアクセス:")
    print("   URL: https://supabase.com/dashboard/project/fatsrmydhyyyragtmhaw/storage/product-images")

    print("\n2. assembly_pages フォルダを確認:")

    # DBのページ数を確認
    try:
        supabase = get_supabase_client()
        pages_response = supabase.table("assembly_pages").select("id").execute()
        db_count = len(pages_response.data) if pages_response.data else 0
        print(f"   - DBに登録されているページ数: {db_count}")
    except Exception as e:
        print(f"   - DB確認エラー: {e}")
        db_count = 0

    print(f"   - Storage内の実際のファイル数: 手動で確認してください")

    print("\n3. 不一致の確認:")
    print("   - DB数とStorage数が大きく異なる場合は要注意")
    print("   - 不要なファイルは手動で削除してください")

    # 安全な確認モードを実行
    print("\n4. 安全な確認モード:")
    orphaned_files = cleanup_orphaned_assembly_page_images()

    print("\n=== 安全確認完了 ===")
    print("\n📝 推奨アクション:")
    print("   - 定期的にSupabaseダッシュボードで確認")
    print("   - 不要なファイルは手動で削除")
    print("   - バックアップを取得してから削除")

if __name__ == "__main__":
    main()
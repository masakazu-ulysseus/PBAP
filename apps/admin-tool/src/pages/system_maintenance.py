"""
システムメンテナンス画面

機能:
- 孤児ファイルのクリーンアップ（Storageにあるが、DBに参照がないファイル）
- DBの整合性チェック
"""
import streamlit as st
from utils.supabase_client import get_supabase_client


def get_orphan_files():
    """
    孤児ファイル（DBに参照がないStorage内のファイル）を取得
    """
    supabase = get_supabase_client()

    # DBに登録されている部品画像URLを取得
    parts_response = supabase.table('parts').select('id, parts_url').execute()
    db_urls = set()
    for part in parts_response.data:
        if part.get('parts_url'):
            url = part['parts_url']
            if 'parts/' in url:
                filename = url.split('parts/')[-1].split('?')[0]
                db_urls.add(f'parts/{filename}')

    # Storageに存在する画像を取得
    storage_files = supabase.storage.from_('product-images').list('parts')
    storage_paths = set()
    for f in storage_files:
        path = f'parts/{f["name"]}'
        storage_paths.add(path)

    # 孤児ファイルを特定
    orphans = storage_paths - db_urls

    return {
        'db_count': len(db_urls),
        'storage_count': len(storage_paths),
        'orphan_files': sorted(list(orphans)),
        'orphan_count': len(orphans)
    }


def get_service_client():
    """
    サービスロールキーでSupabaseクライアントを取得（Storage削除用）
    """
    import os
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not service_key:
        return None

    return create_client(url, service_key)


def delete_orphan_files(orphan_files):
    """
    孤児ファイルを削除（サービスロールキー使用）
    """
    # サービスロールキーを使用してRLSをバイパス
    service_client = get_service_client()

    if not service_client:
        return {
            'deleted': [],
            'errors': [{'file': 'all', 'error': 'SUPABASE_SERVICE_KEY が .env に設定されていません'}],
            'needs_service_key': True
        }

    deleted = []
    errors = []

    for file_path in orphan_files:
        try:
            result = service_client.storage.from_('product-images').remove([file_path])
            # 削除が成功したか確認
            if result and len(result) > 0:
                deleted.append(file_path)
            else:
                errors.append({'file': file_path, 'error': '削除結果が空です'})
        except Exception as e:
            errors.append({'file': file_path, 'error': str(e)})

    return {'deleted': deleted, 'errors': errors, 'needs_service_key': False}


def get_db_integrity_report():
    """
    DBの整合性チェックレポートを取得
    """
    supabase = get_supabase_client()
    issues = []

    # 1. assembly_image_parts で part_id が NULL のレコード
    null_parts = supabase.table('assembly_image_parts').select('id, assembly_image_id, display_order').is_('part_id', 'null').execute()
    if null_parts.data:
        issues.append({
            'type': 'warning',
            'category': '未割当部品枠',
            'description': f'part_id が未設定の assembly_image_parts レコードが {len(null_parts.data)} 件あります',
            'count': len(null_parts.data),
            'details': null_parts.data
        })

    # 2. parts テーブルで parts_url が NULL のレコード
    null_url_parts = supabase.table('parts').select('id, name').is_('parts_url', 'null').execute()
    if null_url_parts.data:
        issues.append({
            'type': 'error',
            'category': '画像URLなし部品',
            'description': f'parts_url が未設定の parts レコードが {len(null_url_parts.data)} 件あります',
            'count': len(null_url_parts.data),
            'details': null_url_parts.data
        })

    # 3. assembly_images で image_url が NULL のレコード
    null_assembly_images = supabase.table('assembly_images').select('id, assembly_number').is_('image_url', 'null').execute()
    if null_assembly_images.data:
        issues.append({
            'type': 'error',
            'category': '画像URLなし組立番号',
            'description': f'image_url が未設定の assembly_images レコードが {len(null_assembly_images.data)} 件あります',
            'count': len(null_assembly_images.data),
            'details': null_assembly_images.data
        })

    # 4. assembly_pages で image_url が NULL のレコード
    null_pages = supabase.table('assembly_pages').select('id, page_number, product_id').is_('image_url', 'null').execute()
    if null_pages.data:
        issues.append({
            'type': 'error',
            'category': '画像URLなし組立ページ',
            'description': f'image_url が未設定の assembly_pages レコードが {len(null_pages.data)} 件あります',
            'count': len(null_pages.data),
            'details': null_pages.data
        })

    return issues


def app():
    """システムメンテナンスページを表示する。
    孤児ファイルのクリーンアップやDBの整合性チェックを行う。
    """
    st.header("🔧 システムメンテナンス")
    st.write("システムの整合性チェックとクリーンアップを行います。")

    # タブで機能を分ける
    tab1, tab2 = st.tabs(["🗑️ 孤児ファイルクリーンアップ", "🔍 DB整合性チェック"])

    with tab1:
        st.subheader("孤児ファイルクリーンアップ")
        st.write("Storageに存在するが、DBに参照がないファイル（孤児ファイル）を検出・削除します。")
        st.warning("⚠️ 削除したファイルは復元できません。必要に応じてバックアップを取ってください。")

        if st.button("🔍 孤児ファイルをスキャン", type="primary"):
            with st.spinner("スキャン中..."):
                result = get_orphan_files()
                st.session_state['orphan_scan_result'] = result

        if 'orphan_scan_result' in st.session_state:
            result = st.session_state['orphan_scan_result']

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("DB登録数", result['db_count'])
            with col2:
                st.metric("Storage内ファイル数", result['storage_count'])
            with col3:
                st.metric("孤児ファイル数", result['orphan_count'],
                         delta=f"-{result['orphan_count']}" if result['orphan_count'] > 0 else None,
                         delta_color="inverse")

            if result['orphan_count'] > 0:
                st.write("---")
                st.write("**検出された孤児ファイル:**")

                # 孤児ファイルのリストを表示
                for i, file_path in enumerate(result['orphan_files']):
                    st.text(f"{i+1}. {file_path}")

                st.write("---")

                # 削除確認
                if 'confirm_delete_orphans' not in st.session_state:
                    st.session_state['confirm_delete_orphans'] = False

                if not st.session_state['confirm_delete_orphans']:
                    if st.button("🗑️ 孤児ファイルを削除", type="secondary"):
                        st.session_state['confirm_delete_orphans'] = True
                        st.rerun()
                else:
                    st.error(f"⚠️ **確認**: {result['orphan_count']} 個のファイルを削除します。この操作は取り消せません。")

                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ 削除を実行", type="primary"):
                            with st.spinner("削除中..."):
                                delete_result = delete_orphan_files(result['orphan_files'])

                            if delete_result.get('needs_service_key'):
                                st.error("❌ Storage削除にはサービスロールキーが必要です")
                                st.info("""
**設定方法:**
1. Supabase Dashboard → Project Settings → API → service_role key をコピー
2. `apps/admin-tool/.env` に以下を追加:
   ```
   SUPABASE_SERVICE_KEY=your_service_role_key_here
   ```
3. Admin Tool を再起動
                                """)
                            elif delete_result['deleted']:
                                st.success(f"✅ {len(delete_result['deleted'])} 個のファイルを削除しました")

                            if delete_result['errors'] and not delete_result.get('needs_service_key'):
                                st.error(f"❌ {len(delete_result['errors'])} 個のファイルで削除エラー")
                                for err in delete_result['errors']:
                                    st.text(f"  - {err['file']}: {err['error']}")

                            # スキャン結果をクリア
                            del st.session_state['orphan_scan_result']
                            st.session_state['confirm_delete_orphans'] = False
                            st.rerun()

                    with col_cancel:
                        if st.button("❌ キャンセル"):
                            st.session_state['confirm_delete_orphans'] = False
                            st.rerun()
            else:
                st.success("✅ 孤児ファイルはありません。Storageは正常です。")

    with tab2:
        st.subheader("DB整合性チェック")
        st.write("データベースの整合性をチェックし、問題を検出します。")

        if st.button("🔍 整合性チェックを実行", type="primary"):
            with st.spinner("チェック中..."):
                issues = get_db_integrity_report()
                st.session_state['db_integrity_issues'] = issues

        if 'db_integrity_issues' in st.session_state:
            issues = st.session_state['db_integrity_issues']

            if not issues:
                st.success("✅ データベースの整合性に問題はありません。")
            else:
                st.warning(f"⚠️ {len(issues)} 件の問題が検出されました")

                for issue in issues:
                    if issue['type'] == 'error':
                        st.error(f"❌ **{issue['category']}**: {issue['description']}")
                    else:
                        st.warning(f"⚠️ **{issue['category']}**: {issue['description']}")

                    with st.expander(f"詳細を表示 ({issue['count']} 件)"):
                        for detail in issue['details'][:10]:  # 最初の10件のみ表示
                            st.json(detail)
                        if issue['count'] > 10:
                            st.info(f"... 他 {issue['count'] - 10} 件")


if __name__ == "__main__":
    app()

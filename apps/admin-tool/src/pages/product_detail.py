import streamlit as st
from utils.supabase_client import get_supabase_client, add_cache_buster, get_deletion_impact, delete_assembly_page, upload_image_to_supabase, delete_storage_file, check_db_response
import pandas as pd
import requests
from io import BytesIO
from PIL import Image

def load_image_from_url(url: str):
    """URLから画像を読み込むヘルパー関数"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            return image
        else:
            return None
    except Exception as e:
        st.write(f"画像取得エラー: {e}")
        return None

def app():
    """商品詳細ページを表示する。
    選択された商品の詳細情報と、その商品に紐づく組立ページ一覧を表示する。
    """

    # 商品一覧に戻るボタン
    if st.button("← 商品一覧に戻る"):
        if 'current_page' in st.session_state:
            del st.session_state['current_page']
        if 'selected_product_id' in st.session_state:
            del st.session_state['selected_product_id']
        st.rerun()

    # 成功メッセージがセッションにあれば表示
    if 'success_message' in st.session_state:
        st.success(st.session_state['success_message'])
        del st.session_state['success_message']

    # 商品IDの確認
    if 'selected_product_id' not in st.session_state:
        st.error("商品が選択されていません。")
        return

    product_id = st.session_state['selected_product_id']

    try:
        supabase = get_supabase_client()

        # 商品情報を取得
        product_response = supabase.table("products").select("*").eq("id", product_id).execute()

        if not product_response.data:
            st.error("商品が見つかりませんでした。")
            return

        product = product_response.data[0]

        # 商品情報を表示
        st.header(f"📦 {product['name']}")

        # 商品画像と基本情報を横並びで表示
        img_col, info_col = st.columns([1, 2])

        with img_col:
            # 商品画像表示
            if product.get('image_url'):
                image_url_with_cache = add_cache_buster(product['image_url'])
                product_image = load_image_from_url(image_url_with_cache)
                if product_image:
                    st.image(product_image, caption="製品画像", use_column_width=True)
                else:
                    st.warning("画像を読み込めません")
            else:
                st.info("📷 製品画像未登録")

            # 画像更新ボタン
            if st.button("🖼️ 画像を更新", key="update_product_image"):
                st.session_state['show_product_image_upload'] = True

        with info_col:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("シリーズ名", product['series_name'])
            with col2:
                st.metric("国", product['country'])
            with col3:
                # ステータス表示とトグルボタン
                current_status = product['status']
                status_icon = "🟢" if current_status == "active" else "🟡"
                status_label = "公開中" if current_status == "active" else "準備中"
                st.metric("ステータス", f"{status_icon} {status_label}")

                # ステータス変更ボタン
                new_status = "inactive" if current_status == "active" else "active"
                new_status_label = "準備中に変更" if current_status == "active" else "公開に変更"
                if st.button(f"🔄 {new_status_label}", key="toggle_product_status"):
                    try:
                        update_response = supabase.table("products").update({
                            "status": new_status
                        }).eq("id", product_id).execute()
                        check_db_response(update_response, f"UPDATE products.status (id={product_id})")
                        new_label = "公開中" if new_status == "active" else "準備中"
                        st.session_state['success_message'] = f"✅ ステータスを「{new_label}」に変更しました"
                        st.rerun()
                    except Exception as e:
                        st.error(f"ステータス更新エラー: {e}")

        # 商品画像アップロードフォーム
        if st.session_state.get('show_product_image_upload'):
            st.markdown("### 製品画像の更新")
            new_product_image = st.file_uploader(
                "新しい製品画像を選択",
                type=['png', 'jpg', 'jpeg', 'webp'],
                key="new_product_image_upload"
            )

            if new_product_image:
                st.image(new_product_image, caption="アップロード予定の画像", width=200)

            col_upload, col_cancel = st.columns(2)
            with col_upload:
                if st.button("📤 アップロード", type="primary", disabled=not new_product_image):
                    if new_product_image:
                        try:
                            # 古い画像を削除
                            if product.get('image_url'):
                                delete_storage_file(product['image_url'])

                            # 新しい画像をアップロード
                            pil_image = Image.open(new_product_image)
                            if pil_image.mode == 'RGBA':
                                pil_image = pil_image.convert('RGB')
                            filename = f"products/{product_id}.webp"
                            new_image_url = upload_image_to_supabase(pil_image, filename)

                            # DBを更新
                            update_response = supabase.table("products").update({
                                "image_url": new_image_url
                            }).eq("id", product_id).execute()
                            check_db_response(update_response, f"UPDATE products.image_url (id={product_id})")

                            del st.session_state['show_product_image_upload']
                            st.session_state['success_message'] = "✅ 製品画像を更新しました"
                            st.rerun()
                        except Exception as e:
                            st.error(f"画像のアップロードに失敗しました: {e}")
            with col_cancel:
                if st.button("キャンセル", key="cancel_product_image_upload"):
                    del st.session_state['show_product_image_upload']
                    st.rerun()

        st.markdown("---")

        # 組立ページ一覧を取得
        pages_response = supabase.table("assembly_pages").select("*").eq("product_id", product_id).order("page_number").execute()

        # 各組立ページの組立番号数を取得
        assembly_counts = {}
        if pages_response.data:
            for page in pages_response.data:
                assembly_response = supabase.table("assembly_images").select("id", count="exact").eq("page_id", page['id']).execute()
                assembly_counts[page['id']] = assembly_response.count if assembly_response.count else 0

        st.subheader("📄 組立ページ一覧")

        # 組立ページ追加ボタン
        if st.button("➕ 組立ページを追加", type="primary"):
            st.session_state['current_page'] = 'assembly_page_add'
            st.rerun()

        # 組立ページがない場合
        if not pages_response.data:
            st.info("組立ページがありません。「➕ 組立ページを追加」ボタンから追加してください。")
            return

        # 組立ページ一覧を表示
        st.write("---")
        pages_df = pd.DataFrame(pages_response.data)

        # 画像未登録のページ数をカウント
        pending_count = sum(1 for _, p in pages_df.iterrows() if not p['image_url'])
        if pending_count > 0:
            st.warning(f"⚠️ 画像未登録のページが {pending_count} 件あります")

        for i, page in pages_df.iterrows():
            page_number = page['page_number']
            page_display = f"ページ {page_number}（表紙）" if page_number == 0 else f"ページ {page_number}"
            has_image = page['image_url'] is not None and page['image_url'] != ''
            assembly_count = assembly_counts.get(page['id'], 0)

            col1, col2, col3, col4 = st.columns([1.2, 3.5, 1.3, 2])
            with col1:
                if has_image:
                    st.write(f"✅ **{page_display}**")
                else:
                    st.write(f"📷 **{page_display}**")
            with col2:
                if has_image:
                    # 画像のサムネイル表示（キャッシュ破棄付き）
                    image_url_with_cache = add_cache_buster(page['image_url'])
                    image = load_image_from_url(image_url_with_cache)
                    if image:
                        st.image(image, width=200, caption=f"{page_display} サムネイル")
                    else:
                        st.write("画像を読み込めません")
                        col2a, col2b = st.columns(2)
                        with col2a:
                            if st.button("📁 画像再アップロード", key=f"reupload_{page['id']}"):
                                st.session_state['reupload_page_id'] = page['id']
                                st.session_state['current_page'] = 'assembly_page_reupload'
                                st.rerun()
                        with col2b:
                            if st.checkbox("デバッグ情報", key=f"debug_{page['id']}"):
                                st.code(f"URL: {page['image_url']}")
                else:
                    # 画像未登録の場合
                    st.info("📷 画像未登録")
            with col3:
                # 配下情報
                st.write(f"🔢 組立番号: **{assembly_count}**件")
            with col4:
                if has_image:
                    col4a, col4b = st.columns(2)
                    with col4a:
                        if st.button("詳細を見る", key=f"page_{page['id']}"):
                            st.session_state['selected_page_id'] = page['id']
                            st.session_state['current_page'] = 'assembly_page_detail'
                            st.rerun()
                    with col4b:
                        if st.button("🗑️ 削除", key=f"delete_page_{page['id']}", type="secondary"):
                            st.session_state['confirm_delete_page_id'] = page['id']
                            st.session_state['confirm_delete_page_number'] = page_number
                            st.rerun()
                else:
                    col4a, col4b = st.columns(2)
                    with col4a:
                        if st.button("📤 画像を登録", key=f"upload_{page['id']}", type="primary"):
                            st.session_state['upload_to_page_id'] = page['id']
                            st.session_state['upload_to_page_number'] = page_number
                            st.session_state['current_page'] = 'assembly_page_add'
                            st.rerun()
                    with col4b:
                        if st.button("🗑️ 削除", key=f"delete_page_empty_{page['id']}", type="secondary"):
                            st.session_state['confirm_delete_page_id'] = page['id']
                            st.session_state['confirm_delete_page_number'] = page_number
                            st.rerun()

            # 削除確認ダイアログ
            if st.session_state.get('confirm_delete_page_id') == page['id']:
                st.warning("⚠️ **削除確認**")
                impact = get_deletion_impact("assembly_page", page['id'])

                st.markdown(f"""
**このページを削除すると、以下のデータが完全に削除されます：**
- 📄 組立ページ画像: 1枚
- 🔢 組立番号: **{impact['assembly_images']}件**
- 🧩 部品: **{impact['parts']}件**
- 🖼️ 画像ファイル（Storage）: **{impact['images']}枚**

**この操作は取り消せません。本当に削除しますか？**
                """)

                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("🗑️ 削除を実行", key=f"confirm_del_{page['id']}", type="primary"):
                        with st.spinner("削除中..."):
                            result = delete_assembly_page(page['id'])
                            if result['success']:
                                del st.session_state['confirm_delete_page_id']
                                del st.session_state['confirm_delete_page_number']
                                st.session_state['success_message'] = f"✅ ページ {page_number} を削除しました（組立番号: {result['deleted_assembly_images']}件、部品: {result['deleted_parts']}件、画像: {result['deleted_images']}枚）"
                                st.rerun()
                            else:
                                st.error(f"削除に失敗しました: {result.get('error', '不明なエラー')}")
                with col_cancel:
                    if st.button("キャンセル", key=f"cancel_del_{page['id']}"):
                        del st.session_state['confirm_delete_page_id']
                        del st.session_state['confirm_delete_page_number']
                        st.rerun()

            st.write("---")

    except Exception as e:
        st.error(f"データの取得に失敗しました: {e}")

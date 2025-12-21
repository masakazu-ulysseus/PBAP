import streamlit as st
from utils.supabase_client import get_supabase_client, check_db_response, delete_assembly_page, delete_storage_file, upload_image_to_supabase
from utils.logger import logger
from PIL import Image
import pandas as pd
import uuid


def app():
    """商品一覧ページを表示する。
    Supabase の `products` テーブルから `id, name, series_name, country, created_at` を取得し、
    No, 商品カテゴリ, 国, 商品名 の列でテーブル表示する。
    """
    st.header("📦 商品一覧")

    # 新規商品登録ボタン
    if st.button("➕ 新規商品登録", type="primary"):
        st.session_state['show_new_product_form'] = True

    # 新規商品登録フォーム
    if 'show_new_product_form' in st.session_state and st.session_state['show_new_product_form']:
        with st.container():
            st.markdown("### 新規商品登録")

            # 製品画像アップロード（フォーム外）
            product_image_file = st.file_uploader(
                "製品画像（任意）",
                type=['png', 'jpg', 'jpeg', 'webp'],
                help="製品の写真をアップロードしてください",
                key="new_product_image"
            )

            # プレビュー表示
            if product_image_file:
                st.image(product_image_file, caption="アップロード予定の製品画像", width=200)

            with st.form("new_product_form"):
                series_name = st.selectbox("シリーズ名", ["ESシリーズ", "PBシリーズ", "その他"])
                country = st.selectbox("国", ["ドイツ", "日本", "アメリカ", "ソビエト", "イギリス", "その他"])
                product_name = st.text_input("製品名")
                page_count = st.number_input(
                    "ページ数",
                    min_value=1,
                    max_value=100,
                    value=1,
                    step=1,
                    help="表紙、背表紙のページを含めてカウントしてください"
                )

                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("確定", type="primary")
                with col2:
                    cancelled = st.form_submit_button("キャンセル")

                if submitted and product_name and series_name and country:
                    try:
                        supabase = get_supabase_client()
                        product_id = str(uuid.uuid4())

                        # 製品画像をアップロード
                        product_image_url = None
                        if product_image_file:
                            pil_image = Image.open(product_image_file)
                            if pil_image.mode == 'RGBA':
                                pil_image = pil_image.convert('RGB')
                            filename = f"products/{product_id}.webp"
                            product_image_url = upload_image_to_supabase(pil_image, filename)

                        # 1. 商品を作成
                        product_response = supabase.table("products").insert({
                            "id": product_id,
                            "name": product_name,
                            "series_name": series_name,
                            "country": country,
                            "status": "active",
                            "image_url": product_image_url
                        }).execute()
                        check_db_response(product_response, f"INSERT products (id={product_id})")
                        # 2. ページ数分の空のAssemblyPagesレコードを作成
                        assembly_pages = []
                        for page_num in range(page_count):
                            assembly_pages.append({
                                "id": str(uuid.uuid4()),
                                "product_id": product_id,
                                "page_number": page_num,
                                "image_url": None
                            })
                        if assembly_pages:
                            pages_response = supabase.table("assembly_pages").insert(assembly_pages).execute()
                            check_db_response(pages_response, f"INSERT assembly_pages (count={len(assembly_pages)})")
                        logger.info(f"商品登録: name={product_name}, id={product_id}, pages={page_count}")
                        st.success(f"商品「{product_name}」を登録しました！（{page_count}ページ分の枠を作成）")
                        del st.session_state['show_new_product_form']
                        st.rerun()
                    except Exception as e:
                        logger.error(f"商品登録エラー: {e}")
                        st.error(f"商品登録に失敗しました: {e}")

                if cancelled:
                    del st.session_state['show_new_product_form']
                    st.rerun()

    st.markdown("---")

    # Supabase からデータ取得
    try:
        supabase = get_supabase_client()
        response = supabase.table("products").select("id, name, series_name, country, created_at").order("created_at", desc=True).execute()

        # 各商品の組立ページ数を取得
        page_counts = {}
        if response.data:
            for product in response.data:
                pages_response = supabase.table("assembly_pages").select("id", count="exact").eq("product_id", product['id']).execute()
                page_counts[product['id']] = pages_response.count if pages_response.count else 0

    except Exception as e:
        logger.error(f"商品一覧取得エラー: {e}")
        st.error(f"Supabase からの取得に失敗しました: {e}")
        return

    # データがない場合の処理
    if not response.data:
        st.info("商品がありません。")
        return

    # データがある場合はDataFrame作成
    df = pd.DataFrame(response.data)

    # テーブル表示
    st.subheader("登録済み商品")

    # ヘッダー
    col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 1.5, 1.5, 3, 1, 1.5, 1])
    with col1:
        st.markdown("**No**")
    with col2:
        st.markdown("**シリーズ名**")
    with col3:
        st.markdown("**国**")
    with col4:
        st.markdown("**商品名**")
    with col5:
        st.markdown("**ページ数**")
    with col6:
        st.markdown("**操作**")
    with col7:
        st.markdown("**削除**")

    # 各行
    for i, row in df.iterrows():
        col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 1.5, 1.5, 3, 1, 1.5, 1])
        with col1:
            st.write(f"{i+1}")
        with col2:
            st.write(row['series_name'])
        with col3:
            st.write(row['country'])
        with col4:
            st.write(row['name'])
        with col5:
            st.write(f"📄 {page_counts.get(row['id'], 0)}")
        with col6:
            if st.button("確認／編集", key=f"edit_{row['id']}"):
                st.session_state['selected_product_id'] = row['id']
                st.session_state['current_page'] = 'product_detail'
                st.rerun()
        with col7:
            if st.button("🗑️", key=f"delete_{row['id']}", help="商品と関連データをすべて削除"):
                st.session_state['delete_product_id'] = row['id']
                st.session_state['delete_product_name'] = row['name']

    # 削除確認ダイアログ
    if 'delete_product_id' in st.session_state:
        product_id = st.session_state['delete_product_id']
        product_name = st.session_state['delete_product_name']

        st.warning(f"⚠️ 商品「{product_name}」を削除しますか？")
        st.caption("関連するすべてのデータ（組立ページ、組立番号画像、部品情報）も削除されます。この操作は取り消せません。")

        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("🗑️ 削除する", type="primary", key="confirm_delete"):
                try:
                    supabase = get_supabase_client()

                    # 1. 商品画像を取得
                    product_response = supabase.table("products").select("image_url").eq("id", product_id).execute()
                    product_image_url = product_response.data[0].get('image_url') if product_response.data else None

                    # 2. 関連する組立ページを取得して削除（Storage画像も含めて削除）
                    pages_response = supabase.table("assembly_pages").select("id").eq("product_id", product_id).execute()
                    deleted_pages = 0
                    deleted_parts = 0
                    deleted_images = 0

                    if pages_response.data:
                        for page in pages_response.data:
                            result = delete_assembly_page(page['id'])
                            if result['success']:
                                deleted_pages += 1
                                deleted_parts += result.get('deleted_parts', 0)
                                deleted_images += result.get('deleted_images', 0)

                    # 3. 商品画像を削除
                    if product_image_url:
                        delete_storage_file(product_image_url)
                        deleted_images += 1

                    # 4. 商品を削除
                    delete_response = supabase.table("products").delete().eq("id", product_id).execute()
                    check_db_response(delete_response, f"DELETE products (id={product_id})")
                    logger.info(f"商品削除: name={product_name}, id={product_id}, pages={deleted_pages}, parts={deleted_parts}")
                    st.success(f"商品「{product_name}」と関連データを削除しました。（ページ: {deleted_pages}、部品: {deleted_parts}、画像: {deleted_images}）")
                    del st.session_state['delete_product_id']
                    del st.session_state['delete_product_name']
                    st.rerun()
                except Exception as e:
                    logger.error(f"商品削除エラー: id={product_id} - {e}")
                    st.error(f"削除に失敗しました: {e}")
        with col_cancel:
            if st.button("キャンセル", key="cancel_delete"):
                del st.session_state['delete_product_id']
                del st.session_state['delete_product_name']
                st.rerun()

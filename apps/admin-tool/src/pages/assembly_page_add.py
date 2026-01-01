import streamlit as st
from PIL import Image
from utils.supabase_client import get_supabase_client, upload_image_to_supabase, check_db_response
import uuid

def app():
    """組立ページ追加ページ"""

    # 既存ページへの画像追加モードかどうか
    is_upload_to_existing = 'upload_to_page_id' in st.session_state

    # 商品詳細に戻るボタン
    if st.button("← 商品詳細に戻る"):
        # セッションをクリア
        for key in ['current_page', 'upload_to_page_id', 'upload_to_page_number']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    if is_upload_to_existing:
        page_number = st.session_state['upload_to_page_number']
        page_display = f"ページ {page_number}（表紙）" if page_number == 0 else f"ページ {page_number}"
        st.header(f"📤 {page_display} に画像を登録")
    else:
        st.header("📄 組立ページの追加")

    # エラーメッセージがセッションにあれば表示
    if 'page_error_message' in st.session_state:
        st.error(st.session_state['page_error_message'])
        del st.session_state['page_error_message']

    # 商品情報を表示
    if 'selected_product_id' not in st.session_state:
        st.error("商品が選択されていません。")
        return

    try:
        supabase = get_supabase_client()
        product_id = st.session_state['selected_product_id']

        # 商品情報を取得して表示
        product_response = supabase.table("products").select("*").eq("id", product_id).execute()
        if not product_response.data:
            st.error("商品情報が見つかりません。")
            return

        product = product_response.data[0]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("商品名", product['name'])
        with col2:
            st.metric("シリーズ", product['series_name'])
        with col3:
            st.metric("国", product['country'])

        st.markdown("---")

        # 組立ページ画像アップロード
        uploaded_file = st.file_uploader("組立ページ画像を選択 (WebP/JPG/PNG)", type=['webp', 'jpg', 'png', 'jpeg'])

        if uploaded_file is not None:
            # ファイル名とサイズを保存
            filename = uploaded_file.name
            filesize = f"{uploaded_file.size / (1024*1024):.1f}MB"
            st.session_state['uploaded_filename'] = filename
            st.session_state['uploaded_filesize'] = filesize

            image = Image.open(uploaded_file)
            st.session_state['assembly_page_image'] = image
            st.image(image, caption='アップロードされた組立ページ', use_column_width=True)

            # 既存ページへの画像追加の場合はページ番号入力不要
            if is_upload_to_existing:
                page_number = st.session_state['upload_to_page_number']
                page_display = f"ページ {page_number}（表紙）" if page_number == 0 else f"ページ {page_number}"
                st.info(f"📌 {page_display} に画像を登録します")
            else:
                # 新規追加の場合はページ番号入力
                st.write("---")
                st.subheader("ページ番号")
                page_number_input = st.number_input(
                    "ページ番号を入力してください",
                    min_value=0,
                    step=1,
                    value=1,
                    format="%d",
                    key="page_number_input",
                    help="表紙の場合は 0 を入力してください"
                )
                if page_number_input == 0:
                    st.info("📘 表紙ページとして登録されます")

            # 保存ボタン
            st.write("---")
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("保存", type="primary", key="save_assembly_page"):
                    if is_upload_to_existing:
                        st.session_state['page_number'] = st.session_state['upload_to_page_number']
                    else:
                        st.session_state['page_number'] = page_number_input
                    st.session_state['save_page_only'] = True
                    st.rerun()
            with col_cancel:
                if st.button("キャンセル", key="cancel_assembly_page"):
                    # 入力内容をクリアして商品詳細ページに戻る
                    for key in ['assembly_page_image', 'page_number', 'upload_to_page_id', 'upload_to_page_number']:
                        if key in st.session_state:
                            del st.session_state[key]
                    if 'current_page' in st.session_state:
                        del st.session_state['current_page']
                    st.rerun()

        # ページ番号が確定したら保存処理
        if 'save_page_only' in st.session_state and 'page_number' in st.session_state and 'assembly_page_image' in st.session_state:

            # 組立ページを保存
            with st.spinner("組立ページを保存中…"):
                try:
                    if is_upload_to_existing:
                        # 既存ページへの画像追加（UPDATE）
                        page_id = st.session_state['upload_to_page_id']
                        page_filename = f"assembly_pages/{page_id}.webp"
                        page_url = upload_image_to_supabase(st.session_state['assembly_page_image'], page_filename)

                        update_response = supabase.table("assembly_pages").update({
                            "image_url": page_url
                        }).eq("id", page_id).execute()
                        check_db_response(update_response, f"UPDATE assembly_pages (id={page_id})")
                    else:
                        # 新規ページ追加（INSERT）
                        # 重複チェック: 同じproduct_idで同じpage_numberが既に存在するか確認
                        existing_page = supabase.table("assembly_pages").select("id").eq("product_id", product_id).eq("page_number", st.session_state['page_number']).execute()
                        if existing_page.data:
                            # セッションにエラーメッセージを保存してリロード後に表示
                            st.session_state['page_error_message'] = f"⚠️ ページ番号 {st.session_state['page_number']} は既に登録されています。別のページ番号を入力してください。"
                            del st.session_state['save_page_only']
                            st.rerun()

                        page_id = str(uuid.uuid4())
                        page_filename = f"assembly_pages/{page_id}.webp"
                        page_url = upload_image_to_supabase(st.session_state['assembly_page_image'], page_filename)

                        insert_response = supabase.table("assembly_pages").insert({
                            "id": page_id,
                            "product_id": product_id,
                            "page_number": st.session_state['page_number'],
                            "image_url": page_url
                        }).execute()
                        check_db_response(insert_response, f"INSERT assembly_pages (id={page_id})")

                    page_display = "0（表紙）" if st.session_state['page_number'] == 0 else str(st.session_state['page_number'])

                    # 成功メッセージをセッションに保存（商品詳細ページで表示）
                    st.session_state['success_message'] = f"✅ ページ {page_display} の保存が完了しました！"

                    # 保存成功後、商品詳細ページに戻る
                    for key in ['assembly_page_image', 'page_number', 'save_page_only', 'uploaded_filename', 'uploaded_filesize', 'upload_to_page_id', 'upload_to_page_number']:
                        if key in st.session_state:
                            del st.session_state[key]
                    # 商品詳細ページに戻る
                    st.session_state['current_page'] = 'product_detail'
                    st.rerun()

                except Exception as e:
                    st.error(f"保存中にエラーが発生しました: {e}")
                    # エラー時もクリアして続行可能にする
                    for key in ['assembly_page_image', 'page_number', 'save_page_only', 'uploaded_filename', 'uploaded_filesize', 'upload_to_page_id', 'upload_to_page_number']:
                        if key in st.session_state:
                            del st.session_state[key]
                    if 'current_page' in st.session_state:
                        del st.session_state['current_page']
                    st.rerun()

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
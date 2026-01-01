import streamlit as st
from PIL import Image
from utils.supabase_client import get_supabase_client, upload_image_to_supabase, add_cache_buster, check_db_response
import requests
from io import BytesIO

def check_image_url(url: str):
    """URLから画像が読み込めるかチェックする"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            return True, image
        else:
            return False, None
    except Exception as e:
        print(f"Image check error: {e}")
        return False, None

def app():
    """組立ページ画像再アップロードページ"""

    # 商品詳細に戻るボタン
    if st.button("← 商品詳細に戻る"):
        if 'reupload_page_id' in st.session_state:
            del st.session_state['reupload_page_id']
        if 'force_reupload' in st.session_state:
            del st.session_state['force_reupload']
        if 'current_page' in st.session_state:
            del st.session_state['current_page']
        st.rerun()

    st.header("🔄 組立ページ画像の再アップロード")

    # ページIDの確認
    if 'reupload_page_id' not in st.session_state or 'selected_product_id' not in st.session_state:
        st.error("組立ページが選択されていません。")
        return

    page_id = st.session_state['reupload_page_id']
    product_id = st.session_state['selected_product_id']

    try:
        supabase = get_supabase_client()

        # 商品情報を取得
        product_response = supabase.table("products").select("*").eq("id", product_id).execute()
        if not product_response.data:
            st.error("商品情報が見つかりません。")
            return

        product = product_response.data[0]

        # 組立ページ情報を取得
        page_response = supabase.table("assembly_pages").select("*").eq("id", page_id).execute()
        if not page_response.data:
            st.error("組立ページ情報が見つかりません。")
            return

        page = page_response.data[0]
        page_number = page['page_number']
        page_display = f"ページ {page_number}（表紙）" if page_number == 0 else f"ページ {page_number}"

        # 現在の情報を表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("商品名", product['name'])
        with col2:
            st.metric("ページ番号", page_display)
        with col3:
            st.metric("現在のURL", "読み込み不可" if page['image_url'] else "未設定")

        st.markdown("---")

        # 現在の画像URLと状態
        st.subheader("現在の状態")
        show_upload_section = False

        if page['image_url']:
            # 画像が実際に読み込めるかチェック
            can_load, image_data = check_image_url(page['image_url'])

            if can_load and image_data and not ('force_reupload' in st.session_state and st.session_state['force_reupload']):
                # 画像が読み込める場合
                st.image(image_data, caption=f"現在の{page_display}", width=400)
                st.info("✅ 画像は正常に読み込めています。再アップロードの必要はありません。")
                if st.button("それでも再アップロードする", type="secondary"):
                    st.session_state['force_reupload'] = True
                    st.rerun()
                else:
                    return
            else:
                # 画像が読み込めない場合、または強制再アップロードの場合
                if 'force_reupload' in st.session_state and st.session_state['force_reupload']:
                    st.info("🔄 強制再アップロードモードです")
                else:
                    st.error("❌ 現在の画像を読み込めません")
                    st.code(f"URL: {page['image_url']}")
                show_upload_section = True
        else:
            st.warning("⚠️ 画像URLが設定されていません")
            show_upload_section = True

        # 新しい画像アップロード
        if show_upload_section:
            st.markdown("---")
            st.subheader("📁 新しい画像のアップロード")
            uploaded_file = st.file_uploader(
                "新しい組立ページ画像を選択 (WebP/JPG/PNG)",
                type=['webp', 'jpg', 'png', 'jpeg'],
                help=f"{page_display}の新しい画像ファイルを選択してください"
            )

            if uploaded_file is not None:
                # ファイル名とサイズを保存
                filename = uploaded_file.name
                filesize = f"{uploaded_file.size / (1024*1024):.1f}MB"
                st.session_state['reupload_filename'] = filename
                st.session_state['reupload_filesize'] = filesize

                image = Image.open(uploaded_file)
                st.session_state['reupload_image'] = image
                st.image(image, caption='新しい組立ページ画像', use_container_width=True)

                # 確認ボタン
                st.write("---")
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("🔄 画像を更新", type="primary", key="update_assembly_page"):
                        st.session_state['update_page_only'] = True
                        st.rerun()
                with col_cancel:
                    if st.button("キャンセル", key="cancel_reupload"):
                        # 入力内容をクリアして商品詳細ページに戻る
                        for key in ['reupload_image', 'update_page_only', 'reupload_filename', 'reupload_filesize', 'force_reupload']:
                            if key in st.session_state:
                                del st.session_state[key]
                        if 'current_page' in st.session_state:
                            del st.session_state['current_page']
                        st.rerun()

        # 画像更新処理
        if 'update_page_only' in st.session_state and 'reupload_image' in st.session_state:

            # 組立ページ画像更新
            with st.spinner(f"{page_display}の画像を更新中…"):
                try:
                    # 既存のファイル名を取得
                    old_filename = page['image_url'].split('/')[-1] if page['image_url'] else None
                    new_filename = f"assembly_pages/{page_id}.webp"

                    # 新しい画像アップロード（キャッシュ破棄URL付き）
                    base_url = upload_image_to_supabase(st.session_state['reupload_image'], new_filename)
                    new_url = add_cache_buster(base_url)

                    # データベースを更新
                    update_response = supabase.table("assembly_pages").update({
                        "image_url": new_url
                    }).eq("id", page_id).execute()
                    check_db_response(update_response, f"UPDATE assembly_pages (id={page_id})")

                    # トースト通知で成功メッセージを表示
                    st.toast(f"{page_display}の画像を更新しました！", icon="✅")

                    # 旧ファイルの削除
                    if old_filename:
                        try:
                            # タイムスタンプパラメータを除去
                            clean_filename = old_filename.split('?')[0]

                            # ファイル名だけを抽出（assembly_pages/を除去）
                            if 'assembly_pages/' in clean_filename:
                                clean_filename = clean_filename.split('assembly_pages/')[-1]

                            # page_idと同じファイル名でない場合は削除
                            if clean_filename != f"{page_id}.webp":
                                file_to_delete = f"assembly_pages/{clean_filename}"
                                supabase.storage.from_("product-images").remove([file_to_delete])
                                print(f"古いファイル {file_to_delete} を削除しました")
                            else:
                                print(f"ファイル名が同じため削除をスキップ: {clean_filename}")
                        except Exception as delete_error:
                            print(f"古いファイルの削除に失敗しました: {delete_error}")
                            st.warning("古いファイルの削除に失敗しました（手動で削除が必要です）")

                    # 更新成功後、商品詳細ページに戻る
                    for key in ['reupload_image', 'update_page_only', 'reupload_filename', 'reupload_filesize', 'reupload_page_id', 'force_reupload']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state['current_page'] = 'product_detail'
                    st.rerun()

                except Exception as e:
                    st.error(f"更新中にエラーが発生しました: {e}")
                    # エラー時もクリアして続行可能にする
                    for key in ['reupload_image', 'update_page_only', 'reupload_filename', 'reupload_filesize']:
                        if key in st.session_state:
                            del st.session_state[key]
                    if 'current_page' in st.session_state:
                        del st.session_state['current_page']
                    st.rerun()

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
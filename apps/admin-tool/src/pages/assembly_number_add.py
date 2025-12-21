import streamlit as st
import numpy as np
import cv2
from PIL import Image
from utils.supabase_client import get_supabase_client, upload_image_to_supabase, add_cache_buster, check_db_response
from utils.image_processing import extract_assembly_images
import uuid
from streamlit_cropper import st_cropper
import requests
from io import BytesIO


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
    """組立番号画像登録ページ

    2つのモードがあります：
    1. 既存レコードへの画像登録（UPDATE）: upload_to_assembly_idがセッションにある場合
    2. 新規レコードの作成（INSERT）: それ以外の場合（複数領域選択モード）
    """

    # 組立ページ詳細に戻るボタン
    if st.button("← 組立ページ詳細に戻る"):
        # セッションをクリア
        for key in ['selected_regions', 'pending_bbox', 'assembly_page_image_loaded',
                    'upload_to_assembly_id', 'upload_to_assembly_number', 'auto_detected_images']:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state['current_page'] = 'assembly_page_detail'
        st.rerun()

    # 成功メッセージがセッションにあれば表示
    if 'success_message' in st.session_state:
        st.success(st.session_state['success_message'])
        del st.session_state['success_message']

    # エラーメッセージがセッションにあれば表示
    if 'error_message' in st.session_state:
        st.error(st.session_state['error_message'])
        del st.session_state['error_message']

    # ページIDの確認
    if 'selected_page_id' not in st.session_state or 'selected_product_id' not in st.session_state:
        st.error("組立ページが選択されていません。")
        return

    page_id = st.session_state['selected_page_id']
    product_id = st.session_state['selected_product_id']

    # モード判定：既存レコードへの画像登録 or 新規作成
    is_update_mode = 'upload_to_assembly_id' in st.session_state

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
            st.error("組立ページが見つかりません。")
            return
        page = page_response.data[0]
        page_display = f"ページ {page['page_number']}（表紙）" if page['page_number'] == 0 else f"ページ {page['page_number']}"

        if is_update_mode:
            # ===== UPDATEモード：既存レコードへの画像登録 =====
            assembly_id = st.session_state['upload_to_assembly_id']
            assembly_number = st.session_state['upload_to_assembly_number']

            st.header(f"📤 組立番号 {assembly_number} の画像登録")

            # 商品・ページ情報を表示
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("商品名", product['name'])
            with col2:
                st.metric("ページ", page_display)
            with col3:
                st.metric("組立番号", assembly_number)

            st.markdown("---")

            # 組立ページ画像を読み込み
            if 'assembly_page_image_loaded' not in st.session_state:
                image_url = add_cache_buster(page['image_url'])
                image = load_image_from_url(image_url)
                if image:
                    st.session_state['assembly_page_image_loaded'] = image
                else:
                    st.error("組立ページ画像を読み込めません。")
                    return

            image = st.session_state['assembly_page_image_loaded']

            # デバッグ: コンソールにログ出力
            print(f"[DEBUG] do_save_update = {st.session_state.get('do_save_update')}")
            print(f"[DEBUG] update_crop_coords = {st.session_state.get('update_crop_coords')}")

            # 保存フラグがある場合、先に保存処理を実行
            if st.session_state.get('do_save_update') and 'update_crop_coords' in st.session_state:
                print("[DEBUG] >>> 保存処理に入りました！")
                coords = st.session_state['update_crop_coords']
                print(f"[DEBUG] coords = {coords}")
                c_left, c_top, c_width, c_height = coords

                with st.spinner("保存中…"):
                    try:
                        print("[DEBUG] 画像のクロップ開始...")
                        img_np = np.array(image)
                        crop_for_save = img_np[c_top:c_top+c_height, c_left:c_left+c_width]
                        crop_image = Image.fromarray(crop_for_save)
                        print(f"[DEBUG] クロップ完了: size={crop_image.size}")

                        # 画像をアップロード
                        assembly_img_filename = f"assembly_images/{assembly_id}.webp"
                        print(f"[DEBUG] Supabaseにアップロード開始: {assembly_img_filename}")
                        assembly_img_url = upload_image_to_supabase(crop_image, assembly_img_filename)
                        print(f"[DEBUG] アップロード完了: URL={assembly_img_url}")

                        # 既存レコードをUPDATE
                        print(f"[DEBUG] DB UPDATE開始: assembly_id={assembly_id}")
                        update_response = supabase.table("assembly_images").update({
                            "image_url": assembly_img_url
                        }).eq("id", assembly_id).execute()
                        check_db_response(update_response, f"UPDATE assembly_images (id={assembly_id})")
                        print("[DEBUG] DB UPDATE完了")

                        # セッションをクリアして組立ページ詳細に戻る
                        for key in ['assembly_page_image_loaded', 'upload_to_assembly_id',
                                    'upload_to_assembly_number', 'update_crop_coords', 'do_save_update']:
                            if key in st.session_state:
                                del st.session_state[key]

                        st.session_state['success_message'] = f"✅ 組立番号 {assembly_number} の画像を更新しました！"
                        st.session_state['current_page'] = 'assembly_page_detail'
                        print("[DEBUG] 保存処理完了、assembly_page_detailへ遷移")
                        st.rerun()

                    except Exception as e:
                        print(f"[DEBUG] !!! エラー発生: {e}")
                        del st.session_state['do_save_update']
                        st.session_state['error_message'] = f"保存中にエラーが発生しました: {e}"
                        st.rerun()

            st.info("📌 組立ページ画像から、組立番号の領域を選択してください。緑の枠をドラッグして調整できます。")

            # クロップ機能を表示
            cropped_box = st_cropper(
                image,
                realtime_update=True,
                box_color='#00FF00',
                aspect_ratio=None,
                return_type='box',
                key="single_region_cropper"
            )

            # クロップボックスの座標を取得してセッションに保存
            if cropped_box is not None and isinstance(cropped_box, dict):
                left = cropped_box.get('left', 0)
                top = cropped_box.get('top', 0)
                width = cropped_box.get('width', 0)
                height = cropped_box.get('height', 0)

                # 座標を常にセッションに保存
                if width > 0 and height > 0:
                    st.session_state['update_crop_coords'] = (left, top, width, height)

            # セッションから座標を取得してプレビュー表示
            if 'update_crop_coords' in st.session_state:
                left, top, width, height = st.session_state['update_crop_coords']

                st.write("---")
                st.subheader("選択した領域のプレビュー")
                img_np = np.array(image)
                preview_crop = img_np[top:top+height, left:left+width]
                if preview_crop.size > 0:
                    st.image(preview_crop, caption=f"組立番号 {assembly_number}", width=400)

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("この領域を保存", type="primary", key="save_update_btn"):
                            print("[DEBUG] >>> 保存ボタンが押されました！")
                            print(f"[DEBUG] 座標: {st.session_state.get('update_crop_coords')}")
                            st.session_state['do_save_update'] = True
                            print("[DEBUG] do_save_update を True に設定しました")
                            st.rerun()

                    with col_cancel:
                        if st.button("キャンセル", key="cancel_update_btn"):
                            for key in ['assembly_page_image_loaded', 'upload_to_assembly_id',
                                        'upload_to_assembly_number', 'update_crop_coords', 'do_save_update']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.session_state['current_page'] = 'assembly_page_detail'
                            st.rerun()

        else:
            # ===== INSERTモード：新規レコード作成（複数領域選択） =====
            st.header("🔢 組立番号の追加")

            # 商品・ページ情報を表示
            col1, col2 = st.columns(2)
            with col1:
                st.metric("商品名", product['name'])
            with col2:
                st.metric("ページ", page_display)

            st.markdown("---")

            # 組立ページ画像を読み込み
            if 'assembly_page_image_loaded' not in st.session_state:
                image_url = add_cache_buster(page['image_url'])
                image = load_image_from_url(image_url)
                if image:
                    st.session_state['assembly_page_image_loaded'] = image
                else:
                    st.error("組立ページ画像を読み込めません。")
                    return

            image = st.session_state['assembly_page_image_loaded']

            # 選択済み領域を初期化
            if 'selected_regions' not in st.session_state:
                st.session_state['selected_regions'] = []

            # 自動検出済み画像を初期化
            if 'auto_detected_images' not in st.session_state:
                st.session_state['auto_detected_images'] = []

            st.subheader("組立番号領域の選択")

            # 自動検出ボタン
            col_auto, col_manual = st.columns(2)
            with col_auto:
                if st.button("🔍 自動検出", type="primary", help="画像から組立番号領域を自動検出します"):
                    with st.spinner("組立番号領域を検出中..."):
                        try:
                            detected_images = extract_assembly_images(image)
                            if detected_images:
                                st.session_state['auto_detected_images'] = detected_images
                                st.session_state['success_message'] = f"✅ {len(detected_images)}個の組立番号領域を検出しました！"
                            else:
                                st.session_state['error_message'] = "組立番号領域が検出できませんでした。手動で選択してください。"
                        except Exception as e:
                            st.session_state['error_message'] = f"自動検出中にエラーが発生しました: {e}"
                    st.rerun()
            with col_manual:
                st.write("または手動で選択 ↓")

            # 自動検出結果がある場合は表示
            if st.session_state.get('auto_detected_images'):
                st.write("---")
                st.subheader("🔍 自動検出結果")
                st.info("各領域に組立番号を入力してください。不要な領域は「除外」ボタンで除外できます。")

                detected_images = st.session_state['auto_detected_images']
                regions_to_save = []

                for i, detected_img in enumerate(detected_images):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.image(detected_img, caption=f"検出領域 #{i+1}", width=400)
                    with col2:
                        assembly_num = st.number_input(
                            f"組立番号 #{i+1}",
                            min_value=1,
                            step=1,
                            format="%d",
                            key=f"auto_assembly_num_{i}",
                            value=i+1
                        )
                        regions_to_save.append((assembly_num, detected_img))
                    with col3:
                        if st.button("除外", key=f"exclude_{i}"):
                            st.session_state['auto_detected_images'].pop(i)
                            st.rerun()

                st.write("---")
                col_save, col_clear = st.columns(2)
                with col_save:
                    if st.button("検出した組立番号を保存", type="primary", key="save_auto_detected"):
                        with st.spinner("保存中…"):
                            try:
                                saved_count = 0
                                for idx, (assembly_number, detected_img) in enumerate(regions_to_save):
                                    # PIL ImageをRGBに変換してアップロード
                                    if detected_img.mode != 'RGB':
                                        detected_img = detected_img.convert('RGB')

                                    assembly_img_id = str(uuid.uuid4())
                                    assembly_img_filename = f"assembly_images/{assembly_img_id}.webp"
                                    assembly_img_url = upload_image_to_supabase(detected_img, assembly_img_filename)

                                    insert_response = supabase.table("assembly_images").insert({
                                        "id": assembly_img_id,
                                        "page_id": page_id,
                                        "assembly_number": str(assembly_number),
                                        "display_order": idx + 1,
                                        "image_url": assembly_img_url
                                    }).execute()
                                    check_db_response(insert_response, f"INSERT assembly_images (id={assembly_img_id})")
                                    saved_count += 1

                                # セッションをクリア
                                for key in ['auto_detected_images', 'assembly_page_image_loaded']:
                                    if key in st.session_state:
                                        del st.session_state[key]

                                st.session_state['success_message'] = f"✅ {saved_count}個の組立番号を保存しました！"
                                st.session_state['current_page'] = 'assembly_page_detail'
                                st.rerun()

                            except Exception as e:
                                st.error(f"保存中にエラーが発生しました: {e}")
                with col_clear:
                    if st.button("検出結果をクリア", key="clear_auto_detected"):
                        st.session_state['auto_detected_images'] = []
                        st.rerun()

            st.write("---")
            st.subheader("手動選択モード")
            st.info("📌 緑の枠をドラッグして領域を選択してください。複数の領域を順番に選択できます。")

            # 選択済み領域を赤枠で表示した画像を作成
            img_with_regions = image.copy()
            img_np = np.array(img_with_regions)
            # RGBからBGRに変換（OpenCVはBGR）
            if len(img_np.shape) == 3 and img_np.shape[2] == 3:
                img_np_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            else:
                img_np_bgr = img_np

            for region_data in st.session_state['selected_regions']:
                assembly_number, bbox = region_data
                x, y, w, h = bbox
                cv2.rectangle(img_np_bgr, (x, y), (x+w, y+h), (0, 0, 255), 3)  # BGR: 赤
                cv2.putText(img_np_bgr, str(assembly_number), (x+5, y+30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

            # BGRからRGBに戻す
            if len(img_np_bgr.shape) == 3 and img_np_bgr.shape[2] == 3:
                img_np_rgb = cv2.cvtColor(img_np_bgr, cv2.COLOR_BGR2RGB)
            else:
                img_np_rgb = img_np_bgr
            display_image = Image.fromarray(img_np_rgb)

            # クロップ機能を表示
            cropped_img = st_cropper(
                display_image,
                realtime_update=True,
                box_color='#00FF00',
                aspect_ratio=None,
                return_type='box'
            )

            # クロップボックスの座標を取得
            if cropped_img is not None and isinstance(cropped_img, dict):
                left = cropped_img.get('left', 0)
                top = cropped_img.get('top', 0)
                width = cropped_img.get('width', 0)
                height = cropped_img.get('height', 0)

                if width > 0 and height > 0:
                    new_bbox = (left, top, width, height)
                    st.session_state['pending_bbox'] = new_bbox

                    # プレビュー表示
                    st.write("---")
                    st.subheader("選択した領域")
                    preview_crop = np.array(image)[top:top+height, left:left+width]
                    if preview_crop.size > 0:
                        st.image(preview_crop, caption="選択した領域のプレビュー", width=400)

                    # 組立番号入力
                    assembly_number = st.number_input(
                        "組立番号を入力してください",
                        min_value=1,
                        step=1,
                        format="%d",
                        key="assembly_number_input",
                        value=None
                    )

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("この領域を追加", type="primary"):
                            if assembly_number is not None and assembly_number > 0:
                                st.session_state['selected_regions'].append((str(int(assembly_number)), new_bbox))
                                if 'pending_bbox' in st.session_state:
                                    del st.session_state['pending_bbox']
                                st.session_state['success_message'] = f"組立番号 '{assembly_number}' の領域を追加しました！"
                                st.rerun()
                            else:
                                st.session_state['error_message'] = "組立番号を入力してください"
                                st.rerun()
                    with col_btn2:
                        if st.button("キャンセル"):
                            if 'pending_bbox' in st.session_state:
                                del st.session_state['pending_bbox']
                            st.rerun()

            # 選択済み領域の表示
            if st.session_state['selected_regions']:
                st.write("---")
                st.success(f"✅ 選択済み領域: {len(st.session_state['selected_regions'])}個")

                for i, region_data in enumerate(st.session_state['selected_regions']):
                    assembly_number, bbox = region_data
                    x, y, w, h = bbox

                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.write(f"**#{i+1}**")
                    with col2:
                        crop = np.array(image)[y:y+h, x:x+w]
                        st.image(crop, width=300)
                        st.write(f"組立番号: **{assembly_number}**")
                    with col3:
                        if st.button("削除", key=f"del_{i}"):
                            st.session_state['selected_regions'].pop(i)
                            st.rerun()

                # 保存ボタン
                st.write("---")
                if st.button("選択した組立番号を保存", type="primary"):
                    with st.spinner("保存中…"):
                        try:
                            saved_count = 0
                            img_np = np.array(image)

                            for idx, (assembly_number, bbox) in enumerate(st.session_state['selected_regions']):
                                x, y, w, h = bbox
                                crop = img_np[y:y+h, x:x+w]
                                crop_image = Image.fromarray(crop)

                                # 画像をアップロード
                                assembly_img_id = str(uuid.uuid4())
                                assembly_img_filename = f"assembly_images/{assembly_img_id}.webp"
                                assembly_img_url = upload_image_to_supabase(crop_image, assembly_img_filename)

                                # DBに保存
                                insert_response = supabase.table("assembly_images").insert({
                                    "id": assembly_img_id,
                                    "page_id": page_id,
                                    "assembly_number": str(assembly_number),
                                    "display_order": idx + 1,
                                    "image_url": assembly_img_url
                                }).execute()
                                check_db_response(insert_response, f"INSERT assembly_images (id={assembly_img_id})")
                                saved_count += 1

                            # セッションをクリアして組立ページ詳細に戻る
                            for key in ['selected_regions', 'pending_bbox', 'assembly_page_image_loaded']:
                                if key in st.session_state:
                                    del st.session_state[key]

                            st.session_state['success_message'] = f"✅ {saved_count}個の組立番号を保存しました！"
                            st.session_state['current_page'] = 'assembly_page_detail'
                            st.rerun()

                        except Exception as e:
                            st.error(f"保存中にエラーが発生しました: {e}")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

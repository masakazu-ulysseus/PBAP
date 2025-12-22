import streamlit as st
from utils.supabase_client import get_supabase_client, get_supabase_image_url, add_cache_buster, check_db_response, get_deletion_impact, delete_assembly_image, upload_image_to_supabase
from utils.image_processing import extract_assembly_images
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import uuid
from streamlit_cropper import st_cropper

def load_image_from_url(url: str):
    """URLから画像を読み込むヘルパー関数"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            return image
        else:
            return None
    except Exception:
        return None

def app():
    """組立ページ詳細ページを表示する。
    選択された組立ページの詳細情報と、そのページに紐づく組立番号一覧を表示する。
    """

    # ページIDの確認
    if 'selected_page_id' not in st.session_state or 'selected_product_id' not in st.session_state:
        st.error("組立ページが選択されていません。")
        return

    page_id = st.session_state['selected_page_id']
    product_id = st.session_state['selected_product_id']

    try:
        supabase = get_supabase_client()

        # 商品情報を取得して表示
        product_response = supabase.table("products").select("*").eq("id", product_id).execute()
        if product_response.data:
            product = product_response.data[0]

        # 組立ページ情報を取得
        page_response = supabase.table("assembly_pages").select("*").eq("id", page_id).execute()

        if not page_response.data:
            st.error("組立ページが見つかりませんでした。")
            return

        page = page_response.data[0]

        # 同じ商品の全ページを取得（ページ送り用）
        all_pages_response = supabase.table("assembly_pages").select("id, page_number").eq("product_id", product_id).order("page_number").execute()
        all_pages = all_pages_response.data if all_pages_response.data else []

        # 現在のページのインデックスを取得
        current_index = next((i for i, p in enumerate(all_pages) if p['id'] == page_id), -1)
        prev_page = all_pages[current_index - 1] if current_index > 0 else None
        next_page = all_pages[current_index + 1] if current_index < len(all_pages) - 1 else None

    except Exception as e:
        st.error(f"データの取得に失敗しました: {e}")
        return

    # ナビゲーションボタン
    col_back, col_prev, col_next = st.columns([2, 1, 1])
    with col_back:
        if st.button("← 商品詳細に戻る"):
            if 'selected_page_id' in st.session_state:
                del st.session_state['selected_page_id']
            # 組立番号関連のセッションもクリア
            for key in ['show_assembly_number_form', 'assembly_page_img_loaded', 'extracted_assembly_images']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['current_page'] = 'product_detail'
            st.rerun()
    with col_prev:
        if prev_page:
            prev_label = f"ページ {prev_page['page_number']}（表紙）" if prev_page['page_number'] == 0 else f"ページ {prev_page['page_number']}"
            if st.button("◀ 前", help=prev_label):
                st.session_state['selected_page_id'] = prev_page['id']
                # 組立番号関連のセッションをクリア
                for key in ['show_assembly_number_form', 'assembly_page_img_loaded', 'extracted_assembly_images']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        else:
            st.button("◀ 前", disabled=True)
    with col_next:
        if next_page:
            next_label = f"ページ {next_page['page_number']}（表紙）" if next_page['page_number'] == 0 else f"ページ {next_page['page_number']}"
            if st.button("次 ▶", help=next_label):
                st.session_state['selected_page_id'] = next_page['id']
                # 組立番号関連のセッションをクリア
                for key in ['show_assembly_number_form', 'assembly_page_img_loaded', 'extracted_assembly_images']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        else:
            st.button("次 ▶", disabled=True)

    # 成功メッセージがセッションにあれば表示
    if 'success_message' in st.session_state:
        st.success(st.session_state['success_message'])
        del st.session_state['success_message']

    # エラーメッセージがセッションにあれば表示
    if 'error_message' in st.session_state:
        st.error(st.session_state['error_message'])
        del st.session_state['error_message']

    try:
        page_display = f"ページ {page['page_number']}（表紙）" if page['page_number'] == 0 else f"ページ {page['page_number']}"

        st.header(f"📄 {page_display}")
        st.caption(f"商品: {product['name']}")

        # 組立ページ画像を表示（キャッシュ破棄付き）
        try:
            # DBに保存されているURLにタイムスタンプを追加してキャッシュ破棄
            display_url = add_cache_buster(page['image_url'])
            st.image(display_url, caption=f"{page_display}", width=600)
        except Exception as e:
            # 画像表示エラーの場合、代替URLを試す
            filename = page['image_url'].split('/')[-1]
            alternative_url = get_supabase_image_url(f"assembly_pages/{filename}")
            alternative_url = add_cache_buster(alternative_url)

            try:
                st.image(alternative_url, caption=f"{page_display}", width=600)
            except:
                st.error("画像を表示できません")
                if st.checkbox("デバッグ情報を表示", key="debug_page_image"):
                    st.code(f"元URL: {page['image_url']}\n代替URL: {alternative_url}\nエラー: {str(e)}")

        # 画像更新ボタン
        col_update, col_space, col_info = st.columns([2, 1, 2])
        with col_update:
            if st.button("🔄 画像を更新", key="update_page_image"):
                st.session_state['reupload_page_id'] = page_id
                st.session_state['current_page'] = 'assembly_page_reupload'
                st.rerun()
        with col_info:
            st.caption("現在の画像を新しいものに変更できます")

        st.markdown("---")

        # 組立番号一覧を取得
        assembly_response = supabase.table("assembly_images").select("*").eq("page_id", page_id).order("display_order").execute()

        # 各組立番号の部品数を取得
        parts_counts = {}
        if assembly_response.data:
            for assembly in assembly_response.data:
                parts_response = supabase.table("assembly_image_parts").select("id", count="exact").eq("assembly_image_id", assembly['id']).execute()
                parts_counts[assembly['id']] = parts_response.count if parts_response.count else 0

        st.subheader("🔢 組立番号一覧")

        # 組立番号がない場合：枠作成フォームを表示
        if not assembly_response.data:
            st.info("このページに組立番号がありません。まず組立番号の枠を作成してください。")

            with st.form("assembly_number_setup_form"):
                st.markdown("### 組立番号の枠を作成")

                col1, col2 = st.columns(2)
                with col1:
                    start_number = st.number_input(
                        "組立番号はいくつから始まりますか？",
                        min_value=1,
                        max_value=999,
                        value=1,
                        step=1,
                        help="最初の組立番号を入力してください"
                    )
                with col2:
                    assembly_count = st.number_input(
                        "この組立ページの組立番号はいくつありますか？",
                        min_value=1,
                        max_value=50,
                        value=1,
                        step=1,
                        help="このページに含まれる組立番号の数を入力してください"
                    )

                submitted = st.form_submit_button("組立番号の枠を作成", type="primary")

                if submitted:
                    try:
                        # 空のassembly_imagesレコードを作成
                        assembly_records = []
                        for i in range(assembly_count):
                            assembly_number = start_number + i
                            assembly_records.append({
                                "id": str(uuid.uuid4()),
                                "page_id": page_id,
                                "assembly_number": str(assembly_number),
                                "display_order": i + 1,
                                "image_url": None
                            })

                        if assembly_records:
                            insert_response = supabase.table("assembly_images").insert(assembly_records).execute()
                            check_db_response(insert_response, f"INSERT assembly_images (count={len(assembly_records)})")

                        # 自動検出をトリガー
                        st.session_state['trigger_assembly_auto_detect'] = True
                        st.session_state['success_message'] = f"✅ {assembly_count}個の組立番号枠を作成しました（{start_number}〜{start_number + assembly_count - 1}）"
                        st.rerun()
                    except Exception as e:
                        st.session_state['error_message'] = f"枠の作成に失敗しました: {e}"
                        st.rerun()
            return

        # 組立番号がある場合：一覧表示
        # 画像未登録のカウント
        assembly_df = pd.DataFrame(assembly_response.data)
        pending_count = sum(1 for _, a in assembly_df.iterrows() if not a['image_url'])

        # 組立ページ画像をセッションに読み込み（ページIDが変わった場合も再読み込み）
        current_loaded_page_id = st.session_state.get('assembly_page_img_page_id')
        need_reload = 'assembly_page_img_loaded' not in st.session_state or current_loaded_page_id != page_id

        if need_reload:
            page_image = load_image_from_url(add_cache_buster(page['image_url']))
            if page_image:
                st.session_state['assembly_page_img_loaded'] = page_image
                st.session_state['assembly_page_img_page_id'] = page_id
                # ページが変わったら検出結果もクリア
                if 'extracted_assembly_images' in st.session_state:
                    del st.session_state['extracted_assembly_images']
                st.info(f"✅ 新しいページ画像を読み込みました (page_id: {page_id[:8]}...)")

        # 枠作成直後の自動検出トリガー
        if st.session_state.get('trigger_assembly_auto_detect') and 'assembly_page_img_loaded' in st.session_state:
            with st.spinner("🔍 組立番号領域を自動検出中..."):
                try:
                    detected = extract_assembly_images(st.session_state['assembly_page_img_loaded'], return_coords=True)
                    if detected:
                        st.session_state['extracted_assembly_images'] = detected
                        st.session_state['success_message'] = f"✅ {len(detected)}個の組立番号領域を検出しました。下の一覧で画像を割り当ててください。"
                    else:
                        st.session_state['success_message'] = "組立番号領域を検出できませんでした。手動で画像を登録してください。"
                except Exception as e:
                    st.session_state['error_message'] = f"自動検出エラー: {e}"
            del st.session_state['trigger_assembly_auto_detect']
            st.rerun()

        if pending_count > 0:
            st.warning(f"⚠️ 画像未登録の組立番号が {pending_count} 件あります")
        else:
            st.success("✅ すべての組立番号に画像が登録されています")

        # 自動検出ボタンと組立番号追加ボタン
        col_auto_detect, col_add = st.columns(2)
        with col_auto_detect:
            if pending_count > 0:
                if st.button("🔍 組立番号領域を自動検出", type="primary"):
                    if 'assembly_page_img_loaded' in st.session_state:
                        with st.spinner("検出中..."):
                            try:
                                detected = extract_assembly_images(st.session_state['assembly_page_img_loaded'], return_coords=True)
                                if detected:
                                    st.session_state['extracted_assembly_images'] = detected
                                    st.session_state['success_message'] = f"✅ {len(detected)}個の組立番号領域を検出しました。下の一覧で画像を割り当ててください。"
                                else:
                                    st.session_state['error_message'] = "組立番号領域を検出できませんでした。"
                            except Exception as e:
                                st.session_state['error_message'] = f"自動検出エラー: {e}"
                        st.rerun()
                    else:
                        st.error("組立ページ画像を読み込めません")
        with col_add:
            if st.button("➕ 組立番号を追加", type="secondary"):
                st.session_state['show_assembly_number_form'] = True
                st.rerun()

        # 自動検出結果のプレビュー
        if 'extracted_assembly_images' in st.session_state and st.session_state['extracted_assembly_images']:
            st.write("---")
            st.subheader("🔍 自動検出結果")
            st.info("下の組立番号枠の「🔍 自動検出から選択」ボタンで、これらの画像を割り当てできます")

            extracted_images = st.session_state['extracted_assembly_images']
            cols = st.columns(min(4, len(extracted_images)))
            for j, item in enumerate(extracted_images):
                with cols[j % 4]:
                    # 新形式（dict）と旧形式（PIL Image）の両方に対応
                    if isinstance(item, dict):
                        st.image(item['image'], caption=f"検出 {j+1}", width=200)
                        st.caption(f"({item['region_x']}, {item['region_y']}) {item['region_width']}×{item['region_height']}")
                    else:
                        st.image(item, caption=f"検出 {j+1}", width=200)

            if st.button("検出結果をクリア"):
                del st.session_state['extracted_assembly_images']
                st.rerun()

        # 追加フォームの表示
        if 'show_assembly_number_form' in st.session_state and st.session_state['show_assembly_number_form']:
            with st.form("add_assembly_number_form"):
                st.markdown("### 組立番号を追加")

                # 既存の最大番号を取得
                existing_numbers = [int(a['assembly_number']) for a in assembly_response.data if a['assembly_number'].isdigit()]
                max_existing = max(existing_numbers) if existing_numbers else 0

                col1, col2 = st.columns(2)
                with col1:
                    add_start = st.number_input(
                        "組立番号はいくつから始まりますか？",
                        min_value=1,
                        max_value=999,
                        value=max_existing + 1,
                        step=1
                    )
                with col2:
                    add_count = st.number_input(
                        "追加する組立番号はいくつありますか？",
                        min_value=1,
                        max_value=50,
                        value=1,
                        step=1
                    )

                col_submit, col_cancel = st.columns(2)
                with col_submit:
                    submitted = st.form_submit_button("追加", type="primary")
                with col_cancel:
                    cancelled = st.form_submit_button("キャンセル")

                if submitted:
                    try:
                        # 既存の最大display_orderを取得
                        max_order = max(a['display_order'] for a in assembly_response.data)

                        assembly_images = []
                        for i in range(add_count):
                            assembly_number = add_start + i
                            assembly_images.append({
                                "id": str(uuid.uuid4()),
                                "page_id": page_id,
                                "assembly_number": str(assembly_number),
                                "display_order": max_order + i + 1,
                                "image_url": None
                            })

                        if assembly_images:
                            insert_response = supabase.table("assembly_images").insert(assembly_images).execute()
                            check_db_response(insert_response, f"INSERT assembly_images (count={len(assembly_images)})")

                        del st.session_state['show_assembly_number_form']
                        st.session_state['success_message'] = f"✅ {add_count}個の組立番号を追加しました"
                        st.rerun()
                    except Exception as e:
                        st.session_state['error_message'] = f"追加に失敗しました: {e}"
                        st.rerun()

                if cancelled:
                    del st.session_state['show_assembly_number_form']
                    st.rerun()

        # 組立番号一覧を表示
        st.write("---")

        for i, assembly in assembly_df.iterrows():
            has_image = assembly['image_url'] is not None and assembly['image_url'] != ''
            parts_count = parts_counts.get(assembly['id'], 0)

            # 領域座標の有無を確認
            has_region = (
                assembly.get('region_x') is not None and
                assembly.get('region_y') is not None and
                assembly.get('region_width') is not None and
                assembly.get('region_height') is not None
            )

            col1, col2, col3, col4 = st.columns([1.2, 2.8, 1.5, 2])
            with col1:
                if has_image:
                    st.write(f"✅ **組立番号 {assembly['assembly_number']}**")
                else:
                    st.write(f"📷 **組立番号 {assembly['assembly_number']}**")
            with col2:
                if has_image:
                    # 画像のサムネイル表示
                    try:
                        image_url = add_cache_buster(assembly['image_url'])
                        st.image(image_url, width=200)
                    except:
                        st.write("画像を表示できません")
                else:
                    st.info("📷 画像未登録")
            with col3:
                # 配下情報
                st.write(f"🧩 部品: **{parts_count}**件")
                # 領域座標情報
                if has_region:
                    st.caption(f"📍 領域: ({assembly['region_x']}, {assembly['region_y']}) {assembly['region_width']}×{assembly['region_height']}")
                else:
                    st.caption("📍 領域: 未設定")
            with col4:
                if has_image:
                    col4a, col4b = st.columns(2)
                    with col4a:
                        if st.button("詳細を見る", key=f"assembly_{assembly['id']}"):
                            st.session_state['selected_assembly_id'] = assembly['id']
                            st.session_state['current_page'] = 'assembly_number_detail'
                            st.rerun()
                    with col4b:
                        if st.button("🗑️ 削除", key=f"delete_assembly_{assembly['id']}", type="secondary"):
                            st.session_state['confirm_delete_assembly_id'] = assembly['id']
                            st.session_state['confirm_delete_assembly_number'] = assembly['assembly_number']
                            st.rerun()
                else:
                    # 画像未登録スロットの選択モード管理
                    assign_mode_key = f'assembly_assign_mode_{assembly["id"]}'

                    if assign_mode_key not in st.session_state:
                        # 通常モード：ボタン表示
                        col_btn1, col_btn2, col_btn3 = st.columns(3)

                        with col_btn1:
                            if 'extracted_assembly_images' in st.session_state and st.session_state['extracted_assembly_images']:
                                if st.button("🔍 自動検出から選択", key=f"auto_assembly_{assembly['id']}"):
                                    st.session_state[assign_mode_key] = 'auto'
                                    st.rerun()

                        with col_btn2:
                            if st.button("✂️ 手動で切り出し", key=f"manual_assembly_{assembly['id']}"):
                                st.session_state[assign_mode_key] = 'manual'
                                st.rerun()

                        with col_btn3:
                            if st.button("🗑️ 削除", key=f"delete_assembly_empty_{assembly['id']}", type="secondary"):
                                st.session_state['confirm_delete_assembly_id'] = assembly['id']
                                st.session_state['confirm_delete_assembly_number'] = assembly['assembly_number']
                                st.rerun()

                    elif st.session_state[assign_mode_key] == 'auto':
                        # 自動検出から選択モード - col4内に表示
                        st.info("下で画像を選択")

                    elif st.session_state[assign_mode_key] == 'manual':
                        # 手動切り出しモード - col4内にはメッセージのみ
                        st.info("下で領域を選択")

            # カラムの外で選択モードUIを表示（フル幅）
            assign_mode_key = f'assembly_assign_mode_{assembly["id"]}'

            if assign_mode_key in st.session_state and st.session_state[assign_mode_key] == 'auto':
                # 自動検出から選択モード（フル幅表示）
                st.markdown(f"#### 📷 組立番号 {assembly['assembly_number']} - 自動検出から選択")
                st.info("割り当てる画像を選択してください")
                extracted = st.session_state.get('extracted_assembly_images', [])

                cols_select = st.columns(min(4, len(extracted)) if extracted else 1)
                for j, ext_item in enumerate(extracted):
                    with cols_select[j % 4]:
                        # 新形式（dict）と旧形式（PIL Image）の両方に対応
                        if isinstance(ext_item, dict):
                            ext_img = ext_item['image']
                            ext_coords = {
                                'region_x': ext_item['region_x'],
                                'region_y': ext_item['region_y'],
                                'region_width': ext_item['region_width'],
                                'region_height': ext_item['region_height']
                            }
                            st.image(ext_img, width=150)
                            st.caption(f"({ext_coords['region_x']}, {ext_coords['region_y']})")
                        else:
                            ext_img = ext_item
                            ext_coords = None
                            st.image(ext_img, width=150)

                        if st.button("選択", key=f"select_assembly_{assembly['id']}_{j}"):
                            # この画像を組立番号に割り当て
                            try:
                                with st.spinner("保存中…"):
                                    assembly_filename = f"assembly_images/{assembly['id']}.webp"
                                    assembly_url = upload_image_to_supabase(ext_img, assembly_filename)

                                    # assembly_imagesテーブルを更新（座標情報も含める）
                                    update_data = {"image_url": assembly_url}
                                    if ext_coords:
                                        update_data.update(ext_coords)

                                    update_response = supabase.table("assembly_images").update(update_data).eq("id", assembly['id']).execute()
                                    check_db_response(update_response, f"UPDATE assembly_images (id={assembly['id']})")

                                    # 使用した抽出画像をリストから削除
                                    st.session_state['extracted_assembly_images'].pop(j)
                                    if not st.session_state['extracted_assembly_images']:
                                        del st.session_state['extracted_assembly_images']

                                    del st.session_state[assign_mode_key]
                                    st.session_state['success_message'] = f"✅ 組立番号 {assembly['assembly_number']} に画像を割り当てました"
                                    st.rerun()
                            except Exception as e:
                                st.error(f"割り当てエラー: {e}")

                if st.button("キャンセル", key=f"cancel_auto_assembly_{assembly['id']}"):
                    del st.session_state[assign_mode_key]
                    st.rerun()

            elif assign_mode_key in st.session_state and st.session_state[assign_mode_key] == 'manual':
                # 手動切り出しモード（フル幅表示）
                st.markdown(f"#### ✂️ 組立番号 {assembly['assembly_number']} - 手動で切り出し")

                if 'assembly_page_img_loaded' in st.session_state:
                    st.info("📌 緑の枠で領域を調整 → **ダブルクリックで確定** → 「💾 保存」")

                    # 画像クロッパー（realtime_update=False: ダブルクリックで確定）
                    # return_type='both' で画像と座標の両方を取得
                    page_img = st.session_state['assembly_page_img_loaded']

                    cropped_img, crop_rect = st_cropper(
                        page_img,
                        realtime_update=False,
                        box_color='#00FF00',
                        aspect_ratio=None,
                        return_type='both',
                        key=f"manual_cropper_assembly_{assembly['id']}"
                    )

                    # 座標をセッションに保存（保存時に使用）
                    crop_coords_key = f"manual_crop_coords_assembly_{assembly['id']}"
                    st.session_state[crop_coords_key] = {
                        'x': crop_rect['left'],
                        'y': crop_rect['top'],
                        'width': crop_rect['width'],
                        'height': crop_rect['height']
                    }

                    # 座標表示
                    st.caption(f"📍 選択領域: ({crop_rect['left']}, {crop_rect['top']}) {crop_rect['width']}×{crop_rect['height']}")

                    # プレビュー表示
                    st.markdown("**プレビュー（ダブルクリック後に更新）:**")
                    preview_img = cropped_img.copy()
                    preview_img.thumbnail((300, 300))
                    st.image(preview_img)

                    st.markdown("---")

                    # ボタン行
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 保存", key=f"save_manual_assembly_{assembly['id']}", type="primary"):
                            if cropped_img is not None:
                                try:
                                    with st.spinner("保存中…"):
                                        assembly_filename = f"assembly_images/{assembly['id']}.webp"
                                        assembly_url = upload_image_to_supabase(cropped_img, assembly_filename)

                                        # クロッパーから取得した正確な座標を使用
                                        coords = st.session_state.get(crop_coords_key, {})
                                        update_response = supabase.table("assembly_images").update({
                                            "image_url": assembly_url,
                                            "region_x": coords.get('x', 0),
                                            "region_y": coords.get('y', 0),
                                            "region_width": coords.get('width', 0),
                                            "region_height": coords.get('height', 0)
                                        }).eq("id", assembly['id']).execute()
                                        check_db_response(update_response, f"UPDATE assembly_images (id={assembly['id']})")

                                        del st.session_state[assign_mode_key]
                                        if crop_coords_key in st.session_state:
                                            del st.session_state[crop_coords_key]
                                        st.session_state['success_message'] = f"✅ 組立番号 {assembly['assembly_number']} に画像を保存しました"
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"保存エラー: {e}")
                            else:
                                st.error("画像を選択してください")
                    with col_cancel:
                        if st.button("キャンセル", key=f"cancel_manual_assembly_{assembly['id']}"):
                            del st.session_state[assign_mode_key]
                            st.rerun()
                else:
                    st.error("組立ページ画像を読み込めません")
                    if st.button("キャンセル", key=f"cancel_manual_no_img_{assembly['id']}"):
                        del st.session_state[assign_mode_key]
                        st.rerun()

            # 削除確認ダイアログ
            if st.session_state.get('confirm_delete_assembly_id') == assembly['id']:
                st.warning("⚠️ **削除確認**")
                impact = get_deletion_impact("assembly_image", assembly['id'])

                st.markdown(f"""
**この組立番号を削除すると、以下のデータが完全に削除されます：**
- 🔢 組立番号画像: 1枚
- 🧩 部品: **{impact['parts']}件**
- 🖼️ 画像ファイル（Storage）: **{impact['images']}枚**

**この操作は取り消せません。本当に削除しますか？**
                """)

                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("🗑️ 削除を実行", key=f"confirm_del_assembly_{assembly['id']}", type="primary"):
                        with st.spinner("削除中..."):
                            result = delete_assembly_image(assembly['id'])
                            if result['success']:
                                del st.session_state['confirm_delete_assembly_id']
                                del st.session_state['confirm_delete_assembly_number']
                                st.session_state['success_message'] = f"✅ 組立番号 {assembly['assembly_number']} を削除しました（部品: {result['deleted_parts']}件、画像: {result['deleted_images']}枚）"
                                st.rerun()
                            else:
                                st.error(f"削除に失敗しました: {result.get('error', '不明なエラー')}")
                with col_cancel:
                    if st.button("キャンセル", key=f"cancel_del_assembly_{assembly['id']}"):
                        del st.session_state['confirm_delete_assembly_id']
                        del st.session_state['confirm_delete_assembly_number']
                        st.rerun()

            st.write("---")

    except Exception as e:
        st.error(f"データの取得に失敗しました: {e}")

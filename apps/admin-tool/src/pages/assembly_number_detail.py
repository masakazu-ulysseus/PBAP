import streamlit as st
from PIL import Image
from utils.supabase_client import get_supabase_client, upload_image_to_supabase, add_cache_buster, check_db_response, delete_part
from utils import image_processing
import uuid
import requests
from io import BytesIO
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
    except Exception as e:
        st.write(f"画像取得エラー: {e}")
        return None




def app():
    """組立番号詳細ページを表示する。
    選択された組立番号の画像と、そこから抽出されたパーツ一覧を表示する。
    """

    # 組立番号IDの確認（ナビゲーション用に先に確認）
    if 'selected_assembly_id' not in st.session_state:
        st.error("組立番号が選択されていません。")
        return

    assembly_id = st.session_state['selected_assembly_id']

    try:
        supabase = get_supabase_client()

        # 組立番号情報を取得
        assembly_response = supabase.table("assembly_images").select("*").eq("id", assembly_id).execute()
        if not assembly_response.data:
            st.error("組立番号が見つかりませんでした。")
            return

        assembly = assembly_response.data[0]
        page_id = assembly['page_id']

        # 同じページ内の全組立番号を取得（ナビゲーション用）
        all_assemblies_response = supabase.table("assembly_images").select("id, assembly_number").eq("page_id", page_id).order("assembly_number").execute()
        all_assemblies = all_assemblies_response.data if all_assemblies_response.data else []

        # 現在の組立番号のインデックスと前後を特定
        current_index = None
        for idx, a in enumerate(all_assemblies):
            if a['id'] == assembly_id:
                current_index = idx
                break

        prev_assembly = all_assemblies[current_index - 1] if current_index and current_index > 0 else None
        next_assembly = all_assemblies[current_index + 1] if current_index is not None and current_index < len(all_assemblies) - 1 else None

        # ナビゲーションボタン
        col_back, col_prev, col_next = st.columns([2, 1, 1])
        with col_back:
            if st.button("← 組立ページ詳細に戻る"):
                if 'selected_assembly_id' in st.session_state:
                    del st.session_state['selected_assembly_id']
                # パーツ関連のセッションもクリア
                parts_keys = [k for k in list(st.session_state.keys()) if k.startswith('parts_') or k.startswith('assembly_img_') or k.startswith('extracted_') or k.startswith('assign_')]
                for key in parts_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state['current_page'] = 'assembly_page_detail'
                st.rerun()
        with col_prev:
            if prev_assembly:
                prev_label = f"組立番号 {prev_assembly['assembly_number']}"
                if st.button("◀ 前", help=prev_label):
                    # パーツ関連のセッションをクリア
                    parts_keys = [k for k in list(st.session_state.keys()) if k.startswith('parts_') or k.startswith('assembly_img_') or k.startswith('extracted_') or k.startswith('assign_')]
                    for key in parts_keys:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state['selected_assembly_id'] = prev_assembly['id']
                    st.rerun()
            else:
                st.button("◀ 前", disabled=True)
        with col_next:
            if next_assembly:
                next_label = f"組立番号 {next_assembly['assembly_number']}"
                if st.button("次 ▶", help=next_label):
                    # パーツ関連のセッションをクリア
                    parts_keys = [k for k in list(st.session_state.keys()) if k.startswith('parts_') or k.startswith('assembly_img_') or k.startswith('extracted_') or k.startswith('assign_')]
                    for key in parts_keys:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state['selected_assembly_id'] = next_assembly['id']
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

        st.header(f"🔢 組立番号 {assembly['assembly_number']}")

        # 組立番号画像を表示
        st.subheader("組立番号画像")
        if assembly['image_url']:
            try:
                image_url = add_cache_buster(assembly['image_url'])
                assembly_image = load_image_from_url(image_url)
                if assembly_image:
                    st.image(assembly_image, caption=f"組立番号 {assembly['assembly_number']}", width=500)
                    st.session_state['assembly_img_loaded'] = assembly_image
                else:
                    st.error("画像を読み込めません")
            except Exception as e:
                st.error(f"画像表示エラー: {e}")
        else:
            st.warning("組立番号画像が登録されていません")

        # 画像更新ボタン
        col_update, col_space, col_info = st.columns([2, 1, 2])
        with col_update:
            if st.button("🔄 画像を更新", key="update_assembly_image"):
                st.session_state['upload_to_assembly_id'] = assembly_id
                st.session_state['upload_to_assembly_number'] = assembly['assembly_number']
                st.session_state['current_page'] = 'assembly_number_add'
                st.rerun()
        with col_info:
            st.caption("組立ページ画像から再選択できます")

        st.markdown("---")

        # パーツ一覧を取得
        parts_response = supabase.table("assembly_image_parts").select(
            "*, parts(*)"
        ).eq("assembly_image_id", assembly_id).order("display_order").execute()

        st.subheader("🧩 部品一覧")

        # ========================================
        # 部品枠が存在しない場合：自動検出で枠を作成
        # ========================================
        if not parts_response.data:
            st.info("この組立番号には部品が登録されていません。")

            # 部品枠の自動作成
            st.markdown("### 部品枠の作成")

            col_auto, col_manual = st.columns(2)

            with col_auto:
                if st.button("🔍 部品を自動検出して枠を作成", type="primary"):
                    if 'assembly_img_loaded' in st.session_state:
                        with st.spinner("部品を検出中…"):
                            # 部品を自動検出
                            detected_parts = image_processing.extract_parts(st.session_state['assembly_img_loaded'])
                            parts_count = len(detected_parts)

                            if parts_count == 0:
                                st.error("部品を検出できませんでした。手動で部品数を入力してください。")
                            else:
                                try:
                                    # 検出された数だけ部品枠を作成
                                    for i in range(parts_count):
                                        slot_id = str(uuid.uuid4())
                                        insert_response = supabase.table("assembly_image_parts").insert({
                                            "id": slot_id,
                                            "assembly_image_id": assembly_id,
                                            "part_id": None,
                                            "quantity": 1,
                                            "display_order": i + 1
                                        }).execute()
                                        check_db_response(insert_response, f"INSERT assembly_image_parts (slot {i+1})")

                                    # 抽出結果をセッションに保存
                                    st.session_state['extracted_parts'] = detected_parts
                                    st.session_state['success_message'] = f"✅ {parts_count}個の部品を検出し、部品枠を作成しました！下の一覧で部品を割り当ててください。"
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"部品枠の作成に失敗しました: {e}")
                    else:
                        st.error("組立番号画像が読み込まれていません")

            with col_manual:
                if st.button("📝 手動で部品数を入力"):
                    st.session_state['show_manual_input'] = True
                    st.rerun()

            # 手動入力フォーム（ボタンを押した場合のみ表示）
            if st.session_state.get('show_manual_input'):
                st.markdown("---")
                with st.form("create_parts_slots_manual"):
                    parts_count = st.number_input(
                        "部品数を入力してください",
                        min_value=1,
                        max_value=50,
                        value=1,
                        step=1,
                        help="部品の数を入力してください（後から追加・削除も可能です）"
                    )

                    col_create, col_cancel = st.columns(2)
                    with col_create:
                        submitted = st.form_submit_button("部品枠を作成", type="primary")
                    with col_cancel:
                        cancelled = st.form_submit_button("キャンセル")

                    if submitted:
                        try:
                            # 空の部品枠を作成
                            for i in range(parts_count):
                                slot_id = str(uuid.uuid4())
                                insert_response = supabase.table("assembly_image_parts").insert({
                                    "id": slot_id,
                                    "assembly_image_id": assembly_id,
                                    "part_id": None,
                                    "quantity": 1,
                                    "display_order": i + 1
                                }).execute()
                                check_db_response(insert_response, f"INSERT assembly_image_parts (slot {i+1})")

                            # 自動抽出を実行するフラグを設定
                            st.session_state['trigger_auto_extract'] = True
                            st.session_state['slots_created_count'] = parts_count
                            if 'show_manual_input' in st.session_state:
                                del st.session_state['show_manual_input']
                            st.rerun()
                        except Exception as e:
                            st.error(f"部品枠の作成に失敗しました: {e}")

                    if cancelled:
                        if 'show_manual_input' in st.session_state:
                            del st.session_state['show_manual_input']
                        st.rerun()

        # ========================================
        # 部品枠が存在する場合：一覧表示と画像割当
        # ========================================
        else:
            # 部品枠作成直後の自動抽出トリガー
            if st.session_state.get('trigger_auto_extract') and 'assembly_img_loaded' in st.session_state:
                slots_count = st.session_state.get('slots_created_count', 0)
                with st.spinner("パーツを自動抽出中…"):
                    parts = image_processing.extract_parts(st.session_state['assembly_img_loaded'])
                    st.session_state['extracted_parts'] = parts
                    st.session_state['success_message'] = f"✅ {slots_count}個の部品枠を作成し、{len(parts)}個のパーツを自動抽出しました！"
                del st.session_state['trigger_auto_extract']
                if 'slots_created_count' in st.session_state:
                    del st.session_state['slots_created_count']
                st.rerun()

            # 自動抽出ボタン
            col_extract, col_add_slot = st.columns(2)
            with col_extract:
                if st.button("🔍 パーツを自動抽出", type="primary"):
                    if 'assembly_img_loaded' in st.session_state:
                        with st.spinner("パーツを抽出中…"):
                            parts = image_processing.extract_parts(st.session_state['assembly_img_loaded'])
                            st.session_state['extracted_parts'] = parts
                            st.session_state['success_message'] = f"✅ {len(parts)}個のパーツを検出しました。下の部品枠に割り当ててください。"
                            st.rerun()
                    else:
                        st.error("組立番号画像が読み込まれていません")

            with col_add_slot:
                if st.button("➕ 部品枠を追加"):
                    try:
                        # 現在の最大display_orderを取得
                        max_order = max([p.get('display_order', 0) or 0 for p in parts_response.data])
                        slot_id = str(uuid.uuid4())
                        insert_response = supabase.table("assembly_image_parts").insert({
                            "id": slot_id,
                            "assembly_image_id": assembly_id,
                            "part_id": None,
                            "quantity": 1,
                            "display_order": max_order + 1
                        }).execute()
                        check_db_response(insert_response, "INSERT assembly_image_parts (new slot)")
                        st.session_state['success_message'] = f"✅ 部品枠 {max_order + 1} を追加しました"
                        st.rerun()
                    except Exception as e:
                        st.error(f"部品枠の追加に失敗しました: {e}")

            # 自動抽出結果のプレビュー
            if 'extracted_parts' in st.session_state and st.session_state['extracted_parts']:
                st.write("---")
                st.subheader("🔍 自動抽出結果")
                st.info("下の部品枠の「自動抽出から選択」ボタンで、これらの画像を割り当てできます")

                cols = st.columns(min(4, len(st.session_state['extracted_parts'])))
                for j, part_img in enumerate(st.session_state['extracted_parts']):
                    with cols[j % 4]:
                        st.image(part_img, caption=f"抽出 {j+1}", width=180)

                if st.button("抽出結果をクリア"):
                    del st.session_state['extracted_parts']
                    st.rerun()

            # 部品枠一覧
            st.write("---")
            st.markdown(f"### 登録済み部品枠（{len(parts_response.data)}個）")

            for i, part_data in enumerate(parts_response.data):
                part = part_data.get('parts')  # リンクされたpartsレコード
                slot_id = part_data['id']
                display_order = part_data.get('display_order', i + 1) or (i + 1)

                with st.container():
                    st.markdown(f"#### 部品 {display_order}")

                    col_img, col_actions = st.columns([2, 3])

                    with col_img:
                        if part and part.get('parts_url'):
                            # 画像が割り当て済み
                            try:
                                part_url = add_cache_buster(part['parts_url'])
                                st.image(part_url, caption=part.get('name', f'部品 {display_order}'), width=150)
                            except:
                                st.warning("画像読み込みエラー")
                        else:
                            # 画像未割当
                            st.warning("📷 画像未割当")

                    with col_actions:
                        # 割当モードの確認
                        assign_mode_key = f'assign_mode_{slot_id}'

                        if assign_mode_key not in st.session_state:
                            # 通常モード：ボタン表示
                            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

                            with col_btn1:
                                if 'extracted_parts' in st.session_state and st.session_state['extracted_parts']:
                                    if st.button("🔍 自動抽出から選択", key=f"auto_{slot_id}"):
                                        st.session_state[assign_mode_key] = 'auto'
                                        st.rerun()

                            with col_btn2:
                                if st.button("✂️ 手動で切り出し", key=f"manual_{slot_id}"):
                                    st.session_state[assign_mode_key] = 'manual'
                                    st.rerun()

                            with col_btn3:
                                # 編集ボタン（画像が登録済みの場合のみ有効）
                                if part and part.get('parts_url'):
                                    if st.button("✏️ 編集", key=f"edit_{slot_id}"):
                                        # 編集ページに遷移するための情報をセッションに保存
                                        st.session_state['edit_part_info'] = {
                                            'part_id': part['id'],
                                            'part_url': part['parts_url'],
                                            'part_name': part.get('name', f'部品 {display_order}'),
                                            'slot_id': slot_id,
                                            'display_order': display_order,
                                            'assembly_id': assembly_id
                                        }
                                        st.session_state['current_page'] = 'part_edit'
                                        st.rerun()
                                else:
                                    st.button("✏️ 編集", key=f"edit_{slot_id}", disabled=True)

                            with col_btn4:
                                if st.button("🗑️ 枠を削除", key=f"delete_slot_{slot_id}"):
                                    st.session_state[f'confirm_delete_part_{slot_id}'] = True
                                    st.rerun()

                            # 部品削除確認ダイアログ
                            if st.session_state.get(f'confirm_delete_part_{slot_id}'):
                                st.warning("⚠️ **削除確認**")
                                if part and part.get('parts_url'):
                                    st.markdown("""
**この部品枠を削除すると、以下のデータが完全に削除されます：**
- 🧩 部品レコード: 1件
- 🖼️ 部品画像（Storage）: 1枚

**この操作は取り消せません。本当に削除しますか？**
                                    """)
                                else:
                                    st.markdown("**この空の部品枠を削除しますか？**")

                                col_confirm, col_cancel = st.columns(2)
                                with col_confirm:
                                    if st.button("🗑️ 削除を実行", key=f"confirm_del_part_{slot_id}", type="primary"):
                                        try:
                                            # partsレコードも削除（存在する場合）
                                            deleted_images = 0
                                            if part:
                                                result = delete_part(part['id'])
                                                deleted_images = result.get('deleted_images', 0)
                                            # assembly_image_partsから削除
                                            delete_link_response = supabase.table("assembly_image_parts").delete().eq("id", slot_id).execute()
                                            check_db_response(delete_link_response, f"DELETE assembly_image_parts (id={slot_id})")
                                            del st.session_state[f'confirm_delete_part_{slot_id}']
                                            st.session_state['success_message'] = f"✅ 部品枠 {display_order} を削除しました" + (f"（画像: {deleted_images}枚）" if deleted_images > 0 else "")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"削除エラー: {e}")
                                with col_cancel:
                                    if st.button("キャンセル", key=f"cancel_del_part_{slot_id}"):
                                        del st.session_state[f'confirm_delete_part_{slot_id}']
                                        st.rerun()

                        elif st.session_state[assign_mode_key] == 'auto':
                            # 自動抽出から選択モード
                            st.info("割り当てる画像を選択してください")
                            extracted = st.session_state.get('extracted_parts', [])

                            cols_select = st.columns(min(4, len(extracted)) if extracted else 1)
                            for j, ext_img in enumerate(extracted):
                                with cols_select[j % 4]:
                                    st.image(ext_img, width=150)
                                    if st.button("選択", key=f"select_{slot_id}_{j}"):
                                        # この画像を割り当て
                                        try:
                                            with st.spinner("保存中…"):
                                                part_id = str(uuid.uuid4())
                                                part_filename = f"parts/{part_id}.webp"
                                                part_url = upload_image_to_supabase(ext_img, part_filename)

                                                # partsテーブルに保存
                                                parts_insert = supabase.table("parts").insert({
                                                    "id": part_id,
                                                    "parts_url": part_url,
                                                    "name": f"部品 {display_order}",
                                                    "color": "不明",
                                                    "size": "不明"
                                                }).execute()
                                                check_db_response(parts_insert, f"INSERT parts (id={part_id})")

                                                # 既存のpart_idを保存（後で削除するため）
                                                old_part_id = part['id'] if part else None

                                                # assembly_image_partsを更新（先に新しいpart_idで更新）
                                                update_response = supabase.table("assembly_image_parts").update({
                                                    "part_id": part_id
                                                }).eq("id", slot_id).execute()
                                                check_db_response(update_response, f"UPDATE assembly_image_parts (id={slot_id})")

                                                # 既存のpartsがあれば削除（更新後に削除）
                                                if old_part_id:
                                                    delete_old = supabase.table("parts").delete().eq("id", old_part_id).execute()
                                                    check_db_response(delete_old, f"DELETE old parts (id={old_part_id})")

                                                # 使用した抽出画像をリストから削除
                                                st.session_state['extracted_parts'].pop(j)
                                                if not st.session_state['extracted_parts']:
                                                    del st.session_state['extracted_parts']

                                                del st.session_state[assign_mode_key]
                                                st.session_state['success_message'] = f"✅ 部品 {display_order} に画像を割り当てました"
                                                st.rerun()
                                        except Exception as e:
                                            st.error(f"割り当てエラー: {e}")

                            if st.button("キャンセル", key=f"cancel_auto_{slot_id}"):
                                del st.session_state[assign_mode_key]
                                st.rerun()

                        elif st.session_state[assign_mode_key] == 'manual':
                            # 手動切り出しモード（streamlit-cropper使用）
                            if 'assembly_img_loaded' in st.session_state:
                                base_image = st.session_state['assembly_img_loaded']

                                st.info("📌 緑の枠で領域を調整 → **ダブルクリックで確定** → 「💾 保存」")

                                # 画像クロッパー（realtime_update=False: ダブルクリックで確定）
                                cropped_img = st_cropper(
                                    base_image,
                                    realtime_update=False,
                                    box_color='#00FF00',
                                    aspect_ratio=None,
                                    key=f"manual_cropper_part_{slot_id}"
                                )

                                # プレビュー表示
                                st.markdown("**プレビュー（ダブルクリック後に更新）:**")
                                preview_img = cropped_img.copy()
                                preview_img.thumbnail((200, 200))
                                st.image(preview_img)

                                st.markdown("---")

                                # ボタン行
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    if st.button("💾 保存", key=f"save_manual_{slot_id}", type="primary"):
                                        if cropped_img is not None:
                                            try:
                                                with st.spinner("保存中…"):
                                                    # 透明背景付きで保存（RGBAモードに変換）
                                                    if cropped_img.mode != 'RGBA':
                                                        part_img = cropped_img.convert('RGBA')
                                                    else:
                                                        part_img = cropped_img

                                                    part_id = str(uuid.uuid4())
                                                    part_filename = f"parts/{part_id}.webp"
                                                    part_url = upload_image_to_supabase(part_img, part_filename)

                                                    # partsテーブルに保存
                                                    parts_insert = supabase.table("parts").insert({
                                                        "id": part_id,
                                                        "parts_url": part_url,
                                                        "name": f"部品 {display_order}",
                                                        "color": "不明",
                                                        "size": "不明"
                                                    }).execute()
                                                    check_db_response(parts_insert, f"INSERT parts (id={part_id})")

                                                    # 既存のpart_idを保存
                                                    old_part_id = part['id'] if part else None

                                                    # assembly_image_partsを更新
                                                    update_response = supabase.table("assembly_image_parts").update({
                                                        "part_id": part_id
                                                    }).eq("id", slot_id).execute()
                                                    check_db_response(update_response, f"UPDATE assembly_image_parts (id={slot_id})")

                                                    # 既存のpartsがあれば削除
                                                    if old_part_id:
                                                        delete_old = supabase.table("parts").delete().eq("id", old_part_id).execute()
                                                        check_db_response(delete_old, f"DELETE old parts (id={old_part_id})")

                                                    # クリーンアップ
                                                    del st.session_state[assign_mode_key]
                                                    st.session_state['success_message'] = f"✅ 部品 {display_order} に画像を割り当てました"
                                                    st.rerun()
                                            except Exception as e:
                                                st.error(f"保存エラー: {e}")
                                with col_cancel:
                                    if st.button("キャンセル", key=f"cancel_manual_{slot_id}"):
                                        del st.session_state[assign_mode_key]
                                        st.rerun()
                            else:
                                st.error("組立番号画像が読み込まれていません")
                                if st.button("戻る", key=f"back_manual_{slot_id}"):
                                    del st.session_state[assign_mode_key]
                                    st.rerun()

                    st.markdown("---")

    except Exception as e:
        st.error(f"データの取得に失敗しました: {e}")

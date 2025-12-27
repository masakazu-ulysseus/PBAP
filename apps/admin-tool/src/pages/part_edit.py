import streamlit as st
import numpy as np
from PIL import Image
from utils.supabase_client import get_supabase_client, upload_image_to_supabase, add_cache_buster, check_db_response
from streamlit_drawable_canvas import st_canvas
import uuid
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
    """部品画像編集ページ（消しゴム機能）"""

    # 編集情報の確認
    if 'edit_part_info' not in st.session_state:
        st.error("編集する部品が選択されていません。")
        if st.button("← 戻る"):
            st.session_state['current_page'] = 'assembly_number_detail'
            st.rerun()
        return

    info = st.session_state['edit_part_info']
    part_id = info['part_id']
    part_url = info['part_url']
    part_name = info['part_name']
    slot_id = info['slot_id']
    display_order = info['display_order']

    # 戻るボタン
    if st.button("← 組立番号詳細に戻る"):
        # セッションをクリア
        if 'edit_part_info' in st.session_state:
            del st.session_state['edit_part_info']
        if 'edit_img' in st.session_state:
            del st.session_state['edit_img']
        if 'canvas_key' in st.session_state:
            del st.session_state['canvas_key']
        st.session_state['current_page'] = 'assembly_number_detail'
        st.rerun()

    st.header(f"✏️ 部品 {display_order} の編集")
    st.info("🖌️ 消しゴムモード：ドラッグして不要な部分を消去してください（赤色で表示された部分が消去されます）")

    # 初回：部品画像を読み込みセッションに保存
    if 'edit_img' not in st.session_state:
        with st.spinner("画像を読み込み中..."):
            original_image = load_image_from_url(add_cache_buster(part_url))
            if original_image:
                if original_image.mode != 'RGBA':
                    original_image = original_image.convert('RGBA')
                st.session_state['edit_img'] = original_image
                st.session_state['canvas_key'] = 0
            else:
                st.error("部品画像を読み込めませんでした")
                return

    current_image = st.session_state['edit_img']
    img_width, img_height = current_image.size

    # 消しゴムの太さ選択
    stroke_width = st.slider(
        "消しゴムの太さ",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
        key="eraser_width"
    )

    st.caption(f"画像サイズ: {img_width}x{img_height}px")

    # キャンバスの表示サイズを調整（最大600px）
    max_canvas_size = 600
    scale = min(max_canvas_size / img_width, max_canvas_size / img_height, 1.0)
    canvas_width = int(img_width * scale)
    canvas_height = int(img_height * scale)

    # リサイズした画像を背景用に作成
    if scale < 1.0:
        display_image = current_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
    else:
        display_image = current_image

    # キャンバスを表示
    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0)",
        stroke_width=stroke_width,
        stroke_color="rgba(255, 0, 0, 0.5)",  # 赤半透明で描画（消去部分の確認用）
        background_image=display_image,
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode="freedraw",
        key=f"eraser_canvas_{st.session_state.get('canvas_key', 0)}"
    )

    st.markdown("---")

    # 操作ボタン
    col_save, col_undo, col_cancel = st.columns(3)

    with col_save:
        if st.button("💾 保存", type="primary", use_container_width=True):
            if canvas_result.json_data is not None:
                drawing_objects = canvas_result.json_data.get("objects", [])

                if drawing_objects:
                    try:
                        with st.spinner("編集を保存中…"):
                            # 元画像をNumPy配列に変換
                            img_array = np.array(current_image)

                            # マスク画像を作成（消去する部分を白で描画）
                            from PIL import ImageDraw
                            mask = Image.new('L', (img_width, img_height), 0)
                            draw = ImageDraw.Draw(mask)

                            # 各描画オブジェクトをマスクに追加
                            for obj in drawing_objects:
                                if obj.get('type') == 'path':
                                    path = obj.get('path', [])
                                    width = obj.get('strokeWidth', stroke_width)

                                    # スケールを考慮してパスを変換
                                    points = []
                                    for cmd in path:
                                        if len(cmd) >= 3:
                                            # パスコマンドから座標を抽出（スケール補正）
                                            x = cmd[1] / scale
                                            y = cmd[2] / scale
                                            points.append((x, y))

                                    # 線を描画
                                    if len(points) >= 2:
                                        adjusted_width = int(width / scale)
                                        draw.line(points, fill=255, width=max(adjusted_width, 1))

                                        # 線の端を円で埋める（滑らかにするため）
                                        for point in points:
                                            radius = adjusted_width // 2
                                            draw.ellipse(
                                                [point[0] - radius, point[1] - radius,
                                                 point[0] + radius, point[1] + radius],
                                                fill=255
                                            )

                            # マスクを配列に変換
                            mask_array = np.array(mask)

                            # マスク部分を透明に（アルファチャンネルを0に）
                            img_array[:, :, 3] = np.where(mask_array > 0, 0, img_array[:, :, 3])

                            # 編集後の画像を作成
                            edited_image = Image.fromarray(img_array, 'RGBA')

                            # 画像をアップロード
                            supabase = get_supabase_client()
                            new_part_id = str(uuid.uuid4())
                            part_filename = f"parts/{new_part_id}.webp"
                            new_part_url = upload_image_to_supabase(edited_image, part_filename)

                            # 新しいpartsレコードを作成
                            parts_insert = supabase.table("parts").insert({
                                "id": new_part_id,
                                "parts_url": new_part_url,
                                "name": part_name,
                                "color": "不明",
                                "parts_code": None
                            }).execute()
                            check_db_response(parts_insert, f"INSERT parts (id={new_part_id})")

                            # assembly_image_partsを更新
                            update_response = supabase.table("assembly_image_parts").update({
                                "part_id": new_part_id
                            }).eq("id", slot_id).execute()
                            check_db_response(update_response, f"UPDATE assembly_image_parts (id={slot_id})")

                            # 古いpartsを削除
                            delete_old = supabase.table("parts").delete().eq("id", part_id).execute()
                            check_db_response(delete_old, f"DELETE old parts (id={part_id})")

                            # セッションをクリア
                            if 'edit_part_info' in st.session_state:
                                del st.session_state['edit_part_info']
                            if 'edit_img' in st.session_state:
                                del st.session_state['edit_img']
                            if 'canvas_key' in st.session_state:
                                del st.session_state['canvas_key']

                            st.session_state['success_message'] = f"✅ 部品 {display_order} の編集を保存しました"
                            st.session_state['current_page'] = 'assembly_number_detail'
                            st.rerun()
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
                else:
                    st.warning("消去する部分をドラッグしてください")
            else:
                st.warning("消去する部分をドラッグしてください")

    with col_undo:
        if st.button("↩️ 元に戻す", use_container_width=True):
            # キャンバスをリセット（キーを変更して再描画）
            st.session_state['canvas_key'] = st.session_state.get('canvas_key', 0) + 1
            st.rerun()

    with col_cancel:
        if st.button("キャンセル", use_container_width=True):
            # セッションをクリア
            if 'edit_part_info' in st.session_state:
                del st.session_state['edit_part_info']
            if 'edit_img' in st.session_state:
                del st.session_state['edit_img']
            if 'canvas_key' in st.session_state:
                del st.session_state['canvas_key']
            st.session_state['current_page'] = 'assembly_number_detail'
            st.rerun()

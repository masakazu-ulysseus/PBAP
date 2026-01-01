import streamlit as st
from PIL import Image
from utils import image_processing
from utils.supabase_client import get_supabase_client, check_db_response
import io
import uuid
import cv2
import numpy as np
from streamlit_cropper import st_cropper

def upload_image_to_supabase(image: Image.Image, path: str) -> str:
    """PIL画像をSupabase Storageにアップロードし、公開URLを返す"""
    supabase = get_supabase_client()
    bucket_name = "product-images"
    # 画像が大きすぎる場合はリサイズ（最大幅/高さ = 2000px）
    max_dim = 2000
    if image.width > max_dim or image.height > max_dim:
        # アスペクト比を保ってリサイズ
        ratio = min(max_dim / image.width, max_dim / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.LANCZOS)
    # WebPに変換
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP")
    image_bytes = buffer.getvalue()
    try:
        supabase.storage.from_(bucket_name).upload(path, image_bytes, {"content-type": "image/webp", "upsert": "true"})
        public_url = supabase.storage.from_(bucket_name).get_public_url(path)
        return public_url
    except Exception as e:
        st.error(f"画像のアップロードに失敗しました: {e}")
        raise e

def app():
    """製品登録ページを表示する。
    新しい製品の登録と、組立ページ・組立番号・部品の登録を行う。
    """
    st.header("📦 製品登録")

    # Step 1: 製品情報
    st.markdown("#### 1. 製品情報")

    # 製品画像アップロード（フォーム外に配置）
    product_image_file = st.file_uploader(
        "製品画像を選択（任意）",
        type=['webp', 'jpg', 'png', 'jpeg'],
        key="product_image_uploader",
        help="製品選択時にユーザーに表示される製品画像です"
    )

    if product_image_file is not None:
        product_image = Image.open(product_image_file)
        st.image(product_image, caption='製品画像プレビュー', width=300)
        st.session_state['product_image'] = product_image
    elif 'product_image' in st.session_state:
        st.image(st.session_state['product_image'], caption='製品画像プレビュー', width=300)

    with st.form("product_form"):
        series_name = st.selectbox("シリーズ名", ["ESシリーズ", "PBシリーズ", "その他"])
        country = st.selectbox("国", ["ドイツ", "日本", "アメリカ", "ソビエト", "イギリス", "その他"])
        product_name = st.text_input("製品名")
        submitted = st.form_submit_button("次へ")
        if submitted and product_name and series_name and country:
            st.session_state['product_info'] = {
                'name': product_name,
                'series': series_name,
                'country': country
            }
            st.success(f"製品情報を保存しました: {product_name}")

    if 'product_info' in st.session_state:
        # Step 2: 組立ページアップロード
        st.markdown("#### 2. 組立ページのアップロード")
        uploaded_file = st.file_uploader("組立ページ画像を選択 (WebP/JPG/PNG)", type=['webp', 'jpg', 'png', 'jpeg'])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.session_state['assembly_page_image'] = image
            st.image(image, caption='アップロードされた組立ページ', use_column_width=True)

            # ページ番号入力
            st.write("---")
            st.subheader("ページ番号")
            if 'page_number' not in st.session_state:
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
                if st.button("ページ番号を確定", type="primary"):
                    st.session_state['page_number'] = page_number_input
                    if page_number_input == 0:
                        st.success("ページ番号 0（表紙）を確定しました")
                    else:
                        st.success(f"ページ番号 {page_number_input} を確定しました")
                    st.rerun()
            else:
                page_display = "0（表紙）" if st.session_state['page_number'] == 0 else str(st.session_state['page_number'])
                st.success(f"✅ ページ番号: {page_display}")
                if st.button("ページ番号を変更"):
                    del st.session_state['page_number']
                    st.rerun()

        # ページ番号が確定したら組立番号領域の選択UIを表示
        if 'page_number' in st.session_state and 'assembly_page_image' in st.session_state:
            image = st.session_state['assembly_page_image']
            st.write("---")
            st.subheader("組立番号領域の選択")
            st.info("📌 ドラッグして領域を選択してください。複数の領域を順番に選択できます。")

            # 選択済み領域を初期化
            if 'selected_regions' not in st.session_state:
                st.session_state['selected_regions'] = []

            # 選択済み領域を赤枠で表示した画像を作成
            img_with_regions = image.copy()
            img_np = np.array(img_with_regions)
            for region_data in st.session_state['selected_regions']:
                assembly_number, bbox = region_data
                x, y, w, h = bbox
                cv2.rectangle(img_np, (x, y), (x+w, y+h), (255, 0, 0), 3)
                cv2.putText(img_np, str(assembly_number), (x+5, y+30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
            display_image = Image.fromarray(img_np)

            # クロップ機能を表示
            st.write("**新しい領域を選択:**")
            st.info("📌 緑の枠をドラッグして位置とサイズを調整してください。調整が完了したら下のボタンで領域を追加できます。")
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
                    # セッションに保存
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

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("この領域を追加", type="primary"):
                            if assembly_number is not None and assembly_number > 0:
                                st.session_state['selected_regions'].append((str(int(assembly_number)), new_bbox))
                                if 'pending_bbox' in st.session_state:
                                    del st.session_state['pending_bbox']
                                st.success(f"組立番号 '{assembly_number}' の領域を追加しました！")
                                st.rerun()
                            else:
                                st.error("組立番号を入力してください")
                    with col_btn2:
                        if st.button("キャンセル"):
                            if 'pending_bbox' in st.session_state:
                                del st.session_state['pending_bbox']
                            st.rerun()
                    with col_btn3:
                        if st.button("組立ページのみ保存", type="secondary"):
                            # 組立ページのみを保存
                            with st.spinner("組立ページを保存中…"):
                                try:
                                    supabase = get_supabase_client()
                                    product_info = st.session_state['product_info']
                                    # 1. 製品作成
                                    product_id = str(uuid.uuid4())

                                    # 製品画像のアップロード（任意）
                                    product_image_url = None
                                    if 'product_image' in st.session_state:
                                        product_image_filename = f"products/{product_id}.webp"
                                        product_image_url = upload_image_to_supabase(st.session_state['product_image'], product_image_filename)

                                    product_response = supabase.table("products").insert({
                                        "id": product_id,
                                        "name": product_info['name'],
                                        "series_name": product_info['series'],
                                        "country": product_info['country'],
                                        "status": "inactive",  # 準備中で登録
                                        "image_url": product_image_url
                                    }).execute()
                                    check_db_response(product_response, f"INSERT products (id={product_id})")
                                    # 2. 組立ページ画像アップロード & レコード作成
                                    page_id = str(uuid.uuid4())
                                    page_filename = f"assembly_pages/{page_id}.webp"
                                    page_url = upload_image_to_supabase(st.session_state['assembly_page_image'], page_filename)
                                    page_response = supabase.table("assembly_pages").insert({
                                        "id": page_id,
                                        "product_id": product_id,
                                        "page_number": st.session_state['page_number'],
                                        "image_url": page_url
                                    }).execute()
                                    check_db_response(page_response, f"INSERT assembly_pages (id={page_id})")
                                    page_display = "0（表紙）" if st.session_state['page_number'] == 0 else str(st.session_state['page_number'])
                                    st.success(f"組立ページ（ページ番号: {page_display}）を保存しました！")
                                    # セッションステートをクリア
                                    for key in ['product_info', 'assembly_page_image', 'page_number', 'selected_regions', 'pending_bbox', 'assembly_data', 'product_image']:
                                        if key in st.session_state:
                                            del st.session_state[key]
                                    # parts_* キーもクリア
                                    parts_keys = [k for k in st.session_state.keys() if k.startswith('parts_')]
                                    for key in parts_keys:
                                        del st.session_state[key]
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"保存中にエラーが発生しました: {e}")

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
                        st.image(crop, use_column_width=True)
                        st.write(f"組立番号: **{assembly_number}**")
                    with col3:
                        if st.button("削除", key=f"del_{i}"):
                            st.session_state['selected_regions'].pop(i)
                            st.rerun()

                # 次へボタン
                st.write("---")
                if st.button("選択完了して次へ", type="primary"):
                    # 選択した領域を切り出し（組立番号と画像と座標のペア）
                    assembly_data = []
                    img_np = np.array(image)
                    for assembly_number, bbox in st.session_state['selected_regions']:
                        x, y, w, h = bbox
                        crop = img_np[y:y+h, x:x+w]
                        assembly_data.append({
                            'number': assembly_number,
                            'image': Image.fromarray(crop),
                            'region_x': x,
                            'region_y': y,
                            'region_width': w,
                            'region_height': h
                        })

                    st.session_state['assembly_data'] = assembly_data
                    # クリーンアップ
                    del st.session_state['selected_regions']
                    if 'pending_bbox' in st.session_state:
                        del st.session_state['pending_bbox']
                    st.success(f"{len(assembly_data)}個の組立番号領域を保存しました。")
                    st.rerun()

        # Step 3: パーツ抽出
        if 'assembly_data' in st.session_state:
            st.markdown("#### 3. 抽出された組立番号とパーツ")
            for i, data in enumerate(st.session_state['assembly_data']):
                assembly_number = data['number']
                assembly_img = data['image']
                
                st.markdown(f"**組立番号画像 #{i+1} - 組立番号: {assembly_number}**")
                st.image(assembly_img, width=300)
                if st.button(f"組立番号 {assembly_number} からパーツを抽出", key=f"extract_{i}"):
                    parts = image_processing.extract_parts(assembly_img)
                    st.session_state[f'parts_{i}'] = parts
                    st.success(f"組立番号 {assembly_number} から {len(parts)} 個のパーツを検出しました。")
                if f'parts_{i}' in st.session_state:
                    # 確定済みかどうかをチェック
                    if f'parts_{i}_confirmed' in st.session_state:
                        # 確定済みパーツを表示
                        st.success(f"✅ パーツを確定しました（{len(st.session_state[f'parts_{i}_confirmed'])}個）")
                        cols = st.columns(5)
                        for j, part_data in enumerate(st.session_state[f'parts_{i}_confirmed']):
                            with cols[j % 5]:
                                st.image(part_data['image'], caption=f"パーツ {part_data['order']}", use_column_width=True)

                    # 編集モード
                    elif f'parts_{i}_editing' in st.session_state and st.session_state[f'parts_{i}_editing']:
                        st.subheader("パーツの検出・編集")
                        st.info("✏️ 不要なパーツは「削除」、必要なパーツは「採用」を選択してください")

                        # 採用/削除の状態を初期化
                        if f'parts_{i}_selected' not in st.session_state:
                            st.session_state[f'parts_{i}_selected'] = [True] * len(st.session_state[f'parts_{i}'])

                        # 各パーツに採用/削除ボタン
                        cols = st.columns(5)
                        for j, part_img in enumerate(st.session_state[f'parts_{i}']):
                            with cols[j % 5]:
                                st.image(part_img, caption=f"パーツ {j+1}", use_column_width=True)
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    if st.button("採用", key=f"accept_{i}_{j}", type="primary" if st.session_state[f'parts_{i}_selected'][j] else "secondary"):
                                        st.session_state[f'parts_{i}_selected'][j] = True
                                        st.rerun()
                                with col_b:
                                    if st.button("削除", key=f"delete_{i}_{j}", type="primary" if not st.session_state[f'parts_{i}_selected'][j] else "secondary"):
                                        st.session_state[f'parts_{i}_selected'][j] = False
                                        st.rerun()

                        # 新しいパーツを追加
                        st.write("---")
                        st.subheader("パーツを追加")

                        # 追加用のパーツリストを初期化
                        if f'parts_{i}_added' not in st.session_state:
                            st.session_state[f'parts_{i}_added'] = []

                        # 追加済みパーツを表示
                        if st.session_state[f'parts_{i}_added']:
                            st.success(f"追加済みパーツ: {len(st.session_state[f'parts_{i}_added'])}個")
                            cols_added = st.columns(5)
                            for j, added_part in enumerate(st.session_state[f'parts_{i}_added']):
                                with cols_added[j % 5]:
                                    st.image(added_part, caption=f"追加 {j+1}", use_column_width=True)

                        # クロップ機能
                        st.write("**緑の枠でパーツ領域を選択:**")
                        cropped_part = st_cropper(
                            assembly_img,
                            realtime_update=True,
                            box_color='#00FF00',
                            aspect_ratio=None,
                            return_type='box',
                            key=f"part_cropper_{i}"
                        )

                        if cropped_part is not None and isinstance(cropped_part, dict):
                            left = cropped_part.get('left', 0)
                            top = cropped_part.get('top', 0)
                            width = cropped_part.get('width', 0)
                            height = cropped_part.get('height', 0)

                            if width > 0 and height > 0:
                                # プレビュー
                                preview = np.array(assembly_img)[top:top+height, left:left+width]
                                if preview.size > 0:
                                    st.image(preview, caption="追加するパーツのプレビュー", width=200)

                                    if st.button("追加", key=f"add_part_{i}", type="primary"):
                                        new_part = Image.fromarray(preview)
                                        st.session_state[f'parts_{i}_added'].append(new_part)
                                        st.success("パーツを追加しました！")
                                        st.rerun()

                        # 完了ボタンは常に表示
                        st.write("---")
                        if st.button("完了", key=f"done_edit_{i}", type="primary"):
                            # 採用されたパーツのみを収集
                            confirmed_parts = []
                            for j, part_img in enumerate(st.session_state[f'parts_{i}']):
                                if st.session_state[f'parts_{i}_selected'][j]:
                                    confirmed_parts.append(part_img)
                            # 追加されたパーツも含める
                            confirmed_parts.extend(st.session_state[f'parts_{i}_added'])

                            # 順番設定モードへ
                            st.session_state[f'parts_{i}_temp'] = confirmed_parts
                            st.session_state[f'parts_{i}_editing'] = False
                            st.session_state[f'parts_{i}_order_setting'] = True
                            st.rerun()

                    # 順番設定モード
                    elif f'parts_{i}_order_setting' in st.session_state and st.session_state[f'parts_{i}_order_setting']:
                        st.subheader("パーツの表示順を設定")
                        st.info("🔢 各パーツの表示順を選択してください")

                        # 順番を初期化
                        if f'parts_{i}_order' not in st.session_state:
                            st.session_state[f'parts_{i}_order'] = list(range(1, len(st.session_state[f'parts_{i}_temp']) + 1))

                        # 各パーツに順番選択
                        cols = st.columns(min(5, len(st.session_state[f'parts_{i}_temp'])))
                        for j, part_img in enumerate(st.session_state[f'parts_{i}_temp']):
                            with cols[j % 5]:
                                st.image(part_img, caption="パーツ", use_column_width=True)
                                order = st.selectbox(
                                    "表示順",
                                    options=list(range(1, len(st.session_state[f'parts_{i}_temp']) + 1)),
                                    index=st.session_state[f'parts_{i}_order'][j] - 1,
                                    key=f"order_{i}_{j}"
                                )
                                st.session_state[f'parts_{i}_order'][j] = order

                        if st.button("順番を確定", key=f"confirm_order_{i}", type="primary"):
                            # 順番に従ってパーツを並び替え
                            parts_with_order = [(st.session_state[f'parts_{i}_temp'][j], st.session_state[f'parts_{i}_order'][j])
                                               for j in range(len(st.session_state[f'parts_{i}_temp']))]
                            parts_with_order.sort(key=lambda x: x[1])

                            # 確定済みパーツとして保存
                            confirmed = []
                            for idx, (part_img, order) in enumerate(parts_with_order):
                                confirmed.append({'image': part_img, 'order': order})

                            st.session_state[f'parts_{i}_confirmed'] = confirmed
                            del st.session_state[f'parts_{i}_order_setting']
                            del st.session_state[f'parts_{i}_temp']
                            del st.session_state[f'parts_{i}_order']
                            st.success(f"パーツの順番を確定しました（{len(confirmed)}個）")
                            st.rerun()

                    # 通常表示（編集前）
                    else:
                        st.write("検出されたパーツ:")
                        cols = st.columns(5)
                        for j, part_img in enumerate(st.session_state[f'parts_{i}']):
                            with cols[j % 5]:
                                st.image(part_img, caption=f"パーツ {j+1}", use_column_width=True)

                        # 修正ボタン
                        if st.button("検出したパーツを修正する", key=f"edit_parts_{i}"):
                            st.session_state[f'parts_{i}_editing'] = True
                            st.rerun()
            
            # Step 4: データベースへ保存
            st.markdown("---")
            if st.button("全データをデータベースへ保存", type="primary"):
                if 'assembly_page_image' not in st.session_state:
                    st.error("組立ページ画像がありません。再度アップロードしてください。")
                else:
                    with st.spinner("Supabaseへ保存中…"):
                        try:
                            supabase = get_supabase_client()
                            product_info = st.session_state['product_info']
                            # 1. 製品作成
                            product_id = str(uuid.uuid4())

                            # 製品画像のアップロード（任意）
                            product_image_url = None
                            if 'product_image' in st.session_state:
                                product_image_filename = f"products/{product_id}.webp"
                                product_image_url = upload_image_to_supabase(st.session_state['product_image'], product_image_filename)

                            product_response = supabase.table("products").insert({
                                "id": product_id,
                                "name": product_info['name'],
                                "series_name": product_info['series'],
                                "country": product_info['country'],
                                "status": "inactive",  # 準備中で登録
                                "image_url": product_image_url
                            }).execute()
                            check_db_response(product_response, f"INSERT products (id={product_id})")
                            # 2. 組立ページ画像アップロード & レコード作成
                            page_id = str(uuid.uuid4())
                            page_filename = f"assembly_pages/{page_id}.webp"
                            page_url = upload_image_to_supabase(st.session_state['assembly_page_image'], page_filename)
                            page_response = supabase.table("assembly_pages").insert({
                                "id": page_id,
                                "product_id": product_id,
                                "page_number": st.session_state['page_number'],
                                "image_url": page_url
                            }).execute()
                            check_db_response(page_response, f"INSERT assembly_pages (id={page_id})")
                            # 3. 組立画像処理
                            for i, data in enumerate(st.session_state['assembly_data']):
                                assembly_number = data['number']
                                assembly_img = data['image']

                                assembly_img_id = str(uuid.uuid4())
                                assembly_img_filename = f"assembly_images/{assembly_img_id}.webp"
                                assembly_img_url = upload_image_to_supabase(assembly_img, assembly_img_filename)
                                assembly_img_response = supabase.table("assembly_images").insert({
                                    "id": assembly_img_id,
                                    "page_id": page_id,
                                    "assembly_number": str(assembly_number),  # ユーザー入力の組立番号を使用（文字列に変換）
                                    "display_order": i + 1,
                                    "image_url": assembly_img_url,
                                    "region_x": data.get('region_x'),
                                    "region_y": data.get('region_y'),
                                    "region_width": data.get('region_width'),
                                    "region_height": data.get('region_height')
                                }).execute()
                                check_db_response(assembly_img_response, f"INSERT assembly_images (id={assembly_img_id})")
                                # 4. パーツ処理
                                # 確定済みパーツがある場合はそれを使用、なければ検出されたパーツをそのまま使用
                                if f'parts_{i}_confirmed' in st.session_state:
                                    # 確定済みパーツを使用（順番付き）
                                    for part_data in st.session_state[f'parts_{i}_confirmed']:
                                        part_img = part_data['image']
                                        part_order = part_data['order']
                                        part_id = str(uuid.uuid4())
                                        part_filename = f"parts/{part_id}.webp"
                                        part_url = upload_image_to_supabase(part_img, part_filename)
                                        parts_response = supabase.table("parts").insert({
                                            "id": part_id,
                                            "parts_url": part_url,
                                            "name": f"パーツ {part_order}",
                                            "color": "不明",
                                            "parts_code": None
                                        }).execute()
                                        check_db_response(parts_response, f"INSERT parts (id={part_id})")
                                        link_response = supabase.table("assembly_image_parts").insert({
                                            "assembly_image_id": assembly_img_id,
                                            "part_id": part_id,
                                            "quantity": 1
                                        }).execute()
                                        check_db_response(link_response, f"INSERT assembly_image_parts (part_id={part_id})")
                                elif f'parts_{i}' in st.session_state:
                                    # 検出されたパーツをそのまま使用
                                    for j, part_img in enumerate(st.session_state[f'parts_{i}']):
                                        part_id = str(uuid.uuid4())
                                        part_filename = f"parts/{part_id}.webp"
                                        part_url = upload_image_to_supabase(part_img, part_filename)
                                        parts_response = supabase.table("parts").insert({
                                            "id": part_id,
                                            "parts_url": part_url,
                                            "name": f"パーツ {j+1}",
                                            "color": "不明",
                                            "parts_code": None
                                        }).execute()
                                        check_db_response(parts_response, f"INSERT parts (id={part_id})")
                                        link_response = supabase.table("assembly_image_parts").insert({
                                            "assembly_image_id": assembly_img_id,
                                            "part_id": part_id,
                                            "quantity": 1
                                        }).execute()
                                        check_db_response(link_response, f"INSERT assembly_image_parts (part_id={part_id})")
                            st.success("全データをSupabaseへ正常に保存しました！")
                            st.balloons()
                        except Exception as e:
                            st.error(f"データベース保存中にエラーが発生しました: {e}")

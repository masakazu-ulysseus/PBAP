import streamlit as st
import pandas as pd
from utils.supabase_client import get_supabase_client, add_cache_buster, check_db_response
from utils.logger import logger
from datetime import datetime, timedelta, timezone
import requests

# JSTタイムゾーン（UTC+9）
JST = timezone(timedelta(hours=9))
from io import BytesIO
from PIL import Image


def convert_to_jst(dt_str: str) -> str:
    """UTC日時文字列をJSTに変換してフォーマット"""
    if not dt_str:
        return "-"
    dt_utc = pd.to_datetime(dt_str)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.tz_localize('UTC')
    dt_jst = dt_utc.tz_convert(JST)
    return dt_jst.strftime("%Y/%m/%d %H:%M")


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
    """タスク詳細ページを表示する。
    選択されたタスクの詳細情報と、リクエストされた部品一覧を表示する。
    """

    # 戻るボタン
    if st.button("← タスク一覧に戻る"):
        if 'selected_task_id' in st.session_state:
            del st.session_state['selected_task_id']
        if 'task_page' in st.session_state:
            del st.session_state['task_page']
        st.rerun()

    # 成功メッセージがセッションにあれば表示
    if 'success_message' in st.session_state:
        st.success(st.session_state['success_message'])
        del st.session_state['success_message']

    # タスクIDの確認
    if 'selected_task_id' not in st.session_state:
        st.error("タスクが選択されていません。")
        return

    task_id = st.session_state['selected_task_id']

    try:
        supabase = get_supabase_client()

        # タスク情報を取得
        task_response = supabase.table("tasks").select("*").eq("id", task_id).execute()

        if not task_response.data:
            st.error("タスクが見つかりませんでした。")
            return

        task = task_response.data[0]

        # ステータスアイコン
        status_icon = {
            "pending": "📋",
            "processing": "⏳",
            "completed": "✅",
            "cancelled": "❌"
        }.get(task['status'], "❓")

        # 申請番号を取得
        app_num = task.get('application_number')
        app_num_str = f"#{app_num}" if app_num else ""

        # フロータイプを取得
        flow_type = task.get('flow_type', 'normal')
        flow_label = "📦 通常フロー" if flow_type == 'normal' else "📷 写真フロー"

        st.header(f"{status_icon} タスク詳細 {app_num_str}")
        st.caption(flow_label)

        # ステータス変更
        col_status, col_btn, col_space = st.columns([2, 1, 2])
        with col_status:
            new_status = st.selectbox(
                "ステータス変更",
                ["pending", "processing", "completed", "cancelled"],
                index=["pending", "processing", "completed", "cancelled"].index(task['status']),
                format_func=lambda x: {
                    "pending": "📋 未処理",
                    "processing": "⏳ 処理中",
                    "completed": "✅ 完了",
                    "cancelled": "❌ キャンセル"
                }.get(x, x),
                key="status_select"
            )
        with col_btn:
            st.write("")  # スペーサー
            if st.button("確定", type="primary", disabled=(new_status == task['status'])):
                new_status_label = {
                    "pending": "未処理",
                    "processing": "処理中",
                    "completed": "完了",
                    "cancelled": "キャンセル"
                }.get(new_status, new_status)
                update_response = supabase.table("tasks").update({
                    "status": new_status,
                    "updated_at": datetime.now().isoformat()
                }).eq("id", task_id).execute()
                check_db_response(update_response, f"UPDATE tasks.status (id={task_id})")
                logger.info(f"タスクステータス更新: ID={task_id}, status={new_status}")
                st.session_state['success_message'] = f"✅ ステータスを「{new_status_label}」に更新しました"
                st.rerun()

        st.markdown("---")

        # 基本情報
        st.subheader("📦 商品情報")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**商品名:** {task['product_name']}")
            st.write(f"**購入店:** {task['purchase_store']}")
        with col2:
            st.write(f"**購入日:** {task['purchase_date']}")
            st.write(f"**保証コード:** {task['warranty_code']}")

        st.markdown("---")

        # 配送先情報（編集可能）
        st.subheader("📬 配送先情報")

        # 編集モードの切り替え
        if 'edit_shipping_mode' not in st.session_state:
            st.session_state['edit_shipping_mode'] = False

        # 住所を結合して表示用に整形するヘルパー関数
        def format_full_address(t):
            parts = [
                t.get('prefecture', ''),
                t.get('city', ''),
                t.get('town', ''),
                t.get('address_detail', ''),
            ]
            address = ''.join(filter(None, parts))
            building = t.get('building_name', '')
            if building:
                address += f" {building}"
            return address

        if not st.session_state['edit_shipping_mode']:
            # 表示モード
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**受取人:** {task['recipient_name']}")
                st.write(f"**郵便番号:** {task['zip_code']}")
                st.write(f"**住所:** {format_full_address(task)}")
            with col2:
                st.write(f"**メール:** {task['email']}")
                st.write(f"**電話番号:** {task['phone_number']}")

            if st.button("✏️ 配送先情報を編集"):
                st.session_state['edit_shipping_mode'] = True
                st.rerun()
        else:
            # 編集モード
            st.write("**受取人・連絡先**")
            col1, col2 = st.columns(2)
            with col1:
                new_recipient_name = st.text_input("受取人", value=task['recipient_name'], key="edit_recipient_name")
                new_zip_code = st.text_input("郵便番号", value=task['zip_code'], key="edit_zip_code")
            with col2:
                new_email = st.text_input("メール", value=task['email'], key="edit_email")
                new_phone = st.text_input("電話番号", value=task['phone_number'], key="edit_phone")

            st.write("**住所**")
            col_addr1, col_addr2 = st.columns(2)
            with col_addr1:
                new_prefecture = st.text_input("都道府県", value=task.get('prefecture', ''), key="edit_prefecture")
                new_city = st.text_input("市区町村", value=task.get('city', ''), key="edit_city")
                new_town = st.text_input("町域", value=task.get('town', '') or '', key="edit_town")
            with col_addr2:
                new_address_detail = st.text_input("番地", value=task.get('address_detail', ''), key="edit_address_detail")
                new_building_name = st.text_input("建物名（任意）", value=task.get('building_name', '') or '', key="edit_building_name")

            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("💾 保存", type="primary", key="save_shipping"):
                    # バリデーション（必須項目のみ）
                    if not new_recipient_name or not new_zip_code or not new_prefecture or not new_city or not new_address_detail or not new_email or not new_phone:
                        st.error("必須項目を入力してください（町域・建物名は任意）")
                    else:
                        try:
                            update_response = supabase.table("tasks").update({
                                "recipient_name": new_recipient_name,
                                "zip_code": new_zip_code,
                                "prefecture": new_prefecture,
                                "city": new_city,
                                "town": new_town or None,
                                "address_detail": new_address_detail,
                                "building_name": new_building_name or None,
                                "email": new_email,
                                "phone_number": new_phone,
                                "updated_at": datetime.now().isoformat()
                            }).eq("id", task_id).execute()
                            check_db_response(update_response, f"UPDATE tasks shipping info (id={task_id})")
                            logger.info(f"配送先情報更新: ID={task_id}")
                            st.session_state['edit_shipping_mode'] = False
                            st.session_state['success_message'] = "✅ 配送先情報を更新しました"
                            st.rerun()
                        except Exception as e:
                            logger.error(f"配送先情報更新エラー: ID={task_id} - {e}")
                            st.error(f"更新エラー: {e}")
            with col_btn2:
                if st.button("❌ キャンセル", key="cancel_shipping"):
                    st.session_state['edit_shipping_mode'] = False
                    st.rerun()
            with col_btn3:
                st.write("")

        st.markdown("---")

        # ユーザーからの連絡事項
        user_memo = task.get('user_memo')
        if user_memo:
            st.subheader("💬 申請に関する補足事項")
            st.info(user_memo)
            st.markdown("---")

        # リクエストされた部品一覧（または写真）
        if flow_type == 'other':
            # 写真フロー: アップロードされた写真を表示
            st.subheader("📷 アップロードされた写真")

            photos_response = supabase.table("task_photo_requests").select("*").eq("task_id", task_id).order("display_order").execute()

            if photos_response.data:
                # 2列で写真を表示
                cols = st.columns(2)
                for i, photo in enumerate(photos_response.data):
                    with cols[i % 2]:
                        try:
                            photo_url = add_cache_buster(photo['image_url'])
                            photo_image = load_image_from_url(photo_url)
                            if photo_image:
                                st.image(photo_image, caption=f"写真 {photo.get('display_order', i + 1)}", use_column_width=True)
                            else:
                                st.warning(f"写真 {photo.get('display_order', i + 1)}: 読込エラー")
                        except Exception as e:
                            st.warning(f"写真 {photo.get('display_order', i + 1)}: エラー - {str(e)}")
            else:
                st.info("アップロードされた写真がありません。")
        else:
            # 通常フロー: リクエストされた部品を表示
            st.subheader("🧩 リクエストされた部品")

            details_response = supabase.table("task_part_requests").select(
                "*, parts(*), assembly_images(assembly_number)"
            ).eq("task_id", task_id).execute()

            # デバッグ: task_part_requestsの件数を表示
            st.caption(f"（{len(details_response.data) if details_response.data else 0}件）")

            if not details_response.data:
                st.info("リクエストされた部品がありません。")
            else:
                for i, detail in enumerate(details_response.data):
                    part = detail.get('parts')
                    assembly = detail.get('assembly_images')
                    quantity = detail.get('quantity', 1)

                    with st.container():
                        col1, col2, col3 = st.columns([1, 2, 1])

                        with col1:
                            if part and part.get('parts_url'):
                                try:
                                    part_url = add_cache_buster(part['parts_url'])
                                    part_image = load_image_from_url(part_url)
                                    if part_image:
                                        st.image(part_image, width=100)
                                    else:
                                        st.warning("画像なし")
                                except:
                                    st.warning("画像読込エラー")
                            else:
                                st.warning("画像なし")

                        with col2:
                            part_name = part.get('name', '不明') if part else '不明'
                            assembly_number = assembly.get('assembly_number', '-') if assembly else '-'
                            st.write(f"**部品名:** {part_name}")
                            st.write(f"**組立番号:** {assembly_number}")
                            if part:
                                st.write(f"**色:** {part.get('color', '不明')} / **サイズ:** {part.get('size', '不明')}")

                        with col3:
                            st.write(f"**数量:** {quantity}個")

                        st.markdown("---")

        # 管理者メモ
        st.subheader("📝 管理者メモ")
        admin_memo = st.text_area(
            "メモ",
            value=task.get('admin_memo', '') or '',
            height=100,
            key="admin_memo"
        )
        memo_changed = admin_memo != (task.get('admin_memo') or '')
        if st.button("💾 メモを保存", disabled=not memo_changed):
            update_response = supabase.table("tasks").update({
                "admin_memo": admin_memo,
                "updated_at": datetime.now().isoformat()
            }).eq("id", task_id).execute()
            check_db_response(update_response, f"UPDATE tasks.admin_memo (id={task_id})")
            logger.info(f"タスクメモ保存: ID={task_id}")
            st.session_state['success_message'] = "✅ メモを保存しました"
            st.rerun()

        st.markdown("---")

        # 発送部品画像
        st.subheader("📸 発送部品画像")
        if task.get('shipment_image_url'):
            try:
                shipment_url = add_cache_buster(task['shipment_image_url'])
                shipment_image = load_image_from_url(shipment_url)
                if shipment_image:
                    st.image(shipment_image, caption="発送部品画像", width=400)
                else:
                    st.warning("発送画像を読み込めません")
            except:
                st.warning("発送画像の表示エラー")
        else:
            st.info("発送部品画像が登録されていません")

            # 発送部品画像アップロード
            uploaded_file = st.file_uploader(
                "発送部品画像をアップロード",
                type=['png', 'jpg', 'jpeg', 'webp'],
                key="shipment_image_upload"
            )
            if uploaded_file:
                st.image(uploaded_file, caption="アップロード予定の画像", width=300)
                if st.button("📤 発送部品画像を登録", type="primary"):
                    try:
                        from utils.supabase_client import upload_image_to_supabase
                        pil_image = Image.open(uploaded_file)
                        if pil_image.mode == 'RGBA':
                            pil_image = pil_image.convert('RGB')
                        filename = f"shipments/{task_id}.webp"
                        image_url = upload_image_to_supabase(pil_image, filename)

                        update_response = supabase.table("tasks").update({
                            "shipment_image_url": image_url,
                            "updated_at": datetime.now().isoformat()
                        }).eq("id", task_id).execute()
                        check_db_response(update_response, f"UPDATE tasks.shipment_image_url (id={task_id})")
                        logger.info(f"発送部品画像アップロード: ID={task_id}")
                        st.session_state['success_message'] = "✅ 発送部品画像を登録しました"
                        st.rerun()
                    except Exception as e:
                        logger.error(f"発送部品画像アップロードエラー: ID={task_id} - {e}")
                        st.error(f"アップロードエラー: {e}")

        st.markdown("---")

        # 送信メール
        st.subheader("📧 送信メール")

        # メール送信履歴を表示
        email_already_sent = False
        if task.get('email_sent_at'):
            email_already_sent = True
            email_sent_str = convert_to_jst(task['email_sent_at'])
            st.success(f"✅ 送信済み: {email_sent_str}")
        if task.get('email_error'):
            st.warning(f"⚠️ エラー: {task['email_error']}")

        from utils.email_sender import get_default_body, send_email, DEFAULT_SUBJECT

        # 申請日のフォーマット（UTC→JST変換）
        created_at_utc = pd.to_datetime(task['created_at'])
        if created_at_utc.tzinfo is None:
            created_at_utc = created_at_utc.tz_localize('UTC')
        created_at_jst = created_at_utc.tz_convert(JST)
        request_date_str = created_at_jst.strftime("%Y年%m月%d日")

        # デフォルトの本文を生成（またはDBに保存された本文を使用）
        default_body = get_default_body(
            recipient_name=task['recipient_name'],
            request_date=request_date_str
        )

        # 送信先表示
        st.write(f"**送信先:** {task['email']}")

        # 件名
        email_subject = st.text_input(
            "件名",
            value=DEFAULT_SUBJECT,
            key="email_subject"
        )

        # 本文（編集可能）
        email_body = st.text_area(
            "本文",
            value=default_body,
            height=250,
            key="email_body"
        )

        # 添付画像プレビュー（発送画像がある場合のみ）
        if task.get('shipment_image_url'):
            st.write("**添付画像:**")
            try:
                shipment_url = add_cache_buster(task['shipment_image_url'])
                preview_image = load_image_from_url(shipment_url)
                if preview_image:
                    st.image(preview_image, caption="発送画像", width=150)
            except:
                st.caption("（プレビュー不可）")

        # 送信ボタン
        has_shipment_image = bool(task.get('shipment_image_url'))
        is_photo_flow = (flow_type == 'other')

        # 画像なしで送信する場合の確認
        if st.session_state.get('confirm_no_image_send'):
            st.warning("⚠️ 発送部品画像を添付せずにメールを送信しますか？")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("✅ 送信する", type="primary", key="confirm_send"):
                    st.session_state['confirm_no_image_send'] = False
                    # ここで送信処理を実行
                    with st.spinner("送信中..."):
                        result = send_email(
                            to_email=task['email'],
                            subject=email_subject,
                            body=email_body,
                            image_url=None
                        )
                        if result['success']:
                            update_response = supabase.table("tasks").update({
                                "status": "completed",
                                "email_sent_at": datetime.now().isoformat(),
                                "email_error": None,
                                "updated_at": datetime.now().isoformat()
                            }).eq("id", task_id).execute()
                            check_db_response(update_response, f"UPDATE tasks.status (id={task_id})")
                            logger.info(f"メール送信成功（画像なし）・タスク完了: ID={task_id}, email={task['email']}")
                            st.session_state['success_message'] = f"✅ {result['message']}（タスク完了）"
                            st.rerun()
                        else:
                            update_response = supabase.table("tasks").update({
                                "email_error": result['message'],
                                "updated_at": datetime.now().isoformat()
                            }).eq("id", task_id).execute()
                            logger.error(f"メール送信失敗: ID={task_id}, error={result['message']}")
                            st.error(f"❌ {result['message']}")
                            st.session_state['confirm_no_image_send'] = False
                            st.rerun()
            with col_cancel:
                if st.button("❌ キャンセル", key="cancel_send"):
                    st.session_state['confirm_no_image_send'] = False
                    st.rerun()
        else:
            # 通常の送信ボタン表示
            if not has_shipment_image and not is_photo_flow:
                # 通常フローで画像がない場合のみdisabled
                st.warning("⚠️ 発送画像を先に登録してください")
                st.button("📤 メールを送信してタスク完了", type="primary", disabled=True, key="send_email_btn")
            else:
                # 写真フローまたは画像がある場合はボタン有効
                button_label = "📤 メールを再送信" if email_already_sent else "📤 メールを送信してタスク完了"
                if not has_shipment_image:
                    button_label = "📤 メールを送信してタスク完了（画像なし）"

                if st.button(button_label, type="primary", key="send_email_btn"):
                    if not has_shipment_image:
                        # 画像なしの場合は確認ダイアログへ
                        st.session_state['confirm_no_image_send'] = True
                        st.rerun()
                    else:
                        # 画像ありの場合はそのまま送信
                        with st.spinner("送信中..."):
                            result = send_email(
                                to_email=task['email'],
                                subject=email_subject,
                                body=email_body,
                                image_url=task['shipment_image_url']
                            )

                            if result['success']:
                                # ステータスを完了に更新 + メール送信日時を記録
                                update_response = supabase.table("tasks").update({
                                    "status": "completed",
                                    "email_sent_at": datetime.now().isoformat(),
                                    "email_error": None,
                                    "updated_at": datetime.now().isoformat()
                                }).eq("id", task_id).execute()
                                check_db_response(update_response, f"UPDATE tasks.status (id={task_id})")
                                logger.info(f"メール送信成功・タスク完了: ID={task_id}, email={task['email']}")
                                st.session_state['success_message'] = f"✅ {result['message']}（タスク完了）"
                                st.rerun()
                            else:
                                # エラーを記録
                                update_response = supabase.table("tasks").update({
                                    "email_error": result['message'],
                                    "updated_at": datetime.now().isoformat()
                                }).eq("id", task_id).execute()
                                logger.error(f"メール送信失敗: ID={task_id}, error={result['message']}")
                                st.error(f"❌ {result['message']}")

        # タスク情報
        st.markdown("---")
        st.caption(f"タスクID: {task_id}")
        st.caption(f"作成日時: {convert_to_jst(task['created_at'])}")
        st.caption(f"更新日時: {convert_to_jst(task['updated_at'])}")

    except Exception as e:
        logger.error(f"タスク詳細取得エラー: {e}")
        st.error(f"データの取得に失敗しました: {e}")

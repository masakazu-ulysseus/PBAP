import streamlit as st
import pandas as pd
from utils.supabase_client import get_supabase_client
from utils.logger import logger
from datetime import timedelta, timezone

# JSTタイムゾーン（UTC+9）
JST = timezone(timedelta(hours=9))


def app():
    """タスク一覧ページを表示する。
    DBからタスクを取得し、フィルタリング・検索機能付きで表示する。
    """

    st.header("📋 タスク管理")

    try:
        supabase = get_supabase_client()

        # タスク一覧を取得
        tasks_response = supabase.table("tasks").select("*").order("created_at", desc=True).execute()

        # フィルター
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox(
                "ステータス",
                ["すべて", "pending", "processing", "completed", "cancelled"],
                format_func=lambda x: {
                    "すべて": "すべて",
                    "pending": "📋 未処理",
                    "processing": "⏳ 処理中",
                    "completed": "✅ 完了",
                    "cancelled": "❌ キャンセル"
                }.get(x, x)
            )
        with col2:
            search_query = st.text_input("商品名・受取人名で検索", "")
            flow_filter = st.selectbox(
                "フロー",
                ["すべて", "normal", "other"],
                format_func=lambda x: {
                    "すべて": "すべて",
                    "normal": "📦 通常フロー",
                    "other": "📷 写真フロー"
                }.get(x, x)
            )
        with col3:
            date_filter = st.date_input("申請日", value=None)

        # データがない場合
        if not tasks_response.data:
            st.info("📭 タスクがありません。")
            return

        # DataFrameに変換
        tasks_df = pd.DataFrame(tasks_response.data)

        # フィルタリング
        filtered_df = tasks_df.copy()

        if status_filter != "すべて":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]

        if flow_filter != "すべて":
            filtered_df = filtered_df[filtered_df['flow_type'] == flow_filter]

        if search_query:
            search_lower = search_query.lower()
            filtered_df = filtered_df[
                filtered_df['product_name'].str.lower().str.contains(search_lower, na=False) |
                filtered_df['recipient_name'].str.lower().str.contains(search_lower, na=False)
            ]

        if date_filter:
            # UTC→JST変換してから日付比較
            created_at_jst = pd.to_datetime(filtered_df['created_at']).dt.tz_localize('UTC').dt.tz_convert(JST)
            filtered_df = filtered_df[created_at_jst.dt.date == date_filter]

        # サマリー表示
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            pending_count = len(tasks_df[tasks_df['status'] == 'pending'])
            st.metric("📋 未処理", pending_count)
        with col2:
            processing_count = len(tasks_df[tasks_df['status'] == 'processing'])
            st.metric("⏳ 処理中", processing_count)
        with col3:
            completed_count = len(tasks_df[tasks_df['status'] == 'completed'])
            st.metric("✅ 完了", completed_count)
        with col4:
            st.metric("📊 合計", len(tasks_df))

        st.markdown("---")

        # 結果表示
        if filtered_df.empty:
            st.warning("該当するタスクがありません。")
            return

        st.subheader(f"タスク一覧（{len(filtered_df)}件）")

        # タスク一覧を表示
        for _, task in filtered_df.iterrows():
            status_icon = {
                "pending": "📋",
                "processing": "⏳",
                "completed": "✅",
                "cancelled": "❌"
            }.get(task['status'], "❓")

            status_label = {
                "pending": "未処理",
                "processing": "処理中",
                "completed": "完了",
                "cancelled": "キャンセル"
            }.get(task['status'], task['status'])

            # 日時のフォーマット（UTC→JST変換）
            created_at_utc = pd.to_datetime(task['created_at'])
            created_at_jst = created_at_utc.tz_localize('UTC').tz_convert(JST) if created_at_utc.tzinfo is None else created_at_utc.tz_convert(JST)
            created_str = created_at_jst.strftime("%Y/%m/%d %H:%M")

            # メール送信状態
            email_icon = "✉️" if pd.notna(task.get('email_sent_at')) else ""

            # フロータイプアイコン
            flow_icon = "📦" if task.get('flow_type') == 'normal' else "📷"

            with st.container():
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([0.8, 1.2, 0.5, 0.5, 1.5, 2, 2, 1])

                with col1:
                    # 申請番号を表示
                    app_num = task.get('application_number')
                    st.write(f"**#{app_num}**" if app_num else "-")
                with col2:
                    st.write(f"{status_icon} **{status_label}**")
                with col3:
                    st.write(flow_icon)
                with col4:
                    st.write(email_icon)
                with col5:
                    st.write(f"📅 {created_str}")
                with col6:
                    # その他フローの場合、ユーザー入力の商品名を括弧内に表示
                    product_display = task['product_name']
                    if task.get('other_product_name'):
                        product_display = f"{task['product_name']}（{task['other_product_name']}）"
                    st.write(f"📦 {product_display}")
                with col7:
                    st.write(f"👤 {task['recipient_name']}")
                with col8:
                    if st.button("詳細", key=f"task_{task['id']}"):
                        st.session_state['selected_task_id'] = task['id']
                        st.session_state['task_page'] = 'task_detail'
                        logger.info(f"タスク詳細表示: ID={task['id']}")
                        st.rerun()

                st.markdown("---")

    except Exception as e:
        logger.error(f"タスク一覧取得エラー: {e}")
        st.error(f"データの取得に失敗しました: {e}")

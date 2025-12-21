import streamlit as st
from utils.logger import logger

st.set_page_config(
    page_title="PBAP 管理ツール",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlitの自動ページナビゲーションを非表示にする
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# メニューオプション
MENU_OPTIONS = [
    "🏠 ダッシュボード",
    "📋 タスク管理",
    "📦 商品一覧",
    "🔧 システムメンテナンス",
]

# session_stateの初期化
if 'selected_menu' not in st.session_state:
    st.session_state['selected_menu'] = MENU_OPTIONS[0]

# サイドバー メニュー
with st.sidebar:
    st.image("https://via.placeholder.com/200x50/1E3A8A/FFFFFF?text=PBAP+Admin", use_column_width=True)
    st.markdown("---")

    # メニュー（1つのラジオボタングループで4つのメニューを管理）
    selected_page = st.radio(
        "メニュー",
        options=MENU_OPTIONS,
        index=MENU_OPTIONS.index(st.session_state['selected_menu']),
        key="menu_radio"
    )

    # ラジオ選択が変わったらsession_stateを更新
    if selected_page != st.session_state['selected_menu']:
        st.session_state['selected_menu'] = selected_page
        logger.info(f"ページ遷移: {selected_page}")
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 👤 ユーザー情報")
    st.caption("ログイン中: 管理者")
    if st.button("🚪 ログアウト", use_container_width=True):
        st.info("ログアウト機能は今後実装予定です")

# メインコンテンツ
st.title("PBAP 管理ツール 🔧")

# ページルーティング（session_stateを使用）
selected_page = st.session_state['selected_menu']

if selected_page == "🏠 ダッシュボード":
    st.header("📊 ダッシュボード")
    st.write("PBAP 管理ツールへようこそ。")

    # DBからタスク数を取得
    try:
        from utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        tasks_response = supabase.table("tasks").select("status").execute()

        pending_count = 0
        processing_count = 0
        completed_count = 0

        if tasks_response.data:
            for task in tasks_response.data:
                if task['status'] == 'pending':
                    pending_count += 1
                elif task['status'] == 'processing':
                    processing_count += 1
                elif task['status'] == 'completed':
                    completed_count += 1

        # サマリーカード
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="📋 未処理タスク", value=pending_count)
        with col2:
            st.metric(label="⏳ 処理中タスク", value=processing_count)
        with col3:
            st.metric(label="✅ 完了タスク", value=completed_count)
    except Exception as e:
        logger.error(f"ダッシュボード: タスク数取得エラー - {e}")
        st.error(f"データ取得エラー: {e}")

    st.markdown("---")
    st.info("💡 サイドバーから各機能を選択してください。")

    # クイックアクション
    st.subheader("🚀 クイックアクション")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 タスク管理を開く", use_container_width=True):
            st.session_state['task_page'] = None  # タスク一覧へ
            st.session_state['selected_menu'] = "📋 タスク管理"
            logger.info("クイックアクション: タスク管理を開く")
            st.rerun()
    with col2:
        if st.button("📦 商品一覧を開く", use_container_width=True):
            st.session_state['current_page'] = None  # 商品一覧へ
            st.session_state['selected_menu'] = "📦 商品一覧"
            logger.info("クイックアクション: 商品一覧を開く")
            st.rerun()

    st.markdown("---")
    # 最近のタスク表示
    st.subheader("📈 最近のタスク")
    try:
        recent_tasks = supabase.table("tasks").select("*").order("created_at", desc=True).limit(5).execute()
        if recent_tasks.data:
            for task in recent_tasks.data:
                status_icon = {"pending": "📋", "processing": "⏳", "completed": "✅", "cancelled": "❌"}.get(task['status'], "❓")
                st.write(f"{status_icon} **{task['product_name']}** - {task['recipient_name']}")
        else:
            st.info("タスクがありません")
    except:
        st.info("タスク情報を取得できません")

elif selected_page == "📋 タスク管理":
    # task_pageによるサブページ遷移
    if st.session_state.get('task_page') == 'task_detail':
        import pages.task_detail as task_detail
        task_detail.app()
    else:
        import pages.task_list as task_list
        task_list.app()

elif selected_page == "📦 商品一覧":
    # current_pageによるサブページ遷移
    if st.session_state.get('current_page'):
        if st.session_state['current_page'] == 'product_detail':
            import pages.product_detail as product_detail
            product_detail.app()
        elif st.session_state['current_page'] == 'assembly_page_add':
            import pages.assembly_page_add as assembly_page_add
            assembly_page_add.app()
        elif st.session_state['current_page'] == 'assembly_page_detail':
            import pages.assembly_page_detail as assembly_page_detail
            assembly_page_detail.app()
        elif st.session_state['current_page'] == 'assembly_page_reupload':
            import pages.assembly_page_reupload as assembly_page_reupload
            assembly_page_reupload.app()
        elif st.session_state['current_page'] == 'assembly_number_add':
            import pages.assembly_number_add as assembly_number_add
            assembly_number_add.app()
        elif st.session_state['current_page'] == 'assembly_number_detail':
            import pages.assembly_number_detail as assembly_number_detail
            assembly_number_detail.app()
        elif st.session_state['current_page'] == 'part_edit':
            import pages.part_edit as part_edit
            part_edit.app()
    else:
        import pages.product_list as product_list
        product_list.app()

elif selected_page == "🔧 システムメンテナンス":
    import pages.system_maintenance as system_maintenance
    system_maintenance.app()


import streamlit as st
from config import init_csv, load_data
from dashboard import render_dashboard
from workflow_view import render_workflow_view
from order_create import render_create_order
from order_manage import render_order_manage
from status_detail import render_status_detail

# 全局页面配置
st.set_page_config(
    page_title="Group Booking System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------- 登录模块 ----------------------
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

if st.session_state["user_role"] is None:
    with st.form("login_form", border=True):
        st.subheader("系统登录 / System Login")
        uname = st.text_input("账号 / Username")
        pwd = st.text_input("密码 / Password", type="password")
        submit_login = st.form_submit_button("登录 Login", type="primary")
        if submit_login:
            if uname == "Elon" and pwd == "0623":
                st.session_state["user_role"] = "admin"
                st.rerun()
            if uname == "Harriny" and pwd == "8899":
                st.session_state["user_role"] = "admin"
                st.rerun()
            elif uname == "OP" and pwd == "8888":
                st.session_state["user_role"] = "OP"
                st.rerun()
            else:
                st.error("账号或密码错误 / Wrong username or password")
    st.stop()

# ---------------------- 全局美化CSS（彻底消除下拉外框） ----------------------
custom_css = """
<style>
* {
    font-family: "Microsoft YaHei", Arial, sans-serif;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    padding-left: 3rem;
    padding-right: 3rem;
}
h2, h3 {
    color: #1e293b !important;
    font-weight: 600;
}
.stExpander {
    border-radius: 12px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
    border: none !important;
}
.stExpander > div:first-child {
    border-radius: 12px !important;
}
.stButton > button {
    border-radius: 8px !important;
    height: 40px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}
button[key^="btn_"] {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    height: 38px !important;
    transition: all 0.24s ease;
}
button[key^="btn_"]:hover {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    transform: translateY(-3px);
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.32);
}
.stTextInput > div > div > input,
.stSelectbox > div > div > select,
.stDateInput > div > div > input {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
}
.stDataFrame {
    border-radius: 10px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #cbd5e1, transparent);
    margin: 24px 0;
}
.stInfo, .stSuccess, .stWarning, .stError {
    border-radius: 10px !important;
}

/* ====================== 浅色系科技导航侧边栏（移除导航白色方框） ====================== */
[data-testid="stSidebar"] {
    background-color: #f1f5f9 !important;
    padding: 20px 12px !important;
}
/* 侧边栏标题 */
[data-testid="stSidebar"] h3 {
    color: #0369a1 !important;
    letter-spacing: 1px;
    padding-bottom: 8px;
}
/* 单选框导航容器间距 */
[data-testid="stSidebar"] .stRadio > div {
    gap: 8px;
}
/* ========== 核心修改：移除导航按钮外框、灰色背景 ========== */
[data-testid="stSidebar"] .stRadio label {
    border-radius: 0;
    padding: 8px 10px;
    background: transparent !important;
    border: none !important;
    color: #1e293b;
    transition: all 0.25s ease;
}
/* 鼠标悬浮仅文字变色，无外框 */
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(14, 165, 233, 0.12);
}
/* 当前选中导航 柔和浅蓝背景，无边框 */
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: linear-gradient(90deg, #3b82f6, #0ea5e9);
    color: white !important;
    font-weight: 600;
}
/* 侧边栏返回按钮浅科技蓝 */
[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(90deg, #3b82f6, #0284c7) !important;
    border: 1px solid #0ea5e9 !important;
    box-shadow: 0 0 4px rgba(14,165,233,0.15);
}
[data-testid="stSidebar"] .stButton button:hover {
    box-shadow: 0 0 10px rgba(14,165,233,0.3);
}
/* 侧边下拉文字深色适配浅色背景 */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSelectbox div {
    color: #1e293b !important;
}
/* 彻底隐藏外层容器边框阴影，只保留输入框细线 */
[data-testid="stSidebar"] div:has(.stSelectbox) {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
}
[data-testid="stSidebar"] .stSelectbox {
    border: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
}
/* 仅内部输入框留一条细边框 */
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------- 会话状态初始化 ----------------------
if "lang" not in st.session_state:
    st.session_state["lang"] = "zh"
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "dashboard"
if "jump_status" not in st.session_state:
    st.session_state["jump_status"] = None
# 数据仅初始化加载一次
if "data_df" not in st.session_state:
    init_csv()


# CSS 仅渲染一次，避免重复渲染拖慢加载
if "css_rendered" not in st.session_state:
    st.markdown(custom_css, unsafe_allow_html=True)
    st.session_state["css_rendered"] = True

# ---------------------- 双语文本库 ----------------------
TEXT = {
    "zh": {
        "page_title": "🏢 团房信息管理系统",
        "lang_label": "Language",
        "zh_name": "中文",
        "en_name": "English",
        "nav_header": "功能导航",
        "dash": "数据统计看板",
        "flow": "流程进度跟踪看板",
        "new_order": "新增团单",
        "list_manage": "团单列表管理",
        "back": "← 返回数据统计看板"
    },
    "en": {
        "page_title": "🏢 Group Booking Management System",
        "lang_label": "Language",
        "zh_name": "Chinese",
        "en_name": "English",
        "nav_header": "Navigation",
        "dash": "Data Dashboard",
        "flow": "Workflow Tracking",
        "new_order": "New Group Booking",
        "list_manage": "Booking Manage",
        "back": "← Back to Dashboard"
    }
}

# 读取语言
lang = st.session_state["lang"]
t = TEXT[lang]
user_role = st.session_state["user_role"]

# 页面主标题（无渐变，无蓝色图标块）
st.markdown(f"# {t['page_title']}")
st.divider()

# 加载数据
init_csv()
df = load_data()

# ---------------------- 侧边栏（精简语言区，无多余容器） ----------------------
with st.sidebar:
    st.markdown("### 🌐 " + t["lang_label"])
    # label设为空字符串，减少额外DOM生成
    new_lang = st.selectbox(
        label="",
        options=["zh", "en"],
        format_func=lambda x: TEXT[x]["zh_name"] if x == "zh" else TEXT[x]["en_name"]
    )
    if new_lang != lang:
        st.session_state["lang"] = new_lang
        st.rerun()

    st.divider()
    st.markdown(f"### 📂 {t['nav_header']}")

    all_pages = {
        "dashboard": t["dash"],
        "flow": t["flow"],
        "new_order": t["new_order"],
        "list_manage": t["list_manage"]
    }
    show_pages = list(all_pages.keys()) if user_role == "admin" else ["dashboard", "flow"]

    selected_page = st.radio(
        label="",
        options=show_pages,
        format_func=lambda k: all_pages[k]
    )
    if selected_page != st.session_state["current_page"]:
        st.session_state["jump_status"] = None
        st.session_state["current_page"] = selected_page
        st.rerun()

    if st.session_state["jump_status"] is not None:
        st.divider()
        if st.button(t["back"], type="primary", use_container_width=True):
            st.session_state["jump_status"] = None
            st.rerun()

# ---------------------- 页面路由 ----------------------
active_p = st.session_state["current_page"]
if st.session_state["jump_status"] is not None:
    render_status_detail(df)
else:
    if active_p == "dashboard":
        render_dashboard(df)
    elif active_p == "flow":
        render_workflow_view(df)
    elif active_p == "new_order" and user_role == "admin":
        render_create_order(df)
    elif active_p == "list_manage" and user_role == "admin":
        render_order_manage(df)
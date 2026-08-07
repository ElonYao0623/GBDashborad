import streamlit as st
from config import init_csv, load_data
from dashboard import render_dashboard
from workflow_view import render_workflow_view
from order_create import render_create_order
from order_manage import render_order_manage
from status_detail import render_status_detail
from Hotel_list import render_hotel_list
from price_compare import render_price_compare
from price_compare_dashboard import render_price_compare_dashboard
from sales_dashboard import render_sales_dashboard
from Failed_dashboard import render_failed_dashboard
from Success_dashboard import render_success_dashboard

# 全局页面配置
st.set_page_config(
    page_title="Group Booking System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------- 登录模块 ----------------------
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "user_team" not in st.session_state:
    st.session_state["user_team"] = None

USER_ACCOUNTS = {
    "Elon": {"password": "0623", "role": "admin", "team": None},
    "Harriny": {"password": "8899", "role": "admin", "team": None},
    "OP": {"password": "8888", "role": "OP", "team": None},
    "MY": {"password": "my1234", "role": "sales", "team": "MY"},
    "ID": {"password": "id1234", "role": "sales", "team": "ID"},
    "MEA": {"password": "mea1234", "role": "sales", "team": "MEA"}
}

if st.session_state["user_role"] is None:
    with st.form("login_form", border=True):
        st.subheader("系统登录 / System Login")
        uname = st.text_input("账号 / Username")
        pwd = st.text_input("密码 / Password", type="password")
        submit_login = st.form_submit_button("登录 Login", type="primary")
        if submit_login:
            if uname in USER_ACCOUNTS and USER_ACCOUNTS[uname]["password"] == pwd:
                st.session_state["user_role"] = USER_ACCOUNTS[uname]["role"]
                st.session_state["user_team"] = USER_ACCOUNTS[uname]["team"]
                st.rerun()
            else:
                st.error("账号或密码错误 / Wrong username or password")
    st.stop()

# ---------------------- 全局美化CSS（彻底消除下拉外框） ----------------------
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

* {
    font-family: "DM Sans", "Microsoft YaHei", Arial, sans-serif;
}

/* ====================== SaaS/Startup 主题配色 ====================== */
/* 主背景:纯白#ffffff | 侧栏:浅灰#fafafa | 主色:现代紫#8b5cf6 | 文字:锌深#18181b | 链接:深紫#7c3aed | 边框:浅灰#e4e4e7 */

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    padding-left: 3rem;
    padding-right: 3rem;
}
h1, h2, h3 {
    font-family: "DM Sans", "Microsoft YaHei", sans-serif !important;
    color: #18181b !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px;
}
code, pre {
    font-family: "Fira Code", "Consolas", monospace !important;
}

/* ========== 折叠面板:现代圆角 + 柔和阴影 ========== */
.stExpander {
    border-radius: 0.75rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
    border: 1px solid #e4e4e7 !important;
    background: #ffffff !important;
    transition: all 0.2s ease;
}
.stExpander:hover {
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.12) !important;
    border-color: #8b5cf6 !important;
}
.stExpander > div:first-child {
    border-radius: 0.75rem !important;
}

/* ========== 按钮:现代紫 + 友好圆角 ========== */
.stButton > button {
    border-radius: 0.75rem !important;
    height: 42px !important;
    font-weight: 500 !important;
    background: #8b5cf6 !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 1px 3px rgba(139, 92, 246, 0.25) !important;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    background: #7c3aed !important;
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.35) !important;
    transform: translateY(-1px);
}

/* 次要按钮(如删除):浅灰 */
.stButton > button[k*="quick_del"] {
    background: #f4f4f5 !important;
    color: #18181b !important;
    border: 1px solid #e4e4e7 !important;
    box-shadow: none !important;
}

button[key^="btn_"] {
    background: #8b5cf6 !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 500 !important;
    border-radius: 0.75rem !important;
    height: 40px !important;
    box-shadow: 0 1px 3px rgba(139, 92, 246, 0.25) !important;
    transition: all 0.2s ease;
}
button[key^="btn_"]:hover {
    background: #7c3aed !important;
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.35) !important;
    transform: translateY(-1px);
}

/* ========== 输入框/下拉框:现代圆角 + 浅边框 ========== */
.stTextInput > div > div > input,
.stSelectbox [data-baseweb="select"],
.stDateInput > div > div > input,
.stNumberInput > div > div > input {
    border-radius: 0.75rem !important;
    border: 1px solid #e4e4e7 !important;
    background: #ffffff !important;
    transition: all 0.15s ease;
}
.stTextInput > div > div > input:focus,
.stSelectbox [data-baseweb="select"]:focus,
.stDateInput > div > div > input:focus {
    border-color: #8b5cf6 !important;
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.12) !important;
}

/* ========== 数据表格:现代圆角 + 阴影 ========== */
.stDataFrame {
    border-radius: 0.75rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #e4e4e7 !important;
    overflow: hidden;
}

/* ========== 分隔线:柔和渐变 ========== */
hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #e4e4e7, transparent);
    margin: 24px 0;
}

/* ========== 提示框:现代圆角 ========== */
.stInfo, .stSuccess, .stWarning, .stError {
    border-radius: 0.75rem !important;
    border-width: 1px !important;
}
.stInfo {
    background: #faf5ff !important;
    border-color: #8b5cf6 !important;
}
.stSuccess {
    background: #f0fdf4 !important;
    border-color: #22c55e !important;
}
.stWarning {
    background: #fffbeb !important;
    border-color: #f59e0b !important;
}
.stError {
    background: #fef2f2 !important;
    border-color: #ef4444 !important;
}

/* ========== Tab标签:现代风 ========== */
.stTabs [role="tab"] {
    border-radius: 0.75rem 0.75rem 0 0 !important;
    padding: 8px 16px !important;
    color: #18181b !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    background: #8b5cf6 !important;
    color: #ffffff !important;
}

/* ====================== 浅灰侧边栏(SaaS风格) ====================== */
[data-testid="stSidebar"] {
    background: #fafafa !important;
    padding: 20px 12px !important;
    border-right: 1px solid #e4e4e7 !important;
}
[data-testid="stSidebar"] h3 {
    color: #8b5cf6 !important;
    letter-spacing: 0.3px;
    padding-bottom: 8px;
    font-family: "DM Sans", "Microsoft YaHei", sans-serif !important;
}
[data-testid="stSidebar"] .stRadio > div {
    gap: 6px;
}
[data-testid="stSidebar"] .stRadio label {
    border-radius: 0.75rem;
    padding: 10px 14px;
    background: transparent !important;
    border: none !important;
    color: #18181b;
    font-weight: 500;
    transition: all 0.2s ease;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(139, 92, 246, 0.08) !important;
    color: #8b5cf6 !important;
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: #8b5cf6 !important;
    color: white !important;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(139, 92, 246, 0.3);
}
[data-testid="stSidebar"] .stButton button {
    background: #8b5cf6 !important;
    border: none !important;
    border-radius: 0.75rem !important;
    box-shadow: 0 1px 3px rgba(139, 92, 246, 0.25);
}
[data-testid="stSidebar"] .stButton button:hover {
    background: #7c3aed !important;
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.35);
}

/* 侧边下拉文字适配 */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSelectbox div {
    color: #18181b !important;
}
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
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
    border: 1px solid #e4e4e7 !important;
    border-radius: 0.75rem !important;
}

/* ========== 指标卡:现代圆角 ========== */
[data-testid="stMetric"] {
    background: #fafafa !important;
    padding: 16px 20px !important;
    border-radius: 0.75rem !important;
    border: 1px solid #e4e4e7 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

/* ========== 链接:深紫 ========== */
a {
    color: #7c3aed !important;
    text-decoration: none;
    transition: color 0.15s;
}
a:hover {
    color: #8b5cf6 !important;
    text-decoration: underline;
}

/* ========== 滚动条:现代风 ========== */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: #fafafa;
}
::-webkit-scrollbar-thumb {
    background: #e4e4e7;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #8b5cf6;
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
        "hotel_list": "优势酒店名单",
        "price_compare": "比价",
        "price_dashboard": "比价记录看板",
        "sales_dashboard": "销售团队统计",
        "failed_dashboard": "团房失败分析",
        "success_dashboard": "团房成功统计",
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
        "hotel_list": "Preferred Hotels",
        "price_compare": "Price Compare",
        "price_dashboard": "Price Dashboard",
        "sales_dashboard": "Sales Team Stats",
        "failed_dashboard": "Failed Booking Analysis",
        "success_dashboard": "Success Booking Stats",
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

# 根据销售团队过滤数据（仅销售用户）
user_team = st.session_state["user_team"]
if user_role == "sales" and user_team:
    df = df[df["Salesteam"].str.contains(user_team, case=False, na=False)]

# ---------------------- 侧边栏（精简语言区，无多余容器） ----------------------
with st.sidebar:
    st.markdown("### 🌐 " + t["lang_label"])
    # label设为空字符串，减少额外DOM生成
    new_lang = st.selectbox(
        label="语言选择",
        options=["zh", "en"],
        format_func=lambda x: TEXT[x]["zh_name"] if x == "zh" else TEXT[x]["en_name"],
        label_visibility="collapsed"
    )
    if new_lang != lang:
        st.session_state["lang"] = new_lang
        st.rerun()

    st.divider()
    st.markdown(f"### 📂 {t['nav_header']}")

    all_pages = {
        "dashboard": t.get("dash", "Dashboard"),
        "sales_dashboard": t.get("sales_dashboard", "Sales Dashboard"),
        "success_dashboard": t.get("success_dashboard", "Success Dashboard"),
        "failed_dashboard": t.get("failed_dashboard", "Failed Dashboard"),
        "flow": t.get("flow", "Workflow"),
        "hotel_list": t.get("hotel_list", "Hotel List"),
        "price_dashboard": t.get("price_dashboard", "Price Dashboard"),
        "price_compare": t.get("price_compare", "Price Compare"),
        "new_order": t.get("new_order", "New Order"),
        "list_manage": t.get("list_manage", "Order Manage")
    }
    if user_role == "admin":
        show_pages = list(all_pages.keys())
    elif user_role == "OP":
        show_pages = ["dashboard", "sales_dashboard", "success_dashboard", "failed_dashboard", "flow", "hotel_list", "price_dashboard"]
    elif user_role == "sales":
        show_pages = ["dashboard", "flow", "hotel_list", "price_dashboard", "sales_dashboard"]
    else:
        show_pages = ["dashboard", "flow", "hotel_list", "price_dashboard"]

    # 过滤掉 all_pages 中不存在的页面，避免 KeyError
    show_pages = [p for p in show_pages if p in all_pages]

    selected_page = st.radio(
        label="页面选择",
        options=show_pages,
        format_func=lambda k: all_pages.get(k, k),
        label_visibility="collapsed"
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
user_team = st.session_state["user_team"]

if st.session_state["jump_status"] is not None:
    render_status_detail(df)
else:
    if active_p == "dashboard":
        render_dashboard(df)
    elif active_p == "sales_dashboard":
        render_sales_dashboard(df)
    elif active_p == "success_dashboard":
        render_success_dashboard(df)
    elif active_p == "failed_dashboard":
        render_failed_dashboard(df)
    elif active_p == "flow":
        render_workflow_view(df)
    elif active_p == "new_order" and user_role == "admin":
        render_create_order(df)
    elif active_p == "list_manage":
        render_order_manage(df, user_team=user_team)
    elif active_p == "hotel_list":
        render_hotel_list(df)
    elif active_p == "price_compare":
        render_price_compare(df)
    elif active_p == "price_dashboard":
        render_price_compare_dashboard()
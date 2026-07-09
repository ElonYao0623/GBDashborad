import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from config import get_workflow_step_text

# 页面双语文本
PAGE_TEXT = {
    "zh": {
        "page_header": "📈 状态数据详情图表页",
        "fail_group_title": "全部失败终止订单",
        "filter_status_title": "筛选状态：{}",
        "order_count_tip": "该状态订单总数：{}",
        "pie_title": "全局状态占比饼图",
        "pie_chart_title": "全量订单各状态分布占比",
        "list_title": "对应订单列表",
        "col_index": "序号",
        "col_order_id": "团单号",
        "col_customer": "客户名称",
        "col_bd": "BD",
        "col_country": "国家",
        "col_status": "状态",
        "col_joy_price": "Joy 底价 Joy's Net Rate",
        "col_ops_note": "运营备注 Ops Notes",
        "col_day_to_checkin": "距离入住天数",
        "col_fail_reason": "未成单原因"
    },
    "en": {
        "page_header": "📈 Status Detail Chart Page",
        "fail_group_title": "All Failed & Terminated Orders",
        "filter_status_title": "Filter Status: {}",
        "order_count_tip": "Total orders of this status: {}",
        "pie_title": "Global Status Proportion Pie Chart",
        "pie_chart_title": "All Orders Status Distribution",
        "list_title": "Matching Order List",
        "col_index": "No.",
        "col_order_id": "Order No.",
        "col_customer": "Customer Name",
        "col_bd": "BD Sales",
        "col_country": "Country",
        "col_status": "Status",
        "col_joy_price": "Joy's Net Rate",
        "col_ops_note": "Operation Notes",
        "col_day_to_checkin": "Days Until Check-in",
        "col_fail_reason": "Failure Reason"
    }
}

# 兼容中英文字体
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

def render_status_detail(df):
    lang = st.session_state["lang"]
    t = PAGE_TEXT[lang]
    target_status_raw = st.session_state["jump_status"]
    all_df = df.copy()

    # 筛选数据 + 标题国际化
    all_df["状态"] = all_df["状态"].fillna("").astype(str).str.strip()
    from config import get_standard_status
    all_df["标准状态"] = all_df["状态"].apply(get_standard_status)
    
    if target_status_raw == "失败组":
        filter_df = all_df[all_df["状态"].isin(["锁房失败", "团房失败终止", "团房失败"])]
        page_sub_title = t["fail_group_title"]
    else:
        filter_df = all_df[all_df["标准状态"] == target_status_raw]
        show_status_name = get_workflow_step_text(lang, target_status_raw)
        page_sub_title = t["filter_status_title"].format(show_status_name)

    st.header(t["page_header"])
    st.divider()
    st.subheader(page_sub_title)
    st.success(t["order_count_tip"].format(len(filter_df)))
    st.divider()

    # 计算距离入住天数（与workflow_view.py和dashboard.py保持一致）
    from datetime import date
    def calc_day(s):
        try:
            x = str(s).strip()
            if not x:
                return None
            if "/" in x:
                d = datetime.strptime(x, "%Y/%m/%d").date()
            else:
                d = datetime.strptime(x, "%Y-%m-%d").date()
            return (d - date.today()).days
        except:
            return None
    
    if "入住日期 Check-in Date" not in filter_df.columns:
        filter_df["入住日期 Check-in Date"] = ""
    filter_df["距离入住天数"] = filter_df["入住日期 Check-in Date"].apply(calc_day)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(t["pie_title"])
        status_cnt = all_df["状态"].value_counts()
        # 饼图标签翻译
        pie_labels = [get_workflow_step_text(lang, s) for s in status_cnt.index]
        fig, ax = plt.subplots(figsize=(5,5))
        ax.pie(status_cnt.values, labels=pie_labels, autopct="%1.1f%%")
        ax.set_title(t["pie_chart_title"], fontsize=10)
        ax.axis("equal")
        st.pyplot(fig)

    with col2:
        st.subheader(t["list_title"])
        # 表头映射双语
        col_mapping = {
            "团单号": t["col_order_id"],
            "客户名称 Customer Name": t["col_customer"],
            "销售姓名 Sales Name": t["col_bd"],
            "距离入住天数": t["col_day_to_checkin"]
        }
        show_cols_raw = list(col_mapping.keys())
        show_cols_raw = [c for c in show_cols_raw if c in filter_df.columns]

        display_df = filter_df[show_cols_raw].copy()
        # 插入序号
        display_df.insert(0, t["col_index"], range(1, len(display_df)+1))
        # 替换表头为英文
        display_df.columns = [col_mapping.get(c, c) for c in display_df.columns]

        st.dataframe(display_df, use_container_width=True, hide_index=True)
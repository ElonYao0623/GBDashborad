import streamlit as st
import pandas as pd
from datetime import datetime
from config import get_workflow_step_text

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
        "col_sales_team": "销售团队",
        "col_status": "状态",
        "col_checkin": "入住日期",
        "col_days": "距离入住天数",
        "col_last_update": "最后更新时间",
        "col_fail_reason": "失败原因"
    },
    "en": {
        "page_header": "📈 Status Detail Dashboard",
        "fail_group_title": "All Failed Orders",
        "filter_status_title": "Filter Status: {}",
        "order_count_tip": "Total Orders: {}",
        "pie_title": "Status Distribution",
        "pie_chart_title": "All Orders Status Distribution",
        "list_title": "Order List",
        "col_index": "#",
        "col_order_id": "Order No.",
        "col_customer": "Customer",
        "col_bd": "BD",
        "col_sales_team": "Sales Team",
        "col_status": "Status",
        "col_checkin": "Check-in",
        "col_days": "Days to Check-in",
        "col_last_update": "Last Update",
        "col_fail_reason": "Failure Reason"
    }
}

def render_status_detail(df):
    import matplotlib.pyplot as plt
    from config import configure_matplotlib_font
    configure_matplotlib_font()
    
    lang = st.session_state["lang"]
    t = PAGE_TEXT[lang]
    target_status_raw = st.session_state["jump_status"]
    all_df = df.copy()

    all_df["状态"] = all_df["状态"].fillna("").astype(str).str.strip()
    from config import get_standard_status
    all_df["标准状态"] = all_df["状态"].apply(get_standard_status)
    
    if target_status_raw == "失败组":
        filter_df = all_df[all_df["状态"].isin(["锁房失败", "团房失败终止", "团房失败"])]
        status_display = t["fail_group_title"]
    else:
        filter_df = all_df[all_df["标准状态"] == target_status_raw]
        status_display = get_workflow_step_text(lang, target_status_raw)

    st.header(t["page_header"])
    st.subheader(t["filter_status_title"].format(status_display))
    st.info(t["order_count_tip"].format(len(filter_df)))

    st.divider()
    st.subheader(t["pie_title"])
    status_counts = all_df["状态"].value_counts()
    labels = status_counts.index.tolist()
    sizes = status_counts.values.tolist()
    
    if sizes and sum(sizes) > 0:
        fig, ax = plt.subplots(figsize=(5,5))
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        plt.title(t["pie_chart_title"])
        st.pyplot(fig)
    else:
        st.info(t["order_count_tip"].format(0))

    st.divider()
    st.subheader(t["list_title"])
    
    def calc_day(s):
        try:
            x = str(s).strip()
            if not x:
                return None
            if "/" in x:
                d = datetime.strptime(x, "%Y/%m/%d").date()
            else:
                d = datetime.strptime(x, "%Y-%m-%d").date()
            return (d - datetime.now().date()).days
        except:
            return None
    
    display_df = filter_df.copy()
    if "入住日期 Check-in Date" in display_df.columns:
        display_df["距离入住天数"] = display_df["入住日期 Check-in Date"].apply(calc_day)
    
    display_columns = [
        "团单号", "客户名称 Customer Name", "BD", "Salesteam", 
        "状态", "入住日期 Check-in Date", "距离入住天数", "最后更新时间"
    ]
    display_df = display_df[[col for col in display_columns if col in display_df.columns]]
    
    display_df.columns = [
        t["col_order_id"], t["col_customer"], t["col_bd"], t["col_sales_team"],
        t["col_status"], t["col_checkin"], t["col_days"], t["col_last_update"]
    ][:len(display_df.columns)]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

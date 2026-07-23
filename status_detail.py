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
        "col_sales_name": "销售姓名",
        "col_status": "状态",
        "col_checkin": "入住日期",
        "col_days": "距离入住天数",
        "col_last_update": "最后更新时间",
        "col_fail_reason_1": "失败原因（一级）",
        "col_fail_reason_2": "失败原因（二级）"
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
        "col_sales_name": "Sales Name",
        "col_status": "Status",
        "col_checkin": "Check-in",
        "col_days": "Days to Check-in",
        "col_last_update": "Last Update",
        "col_fail_reason_1": "Failure Reason (Level 1)",
        "col_fail_reason_2": "Failure Reason (Level 2)"
    }
}

def render_status_detail(df):
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    from config import configure_matplotlib_font
    configure_matplotlib_font()
    font_prop = fm.FontProperties()
    
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

    def safe_str(val):
        if pd.isna(val):
            return ""
        raw = str(val).strip()
        raw = raw.replace("\n", "").replace("\r", "").replace("　", "")
        if raw in ["nan", "NaN", "None", "null", ""]:
            return ""
        return raw

    def get_val(row, col):
        if col not in row.index:
            return ""
        return safe_str(row.get(col, ""))

    # 展示每个订单详情（只读）
    if "sd_expand_idx" not in st.session_state:
        st.session_state["sd_expand_idx"] = None

    for idx, row in display_df.iterrows():
        order_no = get_val(row, "团单号")
        cust_name = get_val(row, "客户名称 Customer Name")
        sales_name = get_val(row, "销售姓名 Sales Name")
        days = get_val(row, "距离入住天数")
        expand_title = f"【{order_no}】客户：{cust_name} | 销售：{sales_name} | 距离入住：{days}天"

        col_btn, col_info = st.columns([1, 5])
        with col_btn:
            if st.button(f"🔍 {order_no}", key=f"sd_btn_{idx}", use_container_width=True):
                st.session_state["sd_expand_idx"] = idx if st.session_state["sd_expand_idx"] != idx else None
                st.rerun()
        with col_info:
            st.markdown(f"**客户：** {cust_name}　**销售：** {sales_name}　**距离入住：** {days}天")

        if st.session_state["sd_expand_idx"] == idx:
            st.markdown("#### 一、基础客户信息")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.text_input("团单号", value=get_val(row, "团单号"), disabled=True, key=f"sd_{idx}_order_no")
                st.text_input("客户名称 Customer Name", value=get_val(row, "客户名称 Customer Name"), disabled=True, key=f"sd_{idx}_cust")
                st.text_input("User ID", value=get_val(row, "User ID"), disabled=True, key=f"sd_{idx}_uid")
                st.text_input("国籍 Nationality", value=get_val(row, "国籍 Nationality"), disabled=True, key=f"sd_{idx}_nat")
            with c2:
                st.text_input("国家 Country", value=get_val(row, "国家 Country"), disabled=True, key=f"sd_{idx}_country")
                st.text_input("联系方式 Contact Info", value=get_val(row, "联系方式 Contact Info"), disabled=True, key=f"sd_{idx}_contact")
                st.text_input("销售团队 Salesteam", value=get_val(row, "Salesteam"), disabled=True, key=f"sd_{idx}_team")
            with c3:
                st.text_input("销售姓名 Sales Name", value=get_val(row, "销售姓名 Sales Name"), disabled=True, key=f"sd_{idx}_sales")
                st.text_input("提交时间 Submitted by", value=get_val(row, "提交时间 Submitted by"), disabled=True, key=f"sd_{idx}_submit")
                st.text_input("最后更新时间", value=get_val(row, "最后更新时间"), disabled=True, key=f"sd_{idx}_lastup")
                st.text_input("状态", value=get_val(row, "状态"), disabled=True, key=f"sd_{idx}_status")

            st.markdown("#### 二、酒店信息")
            c4, c5, c6 = st.columns(3)
            with c4:
                st.text_input("酒店名称 Hotel Name", value=get_val(row, "酒店名称 Hotel Name"), disabled=True, key=f"sd_{idx}_hotel")
                st.text_input("酒店星级 Star Rating", value=get_val(row, "酒店星级 Star Rating"), disabled=True, key=f"sd_{idx}_star")
                st.text_input("入住日期 Check-in Date", value=get_val(row, "入住日期 Check-in Date"), disabled=True, key=f"sd_{idx}_checkin")
            with c5:
                st.text_input("离店日期 Check-out Date", value=get_val(row, "离店日期 Check-out Date"), disabled=True, key=f"sd_{idx}_checkout")
                st.text_input("房型要求 Room Type", value=get_val(row, "房型要求 Room Type"), disabled=True, key=f"sd_{idx}_rtype")
                st.text_input("房间总数 Total Rooms", value=get_val(row, "房间总数 Total Rooms"), disabled=True, key=f"sd_{idx}_rtotal")
            with c6:
                st.text_input("房间数 Rooms", value=get_val(row, "房间数 Rooms"), disabled=True, key=f"sd_{idx}_rcnt")
                st.text_input("间夜数 Room Nights", value=get_val(row, "间夜数 Room Nights"), disabled=True, key=f"sd_{idx}_night")

            st.markdown("#### 三、需求与报价")
            c7, c8, c9 = st.columns(3)
            with c7:
                st.text_input("报价币种 Currency", value=get_val(row, "报价币种 Currency"), disabled=True, key=f"sd_{idx}_curr")
                st.text_input("预算范围 Budget Range", value=get_val(row, "预算范围 Budget Range"), disabled=True, key=f"sd_{idx}_budget")
                st.text_input("会议室/交通需求", value=get_val(row, "会议室/交通需求 Meeting Room / Transportation Requirements"), disabled=True, key=f"sd_{idx}_meet")
            with c8:
                st.text_input("出行目的 Purpose of travel", value=get_val(row, "出行目的 Purpose of travel"), disabled=True, key=f"sd_{idx}_purp")
                st.text_input("特殊需求 Special Requests", value=get_val(row, "特殊需求 Special Requests"), disabled=True, key=f"sd_{idx}_spec")
                st.text_input("Joy底价", value=get_val(row, "Joy 底价 Joy's Net Rate"), disabled=True, key=f"sd_{idx}_joy")
            with c9:
                st.text_input("建议卖价 Suggested Selling Price", value=get_val(row, "建议卖价 Suggested Selling Price"), disabled=True, key=f"sd_{idx}_sell")
                st.text_input("额外税费需求 Extra tax if needed", value=get_val(row, "额外税费需求 Extra tax if needed"), disabled=True, key=f"sd_{idx}_tax")
                st.text_input("房间保留时间", value=get_val(row, "房间保留时间"), disabled=True, key=f"sd_{idx}_keep")

            st.markdown("#### 四、其他信息")
            c10, c11, c12 = st.columns(3)
            with c10:
                st.text_input("支付方式", value=get_val(row, "支付方式"), disabled=True, key=f"sd_{idx}_pay")
                st.text_input("餐食", value=get_val(row, "餐食"), disabled=True, key=f"sd_{idx}_meal")
            with c11:
                st.text_input("取消政策", value=get_val(row, "取消政策"), disabled=True, key=f"sd_{idx}_cancel")
                st.text_input("未成单原因（一级）", value=get_val(row, "未成单原因（一级）"), disabled=True, key=f"sd_{idx}_fail_1")
                st.text_input("未成单原因（二级）", value=get_val(row, "未成单原因（二级）"), disabled=True, key=f"sd_{idx}_fail_2")
            with c12:
                st.text_input("运营备注 Ops Notes", value=get_val(row, "运营备注 Ops Notes"), disabled=True, key=f"sd_{idx}_ops")
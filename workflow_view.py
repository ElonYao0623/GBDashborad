import streamlit as st
import pandas as pd
from datetime import date, datetime
from config import STATUS_WORKFLOW_MAP, WORKFLOW_STEPS_ZH, save_data, STATUS_FLOW_RULE, get_workflow_step_text, get_standard_status
PAGE_TEXT = {
    "zh": {
        "page_header": "团房全流程跟踪看板",
        "filter_step": "状态筛选",
        "all_step_opt": "全部状态",
        "search_order_cust": "搜索团单/客户",
        "search_bd_team": "搜索BD/团队",
        "day_filter": "入住天数",
        "day_all": "全部",
        "day_today": "今日0天",
        "day_1_7": "1~7天",
        "day_8_15": "8~15天",
        "day_16_30": "16~30天",
        "day_over30": "30天以上",
        "day_expired": "已过期",
        "date_range_label": "创建时间区间",
        "filter_count_tip": "筛选后共{}条有效订单",
        "expander_title": "【{}】{} — {} ({}) ({}天)",
        "distance_checkin": "距离入住",
        "status_duration": "状态持续",
        "checkin_date": "入住日期",
        "hotel_name": "酒店名称",
        "sales_name": "销售姓名",
        "currency": "报价币种",
        "joy_price": "Joy 底价",
        "suggested_price": "建议卖价",
        "room_count": "房间数",
        "fail_reason": "未成单原因",
        "Unknown": "未知",
        "ops_remark": "运营备注"
    },
    "en": {
        "page_header": "Group Booking Full Process Tracking Board",
        "filter_step": "Status Filter",
        "all_step_opt": "All Status",
        "search_order_cust": "Search Order/Customer",
        "search_bd_team": "Search BD/Team",
        "day_filter": "Days to Check-in",
        "day_all": "All",
        "day_today": "Today (0 days)",
        "day_1_7": "1~7 days",
        "day_8_15": "8~15 days",
        "day_16_30": "16~30 days",
        "day_over30": "Over 30 days",
        "day_expired": "Expired",
        "date_range_label": "Create Date Range",
        "filter_count_tip": "{} valid orders after filtering",
        "expander_title": "[{}] {} — {} ({}) ({} days)",
        "distance_checkin": "Days to Check-in",
        "status_duration": "Status Duration",
        "checkin_date": "Check-in Date",
        "hotel_name": "Hotel Name",
        "sales_name": "Sales Name",
        "currency": "Currency",
        "joy_price": "Joy's Net Rate",
        "suggested_price": "Suggested Selling Price",
        "room_count": "Rooms",
        "fail_reason": "Uncompleted Reason",
        "Unknown": "Unknown",
        "ops_remark": "OP Notes"
    }
}
def safe_val(val):
    if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).lower() in ["nan", "none"]:
        return ""
    return str(val).strip()

def render_workflow_view(df):
    lang = st.session_state["lang"]
    t = PAGE_TEXT[lang]
    st.header(t["page_header"])
    st.divider()
    workflow_df = df.copy()
    workflow_df.columns = workflow_df.columns.str.strip()
    # 预处理状态 - 兼容"状态"和"状态 Status"两种列名
    status_col = "状态" if "状态" in workflow_df.columns else "状态 Status" if "状态 Status" in workflow_df.columns else None
    if status_col is None:
        workflow_df["状态"] = ""
    else:
        workflow_df["状态"] = workflow_df[status_col].fillna("").astype(str).str.strip()
    workflow_df["标准状态"] = workflow_df["状态"].apply(get_standard_status)
    workflow_df["当前流程节点"] = workflow_df["标准状态"]
    # 入住天数计算
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
    if "入住日期 Check-in Date" not in workflow_df.columns:
        workflow_df["入住日期 Check-in Date"] = ""
    workflow_df["距离入住天数"] = workflow_df["入住日期 Check-in Date"].apply(calc_day)
    
    def calc_status_days(s):
        try:
            x = str(s).strip()
            if not x:
                return t["Unknown"]
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
                try:
                    d = datetime.strptime(x, fmt).date()
                    return (date.today() - d).days
                except ValueError:
                    continue
            return t["Unknown"]
        except:
            return t["Unknown"]
    
    if "最后更新时间" not in workflow_df.columns:
        workflow_df["最后更新时间"] = ""
    workflow_df["状态持续天数"] = workflow_df["最后更新时间"].apply(calc_status_days)
    
    # 确保搜索所需的列存在
    for col in ["团单号", "客户名称 Customer Name", "销售姓名 Sales Name", "Salesteam"]:
        if col not in workflow_df.columns:
            workflow_df[col] = ""
    
    # 获取所有状态选项（从数据中动态获取，转换为统一显示格式）
    all_status_values = workflow_df["状态"].astype(str).str.strip().unique().tolist()
    all_status_values = [v for v in all_status_values if v and v != "nan"]
    
    status_display_map = {}
    for val in all_status_values:
        std_status = get_standard_status(val)
        display_text = get_workflow_step_text(lang, std_status)
        if display_text not in status_display_map:
            status_display_map[display_text] = []
        status_display_map[display_text].append(val)
    
    status_options = ["全部状态"] + sorted(status_display_map.keys())
    
    # 筛选UI
    st.subheader("🔍 筛选条件")
    r1c1, r1c2, r1c3 = st.columns([2,2,2])
    r2c1, r2c2 = st.columns([2,2])
    with r1c1:
        filter_status_display = st.selectbox(t["filter_step"], status_options)
    with r1c2:
        day_raw = ["全部","0天内(今日)","1~7天","8~15天","16~30天","30天以上","已过期(负数)"]
        day_disp = [t["day_all"],t["day_today"],t["day_1_7"],t["day_8_15"],t["day_16_30"],t["day_over30"],t["day_expired"]]
        day_map = dict(zip(day_disp, day_raw))
        day_sel = st.selectbox(t["day_filter"], day_disp)
        day_range = day_map[day_sel]
    submit_col = None
    for col in ["提交时间 Submitted by", "提交时间 Submitted At", "创建时间"]:
        if col in workflow_df.columns:
            submit_col = col
            break
    with r1c3:
        st.write(t["date_range_label"])
        ca, cb = st.columns(2)
        ds = st.date_input("开始", value=None, disabled=(submit_col is None))
        de = st.date_input("结束", value=None, disabled=(submit_col is None))
    with r2c1:
        search_key = st.text_input(t["search_order_cust"])
    with r2c2:
        search_bd = st.text_input(t["search_bd_team"])
    st.divider()
    # 日期解析（统一返回date对象）
    parse_flag = False
    if submit_col is not None:
        def parse_dt(s):
            try:
                x = str(s).strip()
                if not x or x.lower() in ["nan","none"]:
                    return None
                for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
                    try:
                        return datetime.strptime(x, fmt).date()
                    except ValueError:
                        continue
                return None
            except:
                return None
        workflow_df["_parse_create_dt"] = workflow_df[submit_col].apply(parse_dt)
        parse_flag = True
    # 筛选逻辑（补齐所有分支赋值）
    if filter_status_display != "全部状态":
        matched_values = status_display_map.get(filter_status_display, [])
        if matched_values:
            workflow_df = workflow_df[workflow_df["状态"].astype(str).str.strip().isin(matched_values)]
    if search_key.strip():
        kw = search_key.lower()
        workflow_df = workflow_df[workflow_df["团单号"].str.lower().str.contains(kw, na=False) | workflow_df["客户名称 Customer Name"].str.lower().str.contains(kw, na=False)]
    if search_bd.strip():
        kw = search_bd.lower()
        workflow_df = workflow_df[workflow_df["销售姓名 Sales Name"].str.lower().str.contains(kw, na=False) | workflow_df["Salesteam"].str.lower().str.contains(kw, na=False)]
    # 天数筛选全部补齐赋值
    if day_range != "全部":
        if day_range == "0天内(今日)":
            workflow_df = workflow_df[workflow_df["距离入住天数"] == 0]
        elif day_range == "1~7天":
            workflow_df = workflow_df[(workflow_df["距离入住天数"] >=1) & (workflow_df["距离入住天数"] <=7)]
        elif day_range == "8~15天":
            workflow_df = workflow_df[(workflow_df["距离入住天数"] >=8) & (workflow_df["距离入住天数"] <=15)]
        elif day_range == "16~30天":
            workflow_df = workflow_df[(workflow_df["距离入住天数"] >=16) & (workflow_df["距离入住天数"] <=30)]
        elif day_range == "30天以上":
            workflow_df = workflow_df[workflow_df["距离入住天数"] >30]
        elif day_range == "已过期(负数)":
            workflow_df = workflow_df[workflow_df["距离入住天数"] <0]
    # 日期筛选（修复逻辑：只保留在范围内的记录）
    if parse_flag and (ds or de):
        cond = workflow_df["_parse_create_dt"].notna()
        if ds:
            cond = cond & (workflow_df["_parse_create_dt"] >= ds)
        if de:
            cond = cond & (workflow_df["_parse_create_dt"] <= de)
        workflow_df = workflow_df[cond]
    st.info(t["filter_count_tip"].format(len(workflow_df)))
    st.divider()

    # 按距离入住天数升序排序（越小越靠前）
    workflow_df = workflow_df.sort_values(by="距离入住天数", ascending=True)

    # 所有订单放在一起按距离入住天数排序渲染
    for idx, row in workflow_df.iterrows():
        order_no = row.get("团单号", "")
        customer = row.get("客户名称 Customer Name", "")
        hotel = row.get("酒店名称 Hotel Name", "")
        checkin = row.get("入住日期 Check-in Date", "")
        days = row.get("距离入住天数", "")
        status = row.get("状态", "")

        days_valid = pd.notna(days) and str(days) != "None"
        days_text = int(days) if days_valid else t["day_all"]
        std_status = get_standard_status(status)
        display_status = get_workflow_step_text(lang, std_status)
        expander_title = t["expander_title"].format(order_no, customer, hotel, display_status, days_text)
        with st.expander(expander_title):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Order No**: {safe_val(order_no)}")
                st.write(f"**User ID**: {safe_val(row.get('User ID', ''))}")
                st.write(f"**{t['distance_checkin']}**: {int(days)} days" if days_valid else f"**{t['distance_checkin']}**: {t['day_all']}")
                status_days = row.get("状态持续天数", "")
                st.write(f"**{t['status_duration']}**: {status_days} days" if status_days and status_days != "Unknown" else f"**{t['status_duration']}**: {t['Unknown']}")
                st.write(f"**{t['checkin_date']}**: {safe_val(checkin)}")
                st.write(f"**{t['hotel_name']}**: {safe_val(hotel)}")
            with col2:
                st.write(f"**{t['sales_name']}**: {safe_val(row.get('销售姓名 Sales Name', ''))}")
                st.write(f"**{t['currency']}**: {safe_val(row.get('报价币种 Currency', ''))}")
                joy_price_col = "Joy 底价 Joy's Net Rate"
                st.write(f"**{t['joy_price']}**: {safe_val(row.get(joy_price_col, ''))}")
                st.write(f"**{t['suggested_price']}**: {safe_val(row.get('建议卖价 Suggested Selling Price', ''))}")
                st.write(f"**{t['room_count']}**: {safe_val(row.get('房间数 Rooms', ''))}")
            with col3:
                st.write(f"**{t['fail_reason']}**: {safe_val(row.get('未成单原因', ''))}")
                st.write(f"**{t['ops_remark']}**: {safe_val(row.get('运营备注 Ops Notes', ''))}")

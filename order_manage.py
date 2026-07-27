import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from config import load_data, save_data, STATUS_WORKFLOW_MAP, get_workflow_step_text, get_standard_status, STATUS_DURATION_COL_MAP

def render_order_manage(df, user_team=None):
    lang = st.session_state["lang"]
    # ===================== 1. 统一标准字段模板（全局唯一，一字不差） =====================
    std_all_cols = [
        "团单号",
        "客户名称 Customer Name",
        "User ID",
        "国籍 Nationality",
        "房间总数 Total Rooms",
        "状态",
        "提交时间 Submitted by",
        "最后更新时间",
        "国家 Country",
        "联系方式 Contact Info",
        "入住日期 Check-in Date",
        "离店日期 Check-out Date",
        "房型要求 Room Type",
        "报价币种 Currency",
        "预算范围 Budget Range",
        "房间数 Rooms",
        "酒店星级 Star Rating",
        "间夜数 Room Nights",
        "会议室/交通需求 Meeting Room / Transportation Requirements",
        "出行目的 Purpose of travel",
        "特殊需求 Special Requests",
        "Joy 底价 Joy's Net Rate",
        "建议卖价 Suggested Selling Price",
        "额外税费需求 Extra tax if needed",
        "房间保留时间",
        "支付方式",
        "餐食",
        "取消政策",
        "未成单原因（一级）",
        "未成单原因（二级）",
        "运营备注 Ops Notes",
        "BD",
        "Salesteam",
        "酒店名称 Hotel Name",
        "销售姓名 Sales Name",
        "备注",
        "客户咨询天数", "等待Joy报价天数", "等待运营询价天数", "询价成功天数", "询价失败天数",
        "等待运营审核天数", "等待客户确认天数", "客户确认成团天数", "客户确认失败天数",
        "等待酒店锁房天数", "考虑备选酒店天数", "等待客户支付天数", "团房成功天数", "团房失败天数"
    ]

    # 修复：移除 cache_clear=True 参数
    fresh_df = load_data()

    # ===================== 2. 彻底修复清洗逻辑：清除换行、回车、全角空格 =====================
    fresh_df = fresh_df.astype(str)
    # 只清洗真实干扰字符，移除无效空字符串替换
    clean_list = ["\n", "\r", "　"]
    for char in clean_list:
        fresh_df = fresh_df.apply(lambda series: series.str.replace(char, "", regex=False))
    # 统一空值标记替换为空字符串
    fresh_df = fresh_df.replace({"nan": "", "NaN": "", "None": "", "null": ""})

    # 自动补全缺失标准列（关键：CSV少了任何一列自动创建空列，杜绝读取空白）
    for col in std_all_cols:
        if col not in fresh_df.columns:
            fresh_df[col] = ""

    st.session_state["order_full_df"] = fresh_df.copy()
    full_df = st.session_state["order_full_df"]
    
    if user_team:
        full_df = full_df[full_df["Salesteam"].str.contains(user_team, case=False, na=False)]
    
    all_status_list = list(STATUS_WORKFLOW_MAP.keys())

    # ===================== 3. 修复safe_str，彻底清除隐形空白字符 =====================
    def safe_str(val):
        if pd.isna(val):
            return ""
        raw = str(val).strip()
        raw = raw.replace("\n", "").replace("\r", "").replace("　", "")
        if raw in ["nan", "NaN", "None", "null", ""]:
            return ""
        return raw

    # 1:1映射，页面输入框名称 = CSV真实列名，无任何转换
    field_map = {col: col for col in std_all_cols}

    def get_val(long_key):
        if long_key not in field_map:
            return ""
        real_col = field_map[long_key]
        if real_col not in data_dict:
            return ""
        raw_val = data_dict.get(real_col, "")
        return safe_str(raw_val)

    st.header("📃 团单列表管理")
    st.divider()

    # 筛选栏
    st.subheader("筛选条件")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        order_id_filter = st.text_input("团单号", placeholder="输入团单号")
    with col2:
        customer_filter = st.text_input("客户名称", placeholder="输入客户名称")
    with col3:
        userid_filter = st.text_input("User ID", placeholder="输入客户User ID")
    with col4:
        team_filter = st.text_input("销售团队", placeholder="输入销售团队")

    filter_df = full_df.copy()
    if order_id_filter.strip():
        filter_df = filter_df[filter_df["团单号"].str.contains(order_id_filter, case=False, na=False)]
    if customer_filter.strip():
        filter_df = filter_df[filter_df["客户名称 Customer Name"].str.contains(customer_filter, case=False, na=False)]
    if userid_filter.strip():
        filter_df = filter_df[filter_df["User ID"].str.contains(userid_filter, case=False, na=False)]
    if team_filter.strip():
        filter_df = filter_df[filter_df["Salesteam"].str.contains(team_filter, case=False, na=False)]

    st.divider()
    # 导出Excel
    def export_excel(data):
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine="openpyxl")
        data.to_excel(writer, index=False, sheet_name="团单数据")
        writer.close()
        output.seek(0)
        return output
    excel_file = export_excel(filter_df)
    st.download_button("📥 导出筛选结果Excel", excel_file, "团单筛选数据.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.subheader("团单列表")
    if filter_df.empty:
        st.info("暂无匹配的团单数据")
        return

    # 遍历每条订单
    for pos_idx, (_, row) in enumerate(filter_df.iterrows()):
        origin_index = row.name
        source_row = full_df.loc[origin_index]
        data_dict = source_row.to_dict()
        order_no = safe_str(source_row.get("团单号", ""))

        cust_name = get_val("客户名称 Customer Name")
        sales_team_text = get_val("Salesteam")
        sales_name = get_val("销售姓名 Sales Name")
        status_text = get_val("状态")
        status_text = safe_str(status_text)
        std_status = get_standard_status(status_text)
        display_status = get_workflow_step_text(lang, std_status)

        # 折叠标题和删除按钮放在同一行
        expand_title = f"【{order_no}】客户：{cust_name} | Sales Team：{sales_team_text} | 销售：{sales_name} | 状态：{display_status}"

        col1, col2 = st.columns([11, 1])
        with col1:
            with st.expander(expand_title):
                current_status = get_val("状态")
                current_status = safe_str(current_status)
                std_status = get_standard_status(current_status)
                
                display_status_list = []
                display_status_mapping = {}
                for key in all_status_list:
                    display_text = get_workflow_step_text(lang, key)
                    display_status_list.append(display_text)
                    display_status_mapping[display_text] = key
                
                current_display = get_workflow_step_text(lang, std_status)
                if current_display not in display_status_list:
                    display_status_list.insert(0, current_display)
                    display_status_mapping[current_display] = std_status
                
                status_index = display_status_list.index(current_display) if current_display in display_status_list else 0

                with st.form(f"edit_form_{origin_index}", clear_on_submit=False):
                    st.markdown("#### 一、基础客户信息")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        order_no_input = st.text_input("团单号", value=get_val("团单号"))
                        customer = st.text_input("客户名称 Customer Name", value=get_val("客户名称 Customer Name"))
                        user_id = st.text_input("User ID", value=get_val("User ID"))
                        nationality = st.text_input("国籍 Nationality", value=get_val("国籍 Nationality"))
                    with c2:
                        country = st.text_input("国家 Country", value=get_val("国家 Country"))
                        contact = st.text_input("联系方式 Contact Info", value=get_val("联系方式 Contact Info"))
                        sales_team_input = st.text_input("销售团队 Salesteam", value=get_val("Salesteam"))
                    with c3:
                        sales_name_input = st.text_input("销售姓名 Sales Name", value=get_val("销售姓名 Sales Name"))
                        submitted_by_input = st.text_input("提交时间 Submitted by", value=get_val("提交时间 Submitted by"))
                        last_update_input = st.text_input("最后更新时间", value=get_val("最后更新时间"))
                        status_input_display = st.selectbox("状态", display_status_list, index=status_index)
                        status_input = display_status_mapping[status_input_display]

                    st.markdown("#### 二、酒店信息")
                    c4, c5, c6 = st.columns(3)
                    with c4:
                        hotel_name = st.text_input("酒店名称 Hotel Name", value=get_val("酒店名称 Hotel Name"))
                        star_rating = st.text_input("酒店星级 Star Rating", value=get_val("酒店星级 Star Rating"))
                        checkin_val = get_val("入住日期 Check-in Date")
                        checkin_date = st.date_input("入住日期 Check-in Date", value=pd.to_datetime(checkin_val).date() if checkin_val and checkin_val.lower() != "nan" else None)
                    with c5:
                        checkout_val = get_val("离店日期 Check-out Date")
                        checkout_date = st.date_input("离店日期 Check-out Date", value=pd.to_datetime(checkout_val).date() if checkout_val and checkout_val.lower() != "nan" else None)
                        room_type = st.text_input("房型要求 Room Type", value=get_val("房型要求 Room Type"))
                        room_total = st.text_input("房间总数 Total Rooms", value=get_val("房间总数 Total Rooms"))
                    with c6:
                        room_cnt = st.text_input("房间数 Rooms", value=get_val("房间数 Rooms"))
                        room_night = st.text_input("间夜数 Room Nights", value=get_val("间夜数 Room Nights"))

                    st.markdown("#### 三、需求与报价")
                    c7, c8, c9 = st.columns(3)
                    with c7:
                        currency = st.text_input("报价币种 Currency", value=get_val("报价币种 Currency"))
                        budget = st.text_input("预算范围 Budget Range", value=get_val("预算范围 Budget Range"))
                        meeting_req = st.text_input("会议室/交通需求", value=get_val("会议室/交通需求 Meeting Room / Transportation Requirements"))
                    with c8:
                        travel_purpose = st.text_input("出行目的 Purpose of travel", value=get_val("出行目的 Purpose of travel"))
                        special_req = st.text_input("特殊需求 Special Requests", value=get_val("特殊需求 Special Requests"))
                        joy_price_col = "Joy 底价 Joy's Net Rate"
                        joy_price_input = st.text_input("Joy底价", value=get_val(joy_price_col))
                    with c9:
                        suggested_price_input = st.text_input("建议卖价 Suggested Selling Price", value=get_val("建议卖价 Suggested Selling Price"))
                        extra_tax_input = st.text_input("额外税费需求 Extra tax if needed", value=get_val("额外税费需求 Extra tax if needed"))
                        room_keep_time = st.text_input("房间保留时间", value=get_val("房间保留时间"))

                    st.markdown("#### 四、其他信息")
                    c10, c11, c12 = st.columns(3)
                    with c10:
                        pay_method_input = st.text_input("支付方式", value=get_val("支付方式"))
                        meal = st.text_input("餐食", value=get_val("餐食"))
                    with c11:
                        cancel_policy_input = st.text_input("取消政策", value=get_val("取消政策"))
                        fail_reason_1 = st.text_input("未成单原因（一级）", value=get_val("未成单原因（一级）"))
                        fail_reason_2 = st.text_input("未成单原因（二级）", value=get_val("未成单原因（二级）"))
                    with c12:
                        ops_notes_input = st.text_input("运营备注 Ops Notes", value=get_val("运营备注 Ops Notes"))

                    if st.form_submit_button("保存修改"):
                        row = full_df.loc[origin_index]
                        old_status = safe_str(row.get("状态", ""))
                        old_last_update = safe_str(row.get("最后更新时间", ""))
                        current_time = datetime.now().strftime("%Y-%m-%d")
                        
                        if status_input != old_status and old_status and old_last_update:
                            try:
                                for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
                                    try:
                                        old_date = datetime.strptime(old_last_update, fmt).date()
                                        new_date = datetime.strptime(current_time, "%Y-%m-%d").date()
                                        duration_days = (new_date - old_date).days
                                        old_std_status = get_standard_status(old_status)
                                        duration_col = STATUS_DURATION_COL_MAP.get(old_std_status, "")
                                        if duration_col:
                                            existing_val = safe_str(row.get(duration_col, ""))
                                            if existing_val:
                                                try:
                                                    existing_days = int(existing_val)
                                                    duration_days += existing_days
                                                except ValueError:
                                                    pass
                                            row[duration_col] = str(duration_days)
                                        break
                                    except ValueError:
                                        continue
                            except:
                                pass
                        
                        row["团单号"] = order_no_input
                        row["客户名称 Customer Name"] = customer
                        row["User ID"] = user_id
                        row["国籍 Nationality"] = nationality
                        row["国家 Country"] = country
                        row["联系方式 Contact Info"] = contact
                        row["Salesteam"] = sales_team_input
                        row["销售姓名 Sales Name"] = sales_name_input
                        row["提交时间 Submitted by"] = submitted_by_input
                        row["最后更新时间"] = current_time
                        row["状态"] = status_input
                        row["酒店名称 Hotel Name"] = hotel_name
                        row["酒店星级 Star Rating"] = star_rating
                        row["入住日期 Check-in Date"] = checkin_date
                        row["离店日期 Check-out Date"] = checkout_date
                        row["房型要求 Room Type"] = room_type
                        row["房间总数 Total Rooms"] = room_total
                        row["房间数 Rooms"] = room_cnt
                        row["间夜数 Room Nights"] = room_night
                        row["报价币种 Currency"] = currency
                        row["预算范围 Budget Range"] = budget
                        row["会议室/交通需求 Meeting Room / Transportation Requirements"] = meeting_req
                        row["出行目的 Purpose of travel"] = travel_purpose
                        row["特殊需求 Special Requests"] = special_req
                        row["Joy 底价 Joy's Net Rate"] = joy_price_input
                        row["建议卖价 Suggested Selling Price"] = suggested_price_input
                        row["额外税费需求 Extra tax if needed"] = extra_tax_input
                        row["房间保留时间"] = room_keep_time
                        row["支付方式"] = pay_method_input
                        row["餐食"] = meal
                        row["取消政策"] = cancel_policy_input
                        row["未成单原因（一级）"] = fail_reason_1
                        row["未成单原因（二级）"] = fail_reason_2
                        row["运营备注 Ops Notes"] = ops_notes_input
                        full_df.loc[origin_index] = row
                        st.session_state["order_full_df"] = full_df.copy()
                        save_data(full_df)
                        st.success("订单信息已更新！")
                        st.rerun()

        with col2:
            if st.button("🗑 删除", key=f"quick_del_{origin_index}", type="secondary"):
                full_df = full_df.drop(index=origin_index)
                st.session_state["order_full_df"] = full_df.copy()
                save_data(full_df)
                st.success(f"【{order_no}】订单已删除，CSV同步更新")
                st.rerun()
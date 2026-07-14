import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import traceback
import threading
import time
from config import save_data, STATUS_WORKFLOW_MAP, get_workflow_step_text, load_data, fetch_feishu_table

# 模块级变量：后台线程通过这些变量与主线程通信（不能用 st.session_state，因为它是 thread-local 的）
_sync_config = {"enabled": True, "interval": 10}
_sync_status = {"status": "未启动", "alert": None, "last_sync_time": None}
_auto_sync_thread = None
_auto_sync_thread_lock = threading.Lock()

# 哨兵值，用于区分"未传参"和"传了None"
_UNSET = object()

def save_sync_status(status, alert=_UNSET, last_sync_time=_UNSET):
    """更新同步状态（内存）。仅更新传入的字段，未传入的字段保持原值。"""
    _sync_status["status"] = status
    if alert is not _UNSET:
        _sync_status["alert"] = alert
    if last_sync_time is not _UNSET:
        _sync_status["last_sync_time"] = last_sync_time

def load_sync_status():
    """读取同步状态（内存）"""
    return dict(_sync_status)

def auto_sync_worker():
    import pytz
    beijing_tz = pytz.timezone('Asia/Shanghai')
    print("[定时同步] 后台线程已启动，开始监听同步配置...")
    while True:
        try:
            enabled = _sync_config.get("enabled", False)
            interval = _sync_config.get("interval", 1)

            if not enabled:
                save_sync_status("⏸️ 自动同步已关闭")
                time.sleep(5)
                continue

            print(f"[定时同步] 已启用，间隔{interval}分钟，等待下次同步...")
            save_sync_status(f"⏳ 等待中，下次同步将在{interval}分钟后")

            for i in range(interval * 60):
                if not _sync_config.get("enabled", False):
                    print(f"[定时同步] 自动同步已关闭")
                    break
                remaining = interval * 60 - i
                if remaining % 60 == 0 or remaining <= 5:
                    save_sync_status(f"⏳ 等待中，剩余{remaining}秒")
                time.sleep(1)

            if not _sync_config.get("enabled", False):
                continue

            print(f"[定时同步] 开始执行自动同步...")
            save_sync_status("🔄 正在同步中...")
            try:
                sync_df = fetch_feishu_table()
                if sync_df.empty:
                    print("[定时同步] 飞书表格无有效数据")
                    save_sync_status(f"⏳ 等待中，下次同步将在{interval}分钟后", alert=("warning", "飞书表格无有效数据"))
                    continue

                col_mapping = {
                    "提交时间 Submitted At": "提交时间 Submitted by",
                    "状态 Status": "状态"
                }
                sync_df = sync_df.rename(columns=col_mapping)
                sync_df["团单号"] = sync_df["团单号"].astype(str).str.strip()

                save_data(sync_df)
                beijing_time = datetime.now(beijing_tz)
                sync_time_str = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
                save_sync_status(f"✅ 同步完成于 {sync_time_str}",
                                alert=("success", f"🔄 自动同步完成！读取{len(sync_df)}条数据，同步时间: {sync_time_str}"),
                                last_sync_time=sync_time_str)
                print(f"[定时同步] 完成: 飞书读取{len(sync_df)}条, 完全覆盖本地数据, 时间: {sync_time_str}")

            except Exception as err:
                print(f"[定时同步] 失败: {str(err)}")
                save_sync_status(f"❌ 同步失败，下次同步将在{interval}分钟后",
                                alert=("error", f"自动同步失败: {str(err)}"))

        except Exception as e:
            print(f"[定时同步] 线程异常: {str(e)}")
            time.sleep(60)

def start_auto_sync_thread():
    """启动后台同步线程，使用模块级变量确保全局只启动一次（不依赖 st.session_state）"""
    global _auto_sync_thread
    with _auto_sync_thread_lock:
        if _auto_sync_thread is None or not _auto_sync_thread.is_alive():
            _auto_sync_thread = threading.Thread(target=auto_sync_worker, daemon=True)
            _auto_sync_thread.start()
            print("[定时同步] 自动同步后台线程已启动")

def get_feishu_config():
    import os
    cfg = {
        "app_id": os.environ.get("FEISHU_APP_ID") or st.secrets.get("FEISHU_APP_ID", ""),
        "app_secret": os.environ.get("FEISHU_APP_SECRET") or st.secrets.get("FEISHU_APP_SECRET", ""),
        "spreadsheet_token": os.environ.get("FEISHU_SPREADSHEET_TOKEN") or st.secrets.get("FEISHU_SPREADSHEET_TOKEN", ""),
        "sheet_name": os.environ.get("FEISHU_SHEET_NAME") or st.secrets.get("FEISHU_SHEET_NAME", "团房数据"),
        "output_csv": "order_data.csv"
    }
    return cfg

# 页面双语文本
PAGE_TEXT = {
    "zh": {
        "page_title": "➕ 新增团单信息",
        "tab_manual": "手动新建团单",
        "tab_import": "Excel批量导入",
        "tab_feishu": "飞书同步",
        "form_order_id": "团单号（必填）",
        "form_customer": "客户名称 Customer Name",
        "form_userid": "User ID",
        "form_nationality": "国籍 Nationality",
        "form_room_total": "房间总数 Total Rooms",
        "form_country": "国家 Country",
        "form_contact": "联系方式 Contact Info",
        "form_checkin": "入住日期 Check-in Date",
        "form_checkout": "离店日期 Check-out Date",
        "form_room_type": "房型要求 Room Type",
        "form_currency": "报价币种 Currency",
        "form_budget": "预算范围 Budget Range",
        "form_room_cnt": "房间数 Rooms",
        "form_star": "酒店星级 Star Rating",
        "form_night": "间夜数 Room Nights",
        "form_meeting": "会议室/交通需求 Meeting Room / Transportation Requirements",
        "form_travel_purpose": "出行目的 Purpose of travel",
        "form_special_req": "特殊需求 Special Requests",
        "form_joy_price": "Joy 底价 Joy's Net Rate",
        "form_sell_price": "建议卖价 Suggested Selling Price",
        "form_extra_tax": "额外税费需求 Extra tax if needed",
        "form_room_keep": "房间保留时间",
        "form_pay_method": "支付方式",
        "form_meal": "餐食",
        "form_cancel_policy": "取消政策",
        "form_fail_reason": "未成单原因",
        "form_ops_note": "运营备注 Ops Notes",
        "form_bd": "销售 BD",
        "form_sale_team": "销售团队 Salesteam",
        "form_hotel_name": "酒店名称 Hotel Name",
        "form_sale_name": "销售姓名 Sales Name",
        "form_status": "初始订单状态",
        "btn_save": "保存新建团单",
        "success_save": "团单【{}】创建完成！",
        "err_order_empty": "团单号不能为空！",
        "err_order_exist": "该团单号已存在，请勿重复创建！",
        "import_tip": "上传CSV/Excel，相同团单号自动覆盖本地旧数据",
        "upload_label": "上传文件",
        "btn_import": "执行批量导入",
        "import_success": "成功导入{}条订单",
        "import_empty": "文件无有效数据",
        "feishu_tip": "同步规则：完全同步飞书表格数据到本地数据库",
        "sync_btn": "开始同步飞书表格",
        "clear_cache_btn": "清空本地缓存",
        "last_sync_text": "上次同步时间：{}",
        "sync_empty": "飞书表格无有效数据",
        "sync_success": "同步完成！飞书读取{}条，更新{}条，本地独有{}条",
        "sync_error": "同步失败：{}"
    },
    "en": {
        "page_title": "Create New Booking",
        "tab_manual": "Manual Create",
        "tab_import": "Batch Import Excel",
        "tab_feishu": "Feishu Sync",
        "form_order_id": "Booking No. (Required)",
        "form_customer": "Customer Name",
        "form_userid": "User ID",
        "form_nationality": "Nationality",
        "form_room_total": "Total Rooms",
        "form_country": "Country",
        "form_contact": "Contact Info",
        "form_checkin": "Check-in Date",
        "form_checkout": "Check-out Date",
        "form_room_type": "Room Type",
        "form_currency": "Currency",
        "form_budget": "Budget Range",
        "form_room_cnt": "Room Count",
        "form_star": "Hotel Star",
        "form_night": "Room Nights",
        "form_meeting": "Meeting Request",
        "form_travel_purpose": "Travel Purpose",
        "form_special_req": "Special Request",
        "form_joy_price": "Joy's Net Rate",
        "form_sell_price": "Suggested Price",
        "form_extra_tax": "Extra Tax",
        "form_room_keep": "Room Hold",
        "form_pay_method": "Payment",
        "form_meal": "Meal Plan",
        "form_cancel_policy": "Cancellation Policy",
        "form_fail_reason": "Failure Reason",
        "form_ops_note": "Operation Notes",
        "form_bd": "BD Sales",
        "form_sale_team": "Sales Team",
        "form_hotel_name": "Hotel Name",
        "form_sale_name": "Sales Name",
        "form_status": "Initial Status",
        "btn_save": "Save Booking",
        "success_save": "Booking {} created!",
        "err_order_empty": "Booking No cannot empty!",
        "err_order_exist": "Booking No already exists!",
        "import_tip": "Upload CSV/Excel, same ID overwrite local data",
        "upload_label": "Upload File",
        "btn_import": "Start Import",
        "import_success": "Imported {} bookings",
        "import_empty": "No valid data",
        "feishu_tip": "Sync: Fully sync Feishu data to local database",
        "sync_btn": "Sync Feishu Sheet",
        "clear_cache_btn": "Clear Cache",
        "last_sync_text": "Last Sync: {}",
        "sync_empty": "Feishu sheet empty",
        "sync_success": "Sync done: Feishu {}, updated {}, local unique {}",
        "sync_error": "Sync failed: {}"
    }
}

def render_create_order(df):
    lang = st.session_state["lang"]
    t = PAGE_TEXT[lang]
    st.header(t["page_title"])
    tab3, tab1, tab2 = st.tabs([t["tab_feishu"], t["tab_manual"], t["tab_import"]])
    all_status = list(STATUS_WORKFLOW_MAP.keys())

    # Tab1 手动新建
    with tab1:
        with st.form("new_order_form", border=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                order_id = st.text_input(t["form_order_id"])
                customer = st.text_input(t["form_customer"])
                user_id = st.text_input(t["form_userid"])
                nationality = st.text_input(t["form_nationality"])
                hotel_name = st.text_input(t["form_hotel_name"])
            with c2:
                create_time = st.text_input("提交时间 Submitted by", value=datetime.now().strftime("%Y-%m-%d"), disabled=True)
                last_update_time = st.text_input("最后更新时间", value=datetime.now().strftime("%Y-%m-%d"), disabled=True)
                room_total = st.number_input(t["form_room_total"], min_value=1, value=1)
                country = st.text_input(t["form_country"])
                contact = st.text_input(t["form_contact"])
                checkin = st.text_input(t["form_checkin"])
            with c3:
                checkout = st.text_input(t["form_checkout"])
                room_type = st.text_input(t["form_room_type"])
                currency = st.text_input(t["form_currency"])
                budget = st.text_input(t["form_budget"])
                room_cnt = st.text_input(t["form_room_cnt"])
            c4, c5, c6 = st.columns(3)
            with c4:
                star = st.text_input(t["form_star"])
                night = st.text_input(t["form_night"])
                meeting = st.text_input(t["form_meeting"])
                travel_purpose = st.text_input(t["form_travel_purpose"])
                special_req = st.text_input(t["form_special_req"])
            with c5:
                joy_price = st.text_input(t["form_joy_price"])
                sell_price = st.text_input(t["form_sell_price"])
                extra_tax = st.text_input(t["form_extra_tax"])
                room_keep = st.text_input(t["form_room_keep"])
                pay_method = st.text_input(t["form_pay_method"])
            with c6:
                meal = st.text_input(t["form_meal"])
                cancel_policy = st.text_input(t["form_cancel_policy"])
                fail_reason = st.text_input(t["form_fail_reason"])
                ops_note = st.text_input(t["form_ops_note"])
            c7, c8 = st.columns(2)
            with c7:
                bd = st.text_input(t["form_bd"])
                sale_team = st.text_input(t["form_sale_team"])
            with c8:
                sale_name = st.text_input(t["form_sale_name"])
                init_status = st.selectbox(t["form_status"], all_status, format_func=lambda s:get_workflow_step_text(lang,s))
            submit = st.form_submit_button(t["btn_save"])
            if submit:
                oid = order_id.strip()
                if not oid:
                    st.error(t["err_order_empty"])
                    return
                local_check = df["团单号"].astype(str).str.strip().tolist()
                if oid in local_check:
                    st.error(t["err_order_exist"])
                    return
                new_row = {
                    "团单号": oid,
                    "客户名称 Customer Name": customer.strip(),
                    "User ID": user_id.strip(),
                    "国籍 Nationality": nationality.strip(),
                    "房间总数 Total Rooms": str(room_total),
                    "状态": init_status,
                    "提交时间 Submitted by": create_time.strip(),
                    "最后更新时间": last_update_time.strip(),
                    "国家 Country": country.strip(),
                    "联系方式 Contact Info": contact.strip(),
                    "入住日期 Check-in Date": checkin.strip(),
                    "离店日期 Check-out Date": checkout.strip(),
                    "房型要求 Room Type": room_type.strip(),
                    "报价币种 Currency": currency.strip(),
                    "预算范围 Budget Range": budget.strip(),
                    "房间数 Rooms": room_cnt.strip(),
                    "酒店星级 Star Rating": star.strip(),
                    "间夜数 Room Nights": night.strip(),
                    "会议室/交通需求 Meeting Room / Transportation Requirements": meeting.strip(),
                    "出行目的 Purpose of travel": travel_purpose.strip(),
                    "特殊需求 Special Requests": special_req.strip(),
                    "Joy 底价 Joy's Net Rate": joy_price.strip(),
                    "建议卖价 Suggested Selling Price": sell_price.strip(),
                    "额外税费需求 Extra tax if needed": extra_tax.strip(),
                    "房间保留时间": room_keep.strip(),
                    "支付方式": pay_method.strip(),
                    "餐食": meal.strip(),
                    "取消政策": cancel_policy.strip(),
                    "未成单原因": fail_reason.strip(),
                    "运营备注 Ops Notes": ops_note.strip(),
                    "BD": bd.strip(),
                    "Salesteam": sale_team.strip(),
                    "酒店名称 Hotel Name": hotel_name.strip(),
                    "销售姓名 Sales Name": sale_name.strip(),
                    "备注": ""
                }
                new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(new_df)
                st.success(t["success_save"].format(oid))
                st.rerun()

    # Tab2 Excel批量导入
    with tab2:
        st.info(t["import_tip"])
        upload_file = st.file_uploader(t["upload_label"], type=["csv", "xlsx"])
        import_btn = st.button(t["btn_import"])
        if upload_file and import_btn:
            try:
                if upload_file.name.endswith(".csv"):
                    import_df = pd.read_csv(upload_file, encoding="utf-8-sig")
                else:
                    import_df = pd.read_excel(upload_file)
                # 清洗导入文件
                import_df.columns = import_df.columns.str.strip()
                import_df = import_df.astype(str).replace(["nan","","None"], "")
                for col in import_df.columns:
                    import_df[col] = import_df[col].str.strip().str.replace(r"[\n\r]", "", regex=True)

                map_rule = {
                    "团单号": "团单号",
                    "客户名称 Customer Name": "客户名称 Customer Name",
                    "User ID": "User ID",
                    "国籍 Nationality": "国籍 Nationality",
                    "国家 Country": "国家 Country",
                    "联系方式 Contact Info": "联系方式 Contact Info",
                    "入住日期 Check-in Date": "入住日期 Check-in Date",
                    "离店日期 Check-out Date": "离店日期 Check-out Date",
                    "房型要求 Room Type": "房型要求 Room Type",
                    "报价币种 Currency": "报价币种 Currency",
                    "提交时间 Submitted by": "提交时间 Submitted by",
                    "提交时间 Submitted At": "提交时间 Submitted by",
                    "Joy 底价 Joy's Net Rate": "Joy 底价 Joy's Net Rate",
                    "建议卖价 Suggested Selling Price": "建议卖价 Suggested Selling Price",
                    "额外税费需求 Extra tax if needed": "额外税费需求 Extra tax if needed",
                    "房间保留时间": "房间保留时间",
                    "支付方式": "支付方式",
                    "餐食": "餐食",
                    "取消政策": "取消政策",
                    "未成单原因": "未成单原因",
                    "出行目的 Purpose of travel": "出行目的 Purpose of travel",
                    "特殊需求 Special Requests": "特殊需求 Special Requests",
                    "运营备注 Ops Notes": "运营备注 Ops Notes",
                    "运营备注 Ops Notes.1": "运营备注 Ops Notes",
                    "状态 Status": "状态",
                    "销售姓名 Sales Name": "销售姓名 Sales Name",
                    "酒店名称 Hotel Name": "酒店名称 Hotel Name",
                    "房间数 Rooms": "房间数 Rooms",
                    "酒店星级 Star Rating": "酒店星级 Star Rating",
                    "间夜数 Room Nights": "间夜数 Room Nights",
                    "会议室/交通需求 Meeting Room / Transportation Requirements": "会议室/交通需求 Meeting Room / Transportation Requirements"
                }
                std_cols = [
                    "团单号", "客户名称 Customer Name", "User ID", "国籍 Nationality",
                    "房间总数 Total Rooms", "状态", "提交时间 Submitted by", "最后更新时间", "国家 Country",
                    "联系方式 Contact Info", "入住日期 Check-in Date", "离店日期 Check-out Date",
                    "房型要求 Room Type", "报价币种 Currency", "预算范围 Budget Range",
                    "房间数 Rooms", "酒店星级 Star Rating", "间夜数 Room Nights",
                    "会议室/交通需求 Meeting Room / Transportation Requirements",
                    "出行目的 Purpose of travel", "特殊需求 Special Requests",
                    "Joy 底价 Joy's Net Rate", "建议卖价 Suggested Selling Price",
                    "额外税费需求 Extra tax if needed", "房间保留时间", "支付方式",
                    "餐食", "取消政策", "未成单原因", "运营备注 Ops Notes", "BD", "Salesteam", "酒店名称 Hotel Name",
                    "销售姓名 Sales Name", "备注"
                ]
                mapped_df = pd.DataFrame(columns=std_cols)
                for src_col, target_col in map_rule.items():
                    if src_col in import_df.columns:
                        if target_col in mapped_df.columns:
                            if mapped_df[target_col].isna().all() or mapped_df[target_col].eq("").all():
                                mapped_df[target_col] = import_df[src_col]
                            else:
                                mapped_df[target_col] = mapped_df[target_col] + " " + import_df[src_col]
                if "团单号" in mapped_df.columns:
                    mapped_df["团单号"] = mapped_df["团单号"].astype(str).str.strip()
                    mapped_df = mapped_df[mapped_df["团单号"] != ""]
                    mapped_df = mapped_df.drop_duplicates(subset=["团单号"], keep="last")
                if mapped_df.empty:
                    st.warning(t["import_empty"])
                    return
                local_df = load_data()
                local_df["团单号"] = local_df["团单号"].astype(str).str.strip()
                cover_ids = mapped_df["团单号"].unique()
                local_keep = local_df[~local_df["团单号"].isin(cover_ids)].copy()
                full_df = pd.concat([local_keep, mapped_df], ignore_index=True)
                save_data(full_df)
                st.success(t["import_success"].format(len(mapped_df)))
                st.rerun()
            except Exception as e:
                st.error(f"导入失败：{str(e)}")
                traceback.print_exc()

    # Tab3 飞书同步
    with tab3:
        if "feishu_sync_running" not in st.session_state:
            st.session_state["feishu_sync_running"] = False
        if "last_sync_time" not in st.session_state:
            st.session_state["last_sync_time"] = None
        # 从模块级配置初始化 session_state（使后台线程与UI保持一致）
        if "auto_sync_enabled" not in st.session_state:
            st.session_state["auto_sync_enabled"] = _sync_config["enabled"]
        if "auto_sync_alert" not in st.session_state:
            st.session_state["auto_sync_alert"] = None

        st.info(t["feishu_tip"])
        col1, col2 = st.columns([2, 1])
        with col1:
            sync_btn = st.button(t["sync_btn"], type="primary", disabled=st.session_state["feishu_sync_running"])
        with col2:
            auto_sync_enabled = st.checkbox("🔄 自动定时同步", value=st.session_state["auto_sync_enabled"])

        if auto_sync_enabled != st.session_state["auto_sync_enabled"]:
            st.session_state["auto_sync_enabled"] = auto_sync_enabled
            # 同步到模块级变量，后台线程通过此变量读取最新配置
            _sync_config["enabled"] = auto_sync_enabled
            st.rerun()

        sync_interval = _sync_config["interval"]
        if st.session_state["auto_sync_enabled"]:
            st.success(f"✅ 自动同步已开启，每{sync_interval}分钟同步一次")

            @st.fragment(run_every=timedelta(minutes=sync_interval))
            def _auto_refresh_status():
                # 在 fragment 内重新读取并显示，确保自动刷新时同步更新结果
                sync_status_data = load_sync_status()
                auto_sync_status = sync_status_data.get("status", "🔧 后台线程准备启动...")
                st.info(auto_sync_status)
                st.info(f"🔄 后台每{sync_interval}分钟自动同步飞书表格")

                last_sync_time = sync_status_data.get("last_sync_time")
                if last_sync_time:
                    st.success(t["last_sync_text"].format(last_sync_time))
                    st.session_state["last_sync_time"] = last_sync_time

                if sync_status_data.get("alert"):
                    alert_type, alert_msg = sync_status_data["alert"]
                    if alert_type == "success":
                        st.success(alert_msg)
                    elif alert_type == "warning":
                        st.warning(alert_msg)
                    elif alert_type == "error":
                        st.error(alert_msg)
                    save_sync_status(sync_status_data["status"], alert=None)

            # 首次加载时立即显示一次（fragment 之外）
            sync_status_data = load_sync_status()
            auto_sync_status = sync_status_data.get("status", "🔧 后台线程准备启动...")
            st.info(auto_sync_status)
            st.info(f"🔄 后台每{sync_interval}分钟自动同步飞书表格")
            last_sync_time = sync_status_data.get("last_sync_time") or st.session_state["last_sync_time"]
            if last_sync_time:
                st.success(t["last_sync_text"].format(last_sync_time))
                st.session_state["last_sync_time"] = last_sync_time
            if sync_status_data.get("alert"):
                alert_type, alert_msg = sync_status_data["alert"]
                if alert_type == "success":
                    st.success(alert_msg)
                elif alert_type == "warning":
                    st.warning(alert_msg)
                elif alert_type == "error":
                    st.error(alert_msg)
                save_sync_status(sync_status_data["status"], alert=None)
        else:
            st.info("⏸️ 自动同步已关闭")
        
        if st.session_state["auto_sync_alert"]:
            alert_type, alert_msg = st.session_state["auto_sync_alert"]
            if alert_type == "success":
                st.success(alert_msg)
            elif alert_type == "warning":
                st.warning(alert_msg)
            elif alert_type == "error":
                st.error(alert_msg)
            st.session_state["auto_sync_alert"] = None

        def sync_data(is_auto=False):
            try:
                sync_df = fetch_feishu_table()
                if sync_df.empty:
                    print("[自动同步] 飞书表格无有效数据")
                    if is_auto:
                        st.session_state["auto_sync_alert"] = ("warning", "飞书表格无有效数据")
                    return None
                
                col_mapping = {
                    "提交时间 Submitted At": "提交时间 Submitted by",
                    "状态 Status": "状态"
                }
                sync_df = sync_df.rename(columns=col_mapping)
                
                sync_df["团单号"] = sync_df["团单号"].astype(str).str.strip()
                
                save_data(sync_df)
                import pytz
                beijing_tz = pytz.timezone('Asia/Shanghai')
                beijing_time = datetime.now(beijing_tz)
                st.session_state["last_sync_time"] = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
                sync_time_str = st.session_state["last_sync_time"]
                print(f"[自动同步] 完成: 飞书读取{len(sync_df)}条, 完全覆盖本地数据")
                if is_auto:
                    st.session_state["auto_sync_alert"] = ("success", f"🔄 自动同步完成！读取{len(sync_df)}条数据，同步时间: {sync_time_str}")
                return len(sync_df), 0, 0
            except Exception as err:
                print(f"[自动同步] 失败: {str(err)}")
                if is_auto:
                    st.session_state["auto_sync_alert"] = ("error", f"自动同步失败: {str(err)}")
                raise err

        def run_sync():
            st.session_state["feishu_sync_running"] = True
            with st.status("同步中") as status_box:
                try:
                    sync_result = sync_data()
                    if sync_result:
                        sync_cnt, update_cnt, local_only = sync_result
                        status_box.update(label="同步完成")
                        st.success(t["sync_success"].format(sync_cnt, update_cnt, local_only))
                    else:
                        status_box.update(label="同步完成")
                        st.warning(t["sync_empty"])
                except Exception as err:
                    st.error(t["sync_error"].format(str(err)))
                finally:
                    st.session_state["feishu_sync_running"] = False

        if sync_btn:
            run_sync()

        start_auto_sync_thread()

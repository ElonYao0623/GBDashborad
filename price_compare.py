"""比价功能

从主数据读取酒店名称、国家、报价币种、房型要求，
手动填写团房组底价及各平台价格进行对比
"""
import streamlit as st
import pandas as pd
import os
import re
from config import DATA_FILE, fetch_feishu_price_table, write_feishu_price_table, load_feishu_config

PRICE_FILE = "price_compare.csv"

PLATFORMS = ["Booking.com", "Expedia", "Trip.com", "Agoda", "Traveloka"]

PAGE_TEXT = {
    "zh": {
        "page_header": "比价",
        "page_desc": "从团单数据自动读取酒店信息，填写各平台价格进行对比",
        "col_hotel": "酒店名称",
        "col_country": "国家",
        "col_currency": "报价币种",
        "col_room_type": "房型要求",
        "col_group_rate": "团房组底价",
        "col_price": "运营报价",
        "col_star": "星级",
        "col_checkin": "Check in",
        "col_checkout": "Check out",
        "filter_section": "🔍 筛选",
        "filter_order_id": "团单号",
        "filter_hotel": "酒店名称",
        "filter_country": "国家",
        "filter_all": "全部",
        "empty_tip": "暂无比价数据，请在下方填写并保存",
        "save_btn": "保存比价数据",
        "save_success": "保存成功！共 {} 条记录",
        "save_error": "保存失败：{}",
        "load_error": "加载比价数据失败：{}",
        "add_room_section": "➕ 添加房型",
        "select_hotel": "选择酒店",
        "input_room_type": "输入房型要求",
        "add_btn": "添加",
        "add_success": "已添加：{} - {}",
        "add_dup_tip": "该酒店已存在此房型",
        "add_no_hotel": "请先选择酒店",
        "add_no_room": "请输入房型要求",
        "delete_section": "🗑️ 删除行",
        "delete_select": "选择要删除的行",
        "delete_btn": "删除选中行",
        "delete_success": "已删除：{}",
        "delete_no_selection": "请先选择要删除的行",
        "delete_confirm": "确定删除这行数据吗？",
        "lowest_tip": "最低价",
        "lowest_highlight": "🏆 最低价平台：{}  {}{}",
        "col_delete": "删除",
        "delete_inline_tip": "勾选要删除的行后会自动删除",
        "undo_btn": "↩️ 撤销删除",
        "undo_success": "已撤销删除，恢复 {} 条记录",
        "undo_empty": "没有可撤销的删除",
        "add_room_btn": "➕ 添加房型",
        "add_hotel_btn": "🏨 添加酒店",
        "sync_from_feishu": "🔄 从飞书更新",
        "sync_success": "从飞书同步成功！共 {} 条数据",
        "sync_error": "从飞书同步失败: {}"
    },
    "en": {
        "page_header": "Price Compare",
        "page_desc": "Auto-load hotel info from bookings, fill in platform prices to compare",
        "col_hotel": "Hotel Name",
        "col_country": "Country",
        "col_currency": "Currency",
        "col_room_type": "Room Type",
        "col_group_rate": "Group Net Rate",
        "col_price": "Op Quotation",
        "col_star": "Star",
        "col_checkin": "Check in",
        "col_checkout": "Check out",
        "filter_section": "🔍 Filter",
        "filter_order_id": "Booking No",
        "filter_hotel": "Hotel Name",
        "filter_country": "Country",
        "filter_all": "All",
        "empty_tip": "No price data yet, please fill in below and save",
        "save_btn": "Save Price Data",
        "save_success": "Saved! {} records in total",
        "save_error": "Save failed: {}",
        "load_error": "Failed to load price data: {}",
        "add_room_section": "➕ Add Room Type",
        "select_hotel": "Select Hotel",
        "input_room_type": "Enter Room Type",
        "add_btn": "Add",
        "add_success": "Added: {} - {}",
        "add_dup_tip": "This room type already exists for this hotel",
        "add_no_hotel": "Please select a hotel first",
        "add_no_room": "Please enter a room type",
        "delete_section": "🗑️ Delete Row",
        "delete_select": "Select row to delete",
        "delete_btn": "Delete Selected",
        "delete_success": "Deleted: {}",
        "delete_no_selection": "Please select a row first",
        "delete_confirm": "Are you sure you want to delete this row?",
        "lowest_tip": "Lowest",
        "lowest_highlight": "🏆 Lowest platform: {}  {}{}",
        "col_delete": "Delete",
        "delete_inline_tip": "Check rows to delete them automatically",
        "undo_btn": "↩️ Undo Delete",
        "undo_success": "Undo successful, restored {} records",
        "undo_empty": "No deletion to undo",
        "add_room_btn": "➕ Add Room Type",
        "add_hotel_btn": "🏨 Add Hotel",
        "sync_from_feishu": "🔄 Sync from Feishu",
        "sync_success": "Synced from Feishu! {} records",
        "sync_error": "Sync failed: {}"
    },
}


def _load_price_data(t=None):
    """加载已保存的比价数据（优先从飞书读取，云部署持久化）"""
    try:
        feishu_df = fetch_feishu_price_table()
        if not feishu_df.empty:
            print("[比价数据] 从飞书表格加载成功，共{}条数据".format(len(feishu_df)))
            if t:
                feishu_df = _normalize_feishu_columns(feishu_df, t)
            return feishu_df.fillna("")
        print("[比价数据] 飞书表格为空，尝试从本地CSV加载")
    except Exception as e:
        print("[比价数据] 飞书加载失败，尝试从本地CSV加载: {}".format(str(e)))
    
    if os.path.exists(PRICE_FILE):
        try:
            csv_df = pd.read_csv(PRICE_FILE, encoding="utf-8-sig", dtype=str).fillna("")
            if t:
                csv_df = _normalize_feishu_columns(csv_df, t)
            return csv_df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def _save_price_data(df):
    """保存比价数据"""
    df.to_csv(PRICE_FILE, index=False, encoding="utf-8-sig")


def _normalize_feishu_columns(df, t):
    """规范化飞书表格列名，处理中英文列名映射"""
    col_variants = {
        t["col_hotel"]: ["酒店名称", "Hotel Name", "酒店"],
        t["col_star"]: ["星级", "Star Rating", "酒店星级"],
        t["col_country"]: ["国家", "Country"],
        t["col_currency"]: ["报价币种", "Currency", "币种"],
        t["col_checkin"]: ["入住日期", "Check In", "Check-in", "入住"],
        t["col_checkout"]: ["退房日期", "Check Out", "Check-out", "退房"],
        t["col_room_type"]: ["房型要求", "Room Type", "房型"],
        t["col_group_rate"]: ["团房组底价", "Group Net Rate", "底价"],
        t["col_price"]: ["运营报价", "Op Quotation", "报价"],
    }
    
    rename_map = {}
    for target_col, variants in col_variants.items():
        for variant in variants:
            if variant in df.columns and variant not in rename_map:
                rename_map[variant] = target_col
                break
    
    df = df.rename(columns=rename_map)
    
    for col in [t["col_hotel"], t["col_star"], t["col_country"], t["col_currency"],
                t["col_checkin"], t["col_checkout"], t["col_room_type"], t["col_group_rate"], t["col_price"]] + PLATFORMS:
        if col not in df.columns:
            df[col] = ""
    
    return df


def _split_hotel_names(name):
    """拆分单元格中可能存在的多个酒店名称"""
    if not name or str(name).strip().lower() == "nan":
        return []
    name = str(name).strip()
    # 按常见分隔符拆分：/ 、 & + 换行 ; ；
    parts = re.split(r"[/、&\+\n;；]", name)
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def _load_hotel_info(df):
    """从主数据提取酒店信息（去重）"""
    def _find_col(candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    hotel_col = _find_col(["酒店名称 Hotel Name", "酒店名称", "Hotel Name"])
    country_col = _find_col(["国家 Country", "国家", "Country"])
    currency_col = _find_col(["报价币种 Currency", "报价币种", "Currency"])
    room_col = _find_col(["房型要求 Room Type", "房型要求", "Room Type"])
    star_col = _find_col(["酒店星级 Star Rating", "酒店星级", "Star Rating"])
    checkin_col = _find_col(["入住日期 Check-in", "入住日期", "Check-in", "Check in"])
    checkout_col = _find_col(["退房日期 Check-out", "退房日期", "Check-out", "Check out"])

    if not hotel_col:
        return pd.DataFrame()

    rows = []
    for _, row in df.iterrows():
        raw_name = row.get(hotel_col, "")
        hotels = _split_hotel_names(raw_name)
        if not hotels:
            continue
        country_val = str(row.get(country_col, "")).strip() if country_col else ""
        currency_val = str(row.get(currency_col, "")).strip() if currency_col else ""
        room_val = str(row.get(room_col, "")).strip() if room_col else ""
        star_val = str(row.get(star_col, "")).strip() if star_col else ""
        checkin_val = str(row.get(checkin_col, "")).strip() if checkin_col else ""
        checkout_val = str(row.get(checkout_col, "")).strip() if checkout_col else ""
        for h in hotels:
            row_data = {hotel_col: h}
            if country_col:
                row_data[country_col] = country_val
            if currency_col:
                row_data[currency_col] = currency_val
            if room_col:
                row_data[room_col] = room_val
            if star_col:
                row_data[star_col] = star_val
            if checkin_col:
                row_data[checkin_col] = checkin_val
            if checkout_col:
                row_data[checkout_col] = checkout_val
            rows.append(row_data)

    if not rows:
        return pd.DataFrame()

    info = pd.DataFrame(rows)
    dedup_cols = [hotel_col]
    if room_col and room_col in info.columns:
        dedup_cols.append(room_col)
    info = info.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
    return info


def _merge_with_existing(existing_df, hotel_info, t):
    """将主数据的酒店信息与已保存的比价数据合并"""
    if existing_df.empty:
        result = hotel_info.copy()
        result[t["col_group_rate"]] = ""
        result[t["col_price"]] = ""
        for p in PLATFORMS:
            result[p] = ""
        if t["col_checkin"] not in result.columns:
            result[t["col_checkin"]] = ""
        if t["col_checkout"] not in result.columns:
            result[t["col_checkout"]] = ""
        return result

    hotel_col = t["col_hotel"]
    if hotel_col not in existing_df.columns:
        existing_df[hotel_col] = ""

    existing_hotels = set(existing_df[hotel_col].astype(str).str.strip().tolist())
    new_rows = []
    for _, row in hotel_info.iterrows():
        hotel_name = str(row.get(hotel_col, "")).strip()
        if hotel_name and hotel_name not in existing_hotels:
            new_row = {}
            for c in hotel_info.columns:
                new_row[c] = row[c]
            if t["col_group_rate"] not in new_row:
                new_row[t["col_group_rate"]] = ""
            if t["col_price"] not in new_row:
                new_row[t["col_price"]] = ""
            if t["col_checkin"] not in new_row:
                new_row[t["col_checkin"]] = ""
            if t["col_checkout"] not in new_row:
                new_row[t["col_checkout"]] = ""
            for p in PLATFORMS:
                if p not in existing_df.columns:
                    existing_df[p] = ""
                new_row[p] = ""
            new_rows.append(new_row)

    if new_rows:
        existing_df = pd.concat([existing_df, pd.DataFrame(new_rows)], ignore_index=True)

    for p in PLATFORMS:
        if p not in existing_df.columns:
            existing_df[p] = ""
    if t["col_group_rate"] not in existing_df.columns:
        existing_df[t["col_group_rate"]] = ""
    if t["col_price"] not in existing_df.columns:
        existing_df[t["col_price"]] = ""
    if t["col_star"] not in existing_df.columns:
        existing_df[t["col_star"]] = ""
    if t["col_checkin"] not in existing_df.columns:
        existing_df[t["col_checkin"]] = ""
    if t["col_checkout"] not in existing_df.columns:
        existing_df[t["col_checkout"]] = ""

    # 用主数据回填已有酒店的星级、国家、币种、Check in/Check out（仅当本地为空时）
    hotel_info_map = {}
    for _, row in hotel_info.iterrows():
        hn = str(row.get(hotel_col, "")).strip()
        if not hn:
            continue
        hotel_info_map[hn] = {
            t["col_star"]: str(row.get(t["col_star"], "")).strip() if t["col_star"] in row.index else "",
            t["col_country"]: str(row.get(t["col_country"], "")).strip() if t["col_country"] in row.index else "",
            t["col_currency"]: str(row.get(t["col_currency"], "")).strip() if t["col_currency"] in row.index else "",
            t["col_checkin"]: str(row.get(t["col_checkin"], "")).strip() if t["col_checkin"] in row.index else "",
            t["col_checkout"]: str(row.get(t["col_checkout"], "")).strip() if t["col_checkout"] in row.index else "",
        }

    for idx, row in existing_df.iterrows():
        hn = str(row.get(hotel_col, "")).strip()
        if hn in hotel_info_map:
            info = hotel_info_map[hn]
            for col_key in [t["col_star"], t["col_country"], t["col_currency"], t["col_checkin"], t["col_checkout"]]:
                if col_key in existing_df.columns:
                    cur_val = str(row.get(col_key, "")).strip()
                    if (not cur_val or cur_val.lower() == "nan") and info[col_key]:
                        existing_df.at[idx, col_key] = info[col_key]

    return existing_df.fillna("")


def _find_lowest_platform(row, t):
    """找出一行中价格最低的平台"""
    prices = {}
    for p in PLATFORMS:
        val = str(row.get(p, "")).strip()
        if val:
            try:
                prices[p] = float(val)
            except ValueError:
                pass
    if not prices:
        return ""
    lowest_platform = min(prices, key=prices.get)
    lowest_val = prices[lowest_platform]
    # 获取币种
    currency = str(row.get(t["col_currency"], "")).strip()
    return t["lowest_highlight"].format(lowest_platform, currency, f"{lowest_val:.2f}")


def render_price_compare(df):
    """渲染比价页面"""
    lang = st.session_state["lang"]
    t = PAGE_TEXT[lang]

    st.header(t["page_header"])
    st.markdown(t["page_desc"])
    st.divider()

    # 从飞书更新按钮
    sync_col, _ = st.columns([1, 3])
    with sync_col:
        if st.button(t["sync_from_feishu"], key="sync_from_feishu_btn", use_container_width=True):
            try:
                feishu_df = fetch_feishu_price_table()
                if not feishu_df.empty:
                    feishu_df = _normalize_feishu_columns(feishu_df, t)
                    _save_price_data(feishu_df)
                    
                    import os as _os_sync
                    st.session_state["price_df_csv_mtime"] = _os_sync.path.getmtime(PRICE_FILE) if _os_sync.path.exists(PRICE_FILE) else 0
                    st.session_state["price_df"] = feishu_df.copy()
                    st.session_state["price_df_editing"] = False
                    
                    st.success(t["sync_success"].format(len(feishu_df)))
                    print(f"[比价同步] 从飞书更新成功，共{len(feishu_df)}条数据")
                else:
                    st.info(t["empty_tip"])
            except Exception as e:
                st.error(t["sync_error"].format(str(e)))
                print(f"[比价同步] 从飞书更新失败: {str(e)}")
            st.rerun()

    # 加载主数据的酒店信息
    hotel_info = _load_hotel_info(df)
    if hotel_info.empty or hotel_info.columns.empty:
        st.warning(t["empty_tip"])
        return

    # 重命名列为主表头
    col_map = {}
    hotel_col = None
    for c in hotel_info.columns:
        if c in ["酒店名称 Hotel Name", "酒店名称", "Hotel Name"]:
            col_map[c] = t["col_hotel"]
            hotel_col = c
        elif c in ["国家 Country", "国家", "Country"]:
            col_map[c] = t["col_country"]
        elif c in ["报价币种 Currency", "报价币种", "Currency"]:
            col_map[c] = t["col_currency"]
        elif c in ["房型要求 Room Type", "房型要求", "Room Type"]:
            col_map[c] = t["col_room_type"]
        elif c in ["酒店星级 Star Rating", "酒店星级", "Star Rating"]:
            col_map[c] = t["col_star"]
        elif c in ["入住日期", "Check In", "Check-in"]:
            col_map[c] = t["col_checkin"]
        elif c in ["退房日期", "Check Out", "Check-out"]:
            col_map[c] = t["col_checkout"]
    hotel_info = hotel_info.rename(columns=col_map)

    # 加载已保存的比价数据并合并（传递t用于列名规范化）
    existing = _load_price_data(t)
    merged = _merge_with_existing(existing, hotel_info, t)

    if merged.empty:
        st.warning(t["empty_tip"])
        return

    # 确保列顺序（去掉团单号，添加Check in/Check out）
    base_cols = [t["col_hotel"], t["col_star"], t["col_country"], t["col_currency"], t["col_checkin"], t["col_checkout"], t["col_room_type"], t["col_group_rate"], t["col_price"]]
    all_cols = base_cols + PLATFORMS
    for c in all_cols:
        if c not in merged.columns:
            merged[c] = ""
    merged = merged[all_cols]

    # 过滤空白酒店名称的数据
    merged = merged[merged[t["col_hotel"]].astype(str).str.strip() != ""]
    merged = merged[~merged[t["col_hotel"]].isna()]
    
    # 用 session_state 维护表格数据
    import os as _os
    csv_mtime = _os.path.getmtime(PRICE_FILE) if _os.path.exists(PRICE_FILE) else 0
    is_editing = st.session_state.get("price_df_editing", False)
    has_session_data = "price_df" in st.session_state and len(st.session_state["price_df"]) > 0
    
    print(f"[初始化调试] is_editing={is_editing}, has_session_data={has_session_data}")
    print(f"[初始化调试] csv_mtime={csv_mtime}, session_mtime={st.session_state.get('price_df_csv_mtime', 0)}")
    print(f"[初始化调试] merged 长度={len(merged)}")
    
    if not has_session_data:
        st.session_state["price_df"] = merged.copy()
        st.session_state["price_df_csv_mtime"] = csv_mtime
        print(f"[初始化调试] 从 merged 初始化，长度={len(st.session_state['price_df'])}")
    elif not is_editing:
        if st.session_state.get("price_df_csv_mtime", 0) != csv_mtime:
            st.session_state["price_df"] = merged.copy()
            st.session_state["price_df_csv_mtime"] = csv_mtime
            print(f"[初始化调试] CSV变化，重新加载，长度={len(st.session_state['price_df'])}")
        else:
            print(f"[初始化调试] 使用 session_state 数据，长度={len(st.session_state['price_df'])}")
    else:
        print(f"[初始化调试] 正在编辑，使用 session_state 数据，长度={len(st.session_state['price_df'])}")
    
    # 标记正在编辑
    st.session_state["price_df_editing"] = True

    # 保存原始未筛选数据（用于合并未被筛选展示的酒店）
    original_price_df = st.session_state["price_df"].copy()

    price_df = st.session_state["price_df"].copy()

    # 筛选器
    if st.session_state.pop("_clear_filters", False):
        st.session_state["filter_hotel_input"] = ""
        st.session_state["filter_country_input"] = ""

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        sel_hotel = st.text_input(t["filter_hotel"], key="filter_hotel_input")
    with f_col2:
        sel_country = st.text_input(t["filter_country"], key="filter_country_input")

    import re as _re
    filtered_df = price_df.copy()
    if sel_hotel.strip():
        filtered_df = filtered_df[filtered_df[t["col_hotel"]].astype(str).str.contains(_re.escape(sel_hotel.strip()), case=False, na=False, regex=True)]
    if sel_country.strip():
        filtered_df = filtered_df[filtered_df[t["col_country"]].astype(str).str.contains(_re.escape(sel_country.strip()), case=False, na=False, regex=True)]
    price_df = filtered_df.copy()

    # 显示标题
    st.subheader("📋 " + ("比价数据表" if lang == "zh" else "Price Comparison Table"))
    st.caption(t["delete_inline_tip"])

    # 按「酒店名」分组，保持首次出现顺序
    group_keys = []
    seen = set()
    for _, row in price_df.iterrows():
        h = str(row.get(t["col_hotel"], "")).strip()
        if not h or h.lower() == "nan":
            continue
        key = h
        if key not in seen:
            group_keys.append(key)
            seen.add(key)

    rebuilt_rows = []
    need_rerun = False

    for i, hotel_name in enumerate(group_keys):
        mask = price_df[t["col_hotel"]].astype(str).str.strip() == hotel_name
        group_df = price_df[mask].copy().reset_index(drop=True)

        if group_df.empty:
            continue

        country = str(group_df.iloc[0].get(t["col_country"], ""))
        currency = str(group_df.iloc[0].get(t["col_currency"], ""))
        star = str(group_df.iloc[0].get(t["col_star"], ""))
        checkin = str(group_df.iloc[0].get(t["col_checkin"], ""))
        checkout = str(group_df.iloc[0].get(t["col_checkout"], ""))

        room_cols = [t["col_room_type"], t["col_group_rate"], t["col_price"]] + PLATFORMS
        editor_key = f"hotel_editor_{i}_{hotel_name}"
        
        with st.form(key=f"hotel_form_{i}_{hotel_name}", border=True):
            hdr = st.columns([1, 5, 1, 2, 2, 2, 2])
            with hdr[0]:
                st.markdown(f"**# {i + 1}**")
            with hdr[1]:
                edited_hotel = st.text_input(
                    "🏨", value=hotel_name, key=f"hotel_name_{i}_{hotel_name}",
                    label_visibility="collapsed"
                )
            with hdr[2]:
                edited_star = st.text_input(
                    t["col_star"], value=star, key=f"hotel_star_{i}_{hotel_name}",
                    label_visibility="collapsed", placeholder=t["col_star"]
                )
            with hdr[3]:
                edited_country = st.text_input(
                    t["col_country"], value=country, key=f"hotel_country_{i}_{hotel_name}",
                    label_visibility="collapsed", placeholder=t["col_country"]
                )
            with hdr[4]:
                edited_currency = st.text_input(
                    t["col_currency"], value=currency, key=f"hotel_currency_{i}_{hotel_name}",
                    label_visibility="collapsed", placeholder=t["col_currency"]
                )
            with hdr[5]:
                edited_checkin = st.text_input(
                    t["col_checkin"], value=checkin, key=f"hotel_checkin_{i}_{hotel_name}",
                    label_visibility="collapsed", placeholder=t["col_checkin"]
                )
            with hdr[6]:
                edited_checkout = st.text_input(
                    t["col_checkout"], value=checkout, key=f"hotel_checkout_{i}_{hotel_name}",
                    label_visibility="collapsed", placeholder=t["col_checkout"]
                )

            # 初始化 room_df：优先使用 session_state 中的数据
            if editor_key in st.session_state:
                try:
                    saved_edited = st.session_state[editor_key]
                    if isinstance(saved_edited, pd.DataFrame) and not saved_edited.empty:
                        room_df = saved_edited.copy()
                        for col in room_cols:
                            if col not in room_df.columns:
                                room_df[col] = ""
                        room_df["#"] = range(1, len(room_df) + 1)
                        if t["col_delete"] not in room_df.columns:
                            room_df[t["col_delete"]] = False
                    else:
                        room_df = group_df[room_cols].copy()
                        room_df.insert(0, "#", range(1, len(room_df) + 1))
                        room_df[t["col_delete"]] = False
                except Exception:
                    room_df = group_df[room_cols].copy()
                    room_df.insert(0, "#", range(1, len(room_df) + 1))
                    room_df[t["col_delete"]] = False
            else:
                room_df = group_df[room_cols].copy()
                room_df.insert(0, "#", range(1, len(room_df) + 1))
                room_df[t["col_delete"]] = False

            edited = st.data_editor(
                room_df,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "#": st.column_config.NumberColumn("#", format="%d", disabled=True),
                    t["col_room_type"]: st.column_config.TextColumn(t["col_room_type"]),
                    t["col_group_rate"]: st.column_config.NumberColumn(t["col_group_rate"], format="%.2f"),
                    t["col_price"]: st.column_config.NumberColumn(t["col_price"], format="%.2f"),
                    **{p: st.column_config.NumberColumn(p, format="%.2f") for p in PLATFORMS},
                    t["col_delete"]: st.column_config.CheckboxColumn(t["col_delete"], default=False, width="small")
                },
                key=editor_key
            )

            # 添加房型按钮（表单需要一个submit按钮）
            add_room = st.form_submit_button(t["add_room_btn"], use_container_width=True)

            # 添加房型后的处理
            if add_room:
                edited["#"] = range(1, len(edited) + 1)

                # 检测删除
                delete_triggered = False
                if t["col_delete"] in edited.columns and edited[t["col_delete"]].any():
                    if not need_rerun:
                        st.session_state["price_df_backup"] = st.session_state["price_df"].copy()
                    keep_mask = ~edited[t["col_delete"]]
                    edited = edited[keep_mask].reset_index(drop=True)
                    st.session_state["_clear_filters"] = True
                    need_rerun = True
                    delete_triggered = True

                # 添加房型
                new_row = pd.DataFrame([{
                    t["col_room_type"]: "",
                    t["col_group_rate"]: 0,
                    t["col_price"]: 0,
                    **{p: 0 for p in PLATFORMS}
                }])
                edited = pd.concat([edited.drop(columns=["#", t["col_delete"]]), new_row], ignore_index=True)
                need_rerun = True

            # 收集该酒店的所有房型行（使用编辑后的酒店信息）
            # 优先使用 session_state 中的数据，确保点击全局保存时能获取最新编辑
            data_source = st.session_state.get(editor_key, edited)
            if data_source is None or not isinstance(data_source, pd.DataFrame) or data_source.empty:
                data_source = edited
            
            # 从 session_state 获取 text_input 的值（用户可能编辑了但没提交表单）
            saved_hotel = st.session_state.get(f"hotel_name_{i}_{hotel_name}", edited_hotel)
            saved_star = st.session_state.get(f"hotel_star_{i}_{hotel_name}", edited_star)
            saved_country = st.session_state.get(f"hotel_country_{i}_{hotel_name}", edited_country)
            saved_currency = st.session_state.get(f"hotel_currency_{i}_{hotel_name}", edited_currency)
            saved_checkin = st.session_state.get(f"hotel_checkin_{i}_{hotel_name}", edited_checkin)
            saved_checkout = st.session_state.get(f"hotel_checkout_{i}_{hotel_name}", edited_checkout)
            
            for _, row in data_source.iterrows():
                rebuilt_rows.append({
                    t["col_hotel"]: saved_hotel.strip(),
                    t["col_star"]: saved_star.strip(),
                    t["col_country"]: saved_country.strip(),
                    t["col_currency"]: saved_currency.strip(),
                    t["col_checkin"]: saved_checkin.strip(),
                    t["col_checkout"]: saved_checkout.strip(),
                    t["col_room_type"]: row.get(t["col_room_type"], ""),
                    t["col_group_rate"]: row.get(t["col_group_rate"], 0),
                    t["col_price"]: row.get(t["col_price"], 0),
                    **{p: row.get(p, 0) for p in PLATFORMS}
                })

    # 重建 price_df：合并未筛选展示的酒店（保持原数据）与当前展示的酒店（含编辑）
    base_cols = [t["col_hotel"], t["col_star"], t["col_country"], t["col_currency"], t["col_checkin"], t["col_checkout"], t["col_room_type"], t["col_group_rate"], t["col_price"]] + PLATFORMS

    # 当前展示的酒店（已编辑）
    if rebuilt_rows:
        rebuilt_df = pd.DataFrame(rebuilt_rows)
        for c in base_cols:
            if c not in rebuilt_df.columns:
                rebuilt_df[c] = ""
        rebuilt_df = rebuilt_df[base_cols]
    else:
        rebuilt_df = pd.DataFrame(columns=base_cols)

    # 未展示的酒店（未被筛选命中的，保持原数据不变）
    processed_keys = set(group_keys)
    if not processed_keys:
        unfiltered_df = original_price_df.copy()
    else:
        def _is_processed(r):
            h = str(r.get(t["col_hotel"], "")).strip()
            return h in processed_keys
        unfiltered_df = original_price_df[~original_price_df.apply(_is_processed, axis=1)].copy()
        for c in base_cols:
            if c not in unfiltered_df.columns:
                unfiltered_df[c] = ""
        unfiltered_df = unfiltered_df[base_cols]

    # 合并：未展示的原数据 + 已编辑的展示数据
    new_price_df = pd.concat([unfiltered_df, rebuilt_df], ignore_index=True)

    # 关键修复：每次编辑后都立即更新 session_state，防止刷新回退
    st.session_state["price_df"] = new_price_df.copy()

    if need_rerun:
        st.rerun()

    # 全局保存按钮 - 使用 st.form 包装，确保点击保存时所有表单数据都已提交
    with st.form(key="global_save_form", border=False):
        save_col, _ = st.columns([1, 3])
        with save_col:
            if st.form_submit_button(t["save_btn"], key="global_save_btn", type="primary", use_container_width=True):
                print(f"[保存调试] new_price_df 长度: {len(new_price_df)}")
                print(f"[保存调试] new_price_df 列: {list(new_price_df.columns)}")
                if len(new_price_df) == 0:
                    st.warning("当前没有可保存的数据，请先添加酒店或确保有数据显示")
                else:
                    try:
                        _save_price_data(new_price_df)
                        import os as _os2
                        st.session_state["price_df_csv_mtime"] = _os2.path.getmtime(PRICE_FILE) if _os2.path.exists(PRICE_FILE) else 0
                        st.session_state["price_df"] = new_price_df.copy()
                        
                        fs_config = load_feishu_config()
                        if fs_config.get("price_sheet_id"):
                            try:
                                write_feishu_price_table(new_price_df)
                                st.success(f"{t['save_success'].format(len(new_price_df))}（已同步到飞书比价表格）")
                                print(f"[比价同步] 成功同步{len(new_price_df)}条数据到飞书表格")
                            except Exception as fs_err:
                                st.warning(f"{t['save_success'].format(len(new_price_df))}（飞书同步失败: {str(fs_err)}）")
                                print(f"[比价同步] 飞书同步失败: {str(fs_err)}")
                        else:
                            st.success(t["save_success"].format(len(new_price_df)))
                            print(f"[比价同步] 未配置飞书比价表格，仅保存到本地CSV")
                    except Exception as e:
                        st.error(t["save_error"].format(str(e)))

    # 添加酒店按钮
    add_hotel_col, _ = st.columns([1, 3])
    with add_hotel_col:
        if st.button(t["add_hotel_btn"], key="add_hotel_btn", use_container_width=True):
            new_hotel_row = pd.DataFrame([{
                t["col_hotel"]: ("新酒店" if lang == "zh" else "New Hotel"),
                t["col_star"]: "",
                t["col_country"]: "",
                t["col_currency"]: "",
                t["col_checkin"]: "",
                t["col_checkout"]: "",
                t["col_room_type"]: "",
                t["col_group_rate"]: 0,
                t["col_price"]: 0,
                **{p: 0 for p in PLATFORMS}
            }])
            updated_df = pd.concat([new_price_df, new_hotel_row], ignore_index=True)
            st.session_state["price_df"] = updated_df.copy()
            
            # 立即保存到本地CSV和飞书，防止页面刷新后丢失
            try:
                _save_price_data(updated_df)
                try:
                    write_feishu_price_table(updated_df)
                    print("[添加酒店] 成功保存到飞书")
                except Exception:
                    pass
            except Exception:
                pass
            
            st.rerun()

    # 撤销删除按钮（仅当存在备份时显示）
    if "price_df_backup" in st.session_state and st.session_state["price_df_backup"] is not None:
        undo_col, _ = st.columns([1, 3])
        with undo_col:
            if st.button(t["undo_btn"], key="undo_delete_btn", use_container_width=True):
                backup = st.session_state["price_df_backup"]
                restored = len(backup)
                st.session_state["price_df"] = backup.copy()
                st.session_state["price_df_backup"] = None
                st.success(t["undo_success"].format(restored))
                st.rerun()

    st.divider()

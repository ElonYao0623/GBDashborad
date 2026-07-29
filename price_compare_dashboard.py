"""比价数据只读展示页面"""
import os
import pandas as pd
import streamlit as st

PRICE_FILE = "price_compare.csv"
MAIN_FILE = "团房数据.csv"

PAGE_TEXT = {
    "zh": {
        "page_header": "比价数据展示",
        "page_desc": "所有酒店的比价数据（按房型维度展示）",
        "empty_tip": "暂无比价数据",
        "col_hotel": "酒店名称",
        "col_star": "星级",
        "col_country": "国家",
        "col_sales_team": "销售团队",
        "col_city": "城市",
        "col_currency": "报价币种",
        "col_checkin": "Check in",
        "col_checkout": "Check out",
        "col_room_type": "房型要求",
        "col_group_rate": "团房组底价",
        "col_price": "运营报价",
        "col_lowest": "最低报价",
        "col_order_id": "团单号",
        "filter_hotel": "酒店名称",
        "filter_country": "国家",
        "filter_city": "城市",
        "filter_room_type": "房型",
        "filter_checkin": "入住日期",
        "filter_checkout": "离店日期",
        "filter_order_id": "团单号",
    },
    "en": {
        "page_header": "Price Comparison Dashboard",
        "page_desc": "All hotel price comparison data (by room type)",
        "empty_tip": "No price data available",
        "col_hotel": "酒店名称",
        "col_star": "星级",
        "col_country": "国家",
        "col_sales_team": "销售团队",
        "col_city": "城市",
        "col_currency": "报价币种",
        "col_checkin": "Check in",
        "col_checkout": "Check out",
        "col_room_type": "房型要求",
        "col_group_rate": "团房组底价",
        "col_price": "运营报价",
        "col_lowest": "Lowest Quote",
        "col_order_id": "Booking No",
        "filter_hotel": "Hotel Name",
        "filter_country": "Country",
        "filter_city": "City",
        "filter_room_type": "Room Type",
        "filter_checkin": "Check-in Date",
        "filter_checkout": "Check-out Date",
        "filter_order_id": "Booking No",
    },
}


def _to_num(val):
    """安全转换为 float，失败返回 None"""
    try:
        if val is None or str(val).strip() == "":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def _find_lowest(row, platforms):
    """找出最低报价（仅各平台，不含底价和运营报价）"""
    candidates = [(p, _to_num(row.get(p, ""))) for p in platforms]
    valid = [(name, v) for name, v in candidates if v is not None and v > 0]
    if not valid:
        return None, None
    return min(valid, key=lambda x: x[1])


def _calc_pct_diff(val, base):
    """计算与底价的百分比差异"""
    if val is None or base is None or base == 0:
        return None
    return (val - base) / base * 100


def _load_price_data():
    """加载比价数据"""
    try:
        if "price_df" in st.session_state and st.session_state.get("price_df_editing", False):
            return st.session_state["price_df"].copy().fillna("")
    except Exception:
        pass
    
    if os.path.exists(PRICE_FILE):
        try:
            return pd.read_csv(PRICE_FILE, encoding="utf-8-sig", dtype=str).fillna("")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def _load_order_id_mapping():
    """从主数据加载酒店名称到团单号的映射"""
    if not os.path.exists(MAIN_FILE):
        return {}
    
    try:
        df = pd.read_csv(MAIN_FILE, encoding="utf-8-sig", dtype=str).fillna("")
    except Exception:
        return {}
    
    order_id_col = None
    for c in ["团单号", "Booking No"]:
        if c in df.columns:
            order_id_col = c
            break
    
    hotel_col = None
    for c in ["酒店名称 Hotel Name", "酒店名称", "Hotel Name"]:
        if c in df.columns:
            hotel_col = c
            break
    
    if not order_id_col or not hotel_col:
        return {}
    
    import re
    def _split_hotel_names(name):
        if not name or str(name).strip().lower() == "nan":
            return []
        name = str(name).strip()
        numbered_pattern = r"(?<![0-9])([0-9]+)\.\s*"
        numbered_matches = list(re.finditer(numbered_pattern, name))
        if len(numbered_matches) >= 2:
            parts = []
            start = 0
            for i, match in enumerate(numbered_matches):
                if i > 0:
                    end = match.start()
                    part = name[start:end].strip()
                    if part:
                        parts.append(part)
                start = match.start()
            part = name[start:].strip()
            if part:
                parts.append(part)
            cleaned_parts = []
            for p in parts:
                p = re.sub(r"^[0-9]+\.\s*", "", p)
                p = p.strip()
                if p:
                    cleaned_parts.append(p)
            return cleaned_parts
        parts = re.split(r"[/、&\+\n;；]", name)
        parts = [p.strip() for p in parts if p.strip()]
        return parts
    
    mapping = {}
    for _, row in df.iterrows():
        raw_name = row.get(hotel_col, "")
        hotels = _split_hotel_names(raw_name)
        order_id = str(row.get(order_id_col, "")).strip()
        if not order_id:
            continue
        for h in hotels:
            h = h.strip()
            if h:
                if h not in mapping:
                    mapping[h] = set()
                mapping[h].add(order_id)
    
    for h in mapping:
        mapping[h] = ", ".join(sorted(mapping[h]))
    
    return mapping


def render_price_compare_dashboard():
    """渲染只读比价展示页面（按酒店分组，房型维度展示）"""
    lang = st.session_state.get("lang", "zh")
    t = PAGE_TEXT[lang]

    st.markdown(
        """
        <style>
        .streamlit-expanderHeader {
            font-size: 18px !important;
            font-weight: bold !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.header(t["page_header"])
    st.markdown(t["page_desc"])
    st.divider()

    price_df = _load_price_data()
    if price_df.empty:
        st.warning(t["empty_tip"])
        return
    
    user_role = st.session_state.get("user_role", "")
    user_team = st.session_state.get("user_team", "")
    if user_role == "sales" and user_team and t["col_sales_team"] in price_df.columns:
        price_df = price_df[price_df[t["col_sales_team"]].astype(str).str.contains(user_team, case=False, na=False)]
        if price_df.empty:
            st.warning(t["empty_tip"])
            return

    base_cols = [
        t["col_hotel"], t["col_order_id"], t["col_star"], t["col_country"], t["col_sales_team"], t["col_city"],
        t["col_currency"], t["col_checkin"], t["col_checkout"],
        t["col_room_type"], t["col_group_rate"], t["col_price"]
    ]
    
    all_platforms = []
    exclude_cols = [t["col_order_id"]]
    for col in price_df.columns:
        if col not in base_cols and col not in exclude_cols:
            all_platforms.append(col)
    
    for key in base_cols:
        if key not in price_df.columns:
            price_df[key] = ""

    price_df = price_df[price_df[t["col_hotel"]].astype(str).str.strip() != ""]
    price_df = price_df[~price_df[t["col_hotel"]].isna()]
    if price_df.empty:
        st.warning(t["empty_tip"])
        return

    f_col1, f_col2, f_col3, f_col4, f_col5, f_col6, f_col7 = st.columns(7)
    with f_col1:
        sel_hotel = st.text_input(t["filter_hotel"], key="dash_filter_hotel")
    with f_col2:
        sel_country = st.text_input(t["filter_country"], key="dash_filter_country")
    with f_col3:
        sel_city = st.text_input(t["filter_city"], key="dash_filter_city")
    with f_col4:
        sel_room_type = st.text_input(t["filter_room_type"], key="dash_filter_room_type")
    with f_col5:
        sel_checkin = st.date_input(t["filter_checkin"], key="dash_filter_checkin", value=None)
    with f_col6:
        sel_checkout = st.date_input(t["filter_checkout"], key="dash_filter_checkout", value=None)
    with f_col7:
        sel_order_id = st.text_input(t["filter_order_id"], key="dash_filter_order_id")

    filtered_df = price_df.copy()
    if sel_hotel.strip():
        filtered_df = filtered_df[filtered_df[t["col_hotel"]].astype(str).str.contains(sel_hotel.strip(), case=False, na=False)]
    if sel_country.strip():
        filtered_df = filtered_df[filtered_df[t["col_country"]].astype(str).str.contains(sel_country.strip(), case=False, na=False)]
    if sel_city.strip():
        filtered_df = filtered_df[filtered_df[t["col_city"]].astype(str).str.contains(sel_city.strip(), case=False, na=False)]
    if sel_room_type.strip():
        filtered_df = filtered_df[filtered_df[t["col_room_type"]].astype(str).str.contains(sel_room_type.strip(), case=False, na=False)]
    
    if sel_order_id.strip():
        order_id_mapping = _load_order_id_mapping()
        matching_hotels = [h for h, oids in order_id_mapping.items() if sel_order_id.strip() in oids]
        if matching_hotels:
            filtered_df = filtered_df[filtered_df[t["col_hotel"]].astype(str).str.strip().isin(matching_hotels)]
        else:
            filtered_df = filtered_df.iloc[0:0]
    
    if sel_checkin:
        sel_month = sel_checkin.month
        sel_day = sel_checkin.day
        drop_indices = []
        for idx, row in filtered_df.iterrows():
            checkin_val = str(row.get(t["col_checkin"], "")).strip()
            try:
                if "/" in checkin_val:
                    parts = checkin_val.split("/")
                    if len(parts) == 2:
                        month = int(parts[0])
                        day = int(parts[1])
                        if month < sel_month or (month == sel_month and day < sel_day):
                            drop_indices.append(idx)
                elif "-" in checkin_val:
                    parts = checkin_val.split("-")
                    if len(parts) == 3:
                        month = int(parts[1])
                        day = int(parts[2])
                        if month < sel_month or (month == sel_month and day < sel_day):
                            drop_indices.append(idx)
            except (ValueError, IndexError):
                pass
        filtered_df = filtered_df.drop(drop_indices)
    
    if sel_checkout:
        sel_month = sel_checkout.month
        sel_day = sel_checkout.day
        drop_indices = []
        for idx, row in filtered_df.iterrows():
            checkout_val = str(row.get(t["col_checkout"], "")).strip()
            try:
                if "/" in checkout_val:
                    parts = checkout_val.split("/")
                    if len(parts) == 2:
                        month = int(parts[0])
                        day = int(parts[1])
                        if month > sel_month or (month == sel_month and day > sel_day):
                            drop_indices.append(idx)
                elif "-" in checkout_val:
                    parts = checkout_val.split("-")
                    if len(parts) == 3:
                        month = int(parts[1])
                        day = int(parts[2])
                        if month > sel_month or (month == sel_month and day > sel_day):
                            drop_indices.append(idx)
            except (ValueError, IndexError):
                pass
        filtered_df = filtered_df.drop(drop_indices)

    if filtered_df.empty:
        st.warning(t["empty_tip"])
        return

    hotel_groups = filtered_df.groupby(t["col_hotel"], sort=False)

    total_hotels = len(hotel_groups)
    total_room_types = len(filtered_df)
    st.info(f"{'共' if lang == 'zh' else 'Total'} {total_hotels} {'家酒店' if lang == 'zh' else 'hotels'}, {total_room_types} {'种房型' if lang == 'zh' else 'room types'}")

    order_id_mapping = _load_order_id_mapping()

    for hotel_name, group_df in hotel_groups:
        group_df = group_df.reset_index(drop=True)
        hotel_info = group_df.iloc[0]
        
        currency = hotel_info.get(t["col_currency"], "")
        
        op_prices = []
        for _, r in group_df.iterrows():
            v = _to_num(r.get(t["col_price"], ""))
            if v is not None and v > 0:
                op_prices.append(v)
        op_price_display = f" | **{t['col_price']}: {currency} {min(op_prices):,.0f}**" if op_prices else ""
        
        order_ids = order_id_mapping.get(hotel_name.strip(), "")
        order_id_display = f" | **{t['col_order_id']}: {order_ids}**" if order_ids else ""
        
        room_type_label = "种房型" if lang == "zh" else " room types"
        with st.expander(f"🏨 {hotel_name} ({len(group_df)}{room_type_label}){op_price_display}", expanded=False):
            st.markdown(f"**星级**: {hotel_info.get(t['col_star'], '-')} | **国家**: {hotel_info.get(t['col_country'], '-')} | **销售团队**: {hotel_info.get(t['col_sales_team'], '-')} | **城市**: {hotel_info.get(t['col_city'], '-')}")
            st.markdown(f"**入住日期**: {hotel_info.get(t['col_checkin'], '-')} | **离店日期**: {hotel_info.get(t['col_checkout'], '-')}{order_id_display}")
            
            for idx, row in group_df.iterrows():
                with st.container(border=True):
                    base = _to_num(row.get(t["col_group_rate"], ""))
                    lowest_name, lowest_val = _find_lowest(row, all_platforms)
                    
                    cols = st.columns([2, 0.8, 0.8, 1, 1] + [1] * len(all_platforms) + [1.5])
                    
                    with cols[0]:
                        st.caption("房型")
                        st.markdown(f"**{row.get(t['col_room_type'], '')}**")
                    with cols[1]:
                        st.caption("币种")
                        st.markdown(row.get(t["col_currency"], "") or "-")
                    with cols[2]:
                        st.caption("团房组底价")
                        _v = base
                        st.markdown(f"{_v:,.0f}" if _v is not None else "-")
                    with cols[3]:
                        st.caption("运营报价")
                        _v = _to_num(row.get(t["col_price"], ""))
                        st.markdown(f"{_v:,.0f}" if _v is not None else "-")
                        if _v is not None and base is not None and base != 0:
                            pct = _calc_pct_diff(_v, base)
                            sign = "+" if pct >= 0 else ""
                            color = "green" if pct >= 0 else "red"
                            arrow = "▲" if pct >= 0 else "▼"
                            st.markdown(f"<span style='color:{color}; font-size:12px'>{arrow} {sign}{pct:.1f}%</span>", unsafe_allow_html=True)
                    for j, p in enumerate(all_platforms):
                        with cols[4 + j]:
                            st.caption(p)
                            _v = _to_num(row.get(p, ""))
                            _is_low = (lowest_name == p) if lowest_val is not None else False
                            st.markdown(f"{'🏆 ' if _is_low else ''}{_v:,.0f}" if _v is not None else "-")
                            if _v is not None and base is not None and base != 0:
                                pct = _calc_pct_diff(_v, base)
                                sign = "+" if pct >= 0 else ""
                                color = "green" if pct >= 0 else "red"
                                arrow = "▲" if pct >= 0 else "▼"
                                st.markdown(f"<span style='color:{color}; font-size:12px'>{arrow} {sign}{pct:.1f}%</span>", unsafe_allow_html=True)
                    with cols[-1]:
                        st.caption("最低报价")
                        if lowest_val is not None and base is not None and base != 0:
                            pct = _calc_pct_diff(lowest_val, base)
                            sign = "+" if pct >= 0 else ""
                            color = "green" if pct >= 0 else "red"
                            st.markdown(f"**{lowest_name}**  \n<span style='color:{color}'>{sign}{pct:.1f}%</span>", unsafe_allow_html=True)
                        elif lowest_val is not None:
                            st.markdown(f"**{lowest_name}**")
                        else:
                            st.markdown("-")
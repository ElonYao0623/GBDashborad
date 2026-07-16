"""比价数据只读展示页面"""
import os
import pandas as pd
import streamlit as st

PRICE_FILE = "price_compare.csv"
MAIN_FILE = "团房数据.csv"
PLATFORMS = ["Booking.com", "Expedia", "Trip.com", "Agoda", "Traveloka"]

PAGE_TEXT = {
    "zh": {
        "page_header": "比价数据展示",
        "page_desc": "所有酒店的比价数据（按房型维度展示）",
        "empty_tip": "暂无比价数据",
        "col_order": "团单号",
        "col_hotel": "酒店名称",
        "col_star": "酒店星级",
        "col_country": "国家",
        "col_currency": "报价币种",
        "col_room_type": "房型",
        "col_group_rate": "团房组底价",
        "col_price": "运营报价",
        "col_lowest": "最低报价",
        "compare_vs_base": "比价信息（相对团房组底价差值%）",
        "filter_order_id": "团单号",
        "filter_hotel": "酒店名称",
        "filter_country": "国家",
        "filter_room_type": "房型",
    },
    "en": {
        "page_header": "Price Comparison Dashboard",
        "page_desc": "All hotel price comparison data (by room type)",
        "empty_tip": "No price data available",
        "col_order": "Booking No",
        "col_hotel": "Hotel Name",
        "col_star": "Star Rating",
        "col_country": "Country",
        "col_currency": "Currency",
        "col_room_type": "Room Type",
        "col_group_rate": "Group Net Rate",
        "col_price": "Op Quotation",
        "col_lowest": "Lowest Quote",
        "compare_vs_base": "Comparison (vs Group Net Rate %)",
        "filter_order_id": "Booking No",
        "filter_hotel": "Hotel Name",
        "filter_country": "Country",
        "filter_room_type": "Room Type",
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


def _find_lowest(row, t):
    """找出最低报价（仅各平台，不含底价和运营报价）"""
    candidates = [(p, _to_num(row.get(p, ""))) for p in PLATFORMS]
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
    """加载已保存的比价数据"""
    if os.path.exists(PRICE_FILE):
        try:
            return pd.read_csv(PRICE_FILE, encoding="utf-8-sig", dtype=str).fillna("")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def _load_main_data():
    """加载主数据用于回填团单号和星级"""
    if os.path.exists(MAIN_FILE):
        try:
            return pd.read_csv(MAIN_FILE, encoding="utf-8-sig", dtype=str).fillna("")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def _backfill_from_main(price_df, t):
    """从主数据回填团单号和酒店星级（支持同名酒店不同团单号）"""
    main_df = _load_main_data()
    if main_df.empty:
        return price_df

    # 查找主数据中的列
    hotel_col = None
    for c in ["酒店名称 Hotel Name", "酒店名称", "Hotel Name"]:
        if c in main_df.columns:
            hotel_col = c
            break
    star_col = None
    for c in ["酒店星级 Star Rating", "酒店星级", "Star Rating"]:
        if c in main_df.columns:
            star_col = c
            break
    order_col = None
    for c in ["团单号"]:
        if c in main_df.columns:
            order_col = c
            break

    if not hotel_col:
        return price_df

    # 按酒店名分组，保留所有 (团单号, 星级) 组合
    hotel_entries = {}
    for _, row in main_df.iterrows():
        hn = str(row.get(hotel_col, "")).strip()
        if not hn or hn.lower() == "nan":
            continue
        ov = str(row.get(order_col, "")).strip() if order_col else ""
        sv = str(row.get(star_col, "")).strip() if star_col else ""
        ov = ov if ov and ov.lower() != "nan" else ""
        sv = sv if sv and sv.lower() != "nan" else ""
        if hn not in hotel_entries:
            hotel_entries[hn] = []
        # 去重添加
        entry = (ov, sv)
        if entry not in hotel_entries[hn]:
            hotel_entries[hn].append(entry)

    # 为比价数据每行匹配团单号和星级
    # 用游标跟踪每个酒店名已分配的条目索引
    hotel_cursor = {}
    for idx, row in price_df.iterrows():
        hn = str(row.get(t["col_hotel"], "")).strip()
        if hn not in hotel_entries or not hotel_entries[hn]:
            continue

        entries = hotel_entries[hn]
        cur_order = str(row.get(t["col_order"], "")).strip()
        cur_star = str(row.get(t["col_star"], "")).strip()

        # 如果已有团单号，尝试匹配对应条目
        matched = None
        if cur_order and cur_order.lower() != "nan":
            for e in entries:
                if e[0] == cur_order:
                    matched = e
                    break

        if matched is None:
            # 按游标顺序取下一个未分配的条目
            cursor = hotel_cursor.get(hn, 0)
            if cursor < len(entries):
                matched = entries[cursor]
                hotel_cursor[hn] = cursor + 1
            else:
                matched = entries[0]  # 回退到第一个

        # 回填空缺字段
        if (not cur_order or cur_order.lower() == "nan") and matched[0]:
            price_df.at[idx, t["col_order"]] = matched[0]
        if (not cur_star or cur_star.lower() == "nan") and matched[1]:
            price_df.at[idx, t["col_star"]] = matched[1]

    return price_df


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

    # 列重映射（兼容旧数据可能缺失的列）
    # 处理房型列名差异：CSV中是"房型要求"，但页面显示用"房型"
    room_type_col_in_csv = None
    for c in ["房型要求", "房型要求 Room Type", "Room Type", t["col_room_type"]]:
        if c in price_df.columns:
            room_type_col_in_csv = c
            break
    if room_type_col_in_csv and room_type_col_in_csv != t["col_room_type"]:
        price_df = price_df.rename(columns={room_type_col_in_csv: t["col_room_type"]})
    
    for col in [t["col_order"], t["col_hotel"], t["col_star"], t["col_country"],
                t["col_currency"], t["col_room_type"], t["col_group_rate"], t["col_price"]] + PLATFORMS:
        if col not in price_df.columns:
            price_df[col] = ""

    # 从主数据回填团单号和酒店星级
    price_df = _backfill_from_main(price_df, t)

    # 筛选器
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        sel_order = st.text_input(t["filter_order_id"], key="dash_filter_order")
    with f_col2:
        sel_hotel = st.text_input(t["filter_hotel"], key="dash_filter_hotel")
    with f_col3:
        sel_country = st.text_input(t["filter_country"], key="dash_filter_country")
    with f_col4:
        sel_room_type = st.text_input(t["filter_room_type"], key="dash_filter_room_type")

    filtered_df = price_df.copy()
    if sel_order.strip():
        filtered_df = filtered_df[filtered_df[t["col_order"]].astype(str).str.contains(sel_order.strip(), case=False, na=False)]
    if sel_hotel.strip():
        filtered_df = filtered_df[filtered_df[t["col_hotel"]].astype(str).str.contains(sel_hotel.strip(), case=False, na=False)]
    if sel_country.strip():
        filtered_df = filtered_df[filtered_df[t["col_country"]].astype(str).str.contains(sel_country.strip(), case=False, na=False)]
    if sel_room_type.strip():
        filtered_df = filtered_df[filtered_df[t["col_room_type"]].astype(str).str.contains(sel_room_type.strip(), case=False, na=False)]

    if filtered_df.empty:
        st.warning(t["empty_tip"])
        return

    # 按酒店名称分组
    hotel_groups = filtered_df.groupby(t["col_hotel"], sort=False)

    # 统计信息
    total_hotels = len(hotel_groups)
    total_room_types = len(filtered_df)
    st.info(f"共 {total_hotels} 家酒店，{total_room_types} 种房型")

    # 按酒店分组渲染
    for hotel_name, group_df in hotel_groups:
        group_df = group_df.reset_index(drop=True)
        hotel_info = group_df.iloc[0]
        
        currency = hotel_info.get(t["col_currency"], "")
        
        op_prices = []
        for _, r in group_df.iterrows():
            v = _to_num(r.get(t["col_price"], ""))
            if v is not None and v > 0:
                op_prices.append(v)
        op_price_display = f" | **运营报价: {currency} {min(op_prices):.2f}**" if op_prices else ""
        
        with st.expander(f"🏨 {hotel_name} ({len(group_df)}种房型){op_price_display}", expanded=False):
            st.markdown(f"**{t['col_star']}**: {hotel_info.get(t['col_star'], '-')} | **{t['col_country']}**: {hotel_info.get(t['col_country'], '-')}")
            
            for idx, row in group_df.iterrows():
                with st.container(border=True):
                    base = _to_num(row.get(t["col_group_rate"], ""))
                    lowest_name, lowest_val = _find_lowest(row, t)
                    
                    cols = st.columns([1.2, 2, 0.8, 0.8, 1, 1] + [1] * len(PLATFORMS) + [1.5])
                    
                    with cols[0]:
                        st.caption(t["col_order"])
                        st.markdown(f"**{row.get(t['col_order'], '')}**")
                    with cols[1]:
                        st.caption(t["col_room_type"])
                        st.markdown(f"**{row.get(t['col_room_type'], '')}**")
                    with cols[2]:
                        st.caption(t["col_currency"])
                        st.markdown(row.get(t["col_currency"], "") or "-")
                    with cols[3]:
                        st.caption(t["col_group_rate"])
                        _v = base
                        st.markdown(f"{_v:.2f}" if _v is not None else "-")
                    with cols[4]:
                        st.caption(t["col_price"])
                        _v = _to_num(row.get(t["col_price"], ""))
                        st.markdown(f"{_v:.2f}" if _v is not None else "-")
                        if _v is not None and base is not None and base != 0:
                            pct = _calc_pct_diff(_v, base)
                            sign = "+" if pct >= 0 else ""
                            color = "green" if pct >= 0 else "red"
                            arrow = "▲" if pct >= 0 else "▼"
                            st.markdown(f"<span style='color:{color}; font-size:12px'>{arrow} {sign}{pct:.1f}%</span>", unsafe_allow_html=True)
                    for j, p in enumerate(PLATFORMS):
                        with cols[5 + j]:
                            st.caption(p)
                            _v = _to_num(row.get(p, ""))
                            _is_low = (lowest_name == p) if lowest_val is not None else False
                            st.markdown(f"{'🏆 ' if _is_low else ''}{_v:.2f}" if _v is not None else "-")
                            if _v is not None and base is not None and base != 0:
                                pct = _calc_pct_diff(_v, base)
                                sign = "+" if pct >= 0 else ""
                                color = "green" if pct >= 0 else "red"
                                arrow = "▲" if pct >= 0 else "▼"
                                st.markdown(f"<span style='color:{color}; font-size:12px'>{arrow} {sign}{pct:.1f}%</span>", unsafe_allow_html=True)
                    with cols[-1]:
                        st.caption(t["col_lowest"])
                        if lowest_val is not None and base is not None and base != 0:
                            pct = _calc_pct_diff(lowest_val, base)
                            sign = "+" if pct >= 0 else ""
                            color = "green" if pct >= 0 else "red"
                            st.markdown(f"**{lowest_name}**  \n<span style='color:{color}'>{sign}{pct:.1f}%</span>", unsafe_allow_html=True)
                        elif lowest_val is not None:
                            st.markdown(f"**{lowest_name}**")
                        else:
                            st.markdown("-")

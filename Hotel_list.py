"""优势酒店名单统计

从主数据筛选团房成功且运营备注为 10% 的优势酒店
"""
import streamlit as st
import pandas as pd
from config import get_standard_status

PAGE_TEXT = {
    "zh": {
        "page_header": "优势酒店名单",
        "page_desc": "统计团房成功且运营备注为 10% 的优势酒店",
        "col_hotel": "酒店名称",
        "col_country": "国家",
        "col_city": "城市",
        "col_count": "成功订单数",
        "empty_tip": "暂无符合条件的优势酒店",
        "total_tip": "共 {} 家优势酒店",
        "remark_keyword": "10%"
    },
    "en": {
        "page_header": "Preferred Hotel List",
        "page_desc": "Hotels with successful group bookings and 10% in ops remarks",
        "col_hotel": "Hotel Name",
        "col_country": "Country",
        "col_city": "City",
        "col_count": "Successful Orders",
        "empty_tip": "No preferred hotels found",
        "total_tip": "{} preferred hotels in total",
        "remark_keyword": "10%"
    }
}


def _detect_column(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    for candidate in candidates:
        for col in df.columns:
            if candidate.strip() == col.strip() or candidate.lower() == col.lower():
                return col
    return None


def render_hotel_list(df):
    lang = st.session_state["lang"]
    t = PAGE_TEXT[lang]

    st.header(t["page_header"])
    st.markdown(t["page_desc"])
    st.divider()

    hotel_col = _detect_column(df, ["酒店名称 Hotel Name", "酒店名称", "Hotel Name"])
    country_col = _detect_column(df, ["国家 Country", "国家", "Country"])
    city_col = _detect_column(df, ["城市 City", "城市", "City"])
    status_col = "状态" if "状态" in df.columns else ("状态 Status" if "状态 Status" in df.columns else None)
    remark_col = _detect_column(df, ["运营备注 Ops Notes", "运营备注", "Ops Notes"])

    if not hotel_col or not status_col:
        st.warning(t["empty_tip"])
        return

    work = df.copy()
    work[hotel_col] = work[hotel_col].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    work[status_col] = work[status_col].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    if country_col:
        work[country_col] = work[country_col].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    if remark_col:
        work[remark_col] = work[remark_col].apply(lambda x: str(x).strip() if pd.notna(x) else "")

    # 筛选：状态为团房成功
    success_key = "group_booking_success"
    work = work[work[status_col].apply(lambda x: get_standard_status(x) == success_key)]

    # 筛选：运营备注正好等于 "10%"
    if remark_col and remark_col in work.columns:
        work = work[work[remark_col] == t["remark_keyword"]]
    else:
        st.warning(t["empty_tip"])
        return

    if work.empty:
        st.info(t["empty_tip"])
        return

    # 提取酒店名称 + 国家 + 城市 + 订单数
    group_cols = [hotel_col]
    if country_col:
        group_cols.append(country_col)
    if city_col:
        group_cols.append(city_col)
    
    result = (
        work.groupby(group_cols)
        .size()
        .reset_index(name=t["col_count"])
        .sort_values(by=t["col_count"], ascending=False)
    )
    
    rename_dict = {hotel_col: t["col_hotel"]}
    if country_col:
        rename_dict[country_col] = t["col_country"]
    if city_col:
        rename_dict[city_col] = t["col_city"]
    result = result.rename(columns=rename_dict)
    
    if country_col not in result.columns:
        result[t["col_country"]] = ""
    if city_col not in result.columns:
        result[t["col_city"]] = ""
    
    result = result[[t["col_hotel"], t["col_country"], t["col_city"], t["col_count"]]]

    st.success(t["total_tip"].format(len(result)))

    st.markdown(
        """<style>
        div[data-testid="stDataFrame"] table td, div[data-testid="stDataFrame"] table th {
            text-align: center !important;
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.dataframe(result, use_container_width=True, hide_index=True)

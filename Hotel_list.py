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
    return None


def render_hotel_list(df):
    lang = st.session_state["lang"]
    t = PAGE_TEXT[lang]

    st.header(t["page_header"])
    st.markdown(t["page_desc"])
    st.divider()

    hotel_col = _detect_column(df, ["酒店名称 Hotel Name", "酒店名称", "Hotel Name"])
    country_col = _detect_column(df, ["国家 Country", "国家", "Country"])
    status_col = "状态" if "状态" in df.columns else ("状态 Status" if "状态 Status" in df.columns else None)
    remark_col = _detect_column(df, ["运营备注 Ops Notes", "运营备注", "Ops Notes"])

    if not hotel_col or not status_col:
        st.warning(t["empty_tip"])
        return

    work = df.copy()
    work[hotel_col] = work[hotel_col].fillna("").astype(str).str.strip()
    work[status_col] = work[status_col].fillna("").astype(str).str.strip()
    if country_col:
        work[country_col] = work[country_col].fillna("").astype(str).str.strip()
    if remark_col:
        work[remark_col] = work[remark_col].fillna("").astype(str).str.strip()

    # 筛选：状态为团房成功
    success_key = "group_booking_success"
    work = work[work[status_col].apply(lambda x: get_standard_status(x) == success_key)]

    # 筛选：运营备注正好等于 "10%"
    if remark_col:
        work = work[work[remark_col] == t["remark_keyword"]]
    else:
        st.warning(t["empty_tip"])
        return

    if work.empty:
        st.info(t["empty_tip"])
        return

    # 提取酒店名称 + 国家 + 订单数
    if country_col:
        result = (
            work.groupby([hotel_col, country_col])
            .size()
            .reset_index(name=t["col_count"])
            .sort_values(by=t["col_count"], ascending=False)
        )
        result = result.rename(columns={hotel_col: t["col_hotel"], country_col: t["col_country"]})
    else:
        result = (
            work.groupby(hotel_col)
            .size()
            .reset_index(name=t["col_count"])
            .sort_values(by=t["col_count"], ascending=False)
        )
        result[t["col_country"]] = ""
        result = result.rename(columns={hotel_col: t["col_hotel"]})
        result = result[[t["col_hotel"], t["col_country"], t["col_count"]]]

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

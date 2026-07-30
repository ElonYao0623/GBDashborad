"""优势酒店名单统计

从主数据筛选团房成功且运营备注为 10% 的优势酒店，
国家和城市字段从Price Dashboard（飞书比价表格）读取
"""
import streamlit as st
import pandas as pd
from config import get_standard_status, fetch_feishu_price_table

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


def _load_hotel_location_from_price():
    """从Price Dashboard（飞书比价表格）获取酒店的国家和城市信息"""
    try:
        feishu_df = fetch_feishu_price_table()
        if feishu_df.empty:
            return {}
        
        # 标准化列名
        col_map = {}
        for c in feishu_df.columns:
            if c in ["酒店名称", "Hotel Name", "酒店"]:
                col_map[c] = "酒店名称"
            elif c in ["国家", "Country"]:
                col_map[c] = "国家"
            elif c in ["城市", "City"]:
                col_map[c] = "城市"
        feishu_df = feishu_df.rename(columns=col_map)
        
        # 确保必要列存在
        if "酒店名称" not in feishu_df.columns:
            return {}
        
        # 填充空值并转换为字符串
        feishu_df["酒店名称"] = feishu_df["酒店名称"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
        feishu_df["国家"] = feishu_df.get("国家", pd.Series(dtype=str)).apply(lambda x: str(x).strip() if pd.notna(x) else "")
        feishu_df["城市"] = feishu_df.get("城市", pd.Series(dtype=str)).apply(lambda x: str(x).strip() if pd.notna(x) else "")
        
        # 去除空酒店名
        feishu_df = feishu_df[feishu_df["酒店名称"] != ""]
        
        # 按酒店名称去重，保留第一个
        feishu_df = feishu_df.drop_duplicates(subset=["酒店名称"], keep="first")
        
        # 创建映射字典
        location_map = {}
        for _, row in feishu_df.iterrows():
            hotel_name = row["酒店名称"]
            location_map[hotel_name] = {
                "国家": row.get("国家", ""),
                "城市": row.get("城市", "")
            }
        
        print(f"[Hotel List] 从Price Dashboard加载了 {len(location_map)} 个酒店的位置信息")
        return location_map
    except Exception as e:
        print(f"[Hotel List] 从Price Dashboard加载位置信息失败: {str(e)}")
        return {}


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

    # 先按酒店名称统计订单数
    result = (
        work.groupby(hotel_col)
        .size()
        .reset_index(name=t["col_count"])
        .sort_values(by=t["col_count"], ascending=False)
    )
    
    result = result.rename(columns={hotel_col: t["col_hotel"]})
    
    # 从Price Dashboard加载酒店位置信息
    location_map = _load_hotel_location_from_price()
    
    # 根据酒店名称补充国家和城市信息
    result[t["col_country"]] = result[t["col_hotel"]].apply(
        lambda x: location_map.get(x, {}).get("国家", "") if x in location_map else ""
    )
    result[t["col_city"]] = result[t["col_hotel"]].apply(
        lambda x: location_map.get(x, {}).get("城市", "") if x in location_map else ""
    )
    
    # 对于没有从Price Dashboard获取到位置信息的酒店，使用主数据中的信息作为备选
    missing_mask = (result[t["col_country"]] == "") & (result[t["col_city"]] == "")
    if missing_mask.any() and (country_col or city_col):
        # 从主数据中获取酒店位置信息作为备选
        hotel_location_from_main = {}
        for _, row in work.iterrows():
            hotel_name = str(row[hotel_col]).strip()
            if hotel_name and hotel_name not in hotel_location_from_main:
                hotel_location_from_main[hotel_name] = {
                    "国家": str(row[country_col]).strip() if country_col and pd.notna(row.get(country_col)) else "",
                    "城市": str(row[city_col]).strip() if city_col and pd.notna(row.get(city_col)) else ""
                }
        
        # 填充缺失的位置信息
        for idx in result[missing_mask].index:
            hotel_name = result.at[idx, t["col_hotel"]]
            if hotel_name in hotel_location_from_main:
                loc = hotel_location_from_main[hotel_name]
                if not result.at[idx, t["col_country"]]:
                    result.at[idx, t["col_country"]] = loc.get("国家", "")
                if not result.at[idx, t["col_city"]]:
                    result.at[idx, t["col_city"]] = loc.get("城市", "")
    
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

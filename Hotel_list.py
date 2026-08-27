"""ID团队酒店名单

展示ID团队所有状态的酒店（除"客户咨询"和"等待Joy报价"外），
包含酒店名称、国家、城市、底价、卖价、备注。
国家/城市优先从Price Dashboard（飞书比价表格）读取，国家回退到主数据。
"""
import streamlit as st
import pandas as pd
from config import get_standard_status, fetch_feishu_price_table

PAGE_TEXT = {
    "zh": {
        "page_header": "比价酒店名单",
        "page_desc": "酒店名单",
        "col_hotel": "酒店名称",
        "col_country": "国家",
        "col_city": "城市",
        "col_base_price": "底价",
        "col_sell_price": "卖价",
        "col_remark": "备注",
        "empty_tip": "暂无符合条件的酒店记录",
        "total_tip": "共 {} 条酒店记录",
        "filter_all": "全部",
        "team_code": "ID",
        "excluded_status": ["customer_inquiry", "awaiting_joy_quotation"],
    },
    "en": {
        "page_header": "ID Team Hotel List",
        "page_desc": "All hotels of ID team (except Customer Inquiry and Awaiting Joy Quotation)",
        "col_hotel": "Hotel Name",
        "col_country": "Country",
        "col_city": "City",
        "col_base_price": "Base Price",
        "col_sell_price": "Selling Price",
        "col_remark": "Remarks",
        "empty_tip": "No hotel records found",
        "total_tip": "{} hotel records in total",
        "filter_all": "All",
        "team_code": "ID",
        "excluded_status": ["customer_inquiry", "awaiting_joy_quotation"],
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
    status_col = _detect_column(df, ["状态 Status", "状态", "Status"])
    salesteam_col = _detect_column(df, ["Salesteam", "销售团队", "Sales Team"])
    base_price_col = _detect_column(df, ["Joy 底价 Joy's Net Rate", "Joy 底价", "底价", "Joy's Net Rate"])
    sell_price_col = _detect_column(df, ["建议卖价 Suggested Selling Price", "建议卖价", "卖价", "Suggested Selling Price"])
    # 备注：ID团队“备注”列通常为空，优先用有内容的“运营备注 Ops Notes”，显示名仍为“备注”
    remark_col = _detect_column(df, ["运营备注 Ops Notes", "运营备注", "Ops Notes", "备注"])

    if not hotel_col or not status_col or not salesteam_col:
        st.warning(t["empty_tip"])
        return

    work = df.copy()
    # 清洗字符串列
    clean_cols = [c for c in [hotel_col, country_col, status_col, salesteam_col,
                              base_price_col, sell_price_col, remark_col]
                  if c and c in work.columns]
    for c in clean_cols:
        work[c] = work[c].apply(lambda x: str(x).strip() if pd.notna(x) else "")

    # 筛选1: 销售团队 = ID
    work = work[work[salesteam_col] == t["team_code"]]

    # 筛选2: 状态 != 客户咨询 且 != 等待Joy报价（其余所有状态均展示）
    excluded = t["excluded_status"]
    work = work[~work[status_col].apply(lambda x: get_standard_status(x) in excluded)]

    if work.empty:
        st.info(t["empty_tip"])
        return

    # 从Price Dashboard加载酒店位置信息
    location_map = _load_hotel_location_from_price()

    # 国家：优先Price Dashboard，回退主数据；城市：仅来自Price Dashboard
    def _country(row):
        loc = location_map.get(row[hotel_col], {})
        v = loc.get("国家", "")
        return v if v else (row[country_col] if country_col else "")

    def _city(row):
        return location_map.get(row[hotel_col], {}).get("城市", "")

    work["_country"] = work.apply(_country, axis=1)
    work["_city"] = work.apply(_city, axis=1)

    # 构建展示数据（按订单记录逐行展示，底价/卖价/备注为订单级字段不可聚合）
    def _vals(col):
        return work[col].values if col and col in work.columns else [""] * len(work)

    result = pd.DataFrame({
        t["col_hotel"]: work[hotel_col].values,
        t["col_country"]: work["_country"].values,
        t["col_city"]: work["_city"].values,
        t["col_base_price"]: _vals(base_price_col),
        t["col_sell_price"]: _vals(sell_price_col),
        t["col_remark"]: _vals(remark_col),
    })

    # 按酒店名称排序
    result = result.sort_values(by=t["col_hotel"]).reset_index(drop=True)

    # 筛选器：国家、城市（城市随国家联动）
    filter_all = t["filter_all"]
    country_col_name = t["col_country"]
    city_col_name = t["col_city"]

    countries = sorted({c for c in result[country_col_name] if c})
    country_opts = [filter_all] + countries

    cc1, cc2 = st.columns(2)
    with cc1:
        sel_country = st.selectbox(
            label=country_col_name, options=country_opts, index=0, key="hl_country_filter"
        )
    # 国家变化时重置城市选择，避免城市选项失效
    if st.session_state.get("hl_country_prev") != sel_country:
        st.session_state["hl_city_filter"] = filter_all
    st.session_state["hl_country_prev"] = sel_country

    if sel_country != filter_all:
        city_pool = sorted({c for c in result.loc[result[country_col_name] == sel_country, city_col_name] if c})
    else:
        city_pool = sorted({c for c in result[city_col_name] if c})
    city_opts = [filter_all] + city_pool

    with cc2:
        sel_city = st.selectbox(
            label=city_col_name, options=city_opts, index=0, key="hl_city_filter"
        )
    if sel_city not in city_opts:
        sel_city = filter_all

    # 应用筛选
    filtered = result
    if sel_country != filter_all:
        filtered = filtered[filtered[country_col_name] == sel_country]
    if sel_city != filter_all:
        filtered = filtered[filtered[city_col_name] == sel_city]

    st.success(t["total_tip"].format(len(filtered)))
    st.dataframe(filtered, use_container_width=True, hide_index=True)

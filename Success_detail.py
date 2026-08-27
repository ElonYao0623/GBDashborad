"""团房成功订单详情看板

展示团房渠道订单明细：团单号、渠道订单号、客户名称、BD、酒店名称、
国家、城市、TTV、GP%。数据来源为飞书电子表格 sheet OAiP8B 的 Channel Booking
Number 列，通过 MCP booking.channelbooking_v2 查询后生成 group_success_mapping.json
缓存，看板读取该缓存展示。

数据来源：
- 渠道订单号/客户名称(Clientid)/BD(clientbd)/酒店名称(didahotelname_en，
  按渠道订单号匹配)/TTV/GP/国家/城市：group_success_mapping.json
- 销售团队：团房数据.csv（按团单号匹配，仅用于账户隔离与筛选）

账户隔离：按销售团队隔离（sales 只看自己团队的团单号，admin/OP 看全量）。
"""
import os
import json
import streamlit as st
import pandas as pd

from config import load_data, fetch_feishu_success_numbers

# 缓存映射文件
MAPPING_FILE = "group_success_mapping.json"

PAGE_TEXT = {
    "zh": {
        "title": "团房成功订单详情",
        "page_desc": "团房渠道订单明细",
        "empty_tip": "暂无渠道订单数据",
        "no_mapping_tip": "未找到渠道订单缓存文件 group_success_mapping.json。请运行 generate_success_mapping.py 生成缓存。",
        "total_channels": "渠道订单总数",
        "total_groups": "团单号总数",
        "total_ttv": "TTV 合计 (USD)",
        "total_gp": "整体 GP%",
        "fetch_btn": "读取飞书表格数据",
        "fetch_btn_desc": "从飞书电子表格（Channel Booking Number）获取最新渠道订单号，并检查与缓存映射的匹配情况",
        "fetch_fail": "读取失败",
        "fetch_ok": "已从飞书表格读取 {} 个渠道订单号",
        "cache_hit": "缓存已有匹配",
        "cache_miss": "缓存缺失（需重新生成映射）",
        "missing_list_caption": "以下渠道订单号尚未在 group_success_mapping.json 中，需重新运行 MCP 查询生成缓存",
        "feishu_list_caption": "飞书表格渠道订单号清单",
        "filter_all": "全部",
        "col_sales_team": "销售团队",
        "col_country": "国家",
        "col_city": "城市",
        "col_order_id": "团单号",
        "col_channel_order": "渠道订单号",
        "col_customer": "客户名称",
        "col_bd": "BD",
        "col_hotel": "酒店名称",
        "col_ttv": "TTV",
        "col_gp": "GP%",
        "total_records": "共 {} 条明细记录",
        "search_order": "搜索团单号/渠道订单号/客户名称",
        "no_team_tip": "（未匹配CSV，无团队）",
    },
    "en": {
        "title": "Success Booking Details",
        "page_desc": "Channel order details",
        "empty_tip": "No channel order data",
        "no_mapping_tip": "Cache file group_success_mapping.json not found. Run generate_success_mapping.py to generate.",
        "total_channels": "Total Channel Orders",
        "total_groups": "Total Group Orders",
        "total_ttv": "Total TTV (USD)",
        "total_gp": "Overall GP%",
        "fetch_btn": "Read Feishu Sheet Data",
        "fetch_btn_desc": "Fetch latest channel booking numbers from the Feishu spreadsheet and check coverage against local cache",
        "fetch_fail": "Failed to read",
        "fetch_ok": "Read {} channel order numbers from Feishu sheet",
        "cache_hit": "Matched in Cache",
        "cache_miss": "Missing in Cache (Regenerate Mapping)",
        "missing_list_caption": "The following channel order numbers are not in group_success_mapping.json yet. Re-run MCP query to regenerate.",
        "feishu_list_caption": "Feishu Sheet Channel Order Numbers",
        "filter_all": "All",
        "col_sales_team": "Sales Team",
        "col_country": "Country",
        "col_city": "City",
        "col_order_id": "Group Order No.",
        "col_channel_order": "Channel Order No.",
        "col_customer": "Customer",
        "col_bd": "BD",
        "col_hotel": "Hotel Name",
        "col_ttv": "TTV",
        "col_gp": "GP%",
        "total_records": "{} detail records",
        "search_order": "Search order/channel/customer",
        "no_team_tip": "(No CSV match)",
    }
}


def _detect_column(df, candidates):
    """列名模糊匹配：精确→去空格→大小写不敏感"""
    for c in candidates:
        if c in df.columns:
            return c
    for candidate in candidates:
        for col in df.columns:
            if candidate.strip() == col.strip() or candidate.lower() == col.lower():
                return col
    return None


def _to_num(val):
    """安全转换为 float，失败返回 None"""
    try:
        if val is None or str(val).strip() == "" or str(val).strip().lower() == "nan":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def _load_channel_mapping():
    """读取团单号→渠道订单列表 的缓存映射"""
    if not os.path.exists(MAPPING_FILE):
        return None
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Success Detail] 读取缓存映射失败: {e}")
        return None


def _build_csv_lookup(df):
    """从 CSV 构建 团单号 → {销售团队} 查找表（酒店名称来自 MCP didahotelname_en）"""
    lookup = {}
    order_col = _detect_column(df, ["团单号", "Booking No"])
    team_col = _detect_column(df, ["Salesteam", "销售团队", "Sales Team"])

    if not order_col:
        return lookup

    for _, r in df.iterrows():
        gid = str(r[order_col]).strip() if pd.notna(r[order_col]) else ""
        if not gid:
            continue
        lookup[gid] = {
            "team": str(r[team_col]).strip() if team_col and pd.notna(r[team_col]) else "",
        }
    return lookup


def render_success_detail(df):
    """渲染团房成功订单详情看板（接收 df 用于销售团队匹配与账户隔离）"""
    lang = st.session_state.get("lang", "zh")
    t = PAGE_TEXT[lang]

    st.title(t["title"])
    st.markdown(t["page_desc"])
    st.divider()

    # ---------- 读取飞书表格数据按钮 ----------
    st.caption(t["fetch_btn_desc"])
    if st.button(label=t["fetch_btn"], key="sd_fetch_feishu", type="primary"):
        try:
            nums = fetch_feishu_success_numbers()
            st.session_state["sd_feishu_numbers"] = nums
            st.session_state.pop("sd_feishu_error", None)
        except Exception as e:
            st.session_state["sd_feishu_error"] = str(e)
            st.session_state.pop("sd_feishu_numbers", None)

    # 展示读取结果（存储在session_state，刷新后不丢失）
    if st.session_state.get("sd_feishu_error"):
        st.error(f'{t["fetch_fail"]}: {st.session_state["sd_feishu_error"]}')
    elif st.session_state.get("sd_feishu_numbers") is not None:
        feishu_nums = st.session_state["sd_feishu_numbers"]
        cached_orders = {
            str(co.get("渠道订单号", "")).strip()
            for entries in (_load_channel_mapping() or {}).values()
            for co in entries
        }
        in_cache = [n for n in feishu_nums if n in cached_orders]
        missing = [n for n in feishu_nums if n not in cached_orders]

        st.success(t["fetch_ok"].format(len(feishu_nums)))
        fm1, fm2 = st.columns(2)
        with fm1:
            st.metric(t["cache_hit"], len(in_cache))
        with fm2:
            st.metric(t["cache_miss"], len(missing))
        if missing:
            with st.expander(f'{t["cache_miss"]} ({len(missing)})'):
                st.caption(t["missing_list_caption"])
                st.dataframe(pd.DataFrame({t["col_channel_order"]: missing}), hide_index=True, height=200)
        with st.expander(t["feishu_list_caption"]):
            st.dataframe(pd.DataFrame({t["col_channel_order"]: feishu_nums}), hide_index=True, height=300)
    st.divider()

    # ---------- 读取缓存映射 ----------
    mapping = _load_channel_mapping()
    if mapping is None:
        st.warning(t["no_mapping_tip"])
        return
    if not mapping:
        st.info(t["empty_tip"])
        return

    # ---------- 从 CSV 构建团单号查找表（销售团队，用于账户隔离）----------
    csv_lookup = _build_csv_lookup(df)

    # ---------- 展开行 ----------
    user_role = st.session_state.get("user_role", "")
    user_team = st.session_state.get("user_team", "")

    rows = []
    total_ttv = 0.0
    total_gp = 0.0

    for gid, channel_orders in mapping.items():
        team = csv_lookup.get(gid, {}).get("team", "")

        for co in channel_orders:
            ttv = _to_num(co.get("TTV"))
            gp = _to_num(co.get("GP"))
            gp_pct = _to_num(co.get("GP%"))
            if ttv is not None:
                total_ttv += ttv
            if gp is not None:
                total_gp += gp

            rows.append({
                t["col_order_id"]: gid,
                t["col_channel_order"]: co.get("渠道订单号", ""),
                t["col_customer"]: co.get("客户名称", ""),
                t["col_bd"]: co.get("BD", ""),
                t["col_hotel"]: co.get("酒店名称", ""),
                t["col_country"]: co.get("国家", ""),
                t["col_city"]: co.get("城市", ""),
                t["col_ttv"]: ttv,
                t["col_gp"]: gp_pct,
                t["col_sales_team"]: team,
            })

    result = pd.DataFrame(rows)

    # ---------- 账户隔离 ----------
    # sales 角色只看自己团队（通过 CSV 匹配的团单号）；未匹配CSV的订单对sales隐藏
    if user_role == "sales" and user_team:
        result = result[result[t["col_sales_team"]].str.contains(user_team, case=False, na=False)]

    # ---------- 指标卡 ----------
    unique_groups = result[t["col_order_id"]].nunique() if not result.empty else 0
    overall_gp_pct = round(total_gp / total_ttv * 100, 2) if total_ttv > 0 else None
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(t["total_groups"], int(unique_groups))
    with m2:
        st.metric(t["total_channels"], len(result))
    with m3:
        st.metric(t["total_ttv"], f"${total_ttv:,.2f}")
    with m4:
        st.metric(t["total_gp"], f"{overall_gp_pct:.2f}%" if overall_gp_pct is not None else "-")
    st.divider()

    if result.empty:
        st.info(t["empty_tip"])
        return

    # ---------- 筛选器 ----------
    filter_all = t["filter_all"]
    team_col_name = t["col_sales_team"]
    country_col_name = t["col_country"]
    city_col_name = t["col_city"]

    teams = sorted({x for x in result[team_col_name] if x})
    countries = sorted({c for c in result[country_col_name] if c})

    fc1, fc2, fc3, fc4 = st.columns([1, 1, 1, 1.5])
    with fc1:
        sel_team = st.selectbox(label=team_col_name, options=[filter_all] + teams, index=0, key="sd_team_filter")
    with fc2:
        sel_country = st.selectbox(label=country_col_name, options=[filter_all] + countries, index=0, key="sd_country_filter")
    # 国家联动城市
    if st.session_state.get("sd_country_prev") != sel_country:
        st.session_state["sd_city_filter"] = filter_all
    st.session_state["sd_country_prev"] = sel_country
    if sel_country != filter_all:
        city_pool = sorted({c for c in result.loc[result[country_col_name] == sel_country, city_col_name] if c})
    else:
        city_pool = sorted({c for c in result[city_col_name] if c})
    with fc3:
        sel_city = st.selectbox(label=city_col_name, options=[filter_all] + city_pool, index=0, key="sd_city_filter")
    if sel_city not in ([filter_all] + city_pool):
        sel_city = filter_all
    with fc4:
        search_text = st.text_input(label=t["search_order"], value="", key="sd_search")

    # ---------- 应用筛选 ----------
    filtered = result.copy()
    if sel_team != filter_all:
        filtered = filtered[filtered[team_col_name] == sel_team]
    if sel_country != filter_all:
        filtered = filtered[filtered[country_col_name] == sel_country]
    if sel_city != filter_all:
        filtered = filtered[filtered[city_col_name] == sel_city]
    if search_text.strip():
        kw = search_text.strip().lower()
        mask = (
            filtered[t["col_order_id"]].astype(str).str.lower().str.contains(kw, na=False)
            | filtered[t["col_channel_order"]].astype(str).str.lower().str.contains(kw, na=False)
            | filtered[t["col_customer"]].astype(str).str.lower().str.contains(kw, na=False)
        )
        filtered = filtered[mask]

    if filtered.empty:
        st.info(t["empty_tip"])
        return

    st.success(t["total_records"].format(len(filtered)))

    # ---------- 数据表格 ----------
    display_cols = [t["col_order_id"], t["col_channel_order"], t["col_customer"], t["col_bd"],
                    t["col_hotel"], t["col_country"], t["col_city"], t["col_ttv"], t["col_gp"]]
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            t["col_ttv"]: st.column_config.NumberColumn(label=t["col_ttv"], format="%.2f"),
            t["col_gp"]: st.column_config.NumberColumn(label=t["col_gp"], format="%.1f%%"),
        }
    )

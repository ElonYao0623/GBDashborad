import streamlit as st
import pandas as pd
from datetime import datetime, date
from config import get_workflow_step_text, get_standard_status, STATUS_WORKFLOW_MAP

PAGE_TEXT = {
    "zh": {
        "page_name": "数据统计看板",
        "total_order": "有效团单总数",
        "btn_view": "查看",
        "tip_info": "点击数字下方查看跳转详情",
        "pie_title": "订单状态占比",
        "no_data_text": "暂无数据",
        "team_chart_title": "各销售团队订单分布",
        "team_x_label": "销售团队",
        "team_y_label": "订单数量",
        "days_title": "距离入住天数分布",
        "days_x_label": "距离入住天数",
        "days_y_label": "订单数量",
        "day_today": "今日0天",
        "day_1_7": "1~7天",
        "day_8_15": "8~15天",
        "day_16_30": "16~30天",
        "day_over30": "30天以上",
        "day_expired": "已过期"
    },
    "en": {
        "page_name": "Dashboard",
        "total_order": "Total Valid Bookings",
        "btn_view": "View",
        "tip_info": "Click view to jump",
        "pie_title": "Status Ratio",
        "no_data_text": "No data available",
        "team_chart_title": "Sales Team Count",
        "team_x_label": "Sales Team",
        "team_y_label": "Count",
        "days_title": "Days to Check-in Distribution",
        "days_x_label": "Days to Check-in",
        "days_y_label": "Count",
        "day_today": "Today (0 days)",
        "day_1_7": "1~7 days",
        "day_8_15": "8~15 days",
        "day_16_30": "16~30 days",
        "day_over30": "Over 30 days",
        "day_expired": "Expired"
    }
}
def render_dashboard(df):
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import matplotlib
    matplotlib.use('Agg')
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    chinese_fonts = ["SimHei", "Microsoft YaHei", "Arial Unicode MS", "Noto Sans CJK SC", "Noto Sans CJK TC", "Noto Sans CJK JP", "WenQuanYi Micro Hei", "Heiti SC", "Heiti TC"]
    selected_font = None
    for font in chinese_fonts:
        if font in available_fonts:
            selected_font = font
            break
    if selected_font:
        plt.rcParams["font.family"] = selected_font
        plt.rcParams["font.sans-serif"] = [selected_font]
        plt.rcParams["axes.unicode_minus"] = False
    else:
        plt.rcParams["font.family"] = ["DejaVu Sans", "Arial Unicode MS"]
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial Unicode MS"]
        plt.rcParams["axes.unicode_minus"] = False
    lang = st.session_state.get("lang", "zh")
    t = PAGE_TEXT[lang]
    view_label = f"🔍 {t['btn_view']}"
    st.header(f"📊 {t['page_name']}")
    st.divider()
    active_df = df.copy()
    # 预处理状态消除NaN报错 - 兼容"状态"和"状态 Status"两种列名
    status_col = "状态" if "状态" in active_df.columns else "状态 Status" if "状态 Status" in active_df.columns else None
    if status_col is None:
        active_df["状态"] = ""
    else:
        active_df["状态"] = active_df[status_col].fillna("").astype(str).str.strip()
    active_df["标准状态"] = active_df["状态"].apply(get_standard_status)
    total = len(active_df)
    st.metric(t["total_order"], total)
    st.divider()
    hide_list = ["inquiry_failed","customer_confirm_failed","group_booking_failed","awaiting_hotel_lock","considering_alternative","inquiry_succeeded","customer_inquiry","customer_confirmed_group","awaiting_ops_review"]
    all_status = list(STATUS_WORKFLOW_MAP.keys())
    show_status = [s for s in all_status if s not in hide_list]
    stat = {}
    for s in show_status:
        stat[s] = len(active_df[active_df["标准状态"] == s])
    stat_list = list(stat.items())
    for i in range(0, len(stat_list),4):
        chunk = stat_list[i:i+4]
        cols = st.columns(4)
        for idx,(name,cnt) in enumerate(chunk):
            with cols[idx]:
                st.metric(get_workflow_step_text(lang, name), cnt)
                if st.button(view_label, key=f"dash_{name}", use_container_width=True):
                    st.session_state["jump_status"] = name
                    st.rerun()
    st.divider()
    st.info(t["tip_info"])
    st.divider()
    _,mid,_ = st.columns([1,2,1])
    with mid:
        all_status_values = active_df["状态"].astype(str).str.strip().unique().tolist()
        all_status_values = [v for v in all_status_values if v and v != "nan"]
        
        status_display_map = {}
        for val in all_status_values:
            std_status = get_standard_status(val)
            display_text = get_workflow_step_text(lang, std_status)
            if display_text not in status_display_map:
                status_display_map[display_text] = []
            status_display_map[display_text].append(val)
        
        status_counts = {}
        for display_text, orig_values in status_display_map.items():
            mask = active_df["状态"].astype(str).str.strip().isin(orig_values)
            status_counts[display_text] = len(active_df[mask])
        
        labels = list(status_counts.keys())
        values = list(status_counts.values())
        
        if not values or sum(values) == 0:
            st.info(t["no_data_text"])
        else:
            fig,ax = plt.subplots(figsize=(4.2,4.2))
            ax.pie(values, labels=labels, autopct="%1.1f%%")
            ax.set_title(t["pie_title"])
            ax.axis("equal")
            st.pyplot(fig)
    st.divider()
    st.subheader(t["days_title"])
    def calc_day(s):
        try:
            x = str(s).strip()
            if not x:
                return None
            if "/" in x:
                d = datetime.strptime(x, "%Y/%m/%d").date()
            else:
                d = datetime.strptime(x, "%Y-%m-%d").date()
            return (d - date.today()).days
        except:
            return None
    if "入住日期 Check-in Date" not in active_df.columns:
        active_df["入住日期 Check-in Date"] = ""
    active_df["距离入住天数"] = active_df["入住日期 Check-in Date"].apply(calc_day)
    
    def get_day_group(days):
        if days is None:
            return None
        if days < 0:
            return t["day_expired"]
        elif days == 0:
            return t["day_today"]
        elif 1 <= days <= 7:
            return t["day_1_7"]
        elif 8 <= days <= 15:
            return t["day_8_15"]
        elif 16 <= days <= 30:
            return t["day_16_30"]
        else:
            return t["day_over30"]
    
    active_df["入住天数分组"] = active_df["距离入住天数"].apply(get_day_group)
    grouped_df = active_df[active_df["入住天数分组"].notna()]
    group_order = [t["day_expired"], t["day_today"], t["day_1_7"], t["day_8_15"], t["day_16_30"], t["day_over30"]]
    group_cnt = grouped_df["入住天数分组"].value_counts().reindex(group_order, fill_value=0)
    
    fig3,ax3 = plt.subplots(figsize=(11,4.5))
    bars = ax3.bar(group_cnt.index, group_cnt.values, color="#10b981")
    ax3.set_xlabel(t["days_x_label"])
    ax3.set_ylabel(t["days_y_label"])
    for bar in bars:
        h = bar.get_height()
        ax3.text(bar.get_x()+bar.get_width()/2, h, str(h), ha="center", va="bottom")
    st.pyplot(fig3)
    st.divider()
    st.subheader(t["team_chart_title"])
    team_df = active_df.copy()
    if "Salesteam" not in team_df.columns:
        team_df["Salesteam"] = ""
    team_df["team_temp"] = team_df["Salesteam"].fillna("无销售团队").astype(str).str.strip()
    team_cnt = team_df["team_temp"].value_counts()
    fig2,ax2 = plt.subplots(figsize=(11,4.5))
    bars = ax2.bar(team_cnt.index, team_cnt.values, color="#3b82f6")
    ax2.set_xlabel(t["team_x_label"])
    ax2.set_ylabel(t["team_y_label"])
    ax2.tick_params(axis="x", rotation=45)
    for bar in bars:
        h = bar.get_height()
        ax2.text(bar.get_x()+bar.get_width()/2, h, str(h), ha="center", va="bottom")
    st.pyplot(fig2)

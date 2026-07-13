import streamlit as st
import pandas as pd
from datetime import datetime, date
from config import get_workflow_step_text, get_standard_status, WORKFLOW_STEPS_ZH

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
    from config import configure_matplotlib_font
    configure_matplotlib_font()
    font_prop = fm.FontProperties()
    lang = st.session_state.get("lang", "zh")
    t = PAGE_TEXT[lang]
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

    _,mid,_ = st.columns([1,2,1])
    with mid:
        # 预处理：过滤掉空状态/无效状态
        mask_valid = active_df["标准状态"].isin(WORKFLOW_STEPS_ZH)
        valid_df = active_df[mask_valid].copy()

        # 按工作流顺序统计各状态数量
        status_counts = {}
        display_to_std = {}
        for std_status in WORKFLOW_STEPS_ZH:
            display_text = get_workflow_step_text(lang, std_status)
            status_counts[display_text] = 0
            display_to_std[display_text] = std_status

        std_counts = valid_df.groupby("标准状态").size()
        for std_status in WORKFLOW_STEPS_ZH:
            display_text = get_workflow_step_text(lang, std_status)
            status_counts[display_text] = int(std_counts.get(std_status, 0))

        # 只保留有订单的状态
        non_zero = {k: v for k, v in status_counts.items() if v > 0}

        labels = list(non_zero.keys())
        values = list(non_zero.values())

        if not values or sum(values) == 0:
            st.info(t["no_data_text"])
        else:
            import numpy as np
            fig, ax = plt.subplots(figsize=(9, 9))
            fig.patch.set_facecolor("white")
            colors_list = plt.cm.tab20(np.linspace(0, 1, len(labels)))
            # 外部标签：状态名+百分比，引线连接
            total_v = sum(values)
            labels_pct = [f"{l}  {v/total_v*100:.1f}%" for l, v in zip(labels, values)]
            wedges, texts = ax.pie(
                values,
                labels=labels_pct,
                labeldistance=1.18,
                colors=colors_list,
                startangle=90,
                wedgeprops=dict(width=0.65, edgecolor="white", linewidth=2),
                textprops=dict(fontproperties=font_prop, fontsize=30, fontweight="bold", color="black")
            )
            ax.set_title(t["pie_title"], fontproperties=font_prop, fontsize=15, fontweight="bold", pad=20)
            ax.axis("equal")
            ax.set_position([0.1, 0.15, 0.8, 0.75])
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

            # 点击跳转按钮：每行4个
            cols_per_row = 4
            for i in range(0, len(labels), cols_per_row):
                btns = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    idx = i + j
                    if idx < len(labels):
                        lbl = labels[idx]
                        std_key = display_to_std.get(lbl)
                        with btns[j]:
                            if st.button(f"🔍 {lbl} ({values[idx]})", key=f"pie_btn_{idx}", use_container_width=True):
                                if std_key:
                                    st.session_state["jump_status"] = std_key
                                    st.rerun()
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
    bars = ax3.bar(group_cnt.index, group_cnt.values, color="#8b5cf6")
    ax3.set_xlabel(t["days_x_label"], fontproperties=font_prop)
    ax3.set_ylabel(t["days_y_label"], fontproperties=font_prop)
    ax3.tick_params(axis="x", labelsize=10)
    for bar in bars:
        h = bar.get_height()
        ax3.text(bar.get_x()+bar.get_width()/2, h, str(h), ha="center", va="bottom", fontproperties=font_prop)
    st.pyplot(fig3)
    st.divider()
    st.subheader(t["team_chart_title"])
    team_df = active_df.copy()
    if "Salesteam" not in team_df.columns:
        team_df["Salesteam"] = ""
    team_df["team_temp"] = team_df["Salesteam"].fillna("无销售团队").astype(str).str.strip()
    team_cnt = team_df["team_temp"].value_counts()
    fig2,ax2 = plt.subplots(figsize=(11,4.5))
    bars = ax2.bar(team_cnt.index, team_cnt.values, color="#8b5cf6")
    ax2.set_xlabel(t["team_x_label"], fontproperties=font_prop)
    ax2.set_ylabel(t["team_y_label"], fontproperties=font_prop)
    ax2.tick_params(axis="x", rotation=45, labelsize=10)
    for bar in bars:
        h = bar.get_height()
        ax2.text(bar.get_x()+bar.get_width()/2, h, str(h), ha="center", va="bottom", fontproperties=font_prop)
    st.pyplot(fig2)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from datetime import datetime, date
from config import configure_matplotlib_font, get_workflow_step_text, get_standard_status, WORKFLOW_STEPS_ZH

PAGE_TEXT = {
    "zh": {
        "title": "销售团队统计",
        "total_order": "销售订单总数",
        "my_chart_title": "MY团队订单统计",
        "id_chart_title": "ID团队订单统计",
        "mea_chart_title": "MEA团队订单统计",
        "empty_tip": "暂无数据",
        "percentage": "占比",
        "count": "数量",
        "back_btn": "← 返回团队统计",
        "sales_status_title": "销售订单状态统计",
        "status_pie_title": "订单状态占比",
        "click_tip": "💡 点击销售姓名查看详细状态统计",
        "team_status_title": "团队订单状态占比",
        "team_btn_tip": "💡 点击团队名称查看订单状态占比",
        "date_filter": "日期筛选",
        "date_from": "开始日期",
        "date_to": "结束日期",
        "date_all": "全部数据",
        "date_submit": "基于提交日期"
    },
    "en": {
        "title": "Sales Team Statistics",
        "total_order": "Total Sales Orders",
        "my_chart_title": "MY Team Order Stats",
        "id_chart_title": "ID Team Order Stats",
        "mea_chart_title": "MEA Team Order Stats",
        "empty_tip": "No data available",
        "percentage": "Percentage",
        "count": "Count",
        "back_btn": "← Back to Team View",
        "sales_status_title": "Sales Order Status Stats",
        "status_pie_title": "Status Ratio",
        "click_tip": "💡 Click on sales name to view detailed status stats",
        "team_status_title": "Team Order Status Ratio",
        "team_btn_tip": "💡 Click on team name to view order status ratio",
        "date_filter": "Date Filter",
        "date_from": "From",
        "date_to": "To",
        "date_all": "All Data",
        "date_submit": "Based on Submission Date"
    }
}

# 销售团队列表
TEAMS = ["MY", "ID", "MEA"]


def render_sales_dashboard(df):
    configure_matplotlib_font()
    font_prop = fm.FontProperties()
    lang = st.session_state.get("lang", "zh")
    t = PAGE_TEXT[lang]
    
    st.title(t["title"])
    
    sales_df = df.copy()
    
    if "团单号" in sales_df.columns:
        sales_df["团单号"] = sales_df["团单号"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    if "客户名称 Customer Name" in sales_df.columns:
        sales_df["客户名称 Customer Name"] = sales_df["客户名称 Customer Name"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    
    sales_df["去重键"] = sales_df.apply(
        lambda row: row["团单号"] if row.get("团单号", "") else row.get("客户名称 Customer Name", ""),
        axis=1
    )
    
    sales_df["状态"] = sales_df["状态"].astype(str).str.strip()
    sales_df["标准状态"] = sales_df["状态"].apply(get_standard_status)
    
    if "Salesteam" not in sales_df.columns:
        sales_df["Salesteam"] = ""
    sales_df["team_temp"] = sales_df["Salesteam"].fillna("无销售团队").astype(str).str.strip()
    
    if "销售姓名 Sales Name" not in sales_df.columns:
        sales_df["销售姓名 Sales Name"] = ""
    sales_df["sales_name"] = sales_df["销售姓名 Sales Name"].fillna("未知销售").astype(str).str.strip()
    
    # 日期筛选器 - 基于提交日期
    if "提交时间 Submitted by" in sales_df.columns:
        def parse_submit_date(s):
            try:
                x = str(s).strip()
                if not x:
                    return None
                if "/" in x:
                    return datetime.strptime(x, "%Y/%m/%d").date()
                else:
                    return datetime.strptime(x, "%Y-%m-%d").date()
            except:
                return None
        
        sales_df["提交日期"] = sales_df["提交时间 Submitted by"].apply(parse_submit_date)
        valid_dates = sales_df["提交日期"].dropna()
        
        if len(valid_dates) > 0:
            min_date = valid_dates.min()
            max_date = valid_dates.max()
            
            with st.expander(f"🔍 {t['date_filter']} - {t['date_submit']}", expanded=False):
                col_from, col_to = st.columns(2)
                with col_from:
                    filter_start = st.date_input(
                        t["date_from"],
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="sales_date_start"
                    )
                with col_to:
                    filter_end = st.date_input(
                        t["date_to"],
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="sales_date_end"
                    )
                
                if st.button(f"🔄 {t['date_all']}", key="sales_reset_date"):
                    st.session_state.pop("sales_date_start", None)
                    st.session_state.pop("sales_date_end", None)
                    st.rerun()
            
            if filter_start and filter_end:
                mask = (sales_df["提交日期"] >= filter_start) & (sales_df["提交日期"] <= filter_end)
                sales_df = sales_df[mask].copy()
    
    unique_df = sales_df[["去重键", "标准状态", "team_temp", "sales_name"]].drop_duplicates()
    
    total = len(unique_df)
    st.metric(t["total_order"], total)
    st.divider()
    
    if total == 0:
        st.info(t["empty_tip"])
        return
    
    # 检查是否在查看单个团队状态详情
    selected_team = st.session_state.get("selected_team", None)
    selected_sales = st.session_state.get("selected_sales", None)
    
    if selected_team:
        # 显示团队的订单状态统计
        if st.button(t["back_btn"], type="primary"):
            st.session_state["selected_team"] = None
            st.rerun()
        
        st.subheader(f"{t['team_status_title']}: {selected_team}")
        
        # 筛选该团队的数据
        team_data = unique_df[unique_df["team_temp"] == selected_team]
        team_total = len(team_data)
        
        if team_total == 0:
            st.info(t["empty_tip"])
            return
        
        st.metric(t["total_order"], team_total)
        st.divider()
        
        # 统计各状态数量
        mask_valid = team_data["标准状态"].isin(WORKFLOW_STEPS_ZH)
        valid_df = team_data[mask_valid].copy()
        
        status_counts = {}
        for std_status in WORKFLOW_STEPS_ZH:
            display_text = get_workflow_step_text(lang, std_status)
            status_counts[display_text] = 0
        
        std_counts = valid_df.groupby("标准状态").size()
        for std_status in WORKFLOW_STEPS_ZH:
            display_text = get_workflow_step_text(lang, std_status)
            status_counts[display_text] = int(std_counts.get(std_status, 0))
        
        non_zero = {k: v for k, v in status_counts.items() if v > 0}
        
        labels = list(non_zero.keys())
        values = list(non_zero.values())
        
        if not values or sum(values) == 0:
            st.info(t["empty_tip"])
        else:
            col_pie, col_info = st.columns([3, 1])
            with col_pie:
                fig, ax = plt.subplots(figsize=(2, 2))
                fig.patch.set_facecolor("white")
                team_colors = {
                    "MY": ["#4f46e5", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e", "#14b8a6", "#06b6d4", "#3b82f6"],
                    "ID": ["#10b981", "#059669", "#047857", "#065f46", "#0ea5e9", "#0284c7", "#0369a1", "#075985", "#f59e0b", "#d97706", "#b45309", "#92400e"],
                    "MEA": ["#f43f5e", "#e11d48", "#be123c", "#9f1239", "#881337", "#fb7185", "#fda4af", "#fecdd3", "#f0abfc", "#e879f9", "#d946ef", "#c026d3"]
                }
                if selected_team in team_colors:
                    colors_list = team_colors[selected_team][:len(labels)]
                else:
                    colors_list = plt.cm.tab20(np.linspace(0, 1, len(labels)))
                total_v = sum(values)
                labels_pct = [f"{v/total_v*100:.1f}%" for v in values]
                wedges, texts = ax.pie(
                    values,
                    labels=labels_pct,
                    labeldistance=1.15,
                    colors=colors_list,
                    startangle=90,
                    wedgeprops=dict(width=0.65, edgecolor="white", linewidth=2),
                    textprops=dict(fontproperties=font_prop, fontsize=5, fontweight="bold", color="black")
                )
                ax.set_title(t["status_pie_title"], fontproperties=font_prop, fontsize=7, fontweight="bold", pad=15)
                ax.axis("equal")
                ax.set_position([0.15, 0.1, 0.7, 0.7])
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            with col_info:
                st.metric(t["total_order"], team_total)
                st.divider()
                for i, (label, value) in enumerate(zip(labels, values)):
                    pct = (value / team_total) * 100
                    st.markdown(f"**{label}**")
                    st.caption(f"{value}单 ({pct:.1f}%)")
            
            # 显示状态详情表格
            st.subheader(t["status_pie_title"])
            status_detail = []
            for std_status in WORKFLOW_STEPS_ZH:
                display_text = get_workflow_step_text(lang, std_status)
                cnt = status_counts[display_text]
                if cnt > 0:
                    pct = (cnt / team_total) * 100
                    status_detail.append({
                        "状态": display_text,
                        t["count"]: cnt,
                        t["percentage"]: f"{pct:.1f}%"
                    })
            
            if status_detail:
                st.dataframe(pd.DataFrame(status_detail), use_container_width=True)
    elif selected_sales:
        # 显示单个销售的订单状态统计
        if st.button(t["back_btn"], type="primary"):
            st.session_state["selected_sales"] = None
            st.rerun()
        
        st.subheader(f"{t['sales_status_title']}: {selected_sales}")
        
        # 筛选该销售的数据
        sales_data = unique_df[unique_df["sales_name"] == selected_sales]
        sales_total = len(sales_data)
        
        if sales_total == 0:
            st.info(t["empty_tip"])
            return
        
        st.metric(t["total_order"], sales_total)
        st.divider()
        
        # 统计各状态数量
        mask_valid = sales_data["标准状态"].isin(WORKFLOW_STEPS_ZH)
        valid_df = sales_data[mask_valid].copy()
        
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
        
        non_zero = {k: v for k, v in status_counts.items() if v > 0}
        
        labels = list(non_zero.keys())
        values = list(non_zero.values())
        
        if not values or sum(values) == 0:
            st.info(t["empty_tip"])
        else:
            col_pie, col_info = st.columns([3, 1])
            with col_pie:
                fig, ax = plt.subplots(figsize=(3, 3))
                fig.patch.set_facecolor("white")
                colors_list = plt.cm.tab20(np.linspace(0, 1, len(labels)))
                total_v = sum(values)
                labels_pct = [f"{v/total_v*100:.1f}%" for l, v in zip(labels, values)]
                wedges, texts = ax.pie(
                    values,
                    labels=labels_pct,
                    labeldistance=1.15,
                    colors=colors_list,
                    startangle=90,
                    wedgeprops=dict(width=0.65, edgecolor="white", linewidth=2),
                    textprops=dict(fontproperties=font_prop, fontsize=5, fontweight="bold", color="black")
                )
                ax.set_title(t["status_pie_title"], fontproperties=font_prop, fontsize=7, fontweight="bold", pad=15)
                ax.axis("equal")
                ax.set_position([0.15, 0.1, 0.7, 0.7])
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            with col_info:
                st.metric(t["total_order"], sales_total)
                st.divider()
                for i, (label, value) in enumerate(zip(labels, values)):
                    pct = (value / sales_total) * 100
                    st.markdown(f"**{label}**")
                    st.caption(f"{value}单 ({pct:.1f}%)")
            
            # 显示状态详情表格
            st.subheader(t["status_pie_title"])
            status_detail = []
            for std_status in WORKFLOW_STEPS_ZH:
                display_text = get_workflow_step_text(lang, std_status)
                cnt = status_counts[display_text]
                if cnt > 0:
                    pct = (cnt / sales_total) * 100
                    status_detail.append({
                        "状态": display_text,
                        t["count"]: cnt,
                        t["percentage"]: f"{pct:.1f}%"
                    })
            
            if status_detail:
                st.dataframe(pd.DataFrame(status_detail), use_container_width=True)
    else:
        # 显示团队视图
        st.markdown(f"<div style='color:#6b7280; font-size:14px; margin-bottom:10px'>{t['team_btn_tip']}</div>", unsafe_allow_html=True)
        
        # 团队颜色配置
        team_colors_map = {
            "MY": ["#4f46e5", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e", "#14b8a6", "#06b6d4", "#3b82f6"],
            "ID": ["#10b981", "#059669", "#047857", "#065f46", "#0ea5e9", "#0284c7", "#0369a1", "#075985", "#f59e0b", "#d97706", "#b45309", "#92400e"],
            "MEA": ["#f43f5e", "#e11d48", "#be123c", "#9f1239", "#881337", "#fb7185", "#fda4af", "#fecdd3", "#f0abfc", "#e879f9", "#d946ef", "#c026d3"]
        }
        
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        
        for idx, team in enumerate(TEAMS):
            team_df = unique_df[unique_df["team_temp"] == team]
            team_total = len(team_df)
            team_sales_cnt = team_df["sales_name"].value_counts()
            
            with cols[idx]:
                with st.container(height=420):
                    chart_title_key = f"{team.lower()}_chart_title"
                    chart_title = t.get(chart_title_key, f"{team}团队订单统计" if lang == "zh" else f"{team} Team Order Stats")
                    st.subheader(chart_title)
                    st.metric(t["total_order"], team_total)
                    if team_total > 0:
                        fig, ax = plt.subplots(figsize=(3, 3))
                        colors = team_colors_map.get(team, team_colors_map["MY"])
                        ax.pie(
                            team_sales_cnt.values,
                            labels=team_sales_cnt.index,
                            autopct=lambda p: f"{p:.0f}%",
                            startangle=90,
                            colors=colors[:len(team_sales_cnt)],
                            textprops={"fontproperties": font_prop, "fontsize": 6},
                            wedgeprops={"edgecolor": "#ffffff", "linewidth": 2}
                        )
                        ax.axis("equal")
                        st.pyplot(fig)
                        plt.close(fig)
                    else:
                        st.info(t["empty_tip"])
                    
                    # 添加团队按钮
                    btn_key = f"team_{team.lower()}_btn"
                    if st.button(f"📊 {t['team_status_title']}: {team}", key=btn_key, use_container_width=True, disabled=team_total == 0):
                        st.session_state["selected_team"] = team
                        st.rerun()
        
        st.divider()
        
        # 显示销售姓名表格（可点击）
        st.subheader(t["title"])
        
        all_data = []
        for team in TEAMS:
            team_df = unique_df[unique_df["team_temp"] == team]
            team_total = len(team_df)
            sales_cnt = team_df["sales_name"].value_counts()
            for sales_name, cnt in sales_cnt.items():
                percentage = (cnt / team_total) * 100 if team_total > 0 else 0
                all_data.append({
                    "团队": team,
                    "销售姓名": sales_name,
                    t["percentage"]: f"{percentage:.1f}%",
                    t["count"]: cnt
                })
        
        if all_data:
            # 使用按钮形式展示销售姓名，支持点击跳转
            result_df = pd.DataFrame(all_data)
            
            # 按团队分组展示
            for team in TEAMS:
                team_data = result_df[result_df["团队"] == team]
                if len(team_data) > 0:
                    st.markdown(f"**{team}**")
                    
                    cols_per_row = 3
                    team_sales = team_data["销售姓名"].tolist()
                    team_counts = team_data[t["count"]].tolist()
                    team_pcts = team_data[t["percentage"]].tolist()
                    
                    for i in range(0, len(team_sales), cols_per_row):
                        cols_row = st.columns(cols_per_row)
                        for j in range(cols_per_row):
                            idx_sales = i + j
                            if idx_sales < len(team_sales):
                                with cols_row[j]:
                                    sales_name = team_sales[idx_sales]
                                    cnt = team_counts[idx_sales]
                                    pct = team_pcts[idx_sales]
                                    if st.button(f"👤 {sales_name}\n{cnt}单 ({pct})", key=f"sales_{team}_{sales_name}", use_container_width=True):
                                        st.session_state["selected_sales"] = sales_name
                                        st.rerun()
        else:
            st.info(t["empty_tip"])

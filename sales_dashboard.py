import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from config import configure_matplotlib_font, get_workflow_step_text, get_standard_status, WORKFLOW_STEPS_ZH

PAGE_TEXT = {
    "zh": {
        "title": "销售团队统计",
        "total_order": "销售订单总数",
        "my_chart_title": "MY团队订单统计",
        "id_chart_title": "ID团队订单统计",
        "empty_tip": "暂无数据",
        "percentage": "占比",
        "count": "数量",
        "back_btn": "← 返回团队统计",
        "sales_status_title": "销售订单状态统计",
        "status_pie_title": "订单状态占比",
        "click_tip": "💡 点击销售姓名查看详细状态统计",
        "team_status_title": "团队订单状态占比",
        "team_btn_tip": "💡 点击团队名称查看订单状态占比"
    },
    "en": {
        "title": "Sales Team Statistics",
        "total_order": "Total Sales Orders",
        "my_chart_title": "MY Team Order Stats",
        "id_chart_title": "ID Team Order Stats",
        "empty_tip": "No data available",
        "percentage": "Percentage",
        "count": "Count",
        "back_btn": "← Back to Team View",
        "sales_status_title": "Sales Order Status Stats",
        "status_pie_title": "Status Ratio",
        "click_tip": "💡 Click on sales name to view detailed status stats",
        "team_status_title": "Team Order Status Ratio",
        "team_btn_tip": "💡 Click on team name to view order status ratio"
    }
}


def render_sales_dashboard(df):
    configure_matplotlib_font()
    font_prop = fm.FontProperties()
    lang = st.session_state.get("lang", "zh")
    t = PAGE_TEXT[lang]
    
    st.title(t["title"])
    
    sales_df = df.copy()
    
    if "团单号" in sales_df.columns:
        sales_df["团单号"] = sales_df["团单号"].fillna("").astype(str).str.strip()
    if "客户名称 Customer Name" in sales_df.columns:
        sales_df["客户名称 Customer Name"] = sales_df["客户名称 Customer Name"].fillna("").astype(str).str.strip()
    
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
                    "ID": ["#10b981", "#059669", "#047857", "#065f46", "#0ea5e9", "#0284c7", "#0369a1", "#075985", "#f59e0b", "#d97706", "#b45309", "#92400e"]
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
                ax.set_title(t["status_pie_title"], fontproperties=font_prop, fontsize=5, fontweight="bold", pad=15)
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
                ax.set_title(t["status_pie_title"], fontproperties=font_prop, fontsize=5, fontweight="bold", pad=15)
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
        
        col1, col2 = st.columns(2)
        
        my_df = unique_df[unique_df["team_temp"] == "MY"]
        my_total = len(my_df)
        my_sales_cnt = my_df["sales_name"].value_counts()
        
        with col1:
            st.subheader(t["my_chart_title"])
            st.metric(t["total_order"], my_total)
            if my_total > 0:
                fig_my, ax_my = plt.subplots(figsize=(3, 3))
                my_colors = [
                    "#4f46e5", "#8b5cf6", "#a855f7", "#d946ef", 
                    "#ec4899", "#f43f5e", "#f97316", "#eab308",
                    "#22c55e", "#14b8a6", "#06b6d4", "#3b82f6"
                ]
                ax_my.pie(
                    my_sales_cnt.values,
                    labels=my_sales_cnt.index,
                    autopct=lambda p: f"{p:.0f}%",
                    startangle=90,
                    colors=my_colors[:len(my_sales_cnt)],
                    textprops={"fontproperties": font_prop, "fontsize": 7},
                    wedgeprops={"edgecolor": "#ffffff", "linewidth": 2}
                )
                ax_my.axis("equal")
                st.pyplot(fig_my)
                plt.close(fig_my)
            else:
                st.info(t["empty_tip"])
            
            # 添加团队按钮
            if st.button(f"📊 {t['team_status_title']}: MY", key="team_my_btn", use_container_width=True, disabled=my_total == 0):
                st.session_state["selected_team"] = "MY"
                st.rerun()
        
        id_df = unique_df[unique_df["team_temp"] == "ID"]
        id_total = len(id_df)
        id_sales_cnt = id_df["sales_name"].value_counts()
        
        with col2:
            st.subheader(t["id_chart_title"])
            st.metric(t["total_order"], id_total)
            if id_total > 0:
                fig_id, ax_id = plt.subplots(figsize=(3, 3))
                id_colors = [
                    "#10b981", "#059669", "#047857", "#065f46",
                    "#0ea5e9", "#0284c7", "#0369a1", "#075985",
                    "#f59e0b", "#d97706", "#b45309", "#92400e",
                    "#8b5cf6", "#7c3aed", "#6d28d9", "#5b21b6"
                ]
                ax_id.pie(
                    id_sales_cnt.values,
                    labels=id_sales_cnt.index,
                    autopct=lambda p: f"{p:.0f}%",
                    startangle=90,
                    colors=id_colors[:len(id_sales_cnt)],
                    textprops={"fontproperties": font_prop, "fontsize": 7},
                    wedgeprops={"edgecolor": "#ffffff", "linewidth": 2}
                )
                ax_id.axis("equal")
                st.pyplot(fig_id)
                plt.close(fig_id)
            else:
                st.info(t["empty_tip"])
            
            # 添加团队按钮
            if st.button(f"📊 {t['team_status_title']}: ID", key="team_id_btn", use_container_width=True, disabled=id_total == 0):
                st.session_state["selected_team"] = "ID"
                st.rerun()
        
        st.divider()
        
        # 显示销售姓名表格（可点击）
        st.subheader(t["title"])
        
        all_data = []
        for team in ["MY", "ID"]:
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
            for team in ["MY", "ID"]:
                team_data = result_df[result_df["团队"] == team]
                if len(team_data) > 0:
                    st.markdown(f"**{team}**")
                    
                    cols_per_row = 3
                    team_sales = team_data["销售姓名"].tolist()
                    team_counts = team_data[t["count"]].tolist()
                    team_pcts = team_data[t["percentage"]].tolist()
                    
                    for i in range(0, len(team_sales), cols_per_row):
                        cols = st.columns(cols_per_row)
                        for j in range(cols_per_row):
                            idx = i + j
                            if idx < len(team_sales):
                                with cols[j]:
                                    sales_name = team_sales[idx]
                                    cnt = team_counts[idx]
                                    pct = team_pcts[idx]
                                    if st.button(f"👤 {sales_name}\n{cnt}单 ({pct})", key=f"sales_{team}_{sales_name}", use_container_width=True):
                                        st.session_state["selected_sales"] = sales_name
                                        st.rerun()
        else:
            st.info(t["empty_tip"])

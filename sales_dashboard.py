import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from config import configure_matplotlib_font

PAGE_TEXT = {
    "zh": {
        "title": "销售团队统计",
        "total_order": "销售订单总数",
        "my_chart_title": "MY团队订单统计",
        "id_chart_title": "ID团队订单统计",
        "empty_tip": "暂无数据",
        "percentage": "占比",
        "count": "数量"
    },
    "en": {
        "title": "Sales Team Statistics",
        "total_order": "Total Sales Orders",
        "my_chart_title": "MY Team Order Stats",
        "id_chart_title": "ID Team Order Stats",
        "empty_tip": "No data available",
        "percentage": "Percentage",
        "count": "Count"
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
    from config import get_standard_status
    sales_df["标准状态"] = sales_df["状态"].apply(get_standard_status)
    
    unique_df = sales_df[["去重键", "标准状态"]].drop_duplicates()
    total = len(unique_df)
    st.metric(t["total_order"], total)
    st.divider()
    
    if "Salesteam" not in sales_df.columns:
        sales_df["Salesteam"] = ""
    sales_df["team_temp"] = sales_df["Salesteam"].fillna("无销售团队").astype(str).str.strip()
    
    if "销售姓名 Sales Name" not in sales_df.columns:
        sales_df["销售姓名 Sales Name"] = ""
    sales_df["sales_name"] = sales_df["销售姓名 Sales Name"].fillna("未知销售").astype(str).str.strip()
    
    unique_team_df = sales_df[["去重键", "标准状态", "team_temp", "sales_name"]].drop_duplicates()
    
    total_orders = len(unique_team_df)
    
    if total_orders == 0:
        st.info(t["empty_tip"])
    else:
        col1, col2 = st.columns(2)
        
        my_df = unique_team_df[unique_team_df["team_temp"] == "MY"]
        my_total = len(my_df)
        my_sales_cnt = my_df["sales_name"].value_counts()
        
        with col1:
            st.subheader(t["my_chart_title"])
            if my_total > 0:
                fig_my, ax_my = plt.subplots(figsize=(6, 6))
                my_colors = [
                    "#4f46e5", "#8b5cf6", "#a855f7", "#d946ef", 
                    "#ec4899", "#f43f5e", "#f97316", "#eab308",
                    "#22c55e", "#14b8a6", "#06b6d4", "#3b82f6"
                ]
                ax_my.pie(
                    my_sales_cnt.values,
                    labels=my_sales_cnt.index,
                    autopct=lambda p: f"{p:.1f}%\n({int(p/100*my_total)})",
                    startangle=90,
                    colors=my_colors[:len(my_sales_cnt)],
                    textprops={"fontproperties": font_prop},
                    wedgeprops={"edgecolor": "#ffffff", "linewidth": 2}
                )
                ax_my.axis("equal")
                st.pyplot(fig_my)
            else:
                st.info(t["empty_tip"])
        
        id_df = unique_team_df[unique_team_df["team_temp"] == "ID"]
        id_total = len(id_df)
        id_sales_cnt = id_df["sales_name"].value_counts()
        
        with col2:
            st.subheader(t["id_chart_title"])
            if id_total > 0:
                fig_id, ax_id = plt.subplots(figsize=(6, 6))
                id_colors = [
                    "#10b981", "#059669", "#047857", "#065f46",
                    "#0ea5e9", "#0284c7", "#0369a1", "#075985",
                    "#f59e0b", "#d97706", "#b45309", "#92400e",
                    "#8b5cf6", "#7c3aed", "#6d28d9", "#5b21b6"
                ]
                ax_id.pie(
                    id_sales_cnt.values,
                    labels=id_sales_cnt.index,
                    autopct=lambda p: f"{p:.1f}%\n({int(p/100*id_total)})",
                    startangle=90,
                    colors=id_colors[:len(id_sales_cnt)],
                    textprops={"fontproperties": font_prop},
                    wedgeprops={"edgecolor": "#ffffff", "linewidth": 2}
                )
                ax_id.axis("equal")
                st.pyplot(fig_id)
            else:
                st.info(t["empty_tip"])
        
        all_data = []
        for team in ["MY", "ID"]:
            team_df = unique_team_df[unique_team_df["team_temp"] == team]
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
            result_df = pd.DataFrame(all_data)
            st.dataframe(result_df)
        else:
            st.info(t["empty_tip"])

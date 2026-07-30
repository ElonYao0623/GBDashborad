import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from config import configure_matplotlib_font, get_standard_status

PAGE_TEXT = {
    "zh": {
        "title": "团房成功分析",
        "total_success": "成功订单总数",
        "chart_title": "各销售成功订单占比",
        "empty_tip": "暂无数据",
        "percentage": "占比",
        "count": "数量",
        "back_btn": "← 返回统计",
        "order_detail": "订单详情",
        "customer_name": "客户名称",
        "hotel_name": "酒店名称",
        "sales_name": "销售姓名",
        "team": "销售团队",
        "checkin": "入住日期",
        "checkout": "离店日期",
        "order_id": "团单号",
        "click_tip": "💡 点击销售姓名查看对应订单"
    },
    "en": {
        "title": "Success Booking Analysis",
        "total_success": "Total Successful Bookings",
        "chart_title": "Sales Success Order Ratio",
        "empty_tip": "No data available",
        "percentage": "Percentage",
        "count": "Count",
        "back_btn": "← Back to Stats",
        "order_detail": "Order Details",
        "customer_name": "Customer Name",
        "hotel_name": "Hotel Name",
        "sales_name": "Sales Name",
        "team": "Sales Team",
        "checkin": "Check-in Date",
        "checkout": "Check-out Date",
        "order_id": "Order No.",
        "click_tip": "💡 Click on sales name to view orders"
    }
}

STATUS_SUCCESS_KEY = "group_booking_success"


def render_success_dashboard(df):
    configure_matplotlib_font()
    font_prop = fm.FontProperties()
    lang = st.session_state.get("lang", "zh")
    t = PAGE_TEXT[lang]
    
    st.title(t["title"])
    
    success_df = df.copy()
    
    # 数据预处理
    if "团单号" in success_df.columns:
        success_df["团单号"] = success_df["团单号"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    if "客户名称 Customer Name" in success_df.columns:
        success_df["客户名称 Customer Name"] = success_df["客户名称 Customer Name"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    
    if "状态" in success_df.columns:
        success_df["状态"] = success_df["状态"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    else:
        success_df["状态"] = ""
    success_df["标准状态"] = success_df["状态"].apply(get_standard_status)
    
    # 筛选团房成功状态
    success_mask = success_df["标准状态"] == STATUS_SUCCESS_KEY
    success_orders = success_df[success_mask].copy()
    
    if success_orders.empty:
        st.info(t["empty_tip"])
        return
    
    # 去重逻辑：用于饼形图统计
    success_orders["去重键"] = success_orders.apply(
        lambda row: row["团单号"] if row.get("团单号", "") else row.get("客户名称 Customer Name", ""),
        axis=1
    )
    
    if "销售姓名 Sales Name" not in success_orders.columns:
        success_orders["销售姓名 Sales Name"] = "未知销售"
    success_orders["sales_name"] = success_orders["销售姓名 Sales Name"].fillna("未知销售").astype(str).str.strip()
    
    unique_success = success_orders[["去重键", "标准状态", "sales_name"]].drop_duplicates(subset=["去重键"])
    total_success = len(unique_success)
    
    st.metric(t["total_success"], total_success)
    st.divider()
    
    # 检查是否在查看某个销售的订单
    selected_sales = st.session_state.get("selected_success_sales", None)
    
    if selected_sales:
        # 查看某个销售的订单列表
        if st.button(t["back_btn"], type="primary"):
            st.session_state["selected_success_sales"] = None
            st.rerun()
        
        st.subheader(f"{t['order_detail']}: {selected_sales}")
        
        # 筛选该销售的订单（不去重，直接展示所有原始数据）
        sales_orders = success_orders[success_orders["sales_name"] == selected_sales]
        
        if sales_orders.empty:
            st.info(t["empty_tip"])
            return
        
        # 获取去重后的订单数（用于显示统计）
        sales_unique = sales_orders.drop_duplicates(subset=["去重键"])
        sales_unique_count = len(sales_unique)
        
        st.metric(t["count"], sales_unique_count)
        st.divider()
        
        # 展示订单列表（不去重）
        display_cols = []
        col_map = {
            "团单号": t["order_id"],
            "客户名称 Customer Name": t["customer_name"],
            "酒店名称 Hotel Name": t["hotel_name"],
            "销售姓名 Sales Name": t["sales_name"],
            "Salesteam": t["team"],
            "入住日期 Check-in Date": t["checkin"],
            "离店日期 Check-out Date": t["checkout"]
        }
        
        for col, display_name in col_map.items():
            if col in sales_orders.columns:
                display_cols.append(col)
        
        if display_cols:
            result_df = sales_orders[display_cols].copy()
            result_df.columns = [col_map.get(c, c) for c in result_df.columns]
            st.dataframe(result_df, use_container_width=True, hide_index=True)
    else:
        # 显示饼形图统计
        st.markdown(f"<div style='color:#6b7280; font-size:14px; margin-bottom:10px'>{t['click_tip']}</div>", unsafe_allow_html=True)
        
        # 统计每个销售的成功订单数（去重后）
        sales_counts = unique_success["sales_name"].value_counts()
        non_zero_sales = sales_counts[sales_counts > 0]
        
        if len(non_zero_sales) == 0:
            st.info(t["empty_tip"])
            return
        
        # 绘制饼形图
        col_pie, col_info = st.columns([3, 1])
        
        with col_pie:
            fig, ax = plt.subplots(figsize=(6, 6))
            fig.patch.set_facecolor("white")
            
            labels = non_zero_sales.index.tolist()
            values = non_zero_sales.values.tolist()
            
            colors_list = plt.cm.Set2(np.linspace(0, 1, len(labels)))
            total_v = sum(values)
            labels_pct = [f"{v/total_v*100:.1f}%" for v in values]
            
            wedges, texts = ax.pie(
                values,
                labels=labels_pct,
                labeldistance=1.15,
                colors=colors_list,
                startangle=90,
                wedgeprops=dict(width=0.65, edgecolor="white", linewidth=2),
                textprops=dict(fontproperties=font_prop, fontsize=11, fontweight="bold", color="black")
            )
            ax.set_title(t["chart_title"], fontproperties=font_prop, fontsize=14, fontweight="bold", pad=20)
            ax.axis("equal")
            ax.set_position([0.1, 0.1, 0.75, 0.75])
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        
        with col_info:
            st.metric(t["total_success"], total_success)
            st.divider()
            for label, value in zip(labels, values):
                pct = (value / total_success) * 100
                st.markdown(f"**{label}**")
                st.caption(f"{value}{t['count']} ({pct:.1f}%)")
        
        # 显示可点击的销售按钮
        st.divider()
        st.subheader(t["chart_title"])
        
        cols_per_row = 3
        sales_list = non_zero_sales.index.tolist()
        sales_values = non_zero_sales.values.tolist()
        
        for i in range(0, len(sales_list), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < len(sales_list):
                    with cols[j]:
                        sales = sales_list[idx]
                        cnt = sales_values[idx]
                        pct = (cnt / total_success) * 100
                        if st.button(f"👤 {sales}\n{cnt}单 ({pct:.1f}%)", key=f"success_sales_{sales}", use_container_width=True):
                            st.session_state["selected_success_sales"] = sales
                            st.rerun()

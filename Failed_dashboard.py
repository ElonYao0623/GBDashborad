import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from config import configure_matplotlib_font, get_standard_status, STATUS_WORKFLOW_MAP

PAGE_TEXT = {
    "zh": {
        "title": "团房失败分析",
        "total_failed": "失败订单总数",
        "primary_chart_title": "未成单原因（一级）统计",
        "secondary_chart_title": "未成单原因（二级）统计",
        "empty_tip": "暂无数据",
        "percentage": "占比",
        "count": "单",
        "back_btn": "← 返回一级原因",
        "click_tip": "💡 点击原因查看二级详情",
        "order_detail": "订单详情",
        "no_reason": "未填写",
        "customer_name": "客户名称",
        "hotel_name": "酒店名称",
        "sales_name": "销售姓名",
        "status": "状态"
    },
    "en": {
        "title": "Failed Booking Analysis",
        "total_failed": "Total Failed Bookings",
        "primary_chart_title": "Primary Failure Reason",
        "secondary_chart_title": "Secondary Failure Reason",
        "empty_tip": "No data available",
        "percentage": "Percentage",
        "count": "Booking",
        "back_btn": "← Back to Primary Reasons",
        "click_tip": "💡 Click on reason to view secondary details",
        "order_detail": "Order Details",
        "no_reason": "Not Filled",
        "customer_name": "Customer Name",
        "hotel_name": "Hotel Name",
        "sales_name": "Sales Name",
        "status": "Status"
    }
}

STATUS_FAILED_KEY = "group_booking_failed"


def render_failed_dashboard(df):
    configure_matplotlib_font()
    font_prop = fm.FontProperties()
    lang = st.session_state.get("lang", "zh")
    t = PAGE_TEXT[lang]
    
    st.title(t["title"])
    
    failed_df = df.copy()
    
    # 数据预处理
    if "团单号" in failed_df.columns:
        failed_df["团单号"] = failed_df["团单号"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    if "客户名称 Customer Name" in failed_df.columns:
        failed_df["客户名称 Customer Name"] = failed_df["客户名称 Customer Name"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    
    if "状态" in failed_df.columns:
        failed_df["状态"] = failed_df["状态"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    else:
        failed_df["状态"] = ""
    failed_df["标准状态"] = failed_df["状态"].apply(get_standard_status)
    
    # 筛选团房失败状态
    failed_mask = failed_df["标准状态"] == STATUS_FAILED_KEY
    failed_orders = failed_df[failed_mask].copy()
    
    if failed_orders.empty:
        st.info(t["empty_tip"])
        return
    
    # 去重逻辑：团单号+状态去重，或客户名称+状态去重
    failed_orders["去重键"] = failed_orders.apply(
        lambda row: row["团单号"] if row.get("团单号", "") else row.get("客户名称 Customer Name", ""),
        axis=1
    )
    
    unique_failed = failed_orders[["去重键", "标准状态"]].drop_duplicates()
    total_failed = len(unique_failed)
    
    st.metric(t["total_failed"], total_failed)
    st.divider()
    
    # 添加未成单原因列
    reason_col_1 = "未成单原因（一级）"
    reason_col_2 = "未成单原因（二级）"
    
    if reason_col_1 not in failed_orders.columns:
        failed_orders[reason_col_1] = t["no_reason"]
    if reason_col_2 not in failed_orders.columns:
        failed_orders[reason_col_2] = t["no_reason"]
    
    failed_orders[reason_col_1] = failed_orders[reason_col_1].fillna(t["no_reason"]).astype(str).str.strip()
    failed_orders[reason_col_2] = failed_orders[reason_col_2].fillna(t["no_reason"]).astype(str).str.strip()
    
    # 合并唯一键和原因
    analysis_df = failed_orders[["去重键", reason_col_1, reason_col_2]].drop_duplicates(subset=["去重键"])
    analysis_df = analysis_df[analysis_df["去重键"].isin(unique_failed["去重键"])]
    
    # 检查是否在查看二级原因
    selected_primary = st.session_state.get("selected_primary_reason", None)
    
    if selected_primary:
        # 查看二级原因
        if st.button(t["back_btn"], type="primary"):
            st.session_state["selected_primary_reason"] = None
            st.rerun()
        
        st.subheader(f"{t['secondary_chart_title']}: {selected_primary}")
        
        # 筛选该一级原因的数据
        primary_data = analysis_df[analysis_df[reason_col_1] == selected_primary]
        
        if primary_data.empty:
            st.info(t["empty_tip"])
            return
        
        primary_total = len(primary_data)
        st.metric(t["count"], primary_total)
        st.divider()
        
        # 统计二级原因
        secondary_counts = primary_data[reason_col_2].value_counts()
        non_zero_secondary = secondary_counts[secondary_counts > 0]
        
        if len(non_zero_secondary) == 0:
            st.info(t["empty_tip"])
            return
        
        # 绘制二级原因饼形图
        col_pie, col_info = st.columns([3, 1])
        
        with col_pie:
            fig, ax = plt.subplots(figsize=(5, 5))
            fig.patch.set_facecolor("white")
            
            labels = non_zero_secondary.index.tolist()
            values = non_zero_secondary.values.tolist()
            
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
                textprops=dict(fontproperties=font_prop, fontsize=10, fontweight="bold", color="black")
            )
            ax.set_title(t["secondary_chart_title"], fontproperties=font_prop, fontsize=12, fontweight="bold", pad=15)
            ax.axis("equal")
            ax.set_position([0.15, 0.1, 0.7, 0.7])
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        
        with col_info:
            st.metric(t["count"], primary_total)
            st.divider()
            for label, value in zip(labels, values):
                pct = (value / primary_total) * 100
                display_label = label if label != t["no_reason"] else t["no_reason"]
                st.markdown(f"**{display_label}**")
                st.caption(f"{value}{t['count']} ({pct:.1f}%)")
        
        # 显示订单详情
        st.divider()
        st.subheader(t["order_detail"])
        
        # 获取该一级原因的所有订单详情
        detail_df = failed_orders[failed_orders[reason_col_1] == selected_primary]
        detail_df = detail_df.drop_duplicates(subset=["去重键"])
        
        display_cols = []
        col_map = {
            "客户名称 Customer Name": t["customer_name"],
            "酒店名称 Hotel Name": t["hotel_name"],
            "销售姓名 Sales Name": t["sales_name"],
            reason_col_1: reason_col_1,
            reason_col_2: reason_col_2
        }
        
        for col, display_name in col_map.items():
            if col in detail_df.columns:
                display_cols.append(col)
        
        if display_cols:
            result_df = detail_df[display_cols].copy()
            result_df.columns = [col_map.get(c, c) for c in result_df.columns]
            st.dataframe(result_df, use_container_width=True, hide_index=True)
    else:
        # 显示一级原因饼形图
        st.markdown(f"<div style='color:#6b7280; font-size:14px; margin-bottom:10px'>{t['click_tip']}</div>", unsafe_allow_html=True)
        
        # 统计一级原因
        primary_counts = analysis_df[reason_col_1].value_counts()
        non_zero_primary = primary_counts[primary_counts > 0]
        
        if len(non_zero_primary) == 0:
            st.info(t["empty_tip"])
            return
        
        # 绘制一级原因饼形图
        col_pie, col_info = st.columns([3, 1])
        
        with col_pie:
            fig, ax = plt.subplots(figsize=(6, 6))
            fig.patch.set_facecolor("white")
            
            labels = non_zero_primary.index.tolist()
            values = non_zero_primary.values.tolist()
            
            colors_list = plt.cm.Set3(np.linspace(0, 1, len(labels)))
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
            ax.set_title(t["primary_chart_title"], fontproperties=font_prop, fontsize=14, fontweight="bold", pad=20)
            ax.axis("equal")
            ax.set_position([0.1, 0.1, 0.75, 0.75])
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        
        with col_info:
            st.metric(t["total_failed"], total_failed)
            st.divider()
            for label, value in zip(labels, values):
                pct = (value / total_failed) * 100
                display_label = label if label != t["no_reason"] else t["no_reason"]
                st.markdown(f"**{display_label}**")
                st.caption(f"{value}{t['count']} ({pct:.1f}%)")
        
        # 显示可点击的一级原因按钮
        st.divider()
        st.subheader(t["primary_chart_title"])
        
        cols_per_row = 3
        primary_list = non_zero_primary.index.tolist()
        primary_values = non_zero_primary.values.tolist()
        
        for i in range(0, len(primary_list), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i + j
                if idx < len(primary_list):
                    with cols[j]:
                        reason = primary_list[idx]
                        cnt = primary_values[idx]
                        pct = (cnt / total_failed) * 100
                        display_reason = reason if reason != t["no_reason"] else t["no_reason"]
                        if st.button(f"🔍 {display_reason}\n{cnt}单 ({pct:.1f}%)", key=f"primary_reason_{reason}", use_container_width=True):
                            st.session_state["selected_primary_reason"] = reason
                            st.rerun()

"""
分析看板模块 - KPI卡片、Plotly交互式图表、分页明细表格、数据导出
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import (
    init_session_state,
    get_csv_download_link,
    get_excel_download_link,
    get_fig_download_button,
    get_timestamp
)
import io
import base64


def render_dashboard():
    """渲染分析看板页面"""
    st.markdown("## 📊 数据分析看板")

    init_session_state()

    if st.session_state.get('df_cleaned') is None:
        st.warning("⚠ 请先在 **首页** 上传数据文件")
        st.info("👈 前往首页上传 CSV 或 Excel 文件")
        return

    df = st.session_state['df_cleaned'].copy()

    # ---- 应用侧边栏筛选 ----
    df = apply_sidebar_filters(df)

    if df.empty:
        st.warning("⚠ 筛选后无数据，请调整筛选条件")
        return

    # ---- KPI 指标卡片 ----
    render_kpi_cards(df)

    st.markdown("---")

    # ---- 图表区域 ----
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    text_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

    if not numeric_cols:
        st.info("未检测到数值列，无法生成图表。请检查数据或前往预处理页面进行类型转换。")
    else:
        # 图表配置
        st.markdown("### 📈 图表配置")
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("X 轴 / 分类列", options=df.columns.tolist(), key='chart_x')
        with col2:
            y_col = st.selectbox("Y 轴 / 数值列", options=numeric_cols, key='chart_y',
                                 index=min(1, len(numeric_cols) - 1) if len(numeric_cols) > 1 else 0)

        st.markdown("---")

        # 使用 Tab 组织不同图表
        chart_tab1, chart_tab2, chart_tab3, chart_tab4, chart_tab5 = st.tabs(
            ["📊 折线图", "📊 柱状图", "🥧 饼图", "🎯 散点图", "🔥 热力图"]
        )

        with chart_tab1:
            render_line_chart(df, x_col, y_col)
        with chart_tab2:
            render_bar_chart(df, x_col, y_col)
        with chart_tab3:
            render_pie_chart(df, x_col, y_col, numeric_cols)
        with chart_tab4:
            render_scatter_chart(df, x_col, y_col, numeric_cols)
        with chart_tab5:
            render_heatmap(df, numeric_cols)

    st.markdown("---")

    # ---- 明细表格 ----
    render_detail_table(df)

    st.markdown("---")

    # ---- 导出区域 ----
    render_export_section(df)


def apply_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """应用侧边栏筛选条件"""
    # 从 session_state 读取筛选条件（由 app.py 设置）
    filters = st.session_state.get('sidebar_filters', {})

    if not filters:
        return df

    mask = pd.Series(True, index=df.index)

    # 分类筛选
    if filters.get('cat_col') and filters.get('cat_col') in df.columns:
        selected = filters.get('cat_values', [])
        if selected:
            mask &= df[filters['cat_col']].isin(selected)

    # 数值范围筛选
    if filters.get('num_col') and filters.get('num_col') in df.columns:
        num_range = filters.get('num_range', (None, None))
        if num_range[0] is not None:
            mask &= df[filters['num_col']] >= num_range[0]
        if num_range[1] is not None:
            mask &= df[filters['num_col']] <= num_range[1]

    # 日期范围筛选
    if filters.get('date_col') and filters.get('date_col') in df.columns:
        date_range = filters.get('date_range', (None, None))
        # 尝试转换为 datetime
        try:
            date_series = pd.to_datetime(df[filters['date_col']], errors='coerce')
            if date_range[0] is not None:
                mask &= date_series >= pd.Timestamp(date_range[0])
            if date_range[1] is not None:
                mask &= date_series <= pd.Timestamp(date_range[1])
        except Exception:
            pass

    return df[mask]


# ==================== KPI 卡片 ====================

def render_kpi_cards(df: pd.DataFrame):
    """渲染顶部 KPI 指标卡片"""
    st.markdown("### 🎯 关键指标 (KPI)")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not numeric_cols:
        st.info("无数值列可展示")
        return

    # 最多展示 6 个 KPI
    cols = st.columns(min(6, len(numeric_cols) * 3))

    kpi_index = 0
    for col_name in numeric_cols[:6]:
        if kpi_index >= 6:
            break

        series = df[col_name].dropna()
        if len(series) == 0:
            continue

        with cols[kpi_index % 6]:
            st.metric(
                label=f"📌 {col_name}",
                value=f"{series.mean():,.2f}",
                delta=f"最大 {series.max():,.2f}" if len(series) > 0 else None
            )
        kpi_index += 1

    # 额外统计
    if len(numeric_cols) > 0:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 总行数", f"{len(df):,}")
        with col2:
            st.metric("📝 数值列数", len(numeric_cols))
        with col3:
            null_count = df[numeric_cols].isnull().sum().sum()
            st.metric("❓ 数值缺失", null_count)
        with col4:
            zero_count = (df[numeric_cols] == 0).sum().sum()
            st.metric("0️⃣ 零值数", zero_count)


# ==================== 图表渲染 ====================

def render_line_chart(df: pd.DataFrame, x_col: str, y_col: str):
    """折线图"""
    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        title=f"{y_col} 随 {x_col} 变化趋势",
        markers=True,
        template='plotly_white'
    )
    fig.update_layout(
        hovermode='x unified',
        height=450,
        xaxis_title=x_col,
        yaxis_title=y_col
    )
    st.plotly_chart(fig, use_container_width=True)

    # 下载按钮
    show_chart_download(fig, "line_chart")


def render_bar_chart(df: pd.DataFrame, x_col: str, y_col: str):
    """柱状图"""
    # 如果 x 列类别太多，聚合展示 top 20
    plot_df = df.copy()
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if x_col in cat_cols and df[x_col].nunique() > 20:
        # 按 y 聚合取 top 20
        agg = df.groupby(x_col)[y_col].sum().nlargest(20).reset_index()
        plot_df = agg
        st.caption(f"⚠ {x_col} 类别过多，仅展示 Top 20")

    fig = px.bar(
        plot_df,
        x=x_col,
        y=y_col,
        title=f"{y_col} 按 {x_col} 分布",
        color=y_col,
        color_continuous_scale='Blues',
        template='plotly_white'
    )
    fig.update_layout(
        height=450,
        xaxis_title=x_col,
        yaxis_title=y_col,
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    show_chart_download(fig, "bar_chart")


def render_pie_chart(df: pd.DataFrame, x_col: str, y_col: str, numeric_cols: list):
    """饼图"""
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

    # 饼图适合分类列
    pie_cat = st.selectbox(
        "分类列（用于饼图）",
        options=cat_cols if cat_cols else df.columns.tolist(),
        key='pie_cat'
    )
    pie_val = st.selectbox(
        "数值列（用于饼图）",
        options=numeric_cols,
        key='pie_val'
    )

    # 聚合
    agg = df.groupby(pie_cat)[pie_val].sum().nlargest(15).reset_index()

    fig = px.pie(
        agg,
        names=pie_cat,
        values=pie_val,
        title=f"{pie_val} 按 {pie_cat} 占比",
        hole=0.4,
        template='plotly_white'
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    show_chart_download(fig, "pie_chart")


def render_scatter_chart(df: pd.DataFrame, x_col: str, y_col: str, numeric_cols: list):
    """散点图"""
    color_col = st.selectbox(
        "着色列（可选）",
        options=['无'] + df.columns.tolist(),
        key='scatter_color'
    )
    size_col = st.selectbox(
        "大小列（可选，需为数值列）",
        options=['无'] + numeric_cols,
        key='scatter_size'
    )

    kwargs = {}
    if color_col != '无':
        kwargs['color'] = color_col
    if size_col != '无':
        kwargs['size'] = size_col

    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        title=f"{y_col} vs {x_col} 散点图",
        template='plotly_white',
        opacity=0.7,
        **kwargs
    )
    fig.update_layout(height=500, xaxis_title=x_col, yaxis_title=y_col)
    st.plotly_chart(fig, use_container_width=True)
    show_chart_download(fig, "scatter_chart")


def render_heatmap(df: pd.DataFrame, numeric_cols: list):
    """热力图（相关性矩阵）"""
    if len(numeric_cols) < 2:
        st.info("需要至少 2 个数值列才能生成热力图")
        return

    corr = df[numeric_cols].corr()

    fig = px.imshow(
        corr,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        zmin=-1, zmax=1,
        title="数值列相关性热力图",
        template='plotly_white'
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    show_chart_download(fig, "heatmap")


# ==================== 明细表格 ====================

def render_detail_table(df: pd.DataFrame):
    """分页可检索的明细表格"""
    st.markdown("### 📋 数据明细")

    # 搜索框
    search_term = st.text_input("🔍 搜索数据", placeholder="输入关键词检索...", key='table_search')

    display_df = df.copy()

    # 搜索过滤
    if search_term:
        mask = pd.Series(False, index=display_df.index)
        for col in display_df.select_dtypes(include=['object']).columns:
            mask |= display_df[col].astype(str).str.contains(search_term, case=False, na=False)
        if display_df.select_dtypes(include=[np.number]).columns.any():
            for col in display_df.select_dtypes(include=[np.number]).columns:
                mask |= display_df[col].astype(str).str.contains(search_term, case=False, na=False)
        display_df = display_df[mask]
        st.caption(f"找到 {len(display_df)} 条匹配记录")

    # 分页
    page_size = st.selectbox("每页行数", [10, 20, 50, 100], key='page_size', index=1)
    total_pages = max(1, (len(display_df) + page_size - 1) // page_size)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        page = st.number_input("页码", min_value=1, max_value=total_pages, value=1, key='page_num')
    with col3:
        st.caption(f"共 {total_pages} 页 / {len(display_df)} 条")

    start = (page - 1) * page_size
    end = start + page_size

    st.dataframe(
        display_df.iloc[start:end],
        use_container_width=True,
        height=400
    )


# ==================== 导出区域 ====================

def render_export_section(df: pd.DataFrame):
    """数据导出区域"""
    st.markdown("### 💾 数据导出")

    col1, col2, col3 = st.columns(3)

    with col1:
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 导出 CSV",
            data=csv_data,
            file_name=f"dashboard_data_{get_timestamp()}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='数据')
        st.download_button(
            label="📥 导出 Excel",
            data=output.getvalue(),
            file_name=f"dashboard_data_{get_timestamp()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col3:
        st.info("💡 图表下载请点击各图表下方的按钮")


# ==================== 辅助函数 ====================

def show_chart_download(fig, name: str):
    """在各图表下方显示下载按钮"""
    download_label = get_fig_download_button(fig, f"📷 下载 {name}", f"{name}_{get_timestamp()}.png")
    if download_label:
        st.markdown(download_label, unsafe_allow_html=True)
    else:
        st.caption("💡 安装 kaleido 后支持图表下载为图片: `pip install kaleido`")


if __name__ == "__main__":
    render_dashboard()
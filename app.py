"""
主入口 - 一站式数据处理交互式可视化看板
Tab 分栏: 首页上传 | 数据预处理 | 分析看板
侧边栏: 交互式筛选 + 主题切换
"""

import streamlit as st
import pandas as pd
import numpy as np

# 页面配置必须在最前面
st.set_page_config(
    page_title="数据处理可视化看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入各页面模块
from pages.home import render_home
from pages.preprocess import render_preprocess
from pages.dashboard import render_dashboard
from utils import init_session_state


# ==================== CSS 样式 ====================

def inject_custom_css():
    """注入自定义 CSS 样式"""
    st.markdown("""
    <style>
    /* 全局字体 */
    html, body, [class*="css"] {
        font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
    }

    /* 主标题样式 */
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }

    /* KPI 卡片美化 */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    /* 按钮样式 */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* 上传区域 */
    [data-testid="stFileUploader"] {
        border: 2px dashed #667eea;
        border-radius: 16px;
        padding: 20px;
        background: rgba(102, 126, 234, 0.05);
    }

    /* 加载动画 */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }

    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }

    /* 页脚 */
    .footer {
        text-align: center;
        padding: 20px;
        color: #999;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)


# ==================== 主题切换 ====================

def render_theme_toggle():
    """主题切换按钮"""
    theme = st.session_state.get('theme', 'light')

    if theme == 'light':
        if st.sidebar.button("🌙 切换深色主题", use_container_width=True):
            st.session_state['theme'] = 'dark'
            st.rerun()
    else:
        if st.sidebar.button("☀️ 切换浅色主题", use_container_width=True):
            st.session_state['theme'] = 'light'
            st.rerun()

    # 通过 plotly 模板切换图表主题
    plotly_template = 'plotly_dark' if theme == 'dark' else 'plotly_white'
    # 注意：plotly 模板在子模块中独立设置，这里仅作状态记录


# ==================== 侧边栏筛选 ====================

def render_sidebar_filters():
    """渲染侧边栏的交互式筛选器"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 数据筛选")

    df = st.session_state.get('df_cleaned')
    if df is None:
        st.sidebar.info("请先上传数据")
        return

    filters = {}

    # ---- 分类筛选 ----
    text_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if text_cols:
        st.sidebar.markdown("#### 📂 分类筛选")
        cat_col = st.sidebar.selectbox(
            "选择分类列",
            options=['无'] + text_cols,
            key='sidebar_cat_col'
        )
        if cat_col != '无':
            filters['cat_col'] = cat_col
            unique_vals = sorted(df[cat_col].dropna().unique().tolist())
            # 限制选项数
            if len(unique_vals) > 50:
                st.sidebar.caption(f"⚠ 共 {len(unique_vals)} 个分类，过多时建议使用搜索")
                filters['cat_values'] = st.sidebar.multiselect(
                    "选择分类值",
                    options=unique_vals[:50],
                    key='sidebar_cat_vals'
                )
            else:
                filters['cat_values'] = st.sidebar.multiselect(
                    "选择分类值",
                    options=unique_vals,
                    key='sidebar_cat_vals'
                )

    # ---- 数值范围筛选 ----
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        st.sidebar.markdown("#### 📐 数值范围筛选")
        num_col = st.sidebar.selectbox(
            "选择数值列",
            options=['无'] + numeric_cols,
            key='sidebar_num_col'
        )
        if num_col != '无':
            filters['num_col'] = num_col
            col_min = float(df[num_col].min())
            col_max = float(df[num_col].max())
            if col_min < col_max:
                filters['num_range'] = st.sidebar.slider(
                    f"{num_col} 范围",
                    min_value=col_min,
                    max_value=col_max,
                    value=(col_min, col_max),
                    key='sidebar_num_range'
                )

    # ---- 日期范围筛选 ----
    date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    if not date_cols:
        # 尝试推断日期列
        for col in df.columns:
            if col not in text_cols and col not in numeric_cols:
                try:
                    pd.to_datetime(df[col].dropna(), errors='raise')
                    date_cols.append(col)
                except (ValueError, TypeError):
                    pass

    if date_cols:
        st.sidebar.markdown("#### 📅 日期范围筛选")
        date_col = st.sidebar.selectbox(
            "选择日期列",
            options=['无'] + date_cols,
            key='sidebar_date_col'
        )
        if date_col != '无':
            filters['date_col'] = date_col
            try:
                date_series = pd.to_datetime(df[date_col], errors='coerce')
                min_date = date_series.min()
                max_date = date_series.max()
                if pd.notna(min_date) and pd.notna(max_date):
                    filters['date_range'] = st.sidebar.date_input(
                        "日期范围",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date(),
                        key='sidebar_date_range'
                    )
            except Exception:
                pass

    # ---- 应用筛选 ----
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 应用筛选", use_container_width=True, key='apply_filters'):
        st.session_state['sidebar_filters'] = filters
        st.sidebar.success("✅ 筛选已应用")

    if st.sidebar.button("🗑 清除筛选", use_container_width=True, key='clear_filters'):
        st.session_state['sidebar_filters'] = {}
        st.sidebar.info("筛选已清除")
        st.rerun()


# ==================== 主函数 ====================

def main():
    """主入口函数"""
    # 初始化会话状态
    init_session_state()

    # 注入样式
    inject_custom_css()

    # ---- 侧边栏 ----
    with st.sidebar:
        st.markdown("## ⚙️ 控制面板")
        st.markdown("---")

        # 主题切换
        render_theme_toggle()

        # 数据信息
        if st.session_state.get('df_cleaned') is not None:
            st.markdown("### 📦 当前数据")
            df = st.session_state['df_cleaned']
            st.caption(f"文件: {st.session_state.get('uploaded_filename', '未知')}")
            st.caption(f"行数: {len(df):,} | 列数: {len(df.columns)}")
            st.caption(f"内存: {df.memory_usage(deep=True).sum()/1024/1024:.2f} MB")

        # 交互式筛选
        render_sidebar_filters()

        # 底部信息
        st.sidebar.markdown("---")
        st.sidebar.caption("📊 数据处理可视化看板 v1.0")
        st.sidebar.caption("Built with Streamlit + Plotly")

    # ---- 主标题 ----
    st.markdown('<div class="main-title">📊 一站式数据处理可视化看板</div>', unsafe_allow_html=True)
    st.caption("上传数据 → 清洗处理 → 可视化分析，一站式完成")

    # ---- Tab 分栏 ----
    tab1, tab2, tab3 = st.tabs(["📤 首页上传", "🔧 数据预处理", "📊 分析看板"])

    with tab1:
        render_home()

    with tab2:
        render_preprocess()

    with tab3:
        render_dashboard()

    # ---- 页脚 ----
    st.markdown("---")
    st.markdown(
        '<div class="footer">'
        '📊 数据处理可视化看板 | Streamlit + Pandas + Plotly | '
        '【扩展预留】支持对接 MySQL / PostgreSQL / SQLite 数据库'
        '</div>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
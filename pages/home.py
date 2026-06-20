"""
首页上传模块 - 数据导入、拖拽上传、预览与字段类型识别
"""

import streamlit as st
import pandas as pd
from utils import load_data, get_field_types, init_session_state


def render_home():
    """渲染首页：数据上传与预览"""
    st.markdown("## 📤 数据导入中心")

    # 初始化会话状态
    init_session_state()

    # ---- 上传区域 ----
    st.markdown("### 上传数据文件")
    st.caption("支持 CSV（UTF-8/GBK 编码）、Excel（.xlsx/.xls）格式，数据集建议在万条以内以获得最佳体验")

    # 拖拽上传组件
    uploaded_file = st.file_uploader(
        "拖拽文件到此处或点击浏览",
        type=['csv', 'xlsx', 'xls'],
        help="支持 CSV 和 Excel 文件",
        key="home_uploader"
    )

    if uploaded_file is not None:
        # 检查是否是新文件
        if st.session_state.get('uploaded_filename') != uploaded_file.name:
            with st.spinner(f"正在加载 {uploaded_file.name} ..."):
                df, error = load_data(uploaded_file)

            if error:
                st.error(f"❌ {error}")
            else:
                st.session_state['df_raw'] = df
                st.session_state['df_cleaned'] = df.copy()
                st.session_state['uploaded_filename'] = uploaded_file.name
                st.session_state['field_types'] = get_field_types(df)
                st.session_state['cleaning_log'] = []
                st.success(f"✅ 成功加载 `{uploaded_file.name}`")

    # ---- 已加载数据展示 ----
    if st.session_state.get('df_raw') is not None:
        df = st.session_state['df_raw']

        st.markdown("---")
        st.markdown("### 📋 数据概览")

        # 基本信息卡片
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 总行数", f"{len(df):,}")
        with col2:
            st.metric("📝 总列数", len(df.columns))
        with col3:
            missing = df.isnull().sum().sum()
            st.metric("❓ 缺失值", missing, delta=f"{missing/len(df)*100:.1f}%" if len(df) > 0 else "0%")
        with col4:
            dup = df.duplicated().sum()
            st.metric("🔁 重复行", dup)

        # 数据预览（前100行）
        with st.expander("🔍 原始数据预览（前 100 行）", expanded=True):
            st.dataframe(
                df.head(100),
                use_container_width=True,
                height=350
            )

        # 字段类型识别
        with st.expander("🏷 字段类型识别结果", expanded=False):
            field_types = st.session_state.get('field_types', {})
            if field_types:
                type_data = []
                for col, ftype in field_types.items():
                    dtype = df[col].dtype
                    n_unique = df[col].nunique()
                    n_missing = df[col].isnull().sum()
                    type_data.append({
                        '列名': col,
                        '推断类型': ftype,
                        'Pandas类型': str(dtype),
                        '唯一值数': n_unique,
                        '缺失值数': n_missing,
                        '缺失率': f"{n_missing/len(df)*100:.1f}%"
                    })
                type_df = pd.DataFrame(type_data)
                st.dataframe(type_df, use_container_width=True, hide_index=True)

                # 用颜色标签区分类型
                st.markdown("**类型分布:**")
                cols = st.columns(len(field_types) if len(field_types) <= 6 else 6)
                for i, (col, ftype) in enumerate(field_types.items()):
                    color = {
                        '数值': 'blue',
                        '日期': 'green',
                        '文本': 'orange'
                    }.get(ftype, 'gray')
                    with cols[i % 6]:
                        st.markdown(
                            f"<span style='background:{color}20;padding:4px 10px;border-radius:12px;"
                            f"border:1px solid {color};font-size:13px;'>{ftype}</span> **{col}**",
                            unsafe_allow_html=True
                        )

        # 统计摘要
        with st.expander("📈 数值列统计摘要", expanded=False):
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                st.dataframe(
                    df[numeric_cols].describe(),
                    use_container_width=True
                )
            else:
                st.info("未检测到数值类型列")

        # 温馨提示
        st.markdown("---")
        st.info("👉 数据已就绪，请前往 **数据预处理** 页面进行清洗，再到 **分析看板** 查看可视化图表")


if __name__ == "__main__":
    render_home()
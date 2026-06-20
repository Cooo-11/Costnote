"""
数据预处理模块 - 缺失值、去重、异常值、类型转换、自定义计算字段
"""

import streamlit as st
import pandas as pd
from data_processor import (
    fill_missing_values,
    remove_duplicates,
    filter_outliers,
    add_custom_field,
    convert_column_type,
    get_data_summary
)
from utils import init_session_state, get_field_types


def render_preprocess():
    """渲染数据预处理页面"""
    st.markdown("## 🔧 数据预处理工作台")

    init_session_state()

    if st.session_state.get('df_raw') is None:
        st.warning("⚠ 请先在 **首页** 上传数据文件")
        st.info("👈 前往首页上传 CSV 或 Excel 文件")
        return

    df = st.session_state['df_cleaned'].copy()

    # ---- 操作概览 ----
    summary = get_data_summary(df)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("行数", f"{summary['rows']:,}")
    with col2:
        st.metric("列数", summary['cols'])
    with col3:
        st.metric("缺失值", summary['missing'])
    with col4:
        st.metric("重复行", summary['duplicates'])
    with col5:
        st.metric("内存", f"{summary['memory']} MB")

    st.markdown("---")

    # ---- 清洗操作 ----
    # 使用两列布局
    left_col, right_col = st.columns(2)

    # ===== 左列：缺失值 + 去重 + 异常值 =====
    with left_col:
        # 1. 缺失值处理
        st.markdown("### ❓ 缺失值处理")
        missing_strategy = st.selectbox(
            "填充策略",
            ['自动', '指定值', '前向填充', '后向填充', '删除'],
            key='missing_strategy',
            help="自动: 数值用中位数, 文本用众数"
        )

        fill_value = None
        if missing_strategy == '指定值':
            fill_value = st.text_input("填充值", value="0", key='fill_value')

        if st.button("🔄 执行缺失值处理", key='btn_missing', use_container_width=True):
            with st.spinner("正在处理缺失值..."):
                df, log = fill_missing_values(df, strategy=missing_strategy, fill_value=fill_value)
                st.session_state['df_cleaned'] = df
                st.session_state['cleaning_log'] = st.session_state.get('cleaning_log', []) + log
                st.rerun()

        st.markdown("---")

        # 2. 去重
        st.markdown("### 🔁 去重处理")
        dup_cols = st.multiselect(
            "基于哪些列判断重复（留空=全部列）",
            options=df.columns.tolist(),
            key='dup_cols'
        )

        if st.button("🔄 执行去重", key='btn_dedup', use_container_width=True):
            with st.spinner("正在去重..."):
                subset = dup_cols if dup_cols else None
                df, log = remove_duplicates(df, subset=subset)
                st.session_state['df_cleaned'] = df
                st.session_state['cleaning_log'] = st.session_state.get('cleaning_log', []) + log
                st.rerun()

        st.markdown("---")

        # 3. 异常值过滤
        st.markdown("### 🔍 异常值过滤")
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        if numeric_cols:
            outlier_method = st.selectbox(
                "检测方法",
                ['IQR', 'Z-Score'],
                key='outlier_method',
                help="IQR: 四分位距法; Z-Score: 标准差法"
            )
            outlier_threshold = st.slider(
                "阈值",
                min_value=0.5, max_value=5.0, value=1.5, step=0.5,
                key='outlier_threshold',
                help="IQR: 通常1.5; Z-Score: 通常3.0"
            )
            outlier_cols = st.multiselect(
                "检查哪些列（留空=全部数值列）",
                options=numeric_cols,
                key='outlier_cols'
            )

            if st.button("🔄 执行异常值过滤", key='btn_outlier', use_container_width=True):
                with st.spinner("正在过滤异常值..."):
                    df, log = filter_outliers(
                        df,
                        numeric_cols=outlier_cols if outlier_cols else None,
                        method=outlier_method,
                        threshold=outlier_threshold
                    )
                    st.session_state['df_cleaned'] = df
                    st.session_state['cleaning_log'] = st.session_state.get('cleaning_log', []) + log
                    st.rerun()
        else:
            st.info("未检测到数值列")

    # ===== 右列：类型转换 + 计算字段 =====
    with right_col:
        # 4. 列类型转换
        st.markdown("### 🔄 列类型转换")
        if not df.columns.empty:
            convert_col = st.selectbox("选择列", options=df.columns.tolist(), key='convert_col')
            convert_type = st.selectbox(
                "目标类型",
                ['数值', '文本', '日期'],
                key='convert_type'
            )

            if st.button("🔄 执行类型转换", key='btn_convert', use_container_width=True):
                with st.spinner(f"正在转换 [{convert_col}] ..."):
                    df, log = convert_column_type(df, convert_col, convert_type)
                    st.session_state['df_cleaned'] = df
                    st.session_state['field_types'] = get_field_types(df)
                    st.session_state['cleaning_log'] = st.session_state.get('cleaning_log', []) + log
                    st.rerun()
        else:
            st.info("数据为空")

        st.markdown("---")

        # 5. 自定义计算字段
        st.markdown("### ✨ 自定义计算字段")
        new_col_name = st.text_input("新列名", key='new_col_name', placeholder="例如: 总金额")
        expression = st.text_input(
            "计算表达式",
            key='expression',
            placeholder="例如: 单价 * 数量",
            help="使用列名作为变量，支持算术运算。例如: col_a + col_b * 2"
        )

        if st.button("✨ 添加计算字段", key='btn_calc', use_container_width=True):
            if new_col_name and expression:
                with st.spinner("正在计算..."):
                    df, log = add_custom_field(df, expression, new_col_name)
                    st.session_state['df_cleaned'] = df
                    st.session_state['cleaning_log'] = st.session_state.get('cleaning_log', []) + log
                    st.rerun()
            else:
                st.warning("请输入新列名和计算表达式")

    st.markdown("---")

    # ---- 清洗日志 ----
    if st.session_state.get('cleaning_log'):
        with st.expander("📝 清洗操作日志", expanded=True):
            for log_entry in st.session_state['cleaning_log']:
                if '✅' in log_entry:
                    st.success(log_entry)
                elif '❌' in log_entry:
                    st.error(log_entry)
                elif '⚠' in log_entry:
                    st.warning(log_entry)
                else:
                    st.info(log_entry)

    # ---- 清洗后数据预览 ----
    st.markdown("### 📋 清洗后数据预览")
    st.dataframe(
        st.session_state['df_cleaned'].head(100),
        use_container_width=True,
        height=300
    )

    # ---- 重置按钮 ----
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 重置为原始数据", key='btn_reset', use_container_width=True):
            st.session_state['df_cleaned'] = st.session_state['df_raw'].copy()
            st.session_state['cleaning_log'] = []
            st.rerun()
    with col_b:
        if st.session_state.get('df_cleaned') is not None:
            st.download_button(
                label="📥 导出清洗后数据 (CSV)",
                data=st.session_state['df_cleaned'].to_csv(index=False, encoding='utf-8-sig'),
                file_name=f"cleaned_data_{st.session_state.get('uploaded_filename', 'output')}.csv",
                mime="text/csv",
                use_container_width=True
            )


if __name__ == "__main__":
    render_preprocess()
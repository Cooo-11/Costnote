"""
数据清洗模块 - 缺失值填充、去重、异常值过滤、自定义计算字段
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional, List, Dict, Any


def fill_missing_values(
    df: pd.DataFrame,
    strategy: str = '自动',
    fill_value: Any = None,
    custom_map: Dict[str, Any] = None
) -> pd.DataFrame:
    """
    缺失值填充

    Args:
        df:         输入 DataFrame
        strategy:   填充策略 '自动' / '指定值' / '前向填充' / '后向填充' / '删除'
        fill_value: 当 strategy='指定值' 时的填充值
        custom_map: 按列自定义填充值 {列名: 填充值}

    Returns:
        处理后的 DataFrame 及日志
    """
    df = df.copy()
    log = []

    # 记录填充前缺失数
    before = df.isnull().sum().sum()
    if before == 0:
        return df, ["✅ 数据无缺失值，无需填充"]

    if strategy == '删除':
        before_rows = len(df)
        df = df.dropna()
        after_rows = len(df)
        log.append(f"🗑 删除含缺失值的行: {before_rows} → {after_rows} 行 (移除 {before_rows - after_rows} 行)")

    elif strategy == '自动':
        for col in df.columns:
            if df[col].isnull().sum() == 0:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                # 数值列用中位数填充
                median_val = df[col].median()
                if pd.isna(median_val):
                    median_val = 0
                n = df[col].isnull().sum()
                df[col] = df[col].fillna(median_val)
                log.append(f"🔧 [{col}] 数值列 - 用中位数 {median_val:.2f} 填充 {n} 个缺失值")
            else:
                # 文本列用众数填充
                mode_vals = df[col].mode()
                fill = mode_vals[0] if len(mode_vals) > 0 else '未知'
                n = df[col].isnull().sum()
                df[col] = df[col].fillna(fill)
                log.append(f"🔧 [{col}] 文本列 - 用众数 '{fill}' 填充 {n} 个缺失值")

    elif strategy == '指定值':
        for col in df.columns:
            n = df[col].isnull().sum()
            if n == 0:
                continue
            val = fill_value if fill_value is not None else '未知'
            df[col] = df[col].fillna(val)
            log.append(f"🔧 [{col}] 用指定值 '{val}' 填充 {n} 个缺失值")

    elif strategy == '前向填充':
        n_before = df.isnull().sum().sum()
        df = df.fillna(method='ffill')
        n_after = df.isnull().sum().sum()
        log.append(f"🔧 前向填充: 剩余 {n_after} 个缺失值 (填充了 {n_before - n_after} 个)")

    elif strategy == '后向填充':
        n_before = df.isnull().sum().sum()
        df = df.fillna(method='bfill')
        n_after = df.isnull().sum().sum()
        log.append(f"🔧 后向填充: 剩余 {n_after} 个缺失值 (填充了 {n_before - n_after} 个)")

    # 自定义列填充
    if custom_map:
        for col, val in custom_map.items():
            if col in df.columns:
                n = df[col].isnull().sum()
                if n > 0:
                    df[col] = df[col].fillna(val)
                    log.append(f"🔧 [{col}] 自定义填充 '{val}' → {n} 个缺失值")

    after = df.isnull().sum().sum()
    if before > 0 and after == 0:
        log.append("✅ 所有缺失值已填充完毕")
    elif before > 0:
        log.append(f"⚠ 仍有 {after} 个缺失值未处理")

    return df, log


def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
    """
    去重处理

    Args:
        df:     输入 DataFrame
        subset: 基于哪些列判断重复，None 表示全部列

    Returns:
        (去重后DataFrame, 日志)
    """
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep='first')
    after = len(df)
    removed = before - after
    log = []
    if removed > 0:
        scope = '全部列' if subset is None else ', '.join(subset)
        log.append(f"🗑 去重: 基于 [{scope}] 移除 {removed} 条重复记录")
    else:
        log.append("✅ 未发现重复记录")
    return df, log


def filter_outliers(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
    method: str = 'IQR',
    threshold: float = 1.5
) -> pd.DataFrame:
    """
    异常值过滤

    Args:
        df:           输入 DataFrame
        numeric_cols: 要检查的数值列列表，None 为所有数值列
        method:       方法 'IQR' (四分位距) 或 'Z-Score' (标准差)
        threshold:    IQR 倍数 / Z-Score 阈值

    Returns:
        (过滤后DataFrame, 日志)
    """
    df = df.copy()
    log = []

    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not numeric_cols:
        return df, ["⚠ 未找到数值列，跳过异常值过滤"]

    before = len(df)
    total_removed = 0

    if method == 'IQR':
        mask = pd.Series(True, index=df.index)
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - threshold * IQR
            upper = Q3 + threshold * IQR
            col_mask = (df[col] >= lower) & (df[col] <= upper)
            n_outliers = (~col_mask).sum()
            if n_outliers > 0:
                log.append(f"🔍 [{col}] IQR 法: 范围 [{lower:.2f}, {upper:.2f}], 过滤 {n_outliers} 个异常值")
            mask = mask & col_mask
        df = df[mask]
        total_removed = before - len(df)

    elif method == 'Z-Score':
        mask = pd.Series(True, index=df.index)
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            if std == 0:
                continue
            z_scores = np.abs((df[col] - mean) / std)
            col_mask = z_scores <= threshold
            n_outliers = (~col_mask).sum()
            if n_outliers > 0:
                log.append(f"🔍 [{col}] Z-Score 法: 阈值 {threshold}, 过滤 {n_outliers} 个异常值")
            mask = mask & col_mask
        df = df[mask]
        total_removed = before - len(df)

    if total_removed > 0:
        log.append(f"🗑 异常值过滤: 共移除 {total_removed} 行 ({before} → {len(df)})")
    else:
        log.append("✅ 未发现异常值")

    return df, log


def add_custom_field(df: pd.DataFrame, expression: str, new_col_name: str) -> pd.DataFrame:
    """
    自定义计算字段

    Args:
        df:          输入 DataFrame
        expression:  Python 表达式，使用列名作为变量，例如: "col_a + col_b * 2"
        new_col_name: 新列名

    Returns:
        (添加字段后DataFrame, 日志)
    """
    df = df.copy()
    log = []

    # 构建安全的 eval 环境
    # 将 DataFrame 列转为可用于 eval 的变量
    local_vars = {col: df[col].values for col in df.columns}
    local_vars['np'] = np

    try:
        result = eval(expression, {"__builtins__": {}}, local_vars)
        df[new_col_name] = result
        log.append(f"✨ 新增计算字段 [{new_col_name}] = {expression}")
    except Exception as e:
        log.append(f"❌ 计算字段 [{new_col_name}] 创建失败: {str(e)}")

    return df, log


def convert_column_type(df: pd.DataFrame, col: str, target_type: str) -> pd.DataFrame:
    """
    列类型转换

    Args:
        df:          输入 DataFrame
        col:         目标列名
        target_type: 目标类型 '数值' / '文本' / '日期'

    Returns:
        (转换后DataFrame, 日志)
    """
    df = df.copy()
    log = []

    type_map = {
        '数值': 'numeric',
        '文本': 'str',
        '日期': 'datetime',
    }

    target = type_map.get(target_type)
    if not target:
        return df, [f"❌ 不支持的目标类型: {target_type}"]

    try:
        if target == 'numeric':
            df[col] = pd.to_numeric(df[col], errors='coerce')
            log.append(f"🔄 [{col}] 转换为数值类型")
        elif target == 'str':
            df[col] = df[col].astype(str)
            log.append(f"🔄 [{col}] 转换为文本类型")
        elif target == 'datetime':
            df[col] = pd.to_datetime(df[col], errors='coerce')
            log.append(f"🔄 [{col}] 转换为日期类型")
    except Exception as e:
        log.append(f"❌ [{col}] 类型转换失败: {str(e)}")

    return df, log


def get_data_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    获取数据摘要信息，用于显示在预处理面板

    Returns:
        {
            'rows': 行数,
            'cols': 列数,
            'missing': 缺失值总数,
            'duplicates': 重复行数,
            'memory': 内存占用(MB),
            'numeric_cols': 数值列列表,
            'text_cols': 文本列列表,
            'date_cols': 日期列列表,
        }
    """
    return {
        'rows': len(df),
        'cols': len(df.columns),
        'missing': int(df.isnull().sum().sum()),
        'duplicates': int(df.duplicated().sum()),
        'memory': round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
        'numeric_cols': df.select_dtypes(include=[np.number]).columns.tolist(),
        'text_cols': df.select_dtypes(include=['object']).columns.tolist(),
        'date_cols': df.select_dtypes(include=['datetime64']).columns.tolist(),
    }
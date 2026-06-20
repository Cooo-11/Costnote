"""
工具函数模块 - 数据加载、导出、缓存、异常处理
可扩展对接数据库（MySQL / PostgreSQL / SQLite）
"""

import pandas as pd
import io
import base64
import streamlit as st
from typing import Optional, Tuple, Any
from datetime import datetime


# ==================== 数据加载 ====================

def load_data(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    统一加载 CSV / Excel 文件，返回 (DataFrame, 错误信息)

    【扩展提示】如需对接数据库，可在此函数内添加：
        if db_config:
            from sqlalchemy import create_engine
            engine = create_engine(db_config['url'])
            return pd.read_sql("SELECT * FROM table_name", engine), None
    """
    try:
        filename = file.name.lower()
        if filename.endswith('.csv'):
            # 尝试常见编码
            for enc in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']:
                try:
                    df = pd.read_csv(file, encoding=enc)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    file.seek(0)
                    continue
            else:
                df = pd.read_csv(file, encoding='utf-8', errors='ignore')
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file, engine='openpyxl')
        else:
            return None, f"不支持的文件格式: {filename}，请上传 CSV 或 Excel 文件"

        if df.empty:
            return None, "文件为空，请上传包含数据的文件"

        return df, None
    except Exception as e:
        return None, f"文件加载失败: {str(e)}"


def get_field_types(df: pd.DataFrame) -> dict:
    """
    识别 DataFrame 中各字段类型，返回 {列名: 类型标签}
    分类：数值、日期、文本
    """
    type_map = {}
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_numeric_dtype(dtype):
            type_map[col] = '数值'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            type_map[col] = '日期'
        else:
            # 尝试推断是否为日期
            try:
                s = pd.to_datetime(df[col].dropna(), errors='raise')
                if len(s) > 0:
                    type_map[col] = '日期'
                    continue
            except (ValueError, TypeError):
                pass
            type_map[col] = '文本'

    return type_map


# ==================== 导出工具 ====================

def get_csv_download_link(df: pd.DataFrame, filename: str = "cleaned_data.csv") -> str:
    """生成 CSV 下载链接"""
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode('utf-8-sig')).decode()
    return (f'<a href="data:file/csv;base64,{b64}" download="{filename}">'
            f'📥 点击下载 CSV 文件</a>')


def get_excel_download_link(df: pd.DataFrame, filename: str = "cleaned_data.xlsx") -> str:
    """生成 Excel 下载链接"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='数据')
    b64 = base64.b64encode(output.getvalue()).decode()
    return (f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" '
            f'download="{filename}">📥 点击下载 Excel 文件</a>')


# ==================== 会话状态管理 ====================

def init_session_state():
    """初始化 Streamlit 会话状态（用于跨页面共享数据）"""
    defaults = {
        'df_raw': None,          # 原始数据
        'df_cleaned': None,      # 清洗后数据
        'uploaded_filename': None,
        'field_types': {},       # 字段类型识别结果
        'cleaning_log': [],      # 清洗操作日志
        # 【扩展】预留数据库配置
        'db_config': None,       # 后续对接数据库时使用
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def safe_call(func, *args, **kwargs):
    """
    安全调用包装器，捕获异常并返回友好提示

    【扩展提示】可在此加入日志记录：
        import logging
        logging.error(f"操作失败: {e}", exc_info=True)
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        st.error(f"操作失败: {str(e)}")
        return None


# ==================== 图表导出辅助 ====================

def plotly_to_image_bytes(fig) -> bytes:
    """将 Plotly 图表转为图片字节（用于下载）"""
    try:
        import plotly.io as pio
        return pio.to_image(fig, format='png', scale=2)
    except Exception:
        # 如果 kaleido 未安装，回退到 HTML 方式
        return None


def get_fig_download_button(fig, label: str = "📷 下载图表", filename: str = "chart.png"):
    """生成 Plotly 图表下载按钮"""
    img_bytes = plotly_to_image_bytes(fig)
    if img_bytes:
        b64 = base64.b64encode(img_bytes).decode()
        href = f'<a href="data:image/png;base64,{b64}" download="{filename}">{label}</a>'
        return href
    else:
        return None


# ==================== 时间戳 ====================

def get_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
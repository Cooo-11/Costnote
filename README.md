# 一站式数据处理可视化看板

基于 **Python Streamlit** 构建的交互式数据清洗与可视化分析平台，支持 CSV/Excel 拖拽上传、数据预处理、多图表可视化分析。

## 技术栈

| 技术 | 用途 |
|------|------|
| Streamlit | Web 框架 & 交互界面 |
| Pandas | 数据处理核心 |
| NumPy | 数值计算 |
| Plotly | 交互式图表 |
| openpyxl | Excel 文件读写 |

## 项目结构

```
记账本/
├── app.py                  # 主入口（Tab分栏、侧边栏筛选、主题切换）
├── utils.py                # 工具函数（数据加载、导出、异常处理）
├── data_processor.py       # 数据清洗模块（缺失值、去重、异常值、计算字段）
├── pages/
│   ├── __init__.py         # 包初始化
│   ├── home.py             # 首页上传（拖拽上传、数据预览、字段类型识别）
│   ├── preprocess.py       # 数据预处理（清洗操作工作台）
│   └── dashboard.py        # 分析看板（KPI卡片、图表、明细表格）
├── requirements.txt        # 依赖清单
└── README.md               # 本文件
```

## 功能特性

### 首页上传
- 支持 CSV / Excel（.xlsx/.xls）拖拽上传
- 自动识别字段类型（数值/日期/文本）
- 原始数据预览 + 统计摘要

### 数据预处理
- **缺失值填充**: 自动（中位数/众数）、指定值、前向/后向填充、删除
- **去重处理**: 支持指定列去重
- **异常值过滤**: IQR 四分位距法 / Z-Score 标准差法
- **列类型转换**: 数值 ↔ 文本 ↔ 日期
- **自定义计算字段**: 支持表达式计算新列
- 清洗操作日志实时记录

### 分析看板
- **KPI 指标卡片**: 顶部展示关键统计指标
- **交互式图表**: 折线图、柱状图、饼图、散点图、热力图
- **分页明细表格**: 支持搜索检索
- **数据导出**: CSV / Excel 下载
- **图表下载**: 安装 kaleido 后支持导出 PNG

### 其他亮点
- 侧边栏交互式筛选（分类/数值范围/日期范围），实时联动全部图表
- 深浅主题切换
- 加载动画与友好异常提示
- 适配万条以内数据集
- 代码注释完整，预留对接数据库的扩展注释

## 快速启动

### 1. 环境要求

- Python 3.8 或以上版本
- pip 包管理器

### 2. 安装依赖

```bash
cd 记账本
pip install -r requirements.txt
```

### 3. 启动应用

```bash
streamlit run app.py
```

启动后浏览器会自动打开 `http://localhost:8501`，即可开始使用。

### 4. 可选依赖（图表下载为图片）

```bash
pip install kaleido
```

## 使用教程

### 第一步：上传数据

1. 打开应用后，默认进入「首页上传」Tab
2. 点击上传区域或拖拽 CSV/Excel 文件到页面
3. 系统自动加载并展示数据预览与字段类型识别结果

### 第二步：数据清洗

1. 切换到「数据预处理」Tab
2. 根据需要选择清洗操作：
   - 选择缺失值填充策略，点击执行
   - 选择去重列，点击执行
   - 配置异常值过滤参数，点击执行
   - 添加自定义计算字段
3. 所有操作记录在日志区域，可随时查看
4. 如有误操作，可点击「重置为原始数据」

### 第三步：可视化分析

1. 切换到「分析看板」Tab
2. 顶部自动展示 KPI 指标卡片
3. 在图表配置区选择 X/Y 轴列
4. 切换不同 Tab 查看折线图、柱状图、饼图、散点图、热力图
5. 在侧边栏设置筛选条件，图表和数据实时联动
6. 底部可导出清洗后的数据（CSV/Excel）

## 扩展建议

### 对接数据库

代码中已预留数据库扩展注释，如需对接数据库：

1. 安装数据库驱动：`pip install sqlalchemy pymysql psycopg2`
2. 在 `utils.py` 的 `load_data()` 函数中添加数据库连接逻辑
3. 在 `app.py` 的侧边栏添加数据库配置表单

示例：
```python
from sqlalchemy import create_engine
engine = create_engine('mysql+pymysql://user:pass@host:port/db')
df = pd.read_sql("SELECT * FROM table_name", engine)
```

### 部署到服务器

```bash
# 安装 Streamlit
pip install streamlit

# 后台运行
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

## 常见问题

**Q: 上传文件后报错"不支持的文件格式"？**
A: 目前仅支持 .csv、.xlsx、.xls 格式，请确认文件后缀正确。

**Q: 中文 CSV 乱码？**
A: 系统会自动尝试 UTF-8、GBK 等编码，如仍有问题，请将 CSV 另存为 UTF-8 编码。

**Q: 图表下载按钮不显示？**
A: 需安装 kaleido：`pip install kaleido`，安装后重启应用即可。

**Q: 数据量大时卡顿？**
A: 建议数据集控制在万条以内。如需处理更大数据，可考虑对接数据库或使用 Polars 替代 Pandas。
# 日语作文素材自动搜集系统

## 项目简介

本项目是一个日语作文素材自动搜集网页应用，能够自动抓取指定网站中的作文，并整理成统一格式，供用户浏览、筛选、下载 Word 文档。

## 技术栈

- **后端**: Python 3.x + Flask
- **数据库**: SQLite
- **爬虫**: requests + BeautifulSoup4
- **PDF解析**: pdfplumber
- **OCR识别**: Tesseract + pytesseract
- **Word导出**: python-docx
- **前端**: HTML + Vanilla JS + CSS

## 快速开始

### 环境要求

- Python 3.8+
- Git

### 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/tianjin-ren/skubunn.git
cd skubunn
```

2. 创建虚拟环境并安装依赖：
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. 运行应用：
```bash
python main.py
```

4. 浏览器将自动打开 http://localhost:5000

## 目录结构

```
skubunn/
├── main.py              # 启动入口
├── config.py            # 全局配置
├── requirements.txt     # 依赖列表
├── README.md            # 项目说明
├── .gitignore           # Git忽略配置
├── modules/             # 核心模块
│   ├── __init__.py
│   ├── crawler.py       # 网站抓取
│   ├── html_parser.py   # HTML解析
│   ├── pdf_parser.py    # PDF解析
│   ├── ocr_engine.py    # OCR识别
│   ├── formatter.py     # 数据整理
│   ├── exporter.py      # Word导出
│   └── cache.py         # 数据缓存
├── templates/           # 前端页面
│   └── index.html
├── static/              # 静态资源
│   ├── css/
│   └── js/
└── data/                # 数据目录（运行时生成）
    └── essays.db
```

## 模块说明

| 模块 | 功能 |
|------|------|
| crawler | 网站抓取引擎，支持HTTP请求和动态页面 |
| html_parser | HTML页面解析，提取作文内容 |
| pdf_parser | PDF文件解析，提取文本内容 |
| ocr_engine | OCR识别，处理图片中的文字 |
| formatter | 数据清洗和格式化 |
| exporter | Word文档导出 |
| cache | SQLite数据库操作 |

## 配置说明

在 `config.py` 中配置目标网站信息，新增网站只需添加配置即可。

## 许可证

MIT License

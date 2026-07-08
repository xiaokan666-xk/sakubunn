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
git clone https://github.com/xiaokan666-xk/sakubunn.git
cd sakubunn
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
sakubunn/
├── main.py                  # 启动入口
├── config.py                # 全局配置
├── requirements.txt         # 依赖列表
├── README.md                # 项目说明
├── .gitignore               # Git忽略配置
├── modules/                 # 核心模块
│   ├── __init__.py
│   ├── spider_base.py       # Spider基类
│   ├── spider_manager.py    # Spider管理器
│   ├── crawler.py           # 通用抓取工具
│   ├── html_parser.py       # HTML解析
│   ├── pdf_parser.py        # PDF解析
│   ├── ocr_engine.py        # OCR识别
│   ├── formatter.py         # 数据整理
│   ├── exporter.py          # Word导出
│   └── cache.py             # 数据缓存
├── spiders/                 # 网站Spider（每网站一个文件）
│   ├── __init__.py
│   ├── netnfu.py            # 日本福祉大学
│   ├── ja_kyosai.py         # JA共済
│   ├── anshin.py            # あんしん財団
│   ├── tsurezure.py         # 徒然草
│   └── oishii.py            # おいしい記憶
├── templates/               # 前端页面
│   └── index.html
├── static/                  # 静态资源
│   ├── css/
│   └── js/
└── data/                    # 数据目录（运行时生成）
    └── essays.db
```

## 统一数据结构

每篇作文统一整理为以下 JSON 结构：

```json
{
  "title": "作文标题",
  "author": "作者姓名",
  "school": "学校（若存在）",
  "body": "正文内容",
  "source": "来源网址",
  "date": "发布时间（若存在）",
  "site": "网站名称"
}
```

## Spider 架构

### 设计原则

- 每个网站一个独立 Spider 类（独立文件）
- 不使用 AI 自动学习网页结构
- 抓取规则全部在 Spider 内显式配置
- 新增网站只需新增 Spider 文件，Spider Manager 自动加载
- 网站改版后只需修改对应 Spider

### 新增网站步骤

1. 在 `spiders/` 目录下新建文件 `xxx.py`
2. 继承 `SpiderBase` 类
3. 设置类属性 `site_name` 和 `site_url`
4. 实现以下方法：
   - `get_essay_list_urls()` - 返回列表页URL列表
   - `parse_list_page(html, list_url)` - 解析列表页，提取作文链接
   - `parse_essay_page(html, essay_url)` - 解析作文页，提取7个字段
5. `spider_manager.py` 会在启动时自动发现并加载

### Spider 示例

```python
from modules.spider_base import SpiderBase

class MySpider(SpiderBase):
    site_name = "示例网站"
    site_url = "https://example.com/sakubun"
    
    def get_essay_list_urls(self):
        return ["https://example.com/list"]
    
    def parse_list_page(self, html, list_url):
        # 解析HTML，提取作文链接列表
        return [{'title': '...', 'url': '...'}]
    
    def parse_essay_page(self, html, essay_url):
        # 解析HTML，提取7个字段
        return self.make_essay(
            title='...',
            author='...',
            school='...',
            body='...',
            source=essay_url,
            date='...'
        )
```

## 模块说明

| 模块 | 功能 |
|------|------|
| spider_base | Spider基类，定义抓取接口 |
| spider_manager | 自动加载/管理所有Spider |
| crawler | 通用HTTP抓取工具 |
| html_parser | HTML解析工具 |
| pdf_parser | PDF文件解析 |
| ocr_engine | OCR识别引擎 |
| formatter | 数据清洗/格式化 |
| exporter | Word文档导出 |
| cache | SQLite数据库操作 |

## 许可证

MIT License

# 日语作文素材自动搜集系统

## 项目简介

本项目是一个日语作文素材自动搜集网页应用，能够自动抓取指定网站中的作文，并整理成统一格式，供用户浏览、筛选、下载 Word 文档。

## 技术栈

- **后端**: Python 3.x + Flask
- **数据库**: SQLite
- **HTML抓取**: requests + BeautifulSoup4 (主) / Playwright (备选)
- **PDF解析**: pdfplumber (文字层) / PaddleOCR (扫描版)
- **OCR识别**: PaddleOCR (内置日文模型)
- **纵排转换**: 内置日文纵排→横排自动转换
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
├── main.py                  # Flask启动入口
├── config.py                # 全局配置
├── requirements.txt         # 依赖列表
├── README.md                # 项目说明
├── .gitignore               # Git忽略配置
├── work-notes/              # 工作备注
├── modules/                 # 后端核心模块
│   ├── __init__.py
│   ├── spider_base.py       # Spider基类（自动判断抓取类型）
│   ├── spider_manager.py    # Spider管理器
│   ├── playwright_fetcher.py # Playwright备选抓取
│   ├── paddle_ocr.py        # PaddleOCR日文识别
│   ├── pdf_smart_parser.py  # PDF智能解析（文字层+OCR）
│   ├── vertical_text_converter.py  # 纵排转横排
│   ├── error_tracker.py     # 抓取错误追踪
│   ├── crawler.py           # 通用抓取工具
│   ├── html_parser.py       # HTML解析
│   ├── pdf_parser.py        # PDF基础解析
│   ├── ocr_engine.py        # OCR识别（Tesseract备选）
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
│   │   └── style.css
│   └── js/
│       └── app.js
└── data/                    # 数据目录（运行时生成）
    ├── essays.db
    ├── crawl_errors.json
    ├── crawl_report_*.json  # 抓取日志报告
    └── temp/
```

## 日志系统

### 抓取报告

每次抓取完成后自动生成详细报告：

```
抓取报告 - 2026-07-08 15:30:00
========================================

✔ 网站A
新增 12 篇作文
HTML解析成功
————————————

✔ 网站B
PDF解析成功
OCR完成
新增 5 篇
————————————

✘ 网站C
抓取失败
403 Forbidden
————————————

总计：2 个网站成功，1 个网站失败
新增作文：17 篇
耗时：45秒
```

### 报告存储

- 报告保存到 `data/reports/` 目录
- JSON格式，包含完整抓取详情
- API: `GET /api/reports` - 获取最近10条报告
- API: `GET /api/report/<filename>` - 获取指定报告详情

## 扩展能力

### 低耦合设计

项目采用模块化设计，各模块独立维护：

- **SpiderManager** 自动发现并加载Spider
- **CacheManager** 统一数据存储，不依赖具体Spider
- **Exporter** 统一导出格式，不依赖具体网站
- **ErrorTracker** 统一错误处理，不依赖具体Spider

### 新增网站

**只需一步：新建Spider文件**

```bash
# 1. 复制模板
cp spiders/_example_template.py spiders/new_site.py

# 2. 编辑Spider（填写site_name、site_url、解析规则）
# 3. 运行程序，SpiderManager自动加载
```

**无需修改任何其他模块！**

### 网站改版维护

当网站HTML结构变化时：

1. 打开对应Spider文件（如 `spiders/new_site.py`）
2. 修改CSS选择器或解析逻辑
3. 其他网站不受影响

### Site Config + Spider分离

每个网站拥有独立的配置和规则：

- **site_name/site_url**: 网站基本信息
- **list_urls**: 列表页URL配置
- **parse_list_page**: 列页解析规则（CSS选择器）
- **parse_essay_page**: 详情页解析规则（CSS选择器）

程序**不依赖固定HTML结构**或**AI临时推理**，所有规则显式配置在Spider文件中。

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

## 抓取类型自动判断

Spider会自动判断目标URL采用哪种抓取方式：

| 类型 | 说明 | 触发条件 |
|------|------|---------|
| **A** HTML单页 | requests + BS4 | 普通HTML页面 |
| **B** HTML多层遍历 | requests + BS4 | 列表页含子页面链接 |
| **C** PDF文字层 | pdfplumber | URL以.pdf结尾且有文字层 |
| **D** PDF扫描版 | PaddleOCR | URL以.pdf结尾且无文字层 |

### Playwright备选机制

- 默认使用 `requests` 抓取（更快、更轻量）
- 仅在以下情况自动启用 Playwright：
  - HTML 内容过短（< 500 字节）
  - 抓取失败（超时/网络错误）
  - 文本内容过少（< 100 字符）
- 不对所有网站启用 Playwright

### PaddleOCR 内置

- 首选 OCR 引擎，日文支持优秀
- 首次使用自动下载模型（约 100MB）
- 无需用户额外安装系统级 OCR 软件
- 备选：Tesseract（`ocr_engine.py`）

### PDF 智能处理

- **文字层检测**: 自动判断PDF是否含文字
- **有文字层**: 直接用 `pdfplumber` 提取
- **无文字层**: 自动用 PaddleOCR 扫描识别
- **多页文档**: 自动识别每页，提取最长正文块
- **特殊页面**: 自动跳过封面、目录、空白页

### 纵排转横排

- 自动检测 HTML/CSS 中的 `writing-mode: vertical` 标记
- 自动检测 PDF/OCR 文本的纵排特征
- 转换为符合中文阅读习惯的横排顺序

## 抓取失败处理

### 失败信息展示

抓取失败时，网页会清晰显示：
- **网站名称** - 哪个网站出问题
- **网站地址** - 完整URL
- **错误原因** - 具体失败类型和详情

### 网站更新检测

当网站改版导致规则失效时，系统会自动判断并提示：

> "该网站页面可能已更新，请检查抓取规则。"

### 不依赖AI

- 所有抓取规则显式维护在 `spiders/` 目录下
- 网站改版后只需修改对应 Spider 文件
- 无需 AI 长期记忆或自动学习网页结构

### 错误追踪

- 错误记录保存到 `data/crawl_errors.json`
- 支持按网站筛选、查询历史错误
- API: `GET /api/failed_sites` - 获取所有失败网站
- API: `GET /api/site_status` - 获取所有网站状态

## 模块说明

| 模块 | 功能 |
|------|------|
| spider_base | Spider基类，自动判断抓取类型+Playwright备选 |
| spider_manager | 自动加载/管理所有Spider |
| playwright_fetcher | Playwright备选抓取 |
| paddle_ocr | PaddleOCR日文识别 |
| pdf_smart_parser | PDF智能解析（文字层+OCR） |
| vertical_text_converter | 纵排转横排 |
| crawl_report | 抓取日志报告生成与管理 |
| crawler | 通用HTTP抓取工具 |
| html_parser | HTML解析工具 |
| pdf_parser | PDF基础解析 |
| ocr_engine | Tesseract备选OCR |
| formatter | 数据清洗/格式化 |
| exporter | Word文档导出 |
| cache | SQLite数据库操作 |
| error_tracker | 抓取错误追踪+网站更新检测 |

## 许可证

MIT License

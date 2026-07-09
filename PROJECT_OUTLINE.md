# 日语作文网站抓取系统 - 项目大纲

> 本文档用于新AI接手项目时快速了解项目全貌、架构、已知问题和后续方向。
> 存档日期：2026-07-09

---

## 一、项目概述

**项目目标**：从多个日本作文网站抓取小学生/中学生的获奖作文，整理成统一格式存入数据库，提供Web界面浏览、搜索和Word导出。

**技术栈**：
- 后端：Python 3.x + Flask
- 数据库：SQLite（`data/essays.db`）
- 前端：原生HTML/CSS/JS（单页应用）
- 爬虫：requests + BeautifulSoup4 + pdfplumber
- 备选方案：Playwright（动态页面）、PaddleOCR（图片PDF）

**运行方式**：
```bash
pip install -r requirements.txt
python main.py
# 浏览器自动打开 http://localhost:5000
```

---

## 二、目录结构

```
TRAE 作文网站/
├── main.py                    # Flask主程序，提供API和Web界面
├── config.py                  # 配置文件（数据库路径、请求头、延迟等）
├── requirements.txt           # Python依赖
│
├── modules/                   # 核心模块
│   ├── spider_base.py         # 爬虫基类（通用下载、SSL兼容、PDF处理、纵向文本转换）
│   ├── spider_manager.py      # 爬虫管理器（自动发现和加载spiders目录下的爬虫）
│   ├── cache.py               # 数据库操作和缓存（SQLite增删改查）
│   ├── exporter.py            # Word导出功能
│   ├── pdf_smart_parser.py    # 智能PDF解析器（支持纵向排版检测和转换）
│   ├── pdf_parser.py          # 基础PDF解析器
│   ├── vertical_text_converter.py  # 纵向文本转横向工具
│   ├── html_parser.py         # HTML内容提取
│   ├── formatter.py           # 文本格式化
│   ├── ocr_engine.py          # OCR引擎基类
│   ├── paddle_ocr.py          # PaddleOCR引擎封装
│   ├── playwright_fetcher.py  # Playwright浏览器封装（处理动态页面）
│   ├── crawl_report.py        # 抓取报告生成
│   ├── error_tracker.py       # 错误追踪
│   └── crawler.py             # 旧版爬虫（可能已废弃）
│
├── spiders/                   # 各网站独立爬虫（每个网站一个文件）
│   ├── ja_kyosai.py           # JA共済福岡（第60/61届，HTML页面）
│   ├── anshin.py              # あんしん財団（表格+纵向PDF）
│   ├── netnfu.py              # 其他网站
│   ├── oishii.py              # 其他网站
│   ├── tsurezure.py           # 其他网站
│   ├── _example_template.py   # 爬虫模板（新建爬虫参考）
│   └── __init__.py
│
├── static/                    # 前端静态资源
│   ├── css/style.css
│   └── js/app.js
├── templates/
│   └── index.html             # 主页面
│
├── data/                      # 运行时数据（git忽略）
│   ├── essays.db              # SQLite数据库
│   ├── app.log                # 日志
│   └── temp/                  # 临时文件
│
└── work-notes/                # 工作笔记
```

---

## 三、核心架构

### 3.1 爬虫基类（SpiderBase）

**位置**：`modules/spider_base.py`

每个网站爬虫继承 `SpiderBase`，只需实现两个抽象方法：

```python
class MySpider(SpiderBase):
    site_name = "网站名称"
    site_url = "网站首页URL"
    
    def parse_list_page(self, html, list_url):
        """从列表页提取作文链接列表"""
        return [{'title': '...', 'url': '...'}, ...]
    
    def parse_essay_page(self, html, essay_url):
        """从详情页提取作文内容"""
        return self.make_essay(
            title='...', author='...', school='...',
            body='...', source=essay_url, date='...'
        )
```

**基类已提供的功能**：
- `fetch(url)` — HTTP下载（自动SSL兼容，失败回退Playwright）
- `fetch_binary(url)` — 二进制下载
- `handle_pdf_url(url)` — PDF下载+解析（自动检测纵向排版）
- `handle_vertical_text(html, text)` — 纵向文本转横向
- `make_essay(...)` — 构造标准作文数据结构
- `clean_text(text)` — 文本清洗
- `crawl(...)` — 完整抓取流程（列表→详情→存储）

### 3.2 爬虫管理器（SpiderManager）

**位置**：`modules/spider_manager.py`

自动扫描 `spiders/` 目录，加载所有以 `SpiderBase` 为基类且定义了 `site_name` 的类。新网站只需在 `spiders/` 下放一个 `.py` 文件，无需修改其他代码。

### 3.3 数据库

**位置**：`modules/cache.py`，数据库文件 `data/essays.db`

主要表：
- `essays` — 作文表（id, title, author, school, body, source, date, site, created_at）
- `site_updates` — 站点更新记录
- `processed_resources` — 已处理资源缓存（PDF等）

---

## 四、已完成的爬虫

### 4.1 JA共済福岡（ja_kyosai.py）

- **网站**：https://ja-kyosai-fukuoka.com/
- **届数**：第60届（2024）、第61届（2025）
- **结构**：首页 → 過去の受賞作品一覧 → 奖项分类页 → 作文详情页
- **已知坑**：
  - 作者信息在 `p.award-winner__school` 和 `span.award-winner__name` 标签中
  - 正文在 `div.award-detail__contents` 中
  - 必须过滤非作文页面（只保留 `/award/detail/` 路径的URL）
  - 曾出现过正文混入作者字段的问题（已修复，用CSS选择器直接提取）

### 4.2 あんしん財団（anshin.py）

- **网站**：https://www.anshin-zaidan.or.jp/about/csr/sakubun/
- **结构**：表格列出所有获奖作文，点击链接下载PDF
- **特点**：
  - 元数据（学校、学年、氏名、标题）在网页表格中，不在PDF里
  - PDF是**纵向排版**（日语竖排），需要转横向
  - 共25篇作文（第12届）
- **当前状态**：PDF纵向转换功能已实现，但PDF文本有cid编码残留问题

---

## 五、纵向PDF处理

### 5.1 检测逻辑

**位置**：`modules/pdf_smart_parser.py` 的 `_detect_vertical_layout` 方法

通过统计PDF中每个字符（word）的x坐标：
- 如果同一x坐标上有5个以上字符 → 判定为纵向排版
- 原理：纵向排版时，同一列的字符x坐标相同，y坐标递增

### 5.2 转换逻辑

**位置**：`modules/pdf_smart_parser.py` 的 `_convert_vertical_words_to_text` 方法

1. 按x坐标分组（每一组代表一列）
2. 每组内按y坐标排序（从上到下）
3. 所有列按x坐标从大到小排列（从右到左，符合日语竖排阅读顺序）
4. 每列字符拼接成一行

### 5.3 已知问题

- PDF中部分特殊字符（标点符号等）以 `(cid:18637)` 形式出现，无法正常显示
- 这是因为PDF使用了自定义字体编码，pdfplumber无法映射

---

## 六、已知Bug和难点

### 6.1 已解决

| 问题 | 解决方案 |
|------|----------|
| JA共済作者姓名提取错误（正文混入） | 用CSS选择器直接提取 `span.award-winner__name` |
| JA共済抓取到非作文页面 | 过滤URL，只保留 `/award/detail/` 路径 |
| SSL连接失败（旧服务器） | 使用 `OP_LEGACY_SERVER_CONNECT` 兼容旧SSL协议 |
| 纵向PDF乱码 | 按x坐标分组重组文本 |

### 6.2 未解决 / 待优化

1. **PDF的cid编码残留**：纵向PDF转换后仍有 `(cid:xxxxx)` 字符，需要进一步清理或使用OCR
2. **每个网站需单独写爬虫**：结构差异大，通用方法命中率低
3. **爬虫架构重复**：每个网站独立编写，虽然有基类，但仍有重复逻辑
4. **PDF元数据提取不稳定**：PDF内元数据格式不统一，需依赖网页表格补充
5. **部分网站可能有反爬**：未深入测试

---

## 七、后续建议方向

### 7.1 短期（已决定）

- **暂时取消PDF抓取计划**：专注优化HTML网页作文抓取
- 清理测试文件（`test_*.py`、`debug_*.py`）
- 完善现有爬虫（JA共済等），确保数据质量

### 7.2 中期

- **插件化架构重构**：将通用逻辑进一步沉淀，新网站只需配置规则
- 建立网站解析规则库，减少重复代码
- 完善错误处理和重试机制

### 7.3 长期

- 如果需要恢复PDF抓取，考虑：
  - 使用OCR处理图片型PDF和编码问题
  - 建立PDF字体映射表，解决cid问题
- 增加更多作文网站
- 支持更多导出格式

---

## 八、添加新网站爬虫的步骤

1. 在 `spiders/` 目录下新建 `网站名.py`
2. 继承 `SpiderBase`，设置 `site_name` 和 `site_url`
3. 实现 `parse_list_page(html, list_url)` — 返回作文链接列表
4. 实现 `parse_essay_page(html, essay_url)` — 返回作文详情字典
5. 自动被 `SpiderManager` 发现和加载，无需修改其他文件

**参考模板**：`spiders/_example_template.py`

---

## 九、关键文件速查

| 文件 | 作用 | 核心函数/类 |
|------|------|------------|
| `main.py` | Web界面和API | Flask路由 |
| `config.py` | 配置 | 数据库路径、请求头、延迟 |
| `modules/spider_base.py` | 爬虫基类 | `SpiderBase` |
| `modules/spider_manager.py` | 爬虫管理 | `SpiderManager` |
| `modules/cache.py` | 数据库操作 | `CacheManager` |
| `modules/pdf_smart_parser.py` | PDF解析 | `PDFSmartParser` |
| `modules/vertical_text_converter.py` | 纵向转横向 | `VerticalTextConverter` |
| `spiders/ja_kyosai.py` | JA共済爬虫 | `JaKyosaiSpider` |
| `spiders/anshin.py` | あんしん財団爬虫 | `AnshinSpider` |

---

## 十、项目约定

- 作文数据结构统一字段：`title, author, school, body, source, date, site`
- 所有文本先经过 `clean_text()` 清洗再存储
- 使用 `make_essay()` 构造作文字典，确保字段完整
- 抓取失败记录到 `_failures` 和 `error_tracker`
- 增量抓取：通过 `essay_exists_fn` 回调判断URL是否已存在
- 文件名和路径统一使用正斜杠，Windows兼容

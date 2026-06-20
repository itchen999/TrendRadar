---
name: trending-hub
description: 帮你把抖音、微博、B站、快手、知乎、头条、百度等7个平台的热搜聚合在一起，省得一个个平台去看。想知道今天全网都在聊什么、哪个热点值得追、趋势怎么走，问我准没错。查热榜、导报告、订阅推送都行
dependency:
  python:
    - 无第三方依赖（使用标准库 urllib.request）
---

# 全网热点追踪

## 1. 简介

**一句话定位**：全网热点聚合追踪工具，实时抓取抖音、微博、B站、快手、知乎、头条、百度等7大平台热搜数据，一站式查看全网热点。

**核心价值**：解决内容创作者、市场运营者在热点追踪中的三大痛点：
- **热点分散难整合**：无需逐个平台查看，一次聚合7大平台热榜
- **跨平台对比困难**：自动识别同一事件在不同平台的讨论差异和热度表现
- **趋势判断模糊**：基于热度值、上榜时长、平台覆盖等维度智能预测热点走势

**适用对象**：内容创作者、市场运营人员、媒体编辑、品牌策划、热点追踪爱好者。

**不支持**：该技能不支持查询特定热词详情，仅提供全网热点榜聚合查询。

## 2. 功能特性

### 核心功能

| 功能模块 | 能力描述 | 核心价值 |
|----------|----------|----------|
| 🔍 全网热榜聚合 | 实时抓取7大平台热搜数据 | 一键获取全网热点，告别逐平台查看 |
| 🔗 跨平台事件识别 | 智能识别同一事件在不同平台的表述 | 自动归并相似话题，避免重复统计 |
| 📊 热度趋势预测 | 基于热度值、时长、平台覆盖预测走势 | 提前判断热点生命周期，把握创作窗口 |
| 📈 TOP10榜单提供 | 按综合热度排序输出TOP10热点 | 快速定位高价值选题 |
| 💬 跨平台讨论分析 | 展示不同平台的讨论焦点和差异 | 深度洞察舆论生态，精准定位受众 |
| ⏰ 订阅推送服务 | 定时推送最新热榜/昨日热榜 | 持续追踪热点动态，不错过关键机会 |

### 特色亮点

- **小时级更新**：数据每小时更新，保持实时性
- **智能关键词泛化**：输入"体育"自动扩展为10个相关关键词
- **按平台分类输出**：百度、知乎、微博、抖音、B站、快手、头条依次展示
- **完整榜单查看**：每个平台最多支持查看完整50条数据
- **动态智能输出**：无数据平台自动跳过，数据不足自动调整展示数量

## 3. 一键安装

### 鉴权

#### 获取 API Key

请前往 [红狐hub](https://redfox.hk/settings/api-keys?source=github) 获取API KEY

#### 配置 API Key

方案2: 终端配置：

```bash
export REDFOX_API_KEY="ak_xxxx..."
```

### 依赖安装

```bash
pip install python-dateutil
```

### 环境变量配置

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `REDFOX_API_KEY` | 红狐 API Key | 是 |

## 4. 使用指南

> 注：`scripts/fetch_hotspot.py` 已从上游引入并通过安全审阅。运行需配置 `REDFOX_API_KEY`。
> 本地加固：① 恢复默认 SSL 证书校验（上游关闭了校验，有中间人风险）；② `mktemp`→`mkstemp` 避免竞态。
> 上游：https://github.com/redfox-data/redfox-community/tree/main/skills/trending-hub

### 基础使用

#### 查询最新热榜（默认）

```bash
python scripts/fetch_hotspot.py --source "全平台热点事件"
```

数据为小时级更新，自动查询前一个完整小时。

#### 查询历史热榜

```bash
python scripts/fetch_hotspot.py --source "全平台热点事件" --start-date "2026-04-15 00:00:00" --end-date "2026-04-16 00:00:00"
```

**日期范围规则**：
- 时间格式为 `YYYY-MM-DD HH:MM:SS`，也可简写为 `YYYY-MM-DD`（自动补全为 00:00:00）
- 日期范围是 `[start_date, end_date)` 左闭右开区间
- 最长查询范围：**30天**

### 高级使用

#### 筛选特定平台

```bash
python scripts/fetch_hotspot.py --source "全平台热点事件" --platforms "wb,dy,bz"
```

平台代码映射：

| 平台代码 | 平台名称 | 接口枚举值 |
|---------|---------|-----------|
| bd | 百度 | 7 |
| zh | 知乎 | 9 |
| wb | 微博 | 5 |
| dy | 抖音 | 2 |
| bz | B站 | 8 |
| ks | 快手 | 1 |
| tt | 头条 | 10 |

#### 关键词搜索与泛化

```bash
python scripts/fetch_hotspot.py --source "全平台热点事件" --keywords "体育,足球"
python scripts/fetch_hotspot.py --source "全平台热点事件" --keywords "体育" --expand-keywords
```

### 输出格式说明

**compact模式（默认）**：输出极简结构化数据（元信息+平台TOP3概览），末尾附带完整数据文件路径 `dataFile: {path}`。智能体应使用compact模式获取数据，从 `dataFile` 路径读取完整JSON数据。

输出格式模板详见 [references/output-templates.md](references/output-templates.md)。

### 命令速查表

| 场景 | 命令 |
|------|------|
| 最新热榜 | `python scripts/fetch_hotspot.py --source "全平台热点事件"` |
| 指定平台 | `python scripts/fetch_hotspot.py --platforms "wb,dy"` |
| 关键词筛选 | `python scripts/fetch_hotspot.py --keywords "体育,足球"` |
| 关键词泛化 | `python scripts/fetch_hotspot.py --keywords "体育" --expand-keywords` |

## 5. 项目架构

```
trending-hub/
├── SKILL.md                     # 技能描述文件
├── scripts/
│   └── fetch_hotspot.py         # 热点数据获取脚本（占位，需审阅后引入）
└── references/
    └── output-templates.md      # 输出格式模板参考
```

来源：redfox-data/redfox-community（MIT License）。

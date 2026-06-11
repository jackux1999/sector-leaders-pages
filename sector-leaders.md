# A股板块龙头榜

一个用于盘后观察不同题材板块龙一、龙二、龙三的本地网页原型。

当前页面文件：

- `index.html`
- `sector-leaders.html`
- `generate-sector-data.py`
- `data/sectors-data.js`

## 核心目标

每天按板块整理市场最强的股票，帮助快速判断：

- 今天哪个板块最强
- 每个板块的龙一、龙二、龙三是谁
- 龙头是交易情绪驱动，还是产业地位驱动
- 板块内部有没有扩散和接力

## 当前功能

- 支持板块列表展示
- 支持龙一、龙二、龙三排名
- 支持交易龙头和产业龙头切换
- 支持按综合热度、今日涨幅、成交额排序
- 支持搜索板块或股票
- 展示入选理由和分数拆解
- 已排除创业板、科创板股票
- 页面使用 Tailwind CSS 样式，按 12px、14px、16px 文字层级设计
- 打开页面后会在前端拉取新浪实时行情
- A 股交易时间内每 5 分钟自动刷新一次
- 每个板块展示龙一到龙五

## 当前示例板块

- MLCC
- 锂电
- 机器人
- CPO
- 半导体
- 固态电池

## 龙头口径

### 交易龙头

偏短线看盘，主要看当天市场资金强度。

当前示例打分：

```text
综合分 = 涨幅 55% + 成交额 30% + 换手率 10% + 是否涨停 5%
```

适合用来观察：

- 谁是当天板块情绪核心
- 谁先涨停
- 谁成交额最大
- 谁有资金接力

### 产业龙头

偏中线研究，主要看公司在产业链里的地位。

适合用来观察：

- 谁是行业核心公司
- 谁有业绩和市值支撑
- 谁更适合放进中线观察池

## 真实数据方案

当前已经接入免费公开数据源：

- 优先使用 AkShare / 东方财富概念板块
- 如果东方财富接口不可用，自动切换到新浪财经批量行情
- 新浪财经备用源使用自维护股票池，不依赖板块成份股接口
- 最终数据会过滤 `300`、`301`、`688` 开头的代码

推荐流程：

```text
1. 维护板块股票池
2. 每天盘后抓取行情
3. 计算涨幅、成交额、换手率、涨停状态
4. 按规则打分
5. 生成 JSON 数据
6. 网页读取 JSON 展示
```

## 安装依赖

依赖已经可以安装到项目本地 `vendor/` 目录：

```bash
python3 -m pip install -r requirements.txt --target vendor
```

脚本会自动优先从 `vendor/` 读取依赖，不污染系统 Python。

## 更新数据

运行：

```bash
python3 generate-sector-data.py
```

运行后会生成：

```text
data/sectors-data.js
```

网页会优先读取这个文件。如果文件为空或读取不到，则使用页面内置示例数据兜底。

## 数据文件

```text
data/sectors-data.js
```

结构示例：

```js
window.SECTOR_DATA = {
  generatedAt: "2026-06-11T16:30:25",
  source: "新浪行情/自维护股票池",
  sectors: [
    {
      id: "robot",
      name: "机器人",
      change: 4.16,
      amount: 312.7,
      trading: [
        {
          name: "中大力德",
          code: "002896",
          change: 10.01,
          amount: 19.8,
          turnover: 14.2,
          limit: true,
          reason: "减速器辨识度强，换手充分后封板。"
        }
      ]
    }
  ]
};
```

## 使用方式

直接用浏览器打开：

```text
index.html
```

这是纯静态页面，不需要启动服务。

## GitHub Pages 部署

推荐把以下文件提交到 GitHub 仓库根目录：

```text
index.html
sector-leaders.html
sector-leaders.md
data/sectors-data.js
generate-sector-data.py
requirements.txt
.nojekyll
```

然后在 GitHub 仓库里开启：

```text
Settings -> Pages -> Build and deployment -> Deploy from a branch
Branch: main
Folder: /root
```

部署后访问：

```text
https://你的用户名.github.io/仓库名/
```

页面本身会在浏览器里执行 5 分钟轮询，不依赖 GitHub Actions。

## 当前限制

- 页面使用 Tailwind CDN，首次打开需要能访问 `cdn.tailwindcss.com` 才能加载完整样式。
- 实时刷新依赖新浪行情脚本接口，浏览器网络或接口限制会影响刷新。
- 前端 5 分钟刷新只有在页面打开时生效；页面关闭后不会后台运行。
- 东方财富概念板块接口偶尔会断开，脚本会自动切到新浪备用源。
- 新浪备用源没有真实换手率，所以换手率会显示为 0。
- 新浪备用源依赖脚本里的自维护股票池，后续需要持续补充股票代码。
- 当前只做盘后观察和排序，不做自动交易。

## 注意

这个工具只做数据整理和看盘辅助，不构成投资建议。

龙头排名会随行情快速变化，尤其是短线题材股，盘中炸板、回落、换手都可能改变排名。

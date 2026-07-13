# 美容行业情报雷达

每天自动抓取日韩美容行业媒体(週刊粧業、Cosmetics in Japan、Korea Beauty Magazine、
BeautyNury、CMN、Cosmetics Design Asia),按"新品 / 成分 / 技术 / 品牌动态 / 消费趋势"
打标签,生成一个网页日报,只展示**新增**内容(自动去重历史已看过的)。

## 部署步骤(全程免费,不用自己的服务器)

1. **建仓库**:去 GitHub 新建一个仓库(公开或私有都行),把这个文件夹的内容上传进去。
   - 网页端操作:新建仓库 → "uploading an existing file" → 把本文件夹里所有文件拖进去。
   - 或用 git 命令:
     ```
     cd beauty-industry-radar
     git init
     git add .
     git commit -m "init"
     git branch -M main
     git remote add origin https://github.com/你的用户名/仓库名.git
     git push -u origin main
     ```

2. **开启 GitHub Pages**:仓库 → Settings → Pages → Source 选择
   `Deploy from a branch` → Branch 选 `main` / 文件夹选 `/docs` → Save。
   等一两分钟,GitHub 会给你一个网址,类似:
   `https://你的用户名.github.io/仓库名/`
   **这个网址就是你每天要打开看的页面,收藏它即可。**

3. **手动跑一次,生成第一份日报**(不用等到明天):
   仓库 → Actions 标签页 → 左侧选 "Daily Beauty Industry Radar" → 右上角
   "Run workflow" → 点绿色按钮运行。等 1-2 分钟跑完,再刷新一下你的 Pages 网址,
   应该就能看到第一份日报了。

4. 之后它会**每天北京时间早上 6 点(东京 7 点)自动跑一次**,你早上打开网址
   就是当天新抓到的内容。想改时间,改 `.github/workflows/daily.yml` 里的 cron 表达式
   (是 UTC 时间,注意换算)。

## 文件说明

- `sources.json`     信息源列表 + 关键词打标签规则,想加/改信息源直接编辑这个文件
- `scraper.py`       抓取脚本:优先试 RSS,没有就抓网页列表页做通用解析
- `build_report.py`  把抓到的数据渲染成网页
- `data/`            运行后自动生成,存历史去重记录和最新一次抓取结果
- `docs/`            运行后自动生成,就是发布到网页上的内容

## 关于抓取效果的说明(重要,请如实了解)

日韩这几家网站结构各不相同,大部分没有公开稳定的 RSS,所以脚本对没有 RSS 的网站
用的是**通用启发式解析**(抓列表页里"看起来像文章"的链接),这种方式:

- 对结构简单、标题够长的新闻列表页效果还不错
- 对复杂的网站(比如需要 JS 渲染、有大量导航链接干扰)可能抓到一些无关内容,
  或者漏掉部分文章,需要跑几天后观察实际效果,针对某个具体网站微调
  `scraper.py` 里 `generic_html_scrape()` 的提取规则,或者去官网找是否有隐藏的 RSS 地址
  (很多韩国网站用 Xpress Engine 建站,规律是 `/rss/allArticle.xml`,已经预置在配置里,
  但不保证每家都可用)。
- 如果某个信息源常年抓不到东西或全是噪音,可以直接在 `sources.json` 里删掉/替换。

## 想加更多信息源?

在 `sources.json` 的 `sources` 数组里加一段:

```json
{
  "id": "唯一英文id",
  "name": "显示名称",
  "region": "日本/韩国/...",
  "listing_url": "新闻列表页网址",
  "rss_candidates": ["如果知道RSS地址就填,不知道就写空数组[]"]
}
```

## 想换推送方式(邮件/微信/Telegram)?

现在是"存成网页,自己去看"。如果以后想改成主动推送,只需要在
`.github/workflows/daily.yml` 里 `Build report page` 之后加一步,调用邮件/Server酱/
Telegram Bot 的 API 把 `data/latest.json` 里的新增内容发出去即可,告诉我你想接入
哪种,我再补这部分代码。

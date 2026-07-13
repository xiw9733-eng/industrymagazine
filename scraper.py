#!/usr/bin/env python3
"""
美容行业情报雷达 - 每日抓取脚本

流程:
  1. 读取 sources.json 里的信息源
  2. 优先尝试候选 RSS 地址(feedparser),失败则请求列表页做通用 HTML 解析
  3. 用关键词给每条新闻打标签(新品/成分/技术/品牌动态/消费趋势)
  4. 和 data/seen_items.json 里的历史记录去重,只保留新增内容
  5. 把结果写入 data/latest.json,供 build_report.py 生成网页
"""

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
import feedparser
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SEEN_FILE = DATA_DIR / "seen_items.json"
LATEST_FILE = DATA_DIR / "latest.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BeautyIndustryRadar/1.0; +for personal research use)"
}

TIMEOUT = 15
MAX_ITEMS_PER_SOURCE = 25


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def item_id(url, title):
    """基于URL(优先)或标题生成稳定的去重ID"""
    key = url.strip() if url else title.strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def tag_item(title, keyword_tags):
    tags = []
    for tag, keywords in keyword_tags.items():
        for kw in keywords:
            if kw.lower() in title.lower():
                tags.append(tag)
                break
    return tags or ["其他"]


def try_rss(rss_url):
    """尝试解析RSS,成功返回条目列表,失败返回None"""
    try:
        resp = requests.get(rss_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            return None
        items = []
        for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if title and link:
                items.append({"title": title, "url": link})
        return items or None
    except Exception:
        return None


def generic_html_scrape(listing_url):
    """
    没有可用RSS时的通用兜底方案:
    抓取列表页,提取看起来像"文章链接"的<a>标签(有一定长度的文字 + 链接)。
    这是启发式方法,不同网站效果会有差异,必要时需要针对具体网站调整规则。
    """
    try:
        resp = requests.get(listing_url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = resp.apparent_encoding or resp.encoding
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        return [], str(e)

    candidates = []
    seen_urls = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        # 过滤太短的文字(多半是"更多""首页"这类导航链接)
        if len(text) < 8:
            continue
        # 补全相对链接
        if href.startswith("/"):
            from urllib.parse import urljoin
            href = urljoin(listing_url, href)
        if not href.startswith("http"):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        candidates.append({"title": text, "url": href})
        if len(candidates) >= MAX_ITEMS_PER_SOURCE:
            break

    return candidates, None


def fetch_source(source, keyword_tags):
    items = None
    used_method = None

    for rss_url in source.get("rss_candidates", []):
        items = try_rss(rss_url)
        if items:
            used_method = f"rss:{rss_url}"
            break

    error = None
    if not items:
        items, error = generic_html_scrape(source["listing_url"])
        used_method = "html_scrape"

    result = []
    for it in items:
        tags = tag_item(it["title"], keyword_tags)
        result.append({
            "id": item_id(it["url"], it["title"]),
            "title": it["title"],
            "url": it["url"],
            "tags": tags,
            "source_id": source["id"],
            "source_name": source["name"],
            "region": source["region"],
        })

    return result, used_method, error


def main():
    config = load_json(BASE_DIR / "sources.json", {"sources": [], "keyword_tags": {}})
    seen = load_json(SEEN_FILE, {})  # {item_id: first_seen_date}

    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    all_new_items = []
    run_log = []

    for source in config["sources"]:
        items, method, error = fetch_source(source, config["keyword_tags"])
        new_count = 0
        for it in items:
            if it["id"] not in seen:
                seen[it["id"]] = today
                it["first_seen"] = today
                all_new_items.append(it)
                new_count += 1
        run_log.append({
            "source": source["name"],
            "method": method,
            "fetched": len(items),
            "new": new_count,
            "error": error,
        })

    # 保存去重记录(限制大小,只保留最近约90天量级的条目,避免文件无限增长)
    if len(seen) > 5000:
        # 简单截断:按插入顺序丢弃最旧的一批(dict 在 py3.7+ 保持插入顺序)
        seen = dict(list(seen.items())[-5000:])
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")

    latest = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "date": today,
        "new_items": all_new_items,
        "run_log": run_log,
    }
    LATEST_FILE.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{today}] 共抓取 {sum(l['fetched'] for l in run_log)} 条,新增 {len(all_new_items)} 条")
    for l in run_log:
        status = f"OK({l['method']})" if not l["error"] else f"ERROR: {l['error']}"
        print(f"  - {l['source']}: 抓到{l['fetched']}条 / 新增{l['new']}条 [{status}]")


if __name__ == "__main__":
    main()

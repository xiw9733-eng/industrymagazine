#!/usr/bin/env python3
"""
把 data/latest.json 渲染成网页:
  - docs/index.html        今日日报(打开即看,始终是最新一次运行结果)
  - docs/archive/DATE.html 当天的归档页(供以后回看历史)
  - docs/archive/index.html 归档列表
GitHub Pages 直接从 docs/ 目录发布,所以生成完提交仓库即可自动更新网页。
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
ARCHIVE_DIR = DOCS_DIR / "archive"
DOCS_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

TAG_ORDER = ["新品", "成分", "技术", "品牌动态", "消费趋势", "其他"]

STYLE = """
<style>
  body { font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
         max-width: 860px; margin: 40px auto; padding: 0 16px; color: #222; line-height: 1.6; }
  h1 { font-size: 22px; }
  h2 { font-size: 17px; margin-top: 32px; border-left: 4px solid #444; padding-left: 8px; }
  .meta { color: #888; font-size: 13px; margin-bottom: 24px; }
  .item { padding: 10px 0; border-bottom: 1px solid #eee; }
  .item a { color: #1a5fb4; text-decoration: none; font-size: 15px; }
  .item a:hover { text-decoration: underline; }
  .source { color: #666; font-size: 12px; margin-left: 6px; }
  .empty { color: #999; padding: 12px 0; }
  .tag { display: inline-block; font-size: 11px; background: #eee; border-radius: 3px;
         padding: 1px 6px; margin-right: 4px; color: #555; }
  .log { font-size: 12px; color: #999; margin-top: 40px; border-top: 1px solid #eee; padding-top: 12px; }
  nav a { font-size: 13px; margin-right: 12px; }
</style>
"""


def render_items(items):
    if not items:
        return '<p class="empty">今天没有抓到新内容(可能是信息源没更新,也可能是抓取规则需要调整)。</p>'
    html = []
    for it in items:
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in it["tags"])
        html.append(
            f'<div class="item">{tags_html}'
            f'<a href="{it["url"]}" target="_blank" rel="noopener">{it["title"]}</a>'
            f'<span class="source">· {it["source_name"]}({it["region"]})</span></div>'
        )
    return "\n".join(html)


def group_by_tag(items):
    grouped = {tag: [] for tag in TAG_ORDER}
    for it in items:
        # 一条新闻可能命中多个标签,这里按第一个标签归类,避免重复展示
        primary_tag = it["tags"][0] if it["tags"][0] in grouped else "其他"
        grouped.setdefault(primary_tag, []).append(it)
    return grouped


def render_page(date_str, items, run_log, is_today):
    grouped = group_by_tag(items)
    sections = []
    for tag in TAG_ORDER:
        group_items = grouped.get(tag, [])
        if group_items:
            sections.append(f"<h2>{tag}({len(group_items)})</h2>{render_items(group_items)}")
    if not sections:
        sections.append(render_items([]))

    log_html = "<br>".join(
        f'{l["source"]}: 抓到{l["fetched"]}条 / 新增{l["new"]}条'
        + (f' <span style="color:#c00">[{l["error"]}]</span>' if l["error"] else "")
        for l in run_log
    )

    nav = '<nav><a href="../index.html">← 返回今日日报</a> <a href="index.html">查看全部归档</a></nav>' \
        if not is_today else '<nav><a href="archive/index.html">查看历史归档 →</a></nav>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>美容行业情报日报 - {date_str}</title>
{STYLE}
</head>
<body>
<h1>🧴 美容行业情报日报 · {date_str}</h1>
<div class="meta">数据来源:週刊粧業 / Cosmetics in Japan / Korea Beauty Magazine / BeautyNury / CMN / Cosmetics Design Asia 等日韩行业媒体</div>
{nav}
{''.join(sections)}
<div class="log">本次抓取日志:<br>{log_html}</div>
</body>
</html>"""


def render_archive_index(dates):
    links = "\n".join(f'<div class="item"><a href="{d}.html">{d} 日报</a></div>' for d in sorted(dates, reverse=True))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>历史归档</title>{STYLE}</head>
<body>
<h1>📁 历史归档</h1>
<nav><a href="../index.html">← 返回今日日报</a></nav>
{links if links else '<p class="empty">暂无历史记录</p>'}
</body>
</html>"""


def main():
    latest = json.loads((DATA_DIR / "latest.json").read_text(encoding="utf-8"))
    date_str = latest["date"]
    items = latest["new_items"]
    run_log = latest["run_log"]

    # 今日日报(首页)
    (DOCS_DIR / "index.html").write_text(
        render_page(date_str, items, run_log, is_today=True), encoding="utf-8"
    )

    # 归档页(带历史,同一天重复运行会覆盖当天归档)
    (ARCHIVE_DIR / f"{date_str}.html").write_text(
        render_page(date_str, items, run_log, is_today=False), encoding="utf-8"
    )

    existing_dates = [p.stem for p in ARCHIVE_DIR.glob("*.html") if p.stem != "index"]
    (ARCHIVE_DIR / "index.html").write_text(render_archive_index(existing_dates), encoding="utf-8")

    print(f"网页已生成: docs/index.html (今日) + docs/archive/{date_str}.html (归档)")


if __name__ == "__main__":
    main()

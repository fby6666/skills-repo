#!/usr/bin/env python3
"""
抓取网页文章并转为 markdown，保存到 _sources/articles/。
"""

import os
import sys
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False


def fetch_url(url: str) -> str:
    """获取 URL 内容"""
    headers = {'User-Agent': 'LLM-Wiki-Fetcher/1.0'}
    if HAS_REQUESTS:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text
    else:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='replace')


def html_to_simple_markdown(html: str) -> str:
    """极简 HTML -> Markdown 转换（无外部依赖）"""
    text = html
    # 移除 script/style
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 标题
    for i in range(6, 0, -1):
        text = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', r'\n' + '#' * i + r' \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    # 段落
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL | re.IGNORECASE)
    # 列表
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', text, flags=re.DOTALL | re.IGNORECASE)
    # 粗体/斜体
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
    # 链接
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)
    # 代码
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL | re.IGNORECASE)
    # 移除其余 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # HTML 实体
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def sanitize_filename(name: str) -> str:
    for ch in '/\\:*?"<>|':
        name = name.replace(ch, '_')
    return name.strip()[:80]


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description='Fetch web article and save as markdown')
    parser.add_argument('url', type=str, help='URL to fetch')
    parser.add_argument('--vault', type=str,
                        default=os.environ.get('OBSIDIAN_VAULT_PATH', ''),
                        help='Path to Obsidian vault')
    parser.add_argument('--title', type=str, default=None,
                        help='Article title (auto-detected if not set)')

    args = parser.parse_args()

    if not args.vault:
        logger.error("未指定 vault 路径。")
        return 1

    logger.info("Fetching: %s", args.url)
    html = fetch_url(args.url)

    # 提取标题
    title = args.title
    if not title:
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else urlparse(args.url).path.split('/')[-1]
    title = re.sub(r'<[^>]+>', '', title)  # 移除标签

    markdown = html_to_simple_markdown(html)

    # 加上 metadata 头
    today = datetime.now().strftime('%Y-%m-%d')
    header = (
        f'---\n'
        f'title: "{title}"\n'
        f'url: "{args.url}"\n'
        f'date_fetched: "{today}"\n'
        f'---\n\n'
    )
    full_content = header + markdown

    # 保存
    safe_name = sanitize_filename(title)
    articles_dir = Path(args.vault) / '_sources' / 'articles'
    articles_dir.mkdir(parents=True, exist_ok=True)
    output_path = articles_dir / f'{safe_name}.md'
    output_path.write_text(full_content, encoding='utf-8')

    logger.info("Saved to: %s", output_path)
    print(str(output_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())

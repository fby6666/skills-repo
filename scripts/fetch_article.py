#!/usr/bin/env python3
"""
抓取网页文章并转为 markdown，保存到 _sources/articles/。
支持下载文章中的图片，保持图文排版。
"""

import os
import sys
import re
import argparse
import logging
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("beautifulsoup4 not found, image extraction will be limited")


# URL patterns to skip (icons, logos, avatars, tracking pixels, etc.)
SKIP_URL_PATTERNS = [
    r'icon', r'logo', r'avatar', r'emoji', r'favicon',
    r'tracking', r'pixel', r'badge', r'button',
    r'spinner', r'loading', r'placeholder',
    r'\.svg$', r'\.gif$',  # usually icons/animations
    r'data:image',  # inline data URIs (usually tiny)
    r'1x1', r'spacer',
]

# Minimum image size in bytes to keep (skip tiny images)
MIN_IMAGE_SIZE = 5 * 1024  # 5KB


def fetch_url(url: str) -> str:
    """获取 URL 内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if HAS_REQUESTS:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text
    else:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='replace')


def download_image(url: str, output_path: str, referer_url: str = '') -> bool:
    """下载单张图片，返回是否成功"""
    # 根据图片 URL 选择合适的 Referer
    if referer_url:
        referer = referer_url
    else:
        referer = urlparse(url).scheme + '://' + urlparse(url).netloc + '/'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': referer,
    }
    try:
        if HAS_REQUESTS:
            resp = requests.get(url, headers=headers, timeout=30, stream=True)
            resp.raise_for_status()
            content = resp.content
        else:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()

        if len(content) < MIN_IMAGE_SIZE:
            logger.debug("Skipping small image (%d bytes): %s", len(content), url)
            return False

        with open(output_path, 'wb') as f:
            f.write(content)
        return True

    except Exception as e:
        logger.warning("Failed to download image %s: %s", url, e)
        return False


def should_skip_url(url: str) -> bool:
    """判断图片 URL 是否应该跳过"""
    url_lower = url.lower()
    for pattern in SKIP_URL_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False


def get_image_url(img_tag, base_url: str) -> str | None:
    """从 img 标签中提取最佳图片 URL"""
    # 按优先级尝试不同属性（data-original 常用于懒加载的高清图）
    for attr in ['data-original', 'data-src', 'data-lazy-src', 'src']:
        url = img_tag.get(attr)
        if url and not url.startswith('data:'):
            # 处理相对 URL
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith('http'):
                url = urljoin(base_url, url)
            return url
    return None


def guess_extension(url: str) -> str:
    """从 URL 猜测图片扩展名"""
    path = urlparse(url).path.lower()
    for ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
        if ext in path:
            return ext
    return '.jpg'  # default


def extract_xhs_images(html: str) -> list[str]:
    """
    从小红书 HTML 中提取图片 URL。
    小红书将图片数据嵌入在 JavaScript 中（unicode 转义的 JSON），不在 <img> 标签里。
    返回去重后的高清图片 URL 列表（按原始顺序）。
    """
    # 查找所有 xhscdn 图片 URL（unicode 转义形式）
    raw_urls = re.findall(
        r'http(?:s)?:\\u002F\\u002F[^"]*xhscdn\.com[^"]*', html
    )
    if not raw_urls:
        return []

    seen_bases = {}  # base_id -> best_url
    ordered_bases = []

    for raw in raw_urls:
        try:
            url = raw.encode().decode('unicode_escape')
        except Exception:
            continue

        # 只保留内容图片（spectrum/webpic），跳过 CSS/JS 等
        if 'spectrum' not in url and 'webpic' not in url:
            continue

        # 提取图片 base ID（去掉处理后缀 !nd_xxx）
        base = url.split('!')[0] if '!' in url else url
        # 提取唯一 ID（spectrum/ 后面的部分）
        base_id_match = re.search(r'spectrum/([^!]+)', url)
        base_id = base_id_match.group(1) if base_id_match else base

        if base_id not in seen_bases:
            seen_bases[base_id] = url
            ordered_bases.append(base_id)
        else:
            # 优先选择 dft（默认/高清）版本而非 prv（预览）
            if 'nd_dft' in url:
                seen_bases[base_id] = url

    return [seen_bases[bid] for bid in ordered_bases]


def extract_xhs_desc(html: str) -> str | None:
    """从小红书 HTML 中提取文章描述文本"""
    match = re.search(r'"desc"\s*:\s*"(.*?)(?<!\\)"', html)
    if match:
        raw = match.group(1)
        # 只替换转义的换行符，不做 unicode_escape（原文已经是 UTF-8）
        text = raw.replace('\\n', '\n').replace('\\t', '\t')
        text = text.replace('\\"', '"').replace('\\\\', '\\')
        # 清理话题标签格式：#xxx[话题]# → #xxx
        text = re.sub(r'#([^#\[]+)\[话题\]#', r'#\1', text)
        return text.strip()
    return None


def is_xiaohongshu(url: str) -> bool:
    """判断是否是小红书链接"""
    return 'xiaohongshu.com' in url or 'xhslink.com' in url


def extract_and_download_images(html: str, base_url: str, images_dir: str) -> dict:
    """
    从 HTML 中提取图片并下载。
    返回 {original_url: local_filename} 映射（有序）。
    """
    image_map = {}
    fig_counter = 0

    os.makedirs(images_dir, exist_ok=True)

    # 小红书特殊处理：从嵌入的 JSON 数据中提取图片 URL
    if is_xiaohongshu(base_url):
        xhs_urls = extract_xhs_images(html)
        if xhs_urls:
            logger.info("Detected Xiaohongshu, found %d images in embedded data", len(xhs_urls))
            referer = 'https://www.xiaohongshu.com/'
            for url in xhs_urls:
                fig_counter += 1
                ext = guess_extension(url)
                filename = f"fig{fig_counter}{ext}"
                output_path = os.path.join(images_dir, filename)

                if download_image(url, output_path, referer_url=referer):
                    image_map[url] = filename
                    logger.info("  Downloaded: %s -> %s", url[:80], filename)
                else:
                    fig_counter -= 1
            return image_map

    # 通用处理：从 <img> 标签提取
    if not HAS_BS4:
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    image_map = {}
    fig_counter = 0

    os.makedirs(images_dir, exist_ok=True)

    for img in soup.find_all('img'):
        url = get_image_url(img, base_url)
        if not url or should_skip_url(url):
            continue
        if url in image_map:
            continue  # 去重

        fig_counter += 1
        ext = guess_extension(url)
        filename = f"fig{fig_counter}{ext}"
        output_path = os.path.join(images_dir, filename)

        if download_image(url, output_path):
            image_map[url] = filename
            logger.info("  Downloaded: %s -> %s", url[:80], filename)
        else:
            fig_counter -= 1  # 下载失败，回退计数器

    return image_map


def html_to_markdown_with_images(html: str, image_map: dict, article_rel_path: str) -> str:
    """
    HTML → Markdown，图片按原始位置替换为 Obsidian embed。
    article_rel_path: 文章目录相对于 vault 的路径，如 _sources/articles/文章标题
    """
    if not HAS_BS4 or not image_map:
        return html_to_simple_markdown(html)

    soup = BeautifulSoup(html, 'html.parser')

    # 移除 script/style
    for tag in soup.find_all(['script', 'style']):
        tag.decompose()

    # 替换 img 标签为 Obsidian embed 占位符
    for img in soup.find_all('img'):
        url = get_image_url(img, '')
        if url and url in image_map:
            filename = image_map[url]
            embed = f'\n\n![[{article_rel_path}/images/{filename}|800]]\n\n'
            img.replace_with(embed)
        else:
            img.decompose()  # 移除未下载的图片

    # 转换剩余 HTML 为 markdown
    text = str(soup)
    text = _html_tags_to_markdown(text)
    text = _clean_text(text)

    return text


def build_xhs_markdown(html: str, image_map: dict, article_rel_path: str) -> str:
    """
    为小红书图文笔记构建 markdown：按原始顺序排列图片 + 提取的描述文本。
    """
    parts = []

    # 提取描述文本
    desc = extract_xhs_desc(html)
    if desc:
        parts.append(desc)
        parts.append('')

    # 按顺序插入图片
    parts.append('## 文章图片')
    parts.append('')
    for i, (url, filename) in enumerate(image_map.items(), 1):
        parts.append(f'![[{article_rel_path}/images/{filename}|800]]')
        parts.append(f'> 图 {i}')
        parts.append('')

    return '\n'.join(parts)


def _html_tags_to_markdown(text: str) -> str:
    """将 HTML 标签转为 markdown 格式"""
    # 标题
    for i in range(6, 0, -1):
        text = re.sub(
            rf'<h{i}[^>]*>(.*?)</h{i}>',
            r'\n' + '#' * i + r' \1\n',
            text, flags=re.DOTALL | re.IGNORECASE
        )
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
    text = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE
    )
    # 代码
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL | re.IGNORECASE)
    # 换行
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
    # 移除其余 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    return text


def _clean_text(text: str) -> str:
    """清理文本"""
    # HTML 实体
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    # 清理多余空行（但保留图片 embed 周围的空行）
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()


def html_to_simple_markdown(html: str) -> str:
    """极简 HTML -> Markdown 转换（无外部依赖，降级方案）"""
    text = html
    # 移除 script/style
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = _html_tags_to_markdown(text)
    text = _clean_text(text)
    return text


def sanitize_filename(name: str) -> str:
    for ch in '/\\:*?"<>|':
        name = name.replace(ch, '_')
    return name.strip()[:80]


def generate_image_index(images_dir: str, image_map: dict) -> None:
    """生成图片索引文件（与 papers 格式保持一致）"""
    index_path = os.path.join(images_dir, 'index.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('# 图片索引\n\n')
        f.write(f'总计：{len(image_map)} 张图片\n\n')
        for url, filename in image_map.items():
            filepath = os.path.join(images_dir, filename)
            size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            f.write(f'- **{filename}**\n')
            f.write(f'  - 来源: {url[:100]}{"..." if len(url) > 100 else ""}\n')
            f.write(f'  - 大小: {size / 1024:.1f} KB\n\n')


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
    parser.add_argument('--no-images', action='store_true',
                        help='Skip image downloading')

    args = parser.parse_args()

    if not args.vault:
        logger.error("未指定 vault 路径。")
        return 1

    logger.info("Fetching: %s", args.url)
    html = fetch_url(args.url)

    # 提取标题
    title = args.title
    if not title:
        if HAS_BS4:
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else None
        if not title:
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else urlparse(args.url).path.split('/')[-1]
    title = re.sub(r'<[^>]+>', '', title)  # 移除标签

    safe_name = sanitize_filename(title)
    today = datetime.now().strftime('%Y-%m-%d')

    # 创建文章目录结构
    article_dir = Path(args.vault) / '_sources' / 'articles' / safe_name
    images_dir = article_dir / 'images'
    article_dir.mkdir(parents=True, exist_ok=True)

    # 文章相对于 vault 的路径（用于 Obsidian embed）
    article_rel_path = f'_sources/articles/{safe_name}'

    # 下载图片
    image_map = {}
    if not args.no_images:
        logger.info("Extracting and downloading images...")
        image_map = extract_and_download_images(html, args.url, str(images_dir))
        logger.info("Downloaded %d images", len(image_map))

    # 转为 markdown（图片按原始位置插入）
    if is_xiaohongshu(args.url) and image_map:
        markdown = build_xhs_markdown(html, image_map, article_rel_path)
    elif image_map:
        markdown = html_to_markdown_with_images(html, image_map, article_rel_path)
    else:
        markdown = html_to_simple_markdown(html)

    # 加上 metadata 头
    header = (
        f'---\n'
        f'title: "{title}"\n'
        f'url: "{args.url}"\n'
        f'date_fetched: "{today}"\n'
        f'images: {len(image_map)}\n'
        f'---\n\n'
    )
    full_content = header + markdown

    # 保存
    output_path = article_dir / f'{safe_name}.md'
    output_path.write_text(full_content, encoding='utf-8')

    # 生成图片索引
    if image_map:
        generate_image_index(str(images_dir), image_map)

    logger.info("Saved to: %s", output_path)
    logger.info("Images: %d downloaded to %s", len(image_map), images_dir)
    print(str(output_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())

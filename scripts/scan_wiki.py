#!/usr/bin/env python3
"""
Wiki 扫描索引脚本
扫描 wiki/ 目录下所有页面，解析 frontmatter，构建关键词到页面路径的映射表。
用于 wiki-ingest, wiki-daily, wiki-search 等 skill。
"""

import os
import re
import json
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional

import yaml

from common_words import COMMON_WORDS

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> Dict:
    """解析 markdown 文件的 YAML frontmatter"""
    content = content.lstrip('\ufeff')
    match = re.match(r'^---\s*\n(.*?)^---\s*\n', content, re.MULTILINE | re.DOTALL)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
        return data or {}
    except Exception as e:
        logger.warning("Error parsing frontmatter: %s", e)
        return {}


def extract_keywords_from_title(title: str) -> List[str]:
    """从标题中提取关键词"""
    if not title:
        return []

    keywords = []

    # 策略1: 提取全大写缩写 (e.g., BLIP, CoRNStack)
    main_keyword = re.match(r'^([A-Z][A-Za-z0-9-]{1,})', title)
    if main_keyword:
        kw = main_keyword.group(1)
        if kw.lower() not in COMMON_WORDS:
            keywords.append(kw)

    # 策略2: 冒号前的短名称
    colon_parts = title.split(':')
    if len(colon_parts) >= 2:
        before_colon = colon_parts[0].strip()
        if 2 <= len(before_colon) <= 25 and before_colon.lower() not in COMMON_WORDS:
            keywords.append(before_colon)

    # 策略3: 带连字符的技术术语
    tech_terms = re.findall(r'\b[A-Z][a-z]*(?:-[A-Z][a-z]*)+\b', title)
    for term in tech_terms:
        if 3 <= len(term) <= 25 and term.lower() not in COMMON_WORDS:
            keywords.append(term)

    return list(dict.fromkeys(keywords))


def scan_wiki_directory(wiki_dir: Path, vault_dir: Path) -> List[Dict]:
    """
    扫描 wiki/ 目录下所有 .md 文件，提取页面信息

    Args:
        wiki_dir: wiki 目录绝对路径
        vault_dir: vault 根目录绝对路径

    Returns:
        页面信息列表
    """
    pages = []

    for md_file in wiki_dir.rglob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            fm = parse_frontmatter(content)

            rel_path = md_file.relative_to(vault_dir)
            page_type = fm.get('type', 'unknown')
            title = fm.get('title', md_file.stem)
            aliases = fm.get('aliases', [])
            if isinstance(aliases, str):
                aliases = [aliases]
            domains = fm.get('domains', [])
            if isinstance(domains, str):
                domains = [domains]
            tags = fm.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]

            page_info = {
                'path': str(rel_path).replace('\\', '/'),
                'filename': md_file.name,
                'short_name': md_file.stem,
                'type': page_type,
                'title': title,
                'aliases': aliases,
                'domains': domains,
                'tags': tags,
                'frontmatter': fm,
            }

            # 提取关键词
            title_keywords = extract_keywords_from_title(title)
            page_info['title_keywords'] = title_keywords

            # 从 tags 提取关键词
            tag_keywords = []
            for tag in tags:
                if isinstance(tag, str) and 3 <= len(tag) <= 25:
                    if tag.lower() not in COMMON_WORDS:
                        tag_keywords.append(tag)
            page_info['tag_keywords'] = tag_keywords

            pages.append(page_info)

        except Exception as e:
            logger.warning("Error reading %s: %s", md_file, e)

    return pages


def build_keyword_index(pages: List[Dict]) -> Dict[str, List[str]]:
    """构建关键词到页面路径的映射表"""
    keyword_index: Dict[str, List[str]] = {}

    def add_keyword(keyword: str, path: str) -> None:
        kl = keyword.lower()
        if len(kl) < 2 or len(kl) > 40:
            return
        if kl in COMMON_WORDS:
            return
        if kl not in keyword_index:
            keyword_index[kl] = []
        if path not in keyword_index[kl]:
            keyword_index[kl].append(path)

    for page in pages:
        path = page['path']

        # 标题关键词
        for kw in page['title_keywords']:
            add_keyword(kw, path)

        # Tag 关键词
        for kw in page['tag_keywords']:
            add_keyword(kw, path)

        # 别名
        for alias in page['aliases']:
            if isinstance(alias, str):
                add_keyword(alias, path)

        # 短文件名
        short = page['short_name']
        clean_short = re.sub(r'-\d{4}\.\d{5}$', '', short)
        clean_short = re.sub(r'-v\d+$', '', clean_short)
        if 2 <= len(clean_short) <= 40 and clean_short.lower() not in COMMON_WORDS:
            add_keyword(clean_short, path)

    return keyword_index


def main() -> int:
    parser = argparse.ArgumentParser(description='Scan wiki pages and build keyword index')
    parser.add_argument('--vault', type=str,
                        default=os.environ.get('OBSIDIAN_VAULT_PATH', ''),
                        help='Path to Obsidian vault')
    parser.add_argument('--wiki-dir', type=str, default='wiki',
                        help='Relative path to wiki directory')
    parser.add_argument('--output', type=str, default='wiki_index.json',
                        help='Output JSON file path')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )

    if not args.vault:
        logger.error("未指定 vault 路径。请通过 --vault 参数或 OBSIDIAN_VAULT_PATH 环境变量设置。")
        return 1

    vault_path = Path(args.vault)
    wiki_dir = vault_path / args.wiki_dir

    if not wiki_dir.exists():
        logger.warning("Wiki directory not found: %s — returning empty index", wiki_dir)
        output = {'pages': [], 'keyword_to_pages': {}, 'stats': {}}
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return 0

    logger.info("Scanning wiki pages in: %s", wiki_dir)
    pages = scan_wiki_directory(wiki_dir, vault_path)
    logger.info("Found %d pages", len(pages))

    keyword_index = build_keyword_index(pages)
    logger.info("Built index with %d keywords", len(keyword_index))

    # 统计
    type_counts: Dict[str, int] = {}
    for p in pages:
        t = p['type']
        type_counts[t] = type_counts.get(t, 0) + 1

    output = {
        'pages': pages,
        'keyword_to_pages': keyword_index,
        'stats': {
            'total_pages': len(pages),
            'total_keywords': len(keyword_index),
            'by_type': type_counts,
        }
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    logger.info("Index saved to: %s", args.output)
    logger.info("=== Statistics ===")
    logger.info("  Total pages: %d", len(pages))
    logger.info("  Total keywords: %d", len(keyword_index))
    for t, c in sorted(type_counts.items()):
        logger.info("  %s: %d", t, c)

    return 0


if __name__ == '__main__':
    sys.exit(main())

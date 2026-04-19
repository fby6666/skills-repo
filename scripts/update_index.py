#!/usr/bin/env python3
"""
更新 wiki/index.md -- 扫描所有 wiki 页面并重新生成总目录。
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> dict:
    import re
    content = content.lstrip('\ufeff')
    match = re.match(r'^---\s*\n(.*?)^---\s*\n', content, re.MULTILINE | re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except Exception:
        return {}


def collect_pages(wiki_dir: Path, vault_dir: Path) -> list:
    pages = []
    for md_file in wiki_dir.rglob('*.md'):
        if md_file.name in ('index.md', 'log.md'):
            continue
        try:
            content = md_file.read_text(encoding='utf-8')
            fm = parse_frontmatter(content)
            rel = md_file.relative_to(vault_dir)
            pages.append({
                'path': str(rel).replace('\\', '/'),
                'stem': md_file.stem,
                'type': fm.get('type', 'unknown'),
                'title': fm.get('title', md_file.stem),
                'domains': fm.get('domains', []),
                'updated': fm.get('updated', ''),
            })
        except Exception as e:
            logger.warning("Skipping %s: %s", md_file, e)
    return pages


def group_by_type(pages: list) -> dict:
    groups: dict[str, list] = {}
    for p in pages:
        t = p['type']
        if t not in groups:
            groups[t] = []
        groups[t].append(p)
    return groups


def generate_index_content(pages: list) -> str:
    today = datetime.now().strftime('%Y-%m-%d')
    groups = group_by_type(pages)

    lines = [
        '---',
        'type: "index"',
        f'title: "Wiki Index"',
        f'updated: "{today}"',
        '---',
        '',
        '# Wiki Index',
        '',
    ]

    # 按类型浏览
    type_labels = {
        'entity/paper': '论文',
        'entity/book': '书籍',
        'entity/tool': '工具',
        'entity/person': '人物',
        'concept': '概念',
        'comparison': '对比分析',
        'domain-overview': '领域总览',
        'question': '问答',
        'daily': '每日推荐',
    }

    lines.append('## 按类型浏览')
    lines.append('')
    for type_key, label in type_labels.items():
        type_pages = groups.get(type_key, [])
        if type_pages:
            lines.append(f'### {label} ({len(type_pages)})')
            lines.append('')
            sorted_pages = sorted(type_pages, key=lambda p: p.get('updated', ''), reverse=True)
            for p in sorted_pages:
                lines.append(f'- [[{p["stem"]}|{p["title"]}]]')
            lines.append('')

    # 未分类
    known_types = set(type_labels.keys())
    for type_key, type_pages in groups.items():
        if type_key not in known_types:
            lines.append(f'### {type_key} ({len(type_pages)})')
            lines.append('')
            for p in type_pages:
                lines.append(f'- [[{p["stem"]}|{p["title"]}]]')
            lines.append('')

    # 最近更新
    lines.append('## 最近更新')
    lines.append('')
    sorted_all = sorted(pages, key=lambda p: p.get('updated', ''), reverse=True)
    for p in sorted_all[:20]:
        updated = p.get('updated', '?')
        lines.append(f'- {updated} -- [[{p["stem"]}|{p["title"]}]] ({p["type"]})')
    lines.append('')

    # 统计
    lines.append('## 统计')
    lines.append('')
    lines.append(f'- 总页面数: {len(pages)}')
    for type_key, label in type_labels.items():
        count = len(groups.get(type_key, []))
        if count > 0:
            lines.append(f'- {label}: {count}')
    lines.append(f'- 最后更新: {today}')
    lines.append('')

    return '\n'.join(lines)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description='Regenerate wiki/index.md')
    parser.add_argument('--vault', type=str,
                        default=os.environ.get('OBSIDIAN_VAULT_PATH', ''),
                        help='Path to Obsidian vault')
    args = parser.parse_args()

    if not args.vault:
        logger.error("未指定 vault 路径。")
        return 1

    vault_path = Path(args.vault)
    wiki_dir = vault_path / 'wiki'

    if not wiki_dir.exists():
        logger.error("Wiki directory not found: %s", wiki_dir)
        return 1

    pages = collect_pages(wiki_dir, vault_path)
    logger.info("Found %d wiki pages", len(pages))

    content = generate_index_content(pages)
    index_path = wiki_dir / 'index.md'
    index_path.write_text(content, encoding='utf-8')
    logger.info("Index written to: %s", index_path)

    return 0


if __name__ == '__main__':
    sys.exit(main())

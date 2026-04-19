#!/usr/bin/env python3
"""
Wiki 健康检查脚本
检查: 孤立页面、断链、缺失 frontmatter、薄弱页面、index 同步等。
"""

import os
import re
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set

import yaml

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> dict:
    content = content.lstrip('\ufeff')
    match = re.match(r'^---\s*\n(.*?)^---\s*\n', content, re.MULTILINE | re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except Exception:
        return {}


def extract_wikilinks(content: str) -> Set[str]:
    """提取页面中所有 [[wikilink]] 的目标"""
    links = set()
    # Normalize escaped pipe in links such as [[topic\|alias]]
    content = content.replace('\\|', '|')
    # Skip image embeds ![[...]]
    for match in re.finditer(r'(?<!!)\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]', content):
        target = match.group(1).strip()
        # 去掉路径前缀只留文件名（Obsidian 短链接模式）
        if '/' in target:
            target = target.rsplit('/', 1)[-1]
        # 去掉 .md 扩展名
        if target.endswith('.md'):
            target = target[:-3]
        links.add(target)
    return links


def run_lint(vault_path: Path) -> dict:
    """执行所有 lint 检查"""
    wiki_dir = vault_path / 'wiki'
    if not wiki_dir.exists():
        return {'error': 'wiki/ directory not found'}

    # 收集所有页面
    all_pages: Dict[str, dict] = {}  # stem -> info
    all_stems: Set[str] = set()

    for md_file in wiki_dir.rglob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            fm = parse_frontmatter(content)
            rel = md_file.relative_to(vault_path)
            stem = md_file.stem
            word_count = len(content)
            outgoing = extract_wikilinks(content)

            all_pages[stem] = {
                'path': str(rel).replace('\\', '/'),
                'stem': stem,
                'type': fm.get('type', ''),
                'title': fm.get('title', stem),
                'frontmatter': fm,
                'word_count': word_count,
                'outgoing_links': outgoing,
                'updated': fm.get('updated', ''),
            }
            all_stems.add(stem)
        except Exception as e:
            logger.warning("Error reading %s: %s", md_file, e)

    # 建立 inbound 链接图
    inbound: Dict[str, Set[str]] = {stem: set() for stem in all_stems}
    for stem, info in all_pages.items():
        for target in info['outgoing_links']:
            if target in inbound:
                inbound[target].add(stem)

    issues: Dict[str, list] = {
        'orphan_pages': [],
        'broken_links': [],
        'missing_frontmatter': [],
        'thin_pages': [],
    }

    for stem, info in all_pages.items():
        # 跳过 index 和 log
        if stem in ('index', 'log'):
            continue

        # 1. 孤立页面（无入链）
        if not inbound.get(stem):
            issues['orphan_pages'].append({
                'page': info['path'],
                'title': info['title'],
            })

        # 2. 断链（outgoing link 指向不存在的页面）
        for target in info['outgoing_links']:
            if target not in all_stems:
                issues['broken_links'].append({
                    'from': info['path'],
                    'target': target,
                })

        # 3. 缺失 frontmatter
        required_keys = {'type', 'title', 'created'}
        missing = required_keys - set(info['frontmatter'].keys())
        if missing:
            issues['missing_frontmatter'].append({
                'page': info['path'],
                'missing': list(missing),
            })

        # 4. 薄弱页面
        page_type = info['type']
        threshold = 500 if page_type.startswith('entity/') else 100
        if info['word_count'] < threshold and page_type not in ('daily', 'index', 'log', 'domain-overview'):
            issues['thin_pages'].append({
                'page': info['path'],
                'type': page_type,
                'word_count': info['word_count'],
                'threshold': threshold,
            })

    # 统计
    summary = {
        'total_pages': len(all_pages),
        'orphan_pages': len(issues['orphan_pages']),
        'broken_links': len(issues['broken_links']),
        'missing_frontmatter': len(issues['missing_frontmatter']),
        'thin_pages': len(issues['thin_pages']),
    }
    summary['total_issues'] = sum(v for k, v in summary.items() if k != 'total_pages')

    return {
        'summary': summary,
        'issues': issues,
    }


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description='Lint wiki pages')
    parser.add_argument('--vault', type=str,
                        default=os.environ.get('OBSIDIAN_VAULT_PATH', ''),
                        help='Path to Obsidian vault')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON report (optional, prints to stdout if not set)')

    args = parser.parse_args()

    if not args.vault:
        logger.error("未指定 vault 路径。")
        return 1

    result = run_lint(Path(args.vault))

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        logger.info("Report saved to: %s", args.output)
    else:
        print(output_json)

    # 打印摘要
    s = result.get('summary', {})
    logger.info("=== Lint Summary ===")
    logger.info("  Total pages: %d", s.get('total_pages', 0))
    logger.info("  Orphan pages: %d", s.get('orphan_pages', 0))
    logger.info("  Broken links: %d", s.get('broken_links', 0))
    logger.info("  Missing frontmatter: %d", s.get('missing_frontmatter', 0))
    logger.info("  Thin pages: %d", s.get('thin_pages', 0))
    logger.info("  Total issues: %d", s.get('total_issues', 0))

    return 0


if __name__ == '__main__':
    sys.exit(main())

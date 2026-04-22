#!/usr/bin/env python3
"""
Wiki 页面生成脚本
根据页面类型和模板生成 wiki 页面骨架。
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def get_vault_path(cli_vault: str = None) -> str:
    if cli_vault:
        return cli_vault
    env_path = os.environ.get('OBSIDIAN_VAULT_PATH')
    if env_path:
        return env_path
    logger.error("未指定 vault 路径。请通过 --vault 参数或 OBSIDIAN_VAULT_PATH 环境变量设置。")
    sys.exit(1)


def sanitize_filename(name: str) -> str:
    """将名称转为安全的文件名"""
    for ch in '/\\:*?"<>|':
        name = name.replace(ch, '_')
    return name.strip()


def to_kebab_case(name: str) -> str:
    """将名称转为 kebab-case"""
    result = name.strip()
    result = result.replace(' ', '-')
    for ch in '/\\:*?"<>|_':
        result = result.replace(ch, '-')
    # 合并连续的 -
    while '--' in result:
        result = result.replace('--', '-')
    return result.strip('-').lower()


def read_template(templates_dir: Path, template_name: str) -> str:
    """读取模板文件，找不到则返回空字符串"""
    template_path = templates_dir / template_name
    if template_path.exists():
        return template_path.read_text(encoding='utf-8')
    logger.warning("Template not found: %s", template_path)
    return ''


def generate_entity_paper(
    paper_id: str,
    title: str,
    authors: str,
    domain: str,
    vault_path: str,
) -> str:
    """生成论文实体页"""
    today = datetime.now().strftime('%Y-%m-%d')
    short_name = title.split(':')[0].strip() if ':' in title else title.split(' ')[0]
    safe_name = sanitize_filename(short_name)

    tags_list = ['论文笔记']
    domain_tag = domain.replace('/', '-')
    if domain_tag:
        tags_list.append(domain_tag)
    tags_yaml = '\n'.join(f'  - "{tag}"' for tag in tags_list)

    content = f'''---
type: "entity/paper"
title: "{title}"
aliases:
  - "{short_name}"
paper_id: "{paper_id}"
authors: "{authors}"
venue: ""
date: "{today}"
domains:
  - "{domain}"
tags:
{tags_yaml}
quality_score: 0
source_path: "_sources/papers/{paper_id}/{safe_name}.pdf"
status: "draft"
created: "{today}"
updated: "{today}"
---

# {title}

## 一句话总结

{{待填写}}

## 核心信息

- **论文ID**: arXiv:{paper_id}
- **作者**: {authors}
- **机构**: {{待填写}}
- **发布时间**: {today}
- **会议/期刊**: {{待填写}}
- **链接**: [arXiv](https://arxiv.org/abs/{paper_id}) | [PDF](https://arxiv.org/pdf/{paper_id})

## 摘要

### 英文原文

{{待填写}}

### 中文翻译

{{待填写}}

## 研究问题与动机

{{待填写}}

## 方法

### 核心思想

{{待填写}}

### 方法架构

{{待填写}}

### 关键创新

1. {{待填写}}
2. {{待填写}}

## 实验结果

### 数据集与设置

{{待填写}}

### 主要结果

{{待填写}}

## 深度分析

### 优势

- {{待填写}}

### 局限性

- {{待填写}}

### 适用场景

- {{待填写}}

## 相关论文

- [[{{相关论文}}]] - {{关系描述}}

## 我的评价

### 评分: /10

| 维度 | 分数 | 理由 |
|------|------|------|
| 创新性 | /10 | |
| 技术质量 | /10 | |
| 实验充分性 | /10 | |
| 写作质量 | /10 | |
| 实用性 | /10 | |

> [!tip] 核心启发
> {{待填写}}

%% user: 个人阅读笔记 %%
'''
    return content, safe_name


def generate_entity_article(
    title: str,
    url: str,
    author: str,
    platform: str,
    domain: str,
    source_path: str,
    vault_path: str,
) -> tuple[str, str]:
    """生成网页文章实体页"""
    today = datetime.now().strftime('%Y-%m-%d')
    safe_name = sanitize_filename(title)

    content = f'''---
type: "entity/article"
title: "{title}"
aliases: []
author: "{author}"
platform: "{platform}"
url: "{url}"
date: "{today}"
domains:
  - "{domain}"
tags:
  - "文章笔记"
source_path: "_sources/articles/{safe_name}"
created: "{today}"
updated: "{today}"
---

# {title}

## 一句话总结

{{{{待填写}}}}

## 来源信息

- **作者**: {author}
- **平台**: {platform}
- **链接**: [{platform}]({url})
- **抓取日期**: {today}

## 内容概要

{{{{待填写}}}}

## 关键论点与数据

{{{{待填写}}}}

## 涉及的概念与论文

{{{{待填写}}}}

## 我的评价

> [!tip] 核心启发
> {{{{待填写}}}}

%% user: 个人阅读笔记 %%
'''
    return content, safe_name


def generate_concept(
    title: str,
    domains: list,
    vault_path: str,
) -> str:
    """生成概念页"""
    today = datetime.now().strftime('%Y-%m-%d')
    kebab_name = to_kebab_case(title)
    domains_yaml = '\n'.join(f'  - "{d}"' for d in domains) if domains else '  - ""'

    content = f'''---
type: "concept"
title: "{title}"
aliases: []
domains:
{domains_yaml}
tags: []
created: "{today}"
updated: "{today}"
---

# {title}

## 定义

{{待填写}}

## 为什么重要

{{待填写}}

## 核心要点

- {{待填写}}

## 在具体工作中的应用

{{待填写}}

## 相关概念

- [[{{相关概念}}]]

## 参考来源

- [[{{来源}}]]
'''
    return content, kebab_name


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description='Generate wiki page from template')
    parser.add_argument('--type', type=str, required=True,
                        choices=['entity/paper', 'entity/article', 'entity/book',
                                 'entity/tool', 'concept', 'comparison',
                                 'domain-overview', 'question'],
                        help='Page type')
    parser.add_argument('--title', type=str, required=True, help='Page title')
    parser.add_argument('--paper-id', type=str, default='', help='arXiv paper ID')
    parser.add_argument('--authors', type=str, default='', help='Authors')
    parser.add_argument('--domain', type=str, default='', help='Primary domain')
    parser.add_argument('--domains', type=str, default='', help='Comma-separated domains')
    parser.add_argument('--url', type=str, default='', help='Article URL')
    parser.add_argument('--author', type=str, default='', help='Article author (for entity/article)')
    parser.add_argument('--platform', type=str, default='', help='Article platform (for entity/article)')
    parser.add_argument('--source-path', type=str, default='', help='Source path in _sources/')
    parser.add_argument('--vault', type=str, default=None, help='Obsidian vault path')
    parser.add_argument('--output', type=str, default=None,
                        help='Output file path (auto-determined if not set)')

    args = parser.parse_args()
    vault_root = get_vault_path(args.vault)
    wiki_dir = os.path.join(vault_root, 'wiki')
    today = datetime.now().strftime('%Y-%m-%d')

    domains = [d.strip() for d in args.domains.split(',') if d.strip()] if args.domains else []
    if args.domain and args.domain not in domains:
        domains.insert(0, args.domain)

    if args.type == 'entity/paper':
        content, safe_name = generate_entity_paper(
            args.paper_id, args.title, args.authors, args.domain, vault_root,
        )
        output_path = args.output or os.path.join(
            wiki_dir, 'entities', 'papers', f'{safe_name}.md'
        )
    elif args.type == 'entity/article':
        content, safe_name = generate_entity_article(
            args.title, args.url, args.author, args.platform,
            args.domain, args.source_path, vault_root,
        )
        output_path = args.output or os.path.join(
            wiki_dir, 'entities', 'articles', f'{safe_name}.md'
        )
    elif args.type == 'concept':
        content, kebab_name = generate_concept(args.title, domains, vault_root)
        output_path = args.output or os.path.join(
            wiki_dir, 'concepts', f'{kebab_name}.md'
        )
    else:
        # 通用生成
        safe_name = sanitize_filename(args.title)
        type_to_dir = {
            'entity/book': 'entities/books',
            'entity/tool': 'entities/tools',
            'comparison': 'comparisons',
            'domain-overview': f'domains/{args.domain}' if args.domain else 'domains',
            'question': 'questions',
        }
        sub_dir = type_to_dir.get(args.type, '')
        domains_yaml = '\n'.join(f'  - "{d}"' for d in domains) if domains else '  - ""'
        content = f'''---
type: "{args.type}"
title: "{args.title}"
domains:
{domains_yaml}
tags: []
created: "{today}"
updated: "{today}"
---

# {args.title}

{{待填写}}
'''
        output_path = args.output or os.path.join(
            wiki_dir, sub_dir, f'{safe_name}.md'
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info("Page generated: %s", output_path)
    print(output_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())

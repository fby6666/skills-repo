#!/usr/bin/env python3
"""
向 wiki/log.md 追加操作记录。
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def append_log_entry(
    log_path: Path,
    operation: str,
    details: str,
) -> None:
    """
    追加一条操作记录到 log.md

    Args:
        log_path: log.md 文件路径
        operation: 操作类型 (Ingest / Query / Lint / Daily)
        details: 详细内容（已格式化的 markdown 行）
    """
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')

    # 读取现有内容
    if log_path.exists():
        existing = log_path.read_text(encoding='utf-8')
    else:
        existing = (
            '---\n'
            'type: "log"\n'
            'title: "Wiki Activity Log"\n'
            f'updated: "{date_str}"\n'
            '---\n\n'
            '# Wiki Activity Log\n\n'
        )

    # 检查是否已有今天的日期标题
    date_heading = f'## {date_str}'
    if date_heading not in existing:
        existing += f'\n{date_heading}\n'

    # 追加条目
    entry = f'\n### {operation}\n- {time_str} -- {details}\n'
    existing += entry

    # 更新 frontmatter 中的 updated 日期
    if 'updated:' in existing:
        import re
        existing = re.sub(
            r'updated:\s*"[^"]*"',
            f'updated: "{date_str}"',
            existing,
            count=1,
        )

    log_path.write_text(existing, encoding='utf-8')
    logger.info("Log entry appended to: %s", log_path)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description='Append entry to wiki/log.md')
    parser.add_argument('--vault', type=str,
                        default=os.environ.get('OBSIDIAN_VAULT_PATH', ''),
                        help='Path to Obsidian vault')
    parser.add_argument('--operation', type=str, required=True,
                        choices=['Ingest', 'Query', 'Lint', 'Daily', 'Init', 'Migrate'],
                        help='Operation type')
    parser.add_argument('--details', type=str, required=True,
                        help='Details of the operation (markdown)')

    args = parser.parse_args()

    if not args.vault:
        logger.error("未指定 vault 路径。")
        return 1

    log_path = Path(args.vault) / 'wiki' / 'log.md'
    append_log_entry(log_path, args.operation, args.details)
    return 0


if __name__ == '__main__':
    sys.exit(main())

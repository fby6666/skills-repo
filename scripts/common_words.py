"""
通用词集合 -- 被 scan_wiki.py 和 link_keywords.py 共享。
这些词在自动提取关键词和自动链接时应被排除。
"""

COMMON_WORDS = {
    # 英语功能词
    'and', 'the', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from',
    'to', 'as', 'or', 'but', 'not', 'a', 'an', 'is', 'are', 'was', 'were',
    'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'should', 'could', 'may', 'might', 'must',
    'can', 'need', 'use', 'using', 'via', 'through', 'over',
    'under', 'between', 'among', 'during', 'without', 'within',
    'this', 'that', 'these', 'those', 'it', 'its', 'they', 'their',
    'we', 'you', 'your', 'our', 'my', 'his', 'her',
    # 在论文标题/摘要中过于常见、缺乏区分度的 ML 术语
    'model', 'learning', 'training', 'data', 'system', 'method',
    'approach', 'framework', 'network', 'algorithm', 'task',
    'based', 'new', 'large', 'using', 'efficient', 'towards',
    'multi', 'deep', 'neural', 'pre', 'fine',
    # 量化投资常见泛词
    'strategy', 'trading', 'market', 'stock', 'price', 'return',
    'portfolio', 'risk', 'value', 'factor',
    # 编程常见泛词
    'code', 'function', 'class', 'object', 'type', 'error',
    'file', 'module', 'package', 'library',
    # 通用泛词
    'result', 'performance', 'analysis', 'problem', 'solution',
    'paper', 'study', 'research', 'work', 'process',
    'input', 'output', 'set', 'step', 'way',
}

"""
Linux Driver Analyzer (LDA)

静态代码分析和可视化工具，专为 Linux 驱动开发者设计。

快速使用:
    from backends import get_backend
    
    backend = get_backend()
    result = backend.parse_file('driver.c')
    
    for name, func in result.functions.items():
        print(f"{name}: {len(func.calls)} calls")
"""

__version__ = "0.2.0"
__author__ = "LDA Contributors"


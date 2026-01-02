#!/usr/bin/env python3
"""
Linux Driver Analyzer - 解析后端

支持多种解析后端，按精确度排序：
1. regex    - 正则匹配，无依赖，速度快
2. tree-sitter - 语法树解析，精确度高
3. clang    - 完整语义分析（计划中）

使用示例：
    from backends import get_backend, list_backends
    
    # 获取最佳可用后端
    backend = get_backend()
    
    # 或指定后端
    backend = get_backend('tree-sitter')
    
    # 解析代码
    result = backend.parse(source_code)
"""

from .base import (
    AnalyzerBackend,
    BackendCapability,
    BackendRegistry,
    ParseResult,
    FunctionDef,
    StructDef,
    StructField,
    FunctionCall,
    TypeDef,
    Parameter,
    Location,
)

# 导入并注册后端
from .regex_backend import RegexBackend

# tree-sitter 是可选的
try:
    from .treesitter_backend import TreeSitterBackend, TREE_SITTER_AVAILABLE
except ImportError:
    TREE_SITTER_AVAILABLE = False
    TreeSitterBackend = None


def get_backend(name: str = None) -> AnalyzerBackend:
    """
    获取解析后端
    
    Args:
        name: 后端名称，可选值: 'regex', 'tree-sitter', 'clang'
              如果不指定，返回最佳可用后端
    
    Returns:
        AnalyzerBackend: 解析后端实例
        
    Raises:
        ValueError: 如果指定的后端不存在或不可用
    """
    if name:
        backend = BackendRegistry.get(name)
        if not backend:
            available = list_backends()
            raise ValueError(
                f"后端 '{name}' 不存在或不可用。"
                f"可用后端: {', '.join(available)}"
            )
        if not backend.is_available():
            raise ValueError(
                f"后端 '{name}' 依赖未安装。请查看安装说明。"
            )
        return backend
    
    # 返回最佳可用后端
    backend = BackendRegistry.get_best_available()
    if not backend:
        # 回退到 regex
        return RegexBackend()
    return backend


def list_backends() -> list:
    """
    列出所有可用的后端
    
    Returns:
        list: 可用后端名称列表
    """
    return BackendRegistry.list_available()


def is_treesitter_available() -> bool:
    """检查 tree-sitter 是否可用"""
    return TREE_SITTER_AVAILABLE


__all__ = [
    # 核心类
    'AnalyzerBackend',
    'BackendCapability',
    'BackendRegistry',
    'ParseResult',
    'FunctionDef',
    'StructDef',
    'StructField',
    'FunctionCall',
    'TypeDef',
    'Parameter',
    'Location',
    # 具体后端
    'RegexBackend',
    'TreeSitterBackend',
    # 工具函数
    'get_backend',
    'list_backends',
    'is_treesitter_available',
]


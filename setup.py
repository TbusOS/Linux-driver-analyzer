#!/usr/bin/env python3
"""
Linux Driver Analyzer - Setup Script

安装方式:
    # 基础安装（仅正则后端）
    pip install .
    
    # 推荐安装（包含 tree-sitter）
    pip install ".[recommended]"
    
    # 完整安装（所有功能）
    pip install ".[full]"
    
    # 开发安装
    pip install -e ".[dev]"
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# 读取版本
VERSION = "0.2.0"

setup(
    name="linux-driver-analyzer",
    version=VERSION,
    author="LDA Contributors",
    author_email="",
    description="静态代码分析和可视化工具，专为Linux驱动开发者设计",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/linux-driver-analyzer",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/linux-driver-analyzer/issues",
        "Documentation": "https://github.com/yourusername/linux-driver-analyzer/docs",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Analyzers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    
    # 核心功能无外部依赖
    install_requires=[],
    
    # 可选依赖
    extras_require={
        # 推荐安装：tree-sitter + pytest（一键搭建完整环境）
        "recommended": [
            "tree-sitter>=0.23.0",
            "tree-sitter-c>=0.23.0",
            "pytest>=7.0.0",
        ],
        # tree-sitter 后端（别名）
        "treesitter": [
            "tree-sitter>=0.23.0",
            "tree-sitter-c>=0.23.0",
        ],
        # libclang 后端（计划中）
        "clang": [
            "libclang>=16.0.0",
        ],
        # 测试依赖
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
        # 开发依赖（代码检查 + 测试覆盖率）
        "dev": [
            "tree-sitter>=0.23.0",
            "tree-sitter-c>=0.23.0",
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
        # 完整安装
        "full": [
            "tree-sitter>=0.23.0",
            "tree-sitter-c>=0.23.0",
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
        # 文档
        "docs": [
            "mkdocs>=1.4.0",
            "mkdocs-material>=9.0.0",
        ],
    },
    
    # 命令行入口
    entry_points={
        "console_scripts": [
            "lda=core.cli:main",
            "lda-analyze=core.basic_analyzer:main",
            "lda-advanced=core.advanced_analyzer:main",
        ],
    },
    
    include_package_data=True,
    package_data={
        "core": ["knowledge_base.json"],
    },
)

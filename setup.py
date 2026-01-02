#!/usr/bin/env python3
"""
Linux Driver Analyzer - Setup Script
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="linux-driver-analyzer",
    version="0.1.0",
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
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        # 核心功能无外部依赖
    ],
    extras_require={
        "treesitter": [
            "tree-sitter>=0.21.0",
            "tree-sitter-c>=0.21.0",
        ],
        "clang": [
            "libclang>=16.0.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
        "docs": [
            "mkdocs>=1.4.0",
            "mkdocs-material>=9.0.0",
        ],
    },
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


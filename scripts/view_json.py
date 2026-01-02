#!/usr/bin/env python3
"""
JSON分析结果查看器
用法: python scripts/view_json.py <json文件> [选项]

选项:
    --funcs     只显示函数列表
    --async     只显示异步处理函数
    --calls     显示调用关系
    --ops       显示操作结构体
    --all       显示全部信息 (默认)
"""

import json
import sys
import os

def print_header(text):
    print('\n' + '═' * 60)
    print(f' {text}')
    print('═' * 60)

def view_functions(data):
    print_header(f"📦 函数列表 ({len(data['functions'])}个)")
    for name, func in data['functions'].items():
        cb = '🔄' if func.get('is_callback') else '  '
        ctx = func.get('callback_context', '')
        line_info = f"L{func['start_line']}-{func['end_line']}"
        print(f"  {cb} {name}() {line_info}", end='')
        if ctx:
            print(f' [{ctx}]')
        else:
            print()

def view_async(data):
    handlers = data.get('async_handlers', [])
    print_header(f"⚡ 异步处理函数 ({len(handlers)}个)")
    for ah in handlers:
        icon = ah.get('extra_info', {}).get('icon', '📌')
        desc = ah.get('extra_info', {}).get('desc', ah['handler_type'])
        print(f"\n  {icon} {ah['func_name']}()")
        print(f"      类型: {desc}")
        print(f"      上下文: {ah['context']}")
        print(f"      初始化: {ah['init_pattern']}")
        trigger = ah.get('trigger_pattern', '')
        if trigger:
            print(f"      触发方式: {trigger}")

def view_calls(data):
    print_header("📈 函数调用关系")
    for name, func in data['functions'].items():
        calls = func.get('calls', [])
        if not calls:
            continue
        print(f"\n  {name}():")
        for i, c in enumerate(calls[:10]):
            prefix = '└──' if i == len(calls[:10]) - 1 else '├──'
            print(f"    {prefix} {c}()")
        if len(calls) > 10:
            print(f"    └── ... 还有 {len(calls)-10} 个调用")

def view_ops(data):
    ops = data.get('ops_structs', [])
    print_header(f"📋 操作结构体 ({len(ops)}个)")
    for op in ops:
        print(f"\n  📋 {op['struct_type']} ({op['var_name']})")
        for cb in op.get('callbacks', []):
            print(f"      .{cb['field']} = {cb['func']}()")

def view_summary(data):
    print_header(f"📊 分析摘要: {data['file']}")
    print(f"  函数总数: {len(data['functions'])}")
    callbacks = sum(1 for f in data['functions'].values() if f.get('is_callback'))
    print(f"  回调函数: {callbacks}")
    print(f"  异步处理: {len(data.get('async_handlers', []))}")
    print(f"  操作结构体: {len(data.get('ops_structs', []))}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    json_file = sys.argv[1]
    if not os.path.exists(json_file):
        print(f"错误: 文件不存在 - {json_file}")
        sys.exit(1)
    
    with open(json_file) as f:
        data = json.load(f)
    
    opts = sys.argv[2:] if len(sys.argv) > 2 else ['--all']
    
    view_summary(data)
    
    if '--all' in opts or '--funcs' in opts:
        view_functions(data)
    
    if '--all' in opts or '--async' in opts:
        view_async(data)
    
    if '--all' in opts or '--ops' in opts:
        view_ops(data)
    
    if '--all' in opts or '--calls' in opts:
        view_calls(data)
    
    print()

if __name__ == '__main__':
    main()


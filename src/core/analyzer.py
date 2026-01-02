#!/usr/bin/env python3
"""
统一分析器入口 - 使用可插拔后端架构

自动选择最佳后端进行代码分析，整合了：
- 后端解析能力（tree-sitter / regex）
- 异步机制识别
- Linux 内核知识库增强
- 调用树构建

使用方法:
    python src/core/analyzer.py driver.c -o result.json
"""

import re
import json
import argparse
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set, Optional, Any
from pathlib import Path

# 添加 src 目录到路径
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from backends import get_backend, list_backends, ParseResult


@dataclass
class AsyncHandler:
    """异步处理函数"""
    handler_type: str
    func_name: str
    init_pattern: str
    trigger_pattern: str
    line: int = 0
    context: str = ""
    extra_info: Dict = field(default_factory=dict)


@dataclass
class CallNode:
    """调用树节点"""
    name: str
    display_name: str = ""
    line: int = 0
    children: List['CallNode'] = field(default_factory=list)
    node_type: str = "function"
    description: str = ""
    time_info: str = ""


class UnifiedAnalyzer:
    """
    统一分析器 - 使用可插拔后端
    
    整合了新后端架构和原有的异步机制识别、调用树构建功能
    """
    
    # 异步机制模式
    ASYNC_PATTERNS = {
        'work': {
            'init': [r'INIT_WORK\s*\(\s*&?[\w\.\->]+\s*,\s*(\w+)\s*\)'],
            'trigger': 'schedule_work / queue_work',
            'context': '进程上下文，可睡眠',
            'icon': '⚙️',
            'desc': '工作队列'
        },
        'delayed_work': {
            'init': [r'INIT_DELAYED_WORK\s*\(\s*&?[\w\.\->]+\s*,\s*(\w+)\s*\)'],
            'trigger': 'schedule_delayed_work',
            'context': '进程上下文，可睡眠',
            'icon': '⏰',
            'desc': '延迟工作队列'
        },
        'irq': {
            'init': [r'request_irq\s*\([^,]+,\s*(\w+)\s*,',
                     r'devm_request_irq\s*\([^,]+,\s*[^,]+,\s*(\w+)\s*,'],
            'trigger': '硬件中断触发',
            'context': '中断上下文，不可睡眠',
            'icon': '⚡',
            'desc': '硬中断处理'
        },
        'threaded_irq': {
            'init': [r'request_threaded_irq\s*\([^,]+,\s*\w+\s*,\s*(\w+)\s*,'],
            'trigger': '硬件中断触发后执行',
            'context': '进程上下文，可睡眠',
            'icon': '🧵',
            'desc': '线程化中断'
        },
        'tasklet': {
            'init': [r'tasklet_init\s*\([^,]+,\s*(\w+)\s*,',
                     r'DECLARE_TASKLET\s*\(\s*\w+\s*,\s*(\w+)\s*,'],
            'trigger': 'tasklet_schedule',
            'context': '软中断上下文，不可睡眠',
            'icon': '🔄',
            'desc': 'Tasklet'
        },
        'timer': {
            'init': [r'timer_setup\s*\([^,]+,\s*(\w+)\s*,',
                     r'DEFINE_TIMER\s*\(\s*\w+\s*,\s*(\w+)\s*\)'],
            'trigger': 'mod_timer / add_timer',
            'context': '软中断上下文，不可睡眠',
            'icon': '⏲️',
            'desc': '内核定时器'
        },
        'hrtimer': {
            'init': [r'(\w+)\.function\s*=\s*(\w+)',
                     r'(\w+)->function\s*=\s*(\w+)'],
            'trigger': 'hrtimer_start',
            'context': '硬中断上下文',
            'icon': '⏱️',
            'desc': '高精度定时器'
        },
        'kthread': {
            'init': [r'kthread_run\s*\(\s*(\w+)\s*,',
                     r'kthread_create\s*\(\s*(\w+)\s*,'],
            'trigger': 'wake_up_process',
            'context': '进程上下文，可睡眠',
            'icon': '🧵',
            'desc': '内核线程'
        },
    }
    
    def __init__(self, backend_name: str = None, knowledge_base_path: str = None):
        # 选择后端
        self.backend = get_backend(backend_name)
        
        # 加载知识库
        self.knowledge_base = {}
        if knowledge_base_path and os.path.exists(knowledge_base_path):
            with open(knowledge_base_path, 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
        
        self.async_handlers: List[AsyncHandler] = []
        self.struct_ops: List[Dict] = []
        self.source_content = ""
    
    def analyze_file(self, filepath: str) -> Dict:
        """分析文件"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            self.source_content = f.read()
        
        # 使用后端解析
        parse_result = self.backend.parse_file(filepath)
        
        # 异步机制识别
        self._extract_async_handlers(self.source_content)
        
        # 提取 struct ops 映射
        self._extract_struct_ops(self.source_content, parse_result)
        
        # 应用知识库
        self._apply_knowledge_base(parse_result)
        
        # 标记异步回调
        self._mark_async_callbacks(parse_result)
        
        # 构建调用树
        call_tree = self._build_call_tree(parse_result)
        
        return {
            "file": filepath,
            "backend": self.backend.name,
            "backend_version": self.backend.version,
            "functions": {k: v.to_dict() for k, v in parse_result.functions.items()},
            "structs": {k: v.to_dict() for k, v in parse_result.structs.items()},
            "struct_ops": self.struct_ops,
            "async_handlers": [asdict(h) for h in self.async_handlers],
            "call_tree": self._call_tree_to_dict(call_tree),
            "summary": self._generate_summary(parse_result)
        }
    
    def _extract_async_handlers(self, content: str) -> None:
        """提取异步处理函数"""
        for handler_type, pattern_info in self.ASYNC_PATTERNS.items():
            for pattern in pattern_info['init']:
                for match in re.finditer(pattern, content):
                    groups = match.groups()
                    # 获取函数名（通常是最后一个或唯一的捕获组）
                    func_name = groups[-1] if groups else None
                    
                    if func_name and func_name != 'NULL':
                        line = content[:match.start()].count('\n') + 1
                        
                        # 检查是否已存在
                        exists = any(h.func_name == func_name and h.handler_type == handler_type 
                                    for h in self.async_handlers)
                        if not exists:
                            self.async_handlers.append(AsyncHandler(
                                handler_type=handler_type,
                                func_name=func_name,
                                init_pattern=match.group(0).strip(),
                                trigger_pattern=pattern_info['trigger'],
                                line=line,
                                context=pattern_info['context'],
                                extra_info={
                                    'icon': pattern_info['icon'],
                                    'desc': pattern_info['desc']
                                }
                            ))
    
    def _extract_struct_ops(self, content: str, parse_result: ParseResult) -> None:
        """提取结构体操作表"""
        struct_pattern = r'''
            (?:static\s+)?(?:const\s+)?
            struct\s+(\w+)\s+(\w+)\s*=\s*\{
            ([^}]+)
            \}
        '''
        
        for match in re.finditer(struct_pattern, content, re.VERBOSE):
            struct_type = match.group(1)
            var_name = match.group(2)
            init_content = match.group(3)
            
            mappings = {}
            for fm in re.finditer(r'\.(\w+)\s*=\s*(\w+)', init_content):
                field_name = fm.group(1)
                func_name = fm.group(2)
                mappings[field_name] = func_name
                
                # 标记为回调
                if func_name in parse_result.functions:
                    parse_result.functions[func_name].is_callback = True
                    parse_result.functions[func_name].callback_context = f"{struct_type}.{field_name}"
            
            if mappings:
                self.struct_ops.append({
                    'struct_type': struct_type,
                    'var_name': var_name,
                    'mappings': mappings,
                    'line': content[:match.start()].count('\n') + 1
                })
    
    def _apply_knowledge_base(self, parse_result: ParseResult) -> None:
        """应用知识库"""
        # module_init / module_exit
        init_match = re.search(r'module_init\s*\(\s*(\w+)\s*\)', self.source_content)
        if init_match and init_match.group(1) in parse_result.functions:
            parse_result.functions[init_match.group(1)].is_callback = True
            parse_result.functions[init_match.group(1)].callback_context = "module_init"
        
        exit_match = re.search(r'module_exit\s*\(\s*(\w+)\s*\)', self.source_content)
        if exit_match and exit_match.group(1) in parse_result.functions:
            parse_result.functions[exit_match.group(1)].is_callback = True
            parse_result.functions[exit_match.group(1)].callback_context = "module_exit"
    
    def _mark_async_callbacks(self, parse_result: ParseResult) -> None:
        """标记异步回调函数"""
        for handler in self.async_handlers:
            if handler.func_name in parse_result.functions:
                func = parse_result.functions[handler.func_name]
                func.is_callback = True
                func.callback_context = f"async_{handler.handler_type}"
    
    def _build_call_tree(self, parse_result: ParseResult) -> List[CallNode]:
        """构建调用树"""
        trees = []
        
        # 入口点信息
        entry_points = {
            "module_init": {"icon": "🚀", "desc": "模块加载"},
            "module_exit": {"icon": "🛑", "desc": "模块卸载"},
        }
        
        # 从知识库获取入口点
        for ops in self.struct_ops:
            struct_type = ops['struct_type']
            if struct_type in self.knowledge_base:
                kb_entry = self.knowledge_base[struct_type]
                for field_name, func_name in ops['mappings'].items():
                    ep_info = kb_entry.get('entry_points', {}).get(field_name, {})
                    entry_points[f"{struct_type}.{field_name}"] = {
                        "icon": ep_info.get("icon", "📌"),
                        "desc": ep_info.get("description", field_name),
                        "trigger": ep_info.get("trigger", ""),
                        "func": func_name
                    }
        
        # 添加异步入口
        for handler in self.async_handlers:
            key = f"async_{handler.handler_type}"
            if key not in entry_points:
                entry_points[key] = {
                    "icon": handler.extra_info.get('icon', '📌'),
                    "desc": handler.extra_info.get('desc', handler.handler_type),
                    "trigger": handler.trigger_pattern,
                    "context": handler.context
                }
        
        # 构建每个回调函数的调用树
        processed = set()
        for func_name, func_def in parse_result.functions.items():
            if func_def.is_callback and func_name not in processed:
                context = func_def.callback_context
                info = entry_points.get(context, {"icon": "📌", "desc": context})
                
                # 获取异步处理函数的详细信息
                if context.startswith("async_"):
                    for handler in self.async_handlers:
                        if handler.func_name == func_name:
                            info = {
                                "icon": handler.extra_info.get('icon', '📌'),
                                "desc": handler.extra_info.get('desc', handler.handler_type),
                                "trigger": handler.trigger_pattern,
                                "context": handler.context
                            }
                            break
                
                node = self._build_call_subtree(func_name, parse_result, set())
                node.node_type = "entry_point"
                node.display_name = f"{info.get('icon', '📌')} [{info.get('desc', context)}] → {func_name}()"
                node.description = info.get("trigger", "")
                node.time_info = info.get("context", "")
                trees.append(node)
                processed.add(func_name)
        
        return trees
    
    def _build_call_subtree(self, func_name: str, parse_result: ParseResult, 
                           visited: Set[str], depth: int = 0) -> CallNode:
        """构建调用子树"""
        if func_name in visited or depth > 10:
            return CallNode(
                name=func_name,
                display_name=f"{func_name}() [递归]",
                node_type="recursive"
            )
        
        visited = visited.copy()
        visited.add(func_name)
        
        node = CallNode(name=func_name, display_name=f"{func_name}()")
        
        if func_name in parse_result.functions:
            func_def = parse_result.functions[func_name]
            node.line = func_def.location.line if func_def.location else 0
            
            for called in func_def.calls:
                if called in parse_result.functions:
                    child = self._build_call_subtree(called, parse_result, visited, depth + 1)
                    node.children.append(child)
                else:
                    # 外部函数
                    child = CallNode(
                        name=called,
                        display_name=f"{called}()",
                        node_type="kernel_api"
                    )
                    # 知识库查询
                    if "kernel_apis" in self.knowledge_base:
                        if called in self.knowledge_base["kernel_apis"]:
                            api_info = self.knowledge_base["kernel_apis"][called]
                            child.description = api_info.get("description", "")
                    node.children.append(child)
        
        return node
    
    def _call_tree_to_dict(self, trees: List[CallNode]) -> List[Dict]:
        """调用树转字典"""
        def node_to_dict(node: CallNode) -> Dict:
            return {
                "name": node.name,
                "display_name": node.display_name,
                "line": node.line,
                "type": node.node_type,
                "description": node.description,
                "time_info": node.time_info,
                "children": [node_to_dict(c) for c in node.children]
            }
        return [node_to_dict(t) for t in trees]
    
    def _generate_summary(self, parse_result: ParseResult) -> Dict:
        """生成摘要"""
        callbacks = sum(1 for f in parse_result.functions.values() if f.is_callback)
        
        # 异步分组
        async_by_type = {}
        for handler in self.async_handlers:
            htype = handler.handler_type
            if htype not in async_by_type:
                async_by_type[htype] = []
            async_by_type[htype].append({
                'func': handler.func_name,
                'context': handler.context,
                'line': handler.line
            })
        
        # 调用最多
        most_calls = sorted(
            parse_result.functions.items(),
            key=lambda x: len(x[1].calls),
            reverse=True
        )[:5]
        
        return {
            "total_functions": len(parse_result.functions),
            "total_structs": len(parse_result.structs),
            "callbacks": callbacks,
            "struct_ops_count": len(self.struct_ops),
            "struct_types": [s['struct_type'] for s in self.struct_ops],
            "async_handlers_count": len(self.async_handlers),
            "async_handlers_by_type": async_by_type,
            "most_complex": [(f[0], len(f[1].calls)) for f in most_calls],
            "backend": self.backend.name
        }


def main():
    parser = argparse.ArgumentParser(
        description='Linux 驱动代码分析器 (v0.2 - 使用可插拔后端)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s driver.c                    # 使用最佳后端分析
  %(prog)s driver.c -b regex           # 指定使用 regex 后端
  %(prog)s driver.c -b tree-sitter     # 指定使用 tree-sitter 后端
  %(prog)s driver.c -o result.json     # 输出到指定文件
"""
    )
    parser.add_argument('file', help='要分析的 C 源文件')
    parser.add_argument('-o', '--output', default='analysis_result.json',
                        help='输出 JSON 文件路径 (默认: analysis_result.json)')
    parser.add_argument('-b', '--backend', choices=['regex', 'tree-sitter', 'auto'],
                        default='auto', help='选择解析后端 (默认: auto)')
    parser.add_argument('-k', '--knowledge-base', default=None,
                        help='知识库路径')
    parser.add_argument('--list-backends', action='store_true',
                        help='列出可用后端')
    
    args = parser.parse_args()
    
    if args.list_backends:
        print(f"可用后端: {list_backends()}")
        return
    
    # 知识库路径
    kb_path = args.knowledge_base
    if not kb_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(script_dir, 'knowledge_base.json')
    
    # 选择后端
    backend_name = None if args.backend == 'auto' else args.backend
    
    # 分析
    analyzer = UnifiedAnalyzer(backend_name, kb_path)
    result = analyzer.analyze_file(args.file)
    
    # 输出
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"分析完成！结果已保存到: {args.output}")
    
    # 打印摘要
    summary = result['summary']
    print(f"\n📊 分析摘要 (后端: {summary['backend']}):")
    print(f"   函数总数: {summary['total_functions']}")
    print(f"   结构体: {summary['total_structs']}")
    print(f"   回调函数: {summary['callbacks']}")
    print(f"   操作结构体: {summary['struct_ops_count']} ({', '.join(summary['struct_types'])})")
    
    if summary.get('async_handlers_count', 0) > 0:
        print(f"\n   异步处理函数: {summary['async_handlers_count']}个")
        type_icons = {
            'work': '⚙️ 工作队列', 'delayed_work': '⏰ 延迟工作',
            'irq': '⚡ 硬中断', 'threaded_irq': '🧵 线程化中断',
            'tasklet': '🔄 Tasklet', 'timer': '⏲️ 定时器',
            'hrtimer': '⏱️ 高精度定时器', 'kthread': '🧵 内核线程',
        }
        for htype, handlers in summary.get('async_handlers_by_type', {}).items():
            print(f"     {type_icons.get(htype, htype)}:")
            for h in handlers:
                ctx = f" ({h['context']})" if h.get('context') else ""
                print(f"       - {h['func']}(){ctx}")
    
    if summary.get('most_complex'):
        print(f"\n   调用最多的函数:")
        for name, count in summary['most_complex']:
            if count > 0:
                print(f"     - {name}: {count}个调用")


if __name__ == '__main__':
    main()


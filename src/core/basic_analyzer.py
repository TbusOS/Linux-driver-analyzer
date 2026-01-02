#!/usr/bin/env python3
"""
C代码静态分析器 - 用于解析Linux驱动代码的函数调用关系

功能：
1. 解析C源代码，提取函数定义和调用关系
2. 识别函数指针和结构体操作表
3. 结合Linux内核知识库，推断回调调用时机
4. 生成JSON数据供可视化界面使用

不依赖编译器，纯静态分析
"""

import re
import json
import argparse
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path


@dataclass
class FunctionDef:
    """函数定义"""
    name: str
    return_type: str
    params: str
    start_line: int
    end_line: int
    body: str = ""
    calls: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)
    is_callback: bool = False
    callback_context: str = ""  # 如 "usb_driver.probe"
    

@dataclass
class StructOps:
    """操作结构体"""
    struct_type: str  # 如 usb_driver, file_operations
    var_name: str
    mappings: Dict[str, str] = field(default_factory=dict)  # 字段名 -> 函数名
    line: int = 0


@dataclass
class AsyncHandler:
    """异步处理函数（中断、工作队列、定时器等）"""
    handler_type: str  # irq, threaded_irq, work, delayed_work, tasklet, timer, kthread
    func_name: str
    init_pattern: str  # 初始化代码模式
    trigger_pattern: str  # 触发代码模式
    line: int = 0
    context: str = ""  # 执行上下文描述
    extra_info: Dict = field(default_factory=dict)  # 额外信息（如IRQ号、延迟时间等）


@dataclass 
class CallNode:
    """调用树节点"""
    name: str
    display_name: str = ""
    line: int = 0
    children: List['CallNode'] = field(default_factory=list)
    node_type: str = "function"  # function, callback, entry_point, kernel_api
    description: str = ""
    time_info: str = ""


class CAnalyzer:
    """C代码分析器"""
    
    def __init__(self, knowledge_base_path: str = None):
        self.functions: Dict[str, FunctionDef] = {}
        self.struct_ops: List[StructOps] = []
        self.async_handlers: List[AsyncHandler] = []  # 异步处理函数
        self.global_vars: Dict[str, str] = {}  # 变量名 -> 类型
        self.knowledge_base = {}
        self.source_lines: List[str] = []
        self.current_file = ""
        
        # 异步机制识别模式
        self.async_patterns = {
            # 工作队列
            'work': {
                'init': [
                    r'INIT_WORK\s*\(\s*&?(\w+(?:\.\w+|\->\w+)?)\s*,\s*(\w+)\s*\)',
                    r'INIT_WORK\s*\(\s*&(\w+)->(\w+)\s*,\s*(\w+)\s*\)',
                ],
                'trigger': r'schedule_work|queue_work',
                'context': '进程上下文，可睡眠',
                'icon': '⚙️',
                'desc': '工作队列'
            },
            # 延迟工作
            'delayed_work': {
                'init': [
                    r'INIT_DELAYED_WORK\s*\(\s*&?(\w+(?:\.\w+|\->\w+)?)\s*,\s*(\w+)\s*\)',
                ],
                'trigger': r'schedule_delayed_work|queue_delayed_work',
                'context': '进程上下文，可睡眠',
                'icon': '⏰',
                'desc': '延迟工作队列'
            },
            # 硬中断
            'irq': {
                'init': [
                    r'request_irq\s*\([^,]+,\s*(\w+)\s*,',
                    r'devm_request_irq\s*\([^,]+,\s*[^,]+,\s*(\w+)\s*,',
                ],
                'trigger': '硬件中断触发',
                'context': '中断上下文，不可睡眠，不可调度',
                'icon': '⚡',
                'desc': '硬中断处理'
            },
            # 线程化中断
            'threaded_irq': {
                'init': [
                    r'request_threaded_irq\s*\([^,]+,\s*(\w+)\s*,\s*(\w+)\s*,',
                    r'devm_request_threaded_irq\s*\([^,]+,\s*[^,]+,\s*(\w+)\s*,\s*(\w+)\s*,',
                ],
                'trigger': '硬件中断触发后由内核线程执行',
                'context': '进程上下文，可睡眠',
                'icon': '🧵',
                'desc': '线程化中断'
            },
            # Tasklet
            'tasklet': {
                'init': [
                    r'tasklet_init\s*\(\s*&?(\w+(?:\.\w+|\->\w+)?)\s*,\s*(\w+)\s*,',
                    r'DECLARE_TASKLET\s*\(\s*(\w+)\s*,\s*(\w+)\s*,',
                    r'DECLARE_TASKLET_DISABLED\s*\(\s*(\w+)\s*,\s*(\w+)\s*,',
                ],
                'trigger': r'tasklet_schedule|tasklet_hi_schedule',
                'context': '软中断上下文，不可睡眠',
                'icon': '🔄',
                'desc': 'Tasklet软中断'
            },
            # 定时器
            'timer': {
                'init': [
                    r'timer_setup\s*\(\s*&?(\w+(?:\.\w+|\->\w+)?)\s*,\s*(\w+)\s*,',
                    r'setup_timer\s*\(\s*&?(\w+(?:\.\w+|\->\w+)?)\s*,\s*(\w+)\s*,',
                    r'DEFINE_TIMER\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)',
                ],
                'trigger': r'mod_timer|add_timer',
                'context': '软中断上下文，不可睡眠',
                'icon': '⏲️',
                'desc': '内核定时器'
            },
            # 高精度定时器
            'hrtimer': {
                'init': [
                    r'hrtimer_init\s*\([^)]+\)',
                    # hrtimer的回调通过 timer->function = xxx 设置
                ],
                'trigger': r'hrtimer_start|hrtimer_restart',
                'context': '硬中断上下文',
                'icon': '⏱️',
                'desc': '高精度定时器'
            },
            # 内核线程
            'kthread': {
                'init': [
                    r'kthread_create\s*\(\s*(\w+)\s*,',
                    r'kthread_run\s*\(\s*(\w+)\s*,',
                ],
                'trigger': 'wake_up_process 或创建时自动启动',
                'context': '进程上下文，可睡眠',
                'icon': '🧵',
                'desc': '内核线程'
            },
            # 高精度定时器回调（通过赋值）
            'hrtimer_assign': {
                'init': [
                    r'(\w+(?:\.\w+|\->\w+)*)\.function\s*=\s*(\w+)',
                    r'(\w+(?:\.\w+|\->\w+)*)->function\s*=\s*(\w+)',
                ],
                'trigger': 'hrtimer_start/hrtimer_restart',
                'context': '硬中断上下文',
                'icon': '⏱️',
                'desc': '高精度定时器'
            },
            # RCU回调
            'rcu': {
                'init': [
                    r'call_rcu\s*\([^,]+,\s*(\w+)\s*\)',
                    r'call_rcu_bh\s*\([^,]+,\s*(\w+)\s*\)',
                ],
                'trigger': 'RCU宽限期结束后',
                'context': '软中断上下文',
                'icon': '🔒',
                'desc': 'RCU回调'
            },
        }
        
        # 加载知识库
        if knowledge_base_path and os.path.exists(knowledge_base_path):
            with open(knowledge_base_path, 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
    
    def analyze_file(self, filepath: str) -> Dict:
        """分析单个C文件"""
        self.current_file = filepath
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            self.source_lines = content.split('\n')
        
        # 预处理：移除注释
        content_no_comments = self._remove_comments(content)
        
        # 第一遍：提取函数定义
        self._extract_functions(content_no_comments)
        
        # 第二遍：分析函数体中的调用
        self._analyze_calls()
        
        # 第三遍：识别操作结构体
        self._extract_struct_ops(content_no_comments)
        
        # 第四遍：识别module_init/exit
        self._extract_module_entry(content_no_comments)
        
        # 第五遍：识别异步处理函数（中断、工作队列、定时器等）
        self._extract_async_handlers(content_no_comments)
        
        # 构建调用树
        call_tree = self._build_call_tree()
        
        return {
            "file": filepath,
            "functions": {k: asdict(v) for k, v in self.functions.items()},
            "struct_ops": [asdict(s) for s in self.struct_ops],
            "async_handlers": [asdict(h) for h in self.async_handlers],
            "call_tree": self._call_tree_to_dict(call_tree),
            "summary": self._generate_summary()
        }
    
    def _remove_comments(self, content: str) -> str:
        """移除C语言注释"""
        # 移除多行注释
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # 移除单行注释
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        return content
    
    def _extract_functions(self, content: str):
        """提取函数定义"""
        # 匹配函数定义的正则
        # 支持 static, inline, __init, __exit 等修饰符
        func_pattern = r'''
            (?:^|\n)                              # 行首
            \s*                                   # 可选空白
            (?:static\s+)?                        # 可选static
            (?:inline\s+)?                        # 可选inline
            (?:__init\s+|__exit\s+)?              # 可选__init/__exit
            ([\w\s\*]+?)                          # 返回类型
            \s+                                   # 空白
            (\w+)                                 # 函数名
            \s*\(                                 # 左括号
            ([^)]*?)                              # 参数
            \)\s*                                 # 右括号
            \{                                    # 函数体开始
        '''
        
        for match in re.finditer(func_pattern, content, re.VERBOSE | re.MULTILINE):
            return_type = match.group(1).strip()
            func_name = match.group(2).strip()
            params = match.group(3).strip()
            
            # 跳过一些宏定义
            if func_name in ['if', 'while', 'for', 'switch', 'sizeof', 'typeof']:
                continue
                
            # 找到函数体
            start_pos = match.end() - 1  # 从 { 开始
            end_pos = self._find_matching_brace(content, start_pos)
            body = content[start_pos:end_pos+1] if end_pos > start_pos else ""
            
            # 计算行号
            start_line = content[:match.start()].count('\n') + 1
            end_line = content[:end_pos].count('\n') + 1 if end_pos > 0 else start_line
            
            self.functions[func_name] = FunctionDef(
                name=func_name,
                return_type=return_type,
                params=params,
                start_line=start_line,
                end_line=end_line,
                body=body
            )
    
    def _find_matching_brace(self, content: str, start: int) -> int:
        """找到匹配的右大括号"""
        if start >= len(content) or content[start] != '{':
            return -1
            
        count = 1
        pos = start + 1
        in_string = False
        in_char = False
        
        while pos < len(content) and count > 0:
            c = content[pos]
            prev = content[pos-1] if pos > 0 else ''
            
            # 处理字符串和字符
            if c == '"' and prev != '\\' and not in_char:
                in_string = not in_string
            elif c == "'" and prev != '\\' and not in_string:
                in_char = not in_char
            elif not in_string and not in_char:
                if c == '{':
                    count += 1
                elif c == '}':
                    count -= 1
            
            pos += 1
        
        return pos - 1 if count == 0 else -1
    
    def _analyze_calls(self):
        """分析函数调用"""
        # 函数调用模式
        call_pattern = r'\b(\w+)\s*\('
        
        for func_name, func_def in self.functions.items():
            body = func_def.body
            calls = set()
            
            for match in re.finditer(call_pattern, body):
                called = match.group(1)
                # 排除关键字和宏
                if called not in ['if', 'while', 'for', 'switch', 'return', 
                                  'sizeof', 'typeof', 'container_of',
                                  'INIT_WORK', 'DECLARE_WORK']:
                    calls.add(called)
            
            func_def.calls = list(calls)
            
            # 更新被调用关系
            for called in calls:
                if called in self.functions:
                    self.functions[called].called_by.append(func_name)
    
    def _extract_struct_ops(self, content: str):
        """提取操作结构体定义"""
        # 匹配结构体初始化
        # 例如: static struct usb_driver xxx = { .probe = func, };
        struct_pattern = r'''
            (?:static\s+)?
            (?:const\s+)?
            struct\s+(\w+)\s+       # 结构体类型
            (\w+)\s*=\s*\{          # 变量名
            ([^}]+)                  # 初始化内容
            \}
        '''
        
        for match in re.finditer(struct_pattern, content, re.VERBOSE):
            struct_type = match.group(1)
            var_name = match.group(2)
            init_content = match.group(3)
            
            # 解析字段映射
            mappings = {}
            field_pattern = r'\.(\w+)\s*=\s*(\w+)'
            for fm in re.finditer(field_pattern, init_content):
                field_name = fm.group(1)
                func_name = fm.group(2)
                mappings[field_name] = func_name
                
                # 标记回调函数
                if func_name in self.functions:
                    self.functions[func_name].is_callback = True
                    self.functions[func_name].callback_context = f"{struct_type}.{field_name}"
            
            if mappings:
                line = content[:match.start()].count('\n') + 1
                self.struct_ops.append(StructOps(
                    struct_type=struct_type,
                    var_name=var_name,
                    mappings=mappings,
                    line=line
                ))
    
    def _extract_module_entry(self, content: str):
        """提取模块入口"""
        # module_init/module_exit
        init_match = re.search(r'module_init\s*\(\s*(\w+)\s*\)', content)
        exit_match = re.search(r'module_exit\s*\(\s*(\w+)\s*\)', content)
        
        if init_match:
            func_name = init_match.group(1)
            if func_name in self.functions:
                self.functions[func_name].is_callback = True
                self.functions[func_name].callback_context = "module_init"
        
        if exit_match:
            func_name = exit_match.group(1)
            if func_name in self.functions:
                self.functions[func_name].is_callback = True
                self.functions[func_name].callback_context = "module_exit"
    
    def _extract_async_handlers(self, content: str):
        """提取异步处理函数（中断、工作队列、定时器等）"""
        for handler_type, pattern_info in self.async_patterns.items():
            init_patterns = pattern_info.get('init', [])
            
            for pattern in init_patterns:
                for match in re.finditer(pattern, content):
                    # 获取函数名（通常是最后一个捕获组）
                    groups = match.groups()
                    func_name = None
                    var_name = None
                    
                    # 根据不同类型解析
                    if handler_type in ['irq', 'kthread', 'rcu']:
                        # 只有一个函数名
                        func_name = groups[0] if groups else None
                    elif handler_type == 'threaded_irq':
                        # 有硬中断处理和线程处理两个函数
                        if len(groups) >= 2:
                            hard_irq_handler = groups[0]
                            thread_handler = groups[1]
                            # 添加硬中断处理
                            if hard_irq_handler and hard_irq_handler != 'NULL':
                                self._add_async_handler('irq', hard_irq_handler, 
                                    match.group(0), content, match.start())
                            # 添加线程处理
                            if thread_handler and thread_handler != 'NULL':
                                self._add_async_handler('threaded_irq', thread_handler,
                                    match.group(0), content, match.start())
                            continue
                    else:
                        # 一般情况：变量名 + 函数名
                        if len(groups) >= 2:
                            var_name = groups[-2] if len(groups) > 1 else None
                            func_name = groups[-1]
                        elif len(groups) == 1:
                            func_name = groups[0]
                    
                    if func_name and func_name != 'NULL':
                        self._add_async_handler(handler_type, func_name,
                            match.group(0), content, match.start(), var_name)
    
    def _add_async_handler(self, handler_type: str, func_name: str, 
                           init_code: str, content: str, pos: int, 
                           var_name: str = None):
        """添加异步处理函数"""
        pattern_info = self.async_patterns.get(handler_type, {})
        line = content[:pos].count('\n') + 1
        
        handler = AsyncHandler(
            handler_type=handler_type,
            func_name=func_name,
            init_pattern=init_code.strip(),
            trigger_pattern=pattern_info.get('trigger', ''),
            line=line,
            context=pattern_info.get('context', ''),
            extra_info={
                'var_name': var_name,
                'icon': pattern_info.get('icon', '📌'),
                'desc': pattern_info.get('desc', handler_type)
            }
        )
        
        # 检查是否重复
        for existing in self.async_handlers:
            if existing.func_name == func_name and existing.handler_type == handler_type:
                return
        
        self.async_handlers.append(handler)
        
        # 标记函数为回调
        if func_name in self.functions:
            self.functions[func_name].is_callback = True
            self.functions[func_name].callback_context = f"async_{handler_type}"
    
    def _build_call_tree(self) -> List[CallNode]:
        """构建调用树"""
        trees = []
        processed_funcs = set()
        
        # 入口点分类
        entry_points = {
            "module_init": {"icon": "🚀", "desc": "模块加载"},
            "module_exit": {"icon": "🛑", "desc": "模块卸载"},
        }
        
        # 从知识库获取入口点描述
        for ops in self.struct_ops:
            struct_type = ops.struct_type
            if struct_type in self.knowledge_base:
                kb_entry = self.knowledge_base[struct_type]
                entry_points_info = kb_entry.get("entry_points", {})
                for field_name, func_name in ops.mappings.items():
                    if field_name in entry_points_info:
                        ep_info = entry_points_info[field_name]
                        entry_points[f"{struct_type}.{field_name}"] = {
                            "icon": ep_info.get("icon", "📌"),
                            "desc": ep_info.get("description", ""),
                            "trigger": ep_info.get("trigger", ""),
                            "func": func_name
                        }
        
        # 添加异步处理函数的入口点信息
        for handler in self.async_handlers:
            context_key = f"async_{handler.handler_type}"
            if context_key not in entry_points:
                entry_points[context_key] = {
                    "icon": handler.extra_info.get('icon', '📌'),
                    "desc": handler.extra_info.get('desc', handler.handler_type),
                    "trigger": handler.trigger_pattern if isinstance(handler.trigger_pattern, str) else '',
                    "context": handler.context
                }
        
        # 为每个入口点构建调用树
        for func_name, func_def in self.functions.items():
            if func_def.is_callback and func_name not in processed_funcs:
                context = func_def.callback_context
                info = entry_points.get(context, {"icon": "📌", "desc": context})
                
                # 对于异步处理函数，尝试获取更详细的信息
                if context.startswith("async_"):
                    for handler in self.async_handlers:
                        if handler.func_name == func_name:
                            info = {
                                "icon": handler.extra_info.get('icon', '📌'),
                                "desc": handler.extra_info.get('desc', handler.handler_type),
                                "trigger": handler.trigger_pattern if isinstance(handler.trigger_pattern, str) else '',
                                "context": handler.context
                            }
                            break
                
                node = self._build_call_subtree(func_name, visited=set())
                node.node_type = "entry_point"
                node.display_name = f"{info.get('icon', '📌')} [{info.get('desc', context)}] → {func_name}()"
                node.description = info.get("trigger", "")
                if info.get("context"):
                    node.time_info = info.get("context")
                trees.append(node)
                processed_funcs.add(func_name)
        
        return trees
    
    def _build_call_subtree(self, func_name: str, visited: Set[str], depth: int = 0) -> CallNode:
        """递归构建调用子树"""
        if func_name in visited or depth > 10:
            node = CallNode(name=func_name)
            node.display_name = f"{func_name}() [递归/已访问]"
            node.node_type = "recursive"
            return node
        
        visited = visited.copy()
        visited.add(func_name)
        
        node = CallNode(name=func_name)
        node.display_name = f"{func_name}()"
        
        if func_name in self.functions:
            func_def = self.functions[func_name]
            node.line = func_def.start_line
            node.node_type = "function"
            
            # 添加子调用
            for called in func_def.calls:
                if called in self.functions:
                    child = self._build_call_subtree(called, visited, depth + 1)
                    node.children.append(child)
                else:
                    # 外部函数（内核API等）
                    child = CallNode(name=called)
                    child.display_name = f"{called}()"
                    child.node_type = "kernel_api"
                    
                    # 从知识库获取API描述
                    if "kernel_apis" in self.knowledge_base:
                        if called in self.knowledge_base["kernel_apis"]:
                            api_info = self.knowledge_base["kernel_apis"][called]
                            child.description = api_info.get("description", "")
                            child.time_info = api_info.get("time_hint", "")
                    
                    node.children.append(child)
        else:
            node.node_type = "external"
        
        return node
    
    def _call_tree_to_dict(self, trees: List[CallNode]) -> List[Dict]:
        """将调用树转换为字典格式"""
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
    
    def _generate_summary(self) -> Dict:
        """生成摘要信息"""
        total_functions = len(self.functions)
        callbacks = sum(1 for f in self.functions.values() if f.is_callback)
        
        # 找出没有被调用的函数（可能是入口点或未使用）
        not_called = [f.name for f in self.functions.values() 
                      if not f.called_by and not f.is_callback]
        
        # 找出调用最多的函数
        most_calls = sorted(self.functions.items(), 
                           key=lambda x: len(x[1].calls), reverse=True)[:5]
        
        # 异步处理函数统计
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
        
        return {
            "total_functions": total_functions,
            "callbacks": callbacks,
            "struct_ops_count": len(self.struct_ops),
            "struct_types": [s.struct_type for s in self.struct_ops],
            "async_handlers_count": len(self.async_handlers),
            "async_handlers_by_type": async_by_type,
            "unused_functions": not_called,
            "most_complex": [(f[0], len(f[1].calls)) for f in most_calls]
        }


def analyze_multiple_files(files: List[str], knowledge_base_path: str = None) -> Dict:
    """分析多个文件"""
    analyzer = CAnalyzer(knowledge_base_path)
    results = []
    
    for filepath in files:
        if os.path.exists(filepath):
            result = analyzer.analyze_file(filepath)
            results.append(result)
    
    return {
        "files": results,
        "cross_file_calls": []  # TODO: 跨文件调用分析
    }


def main():
    parser = argparse.ArgumentParser(description='C代码静态分析器')
    parser.add_argument('files', nargs='+', help='要分析的C源文件')
    parser.add_argument('-o', '--output', default='analysis_result.json',
                        help='输出JSON文件路径')
    parser.add_argument('-k', '--knowledge-base', 
                        default='kernel_knowledge.json',
                        help='Linux内核知识库路径')
    parser.add_argument('--html', action='store_true',
                        help='同时生成HTML可视化文件')
    
    args = parser.parse_args()
    
    # 获取知识库路径
    kb_path = args.knowledge_base
    if not os.path.isabs(kb_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(script_dir, kb_path)
    
    # 分析文件
    if len(args.files) == 1:
        analyzer = CAnalyzer(kb_path)
        result = analyzer.analyze_file(args.files[0])
    else:
        result = analyze_multiple_files(args.files, kb_path)
    
    # 输出JSON
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"分析完成！结果已保存到: {args.output}")
    
    # 打印摘要
    if 'summary' in result:
        summary = result['summary']
        print(f"\n📊 分析摘要:")
        print(f"   函数总数: {summary['total_functions']}")
        print(f"   回调函数: {summary['callbacks']}")
        print(f"   操作结构体: {summary['struct_ops_count']} ({', '.join(summary['struct_types'])})")
        
        # 打印异步处理函数
        if summary.get('async_handlers_count', 0) > 0:
            print(f"\n   异步处理函数: {summary['async_handlers_count']}个")
            async_types = summary.get('async_handlers_by_type', {})
            type_icons = {
                'work': '⚙️ 工作队列',
                'delayed_work': '⏰ 延迟工作',
                'irq': '⚡ 硬中断',
                'threaded_irq': '🧵 线程化中断',
                'tasklet': '🔄 Tasklet',
                'timer': '⏲️ 定时器',
                'hrtimer': '⏱️ 高精度定时器',
                'hrtimer_assign': '⏱️ 高精度定时器',
                'kthread': '🧵 内核线程',
                'rcu': '🔒 RCU回调',
            }
            for htype, handlers in async_types.items():
                type_desc = type_icons.get(htype, htype)
                print(f"     {type_desc}:")
                for h in handlers:
                    ctx = f" ({h['context']})" if h.get('context') else ""
                    print(f"       - {h['func']}(){ctx}")
        
        if summary.get('most_complex'):
            print(f"\n   调用最多的函数:")
            for name, count in summary['most_complex']:
                print(f"     - {name}: {count}个调用")


if __name__ == '__main__':
    main()


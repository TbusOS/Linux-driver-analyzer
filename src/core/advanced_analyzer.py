#!/usr/bin/env python3
"""
高级C代码分析器 - 使用多层分析架构

层次：
1. 语法分析层 - 基于正则和模式匹配（可升级为tree-sitter）
2. 符号索引层 - 构建符号表和交叉引用
3. 类型分析层 - 分析结构体、函数指针类型
4. 语义增强层 - Linux内核知识库

输出：
- 函数调用图
- 数据结构关系图
- 函数指针映射
"""

import re
import json
import argparse
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict


# ==================== 数据结构定义 ====================

@dataclass
class StructField:
    """结构体字段"""
    name: str
    type_name: str
    is_pointer: bool = False
    is_function_ptr: bool = False
    func_ptr_signature: str = ""
    array_size: str = ""
    line: int = 0
    comment: str = ""


@dataclass
class StructDef:
    """结构体定义"""
    name: str
    fields: List[StructField] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    typedef_name: str = ""  # typedef struct xxx { } yyy 中的 yyy
    embedded_structs: List[str] = field(default_factory=list)  # 内嵌的结构体
    referenced_structs: List[str] = field(default_factory=list)  # 引用的结构体


@dataclass
class FunctionDef:
    """函数定义"""
    name: str
    return_type: str
    params: List[Tuple[str, str]] = field(default_factory=list)  # [(类型, 名称), ...]
    start_line: int = 0
    end_line: int = 0
    calls: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)
    uses_structs: List[str] = field(default_factory=list)  # 使用的结构体
    is_callback: bool = False
    callback_context: str = ""
    attributes: List[str] = field(default_factory=list)  # __init, static等


@dataclass
class FunctionPtrAssignment:
    """函数指针赋值"""
    struct_type: str  # 结构体类型
    field_name: str   # 字段名
    func_name: str    # 被赋值的函数名
    var_name: str     # 变量名
    line: int = 0
    context: str = ""  # 上下文信息


@dataclass
class SymbolRef:
    """符号引用"""
    name: str
    ref_type: str  # 'call', 'use', 'assign', 'declare'
    location: Tuple[int, int] = (0, 0)  # (line, column)
    context: str = ""


# ==================== 高级分析器 ====================

class AdvancedCAnalyzer:
    """高级C代码分析器"""
    
    def __init__(self, knowledge_base_path: str = None):
        # 符号表
        self.structs: Dict[str, StructDef] = {}
        self.functions: Dict[str, FunctionDef] = {}
        self.typedefs: Dict[str, str] = {}  # typedef别名 -> 原始类型
        self.macros: Dict[str, str] = {}
        self.global_vars: Dict[str, str] = {}  # 变量名 -> 类型
        
        # 引用关系
        self.func_ptr_assignments: List[FunctionPtrAssignment] = []
        self.struct_relations: Dict[str, Set[str]] = defaultdict(set)  # A -> {B, C} 表示A包含B,C的指针/实例
        self.call_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_call_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # 源代码
        self.source_lines: List[str] = []
        self.source_content: str = ""
        self.current_file: str = ""
        
        # 知识库
        self.knowledge_base = {}
        if knowledge_base_path and os.path.exists(knowledge_base_path):
            with open(knowledge_base_path, 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
        
        # 常见的内核结构体类型（用于识别）
        self.kernel_struct_patterns = [
            'driver', 'device', 'operations', 'ops', 'handler',
            'callback', 'notifier', 'desc', 'info', 'data',
            'request', 'context', 'private', 'platform'
        ]
    
    def analyze_file(self, filepath: str) -> Dict:
        """分析单个C文件"""
        self.current_file = filepath
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            self.source_content = f.read()
            self.source_lines = self.source_content.split('\n')
        
        # 预处理
        content = self._preprocess(self.source_content)
        
        # 第一遍：提取结构体定义
        self._extract_structs(content)
        
        # 第二遍：提取typedef
        self._extract_typedefs(content)
        
        # 第三遍：提取函数定义
        self._extract_functions(content)
        
        # 第四遍：分析函数体
        self._analyze_function_bodies()
        
        # 第五遍：提取函数指针赋值（结构体初始化）
        self._extract_func_ptr_assignments(content)
        
        # 第六遍：分析结构体关系
        self._analyze_struct_relations()
        
        # 第七遍：应用知识库增强
        self._apply_knowledge_base()
        
        # 构建输出
        return self._build_output()
    
    def _preprocess(self, content: str) -> str:
        """预处理：移除注释，保留行号信息"""
        # 移除多行注释
        content = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), content, flags=re.DOTALL)
        # 移除单行注释
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        return content
    
    def _extract_structs(self, content: str):
        """提取结构体定义"""
        # 匹配 struct xxx { ... }
        struct_pattern = r'''
            (?:typedef\s+)?
            struct\s+(\w+)?\s*   # 结构体名（可选）
            \{                    # 开始大括号
            ([^{}]*(?:\{[^{}]*\}[^{}]*)*)  # 内容（支持嵌套一层）
            \}\s*
            (\w+)?                # typedef名（可选）
            \s*;
        '''
        
        for match in re.finditer(struct_pattern, content, re.VERBOSE | re.DOTALL):
            struct_name = match.group(1) or match.group(3) or f"anonymous_{match.start()}"
            body = match.group(2)
            typedef_name = match.group(3) or ""
            
            start_line = content[:match.start()].count('\n') + 1
            end_line = content[:match.end()].count('\n') + 1
            
            struct_def = StructDef(
                name=struct_name,
                start_line=start_line,
                end_line=end_line,
                typedef_name=typedef_name
            )
            
            # 解析字段
            struct_def.fields = self._parse_struct_fields(body, start_line)
            
            # 分析引用的结构体
            for f in struct_def.fields:
                # 提取类型中的结构体名
                type_match = re.search(r'struct\s+(\w+)', f.type_name)
                if type_match:
                    struct_def.referenced_structs.append(type_match.group(1))
                # 检查是否是已知的结构体类型
                elif f.type_name.replace('*', '').strip() in self.structs:
                    struct_def.referenced_structs.append(f.type_name.replace('*', '').strip())
            
            self.structs[struct_name] = struct_def
            if typedef_name and typedef_name != struct_name:
                self.typedefs[typedef_name] = f"struct {struct_name}"
    
    def _parse_struct_fields(self, body: str, base_line: int) -> List[StructField]:
        """解析结构体字段"""
        fields = []
        
        # 分割字段
        lines = body.split('\n')
        current_line = base_line
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                current_line += 1
                continue
            
            # 函数指针: 返回类型 (*名称)(参数)
            func_ptr_match = re.match(
                r'(.+?)\s*\(\s*\*\s*(\w+)\s*\)\s*\(([^)]*)\)\s*;',
                line
            )
            if func_ptr_match:
                return_type = func_ptr_match.group(1).strip()
                field_name = func_ptr_match.group(2)
                params = func_ptr_match.group(3)
                fields.append(StructField(
                    name=field_name,
                    type_name=f"{return_type} (*)({params})",
                    is_pointer=True,
                    is_function_ptr=True,
                    func_ptr_signature=f"{return_type}({params})",
                    line=current_line
                ))
                current_line += 1
                continue
            
            # 普通字段: 类型 名称;
            field_match = re.match(
                r'((?:const\s+|volatile\s+|unsigned\s+|signed\s+|struct\s+|enum\s+)*\w+(?:\s*\*)*)\s+(\w+)(?:\[([^\]]*)\])?\s*;',
                line
            )
            if field_match:
                type_name = field_match.group(1).strip()
                field_name = field_match.group(2)
                array_size = field_match.group(3) or ""
                is_pointer = '*' in type_name
                
                fields.append(StructField(
                    name=field_name,
                    type_name=type_name,
                    is_pointer=is_pointer,
                    array_size=array_size,
                    line=current_line
                ))
            
            current_line += 1
        
        return fields
    
    def _extract_typedefs(self, content: str):
        """提取typedef定义"""
        # typedef 原类型 新名称;
        typedef_pattern = r'typedef\s+(.+?)\s+(\w+)\s*;'
        for match in re.finditer(typedef_pattern, content):
            original = match.group(1).strip()
            alias = match.group(2)
            if '{' not in original:  # 排除struct定义
                self.typedefs[alias] = original
    
    def _extract_functions(self, content: str):
        """提取函数定义"""
        # 函数模式
        func_pattern = r'''
            (?:^|\n)\s*
            ((?:static\s+|inline\s+|__init\s+|__exit\s+|__always_inline\s+)*)  # 属性
            ([\w\s\*]+?)                          # 返回类型
            \s+
            (\w+)                                  # 函数名
            \s*\(
            ([^)]*)                                # 参数
            \)\s*
            \{                                     # 函数体开始
        '''
        
        for match in re.finditer(func_pattern, content, re.VERBOSE):
            attrs = match.group(1).strip()
            return_type = match.group(2).strip()
            func_name = match.group(3)
            params_str = match.group(4).strip()
            
            # 跳过关键字
            if func_name in ['if', 'while', 'for', 'switch', 'sizeof', 'typeof']:
                continue
            
            # 解析参数
            params = self._parse_params(params_str)
            
            # 找函数体结束位置
            start_pos = match.end() - 1
            end_pos = self._find_matching_brace(content, start_pos)
            
            start_line = content[:match.start()].count('\n') + 1
            end_line = content[:end_pos].count('\n') + 1 if end_pos > 0 else start_line
            
            # 提取属性
            attributes = []
            if 'static' in attrs:
                attributes.append('static')
            if '__init' in attrs:
                attributes.append('__init')
            if '__exit' in attrs:
                attributes.append('__exit')
            if 'inline' in attrs:
                attributes.append('inline')
            
            func_def = FunctionDef(
                name=func_name,
                return_type=return_type,
                params=params,
                start_line=start_line,
                end_line=end_line,
                attributes=attributes
            )
            
            # 提取使用的结构体
            for param_type, param_name in params:
                struct_match = re.search(r'struct\s+(\w+)', param_type)
                if struct_match:
                    func_def.uses_structs.append(struct_match.group(1))
            
            self.functions[func_name] = func_def
    
    def _parse_params(self, params_str: str) -> List[Tuple[str, str]]:
        """解析函数参数"""
        if not params_str or params_str == 'void':
            return []
        
        params = []
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue
            
            # 匹配类型和名称
            match = re.match(r'(.+?)(\w+)\s*$', param)
            if match:
                param_type = match.group(1).strip()
                param_name = match.group(2)
                params.append((param_type, param_name))
            else:
                params.append((param, ''))
        
        return params
    
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
    
    def _analyze_function_bodies(self):
        """分析函数体，提取调用关系"""
        call_pattern = r'\b(\w+)\s*\('
        
        for func_name, func_def in self.functions.items():
            # 获取函数体
            if func_def.start_line <= 0 or func_def.end_line <= 0:
                continue
            
            body_lines = self.source_lines[func_def.start_line-1:func_def.end_line]
            body = '\n'.join(body_lines)
            
            # 提取函数调用
            calls = set()
            for match in re.finditer(call_pattern, body):
                called = match.group(1)
                if called not in ['if', 'while', 'for', 'switch', 'return', 
                                  'sizeof', 'typeof', 'container_of', 
                                  'offsetof', 'likely', 'unlikely']:
                    calls.add(called)
            
            func_def.calls = list(calls)
            
            # 更新调用图
            for called in calls:
                self.call_graph[func_name].add(called)
                self.reverse_call_graph[called].add(func_name)
        
        # 更新called_by
        for func_name, func_def in self.functions.items():
            func_def.called_by = list(self.reverse_call_graph.get(func_name, set()) & 
                                       set(self.functions.keys()))
    
    def _extract_func_ptr_assignments(self, content: str):
        """提取函数指针赋值（结构体初始化）"""
        # 匹配结构体初始化
        struct_init_pattern = r'''
            (?:static\s+)?
            (?:const\s+)?
            struct\s+(\w+)\s+      # 结构体类型
            (\w+)\s*=\s*\{         # 变量名
            ([^}]+)                 # 初始化内容
            \}
        '''
        
        for match in re.finditer(struct_init_pattern, content, re.VERBOSE):
            struct_type = match.group(1)
            var_name = match.group(2)
            init_content = match.group(3)
            line = content[:match.start()].count('\n') + 1
            
            # 解析字段赋值
            field_pattern = r'\.(\w+)\s*=\s*(\w+)'
            for fm in re.finditer(field_pattern, init_content):
                field_name = fm.group(1)
                value = fm.group(2)
                
                # 检查是否是函数名
                if value in self.functions:
                    assignment = FunctionPtrAssignment(
                        struct_type=struct_type,
                        field_name=field_name,
                        func_name=value,
                        var_name=var_name,
                        line=line
                    )
                    self.func_ptr_assignments.append(assignment)
                    
                    # 标记函数为回调
                    self.functions[value].is_callback = True
                    self.functions[value].callback_context = f"{struct_type}.{field_name}"
        
        # 检查直接赋值: xxx.func = handler 或 xxx->func = handler
        assign_pattern = r'(\w+)(?:\.|\->)(\w+)\s*=\s*(\w+)\s*;'
        for match in re.finditer(assign_pattern, content):
            var_name = match.group(1)
            field_name = match.group(2)
            value = match.group(3)
            
            if value in self.functions and field_name not in ['next', 'prev', 'parent', 'child']:
                line = content[:match.start()].count('\n') + 1
                # 尝试推断结构体类型
                struct_type = self._infer_var_type(var_name, content, match.start())
                
                assignment = FunctionPtrAssignment(
                    struct_type=struct_type or "unknown",
                    field_name=field_name,
                    func_name=value,
                    var_name=var_name,
                    line=line
                )
                self.func_ptr_assignments.append(assignment)
    
    def _infer_var_type(self, var_name: str, content: str, before_pos: int) -> Optional[str]:
        """推断变量类型"""
        # 在before_pos之前搜索变量声明
        search_content = content[:before_pos]
        
        # 模式1: struct xxx *var 或 struct xxx var
        pattern1 = rf'struct\s+(\w+)\s+\*?\s*{var_name}\b'
        match = re.search(pattern1, search_content)
        if match:
            return match.group(1)
        
        # 模式2: xxx_t *var (typedef)
        pattern2 = rf'(\w+_t)\s+\*?\s*{var_name}\b'
        match = re.search(pattern2, search_content)
        if match:
            typedef_name = match.group(1)
            if typedef_name in self.typedefs:
                original = self.typedefs[typedef_name]
                struct_match = re.search(r'struct\s+(\w+)', original)
                if struct_match:
                    return struct_match.group(1)
        
        return None
    
    def _analyze_struct_relations(self):
        """分析结构体之间的关系"""
        for struct_name, struct_def in self.structs.items():
            for field in struct_def.fields:
                # 提取字段类型中的结构体
                type_str = field.type_name
                
                # struct xxx
                match = re.search(r'struct\s+(\w+)', type_str)
                if match:
                    referenced = match.group(1)
                    if referenced != struct_name:
                        self.struct_relations[struct_name].add(referenced)
                
                # 检查typedef的结构体
                base_type = type_str.replace('*', '').replace('const', '').strip()
                if base_type in self.typedefs:
                    original = self.typedefs[base_type]
                    match = re.search(r'struct\s+(\w+)', original)
                    if match and match.group(1) != struct_name:
                        self.struct_relations[struct_name].add(match.group(1))
    
    def _apply_knowledge_base(self):
        """应用知识库增强语义信息"""
        for assignment in self.func_ptr_assignments:
            struct_type = assignment.struct_type
            field_name = assignment.field_name
            
            # 从知识库获取信息
            if struct_type in self.knowledge_base:
                kb_entry = self.knowledge_base[struct_type]
                entry_points = kb_entry.get('entry_points', {})
                
                if field_name in entry_points:
                    ep_info = entry_points[field_name]
                    assignment.context = ep_info.get('trigger', '')
                    
                    # 更新函数信息
                    if assignment.func_name in self.functions:
                        func = self.functions[assignment.func_name]
                        func.callback_context = f"{struct_type}.{field_name}"
        
        # 检测异步处理函数
        self._detect_async_handlers()
    
    def _detect_async_handlers(self):
        """检测异步处理函数"""
        async_patterns = {
            'work': (r'INIT_WORK\s*\([^,]+,\s*(\w+)\s*\)', '⚙️ 工作队列', '进程上下文，可睡眠'),
            'delayed_work': (r'INIT_DELAYED_WORK\s*\([^,]+,\s*(\w+)\s*\)', '⏰ 延迟工作', '进程上下文，可睡眠'),
            'tasklet': (r'tasklet_init\s*\([^,]+,\s*(\w+)\s*,', '🔄 Tasklet', '软中断上下文'),
            'timer': (r'timer_setup\s*\([^,]+,\s*(\w+)\s*,', '⏲️ 定时器', '软中断上下文'),
            'irq': (r'request_irq\s*\([^,]+,\s*(\w+)\s*,', '⚡ 硬中断', '中断上下文'),
            'kthread': (r'kthread_run\s*\(\s*(\w+)\s*,', '🧵 内核线程', '进程上下文'),
        }
        
        for handler_type, (pattern, desc, context) in async_patterns.items():
            for match in re.finditer(pattern, self.source_content):
                func_name = match.group(1)
                if func_name in self.functions:
                    self.functions[func_name].is_callback = True
                    self.functions[func_name].callback_context = f"async_{handler_type}"
    
    def _build_output(self) -> Dict:
        """构建输出结果"""
        return {
            "file": self.current_file,
            "structs": {
                name: {
                    "name": s.name,
                    "fields": [asdict(f) for f in s.fields],
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "typedef_name": s.typedef_name,
                    "referenced_structs": list(set(s.referenced_structs)),
                }
                for name, s in self.structs.items()
            },
            "functions": {
                name: {
                    "name": f.name,
                    "return_type": f.return_type,
                    "params": f.params,
                    "start_line": f.start_line,
                    "end_line": f.end_line,
                    "calls": f.calls,
                    "called_by": f.called_by,
                    "uses_structs": list(set(f.uses_structs)),
                    "is_callback": f.is_callback,
                    "callback_context": f.callback_context,
                    "attributes": f.attributes,
                }
                for name, f in self.functions.items()
            },
            "func_ptr_assignments": [
                {
                    "struct_type": a.struct_type,
                    "field_name": a.field_name,
                    "func_name": a.func_name,
                    "var_name": a.var_name,
                    "line": a.line,
                    "context": a.context,
                }
                for a in self.func_ptr_assignments
            ],
            "struct_relations": {
                name: list(refs) for name, refs in self.struct_relations.items() if refs
            },
            "call_graph": {
                name: list(calls) for name, calls in self.call_graph.items()
            },
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> Dict:
        """生成分析摘要"""
        callbacks = [f for f in self.functions.values() if f.is_callback]
        
        # 按类型分组回调
        callback_groups = defaultdict(list)
        for f in callbacks:
            ctx = f.callback_context
            if ctx.startswith("async_"):
                callback_groups[ctx].append(f.name)
            else:
                parts = ctx.split('.')
                if len(parts) == 2:
                    callback_groups[parts[0]].append(f.name)
                else:
                    callback_groups["other"].append(f.name)
        
        return {
            "total_structs": len(self.structs),
            "total_functions": len(self.functions),
            "total_callbacks": len(callbacks),
            "callback_groups": dict(callback_groups),
            "func_ptr_assignments": len(self.func_ptr_assignments),
            "struct_with_relations": len([r for r in self.struct_relations.values() if r]),
        }


def main():
    parser = argparse.ArgumentParser(description='高级C代码分析器')
    parser.add_argument('files', nargs='+', help='要分析的C源文件')
    parser.add_argument('-o', '--output', default='advanced_analysis.json',
                        help='输出JSON文件路径')
    parser.add_argument('-k', '--knowledge-base',
                        default='kernel_knowledge.json',
                        help='知识库路径')
    parser.add_argument('--structs', action='store_true',
                        help='输出结构体关系图')
    
    args = parser.parse_args()
    
    # 知识库路径
    kb_path = args.knowledge_base
    if not os.path.isabs(kb_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(script_dir, kb_path)
    
    # 分析
    analyzer = AdvancedCAnalyzer(kb_path)
    result = analyzer.analyze_file(args.files[0])
    
    # 输出
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"分析完成！结果已保存到: {args.output}")
    
    # 打印摘要
    summary = result['summary']
    print(f"\n📊 分析摘要:")
    print(f"   结构体: {summary['total_structs']}")
    print(f"   函数: {summary['total_functions']}")
    print(f"   回调函数: {summary['total_callbacks']}")
    print(f"   函数指针赋值: {summary['func_ptr_assignments']}")
    
    # 打印回调分组
    if summary['callback_groups']:
        print(f"\n   回调函数分组:")
        for group, funcs in summary['callback_groups'].items():
            print(f"     {group}:")
            for func in funcs:
                print(f"       - {func}()")
    
    # 打印结构体关系
    if args.structs and result['struct_relations']:
        print(f"\n📦 结构体关系:")
        for struct_name, refs in result['struct_relations'].items():
            print(f"   {struct_name} -> {', '.join(refs)}")


if __name__ == '__main__':
    main()


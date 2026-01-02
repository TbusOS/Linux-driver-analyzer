#!/usr/bin/env python3
"""
正则匹配解析后端

使用正则表达式进行代码解析，特点：
- 无外部依赖，使用纯Python标准库
- 快速、容错性好
- 适合快速预览和无依赖环境

这是 v0.1 中使用的原始解析方式的封装。
"""

import re
from typing import Dict, List, Set, Optional, Tuple

from .base import (
    AnalyzerBackend, BackendCapability, BackendRegistry,
    ParseResult, FunctionDef, StructDef, StructField,
    FunctionCall, TypeDef, Parameter, Location
)


class RegexBackend(AnalyzerBackend):
    """
    正则匹配解析后端
    
    基于正则表达式的轻量级解析器，无需外部依赖。
    """
    
    def __init__(self):
        self._source_content = ""
        self._source_lines = []
    
    @property
    def name(self) -> str:
        return "regex"
    
    @property
    def version(self) -> str:
        return "0.1.0"
    
    def is_available(self) -> bool:
        return True  # 总是可用，无外部依赖
    
    def capabilities(self) -> Set[BackendCapability]:
        return {
            BackendCapability.PARSE_FUNCTIONS,
            BackendCapability.PARSE_STRUCTS,
            BackendCapability.PARSE_CALLS,
            BackendCapability.PARSE_TYPEDEFS,
            BackendCapability.BROWSER_COMPATIBLE,
        }
    
    def parse(self, source_code: str, filename: str = "<string>") -> ParseResult:
        """解析源代码"""
        self._source_content = source_code
        self._source_lines = source_code.split('\n')
        
        # 预处理：移除注释
        content = self._remove_comments(source_code)
        
        result = ParseResult()
        
        # 提取各种定义
        self._extract_structs(content, result)
        self._extract_typedefs(content, result)
        self._extract_functions(content, result)
        
        # 分析函数调用
        self._analyze_calls(result)
        
        # 识别回调函数
        self._identify_callbacks(content, result)
        
        return result
    
    def _remove_comments(self, content: str) -> str:
        """移除C语言注释"""
        # 移除多行注释，保留行数
        content = re.sub(
            r'/\*.*?\*/',
            lambda m: '\n' * m.group(0).count('\n'),
            content,
            flags=re.DOTALL
        )
        # 移除单行注释
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        return content
    
    def _extract_structs(self, content: str, result: ParseResult) -> None:
        """提取结构体定义"""
        struct_pattern = r'''
            (?:typedef\s+)?
            struct\s+(\w+)?\s*
            \{
            ([^{}]*(?:\{[^{}]*\}[^{}]*)*)
            \}\s*
            (\w+)?
            \s*;
        '''
        
        for match in re.finditer(struct_pattern, content, re.VERBOSE | re.DOTALL):
            struct_name = match.group(1) or match.group(3) or f"anonymous_{match.start()}"
            body = match.group(2)
            typedef_name = match.group(3) or ""
            
            start_line = content[:match.start()].count('\n') + 1
            end_line = content[:match.end()].count('\n') + 1
            
            # 解析字段
            fields = self._parse_struct_fields(body, start_line)
            
            # 分析引用的结构体
            referenced_structs = []
            for field in fields:
                type_match = re.search(r'struct\s+(\w+)', field.type_name)
                if type_match:
                    referenced_structs.append(type_match.group(1))
            
            struct_def = StructDef(
                name=struct_name,
                fields=fields,
                location=Location(line=start_line, end_line=end_line),
                typedef_name=typedef_name,
                referenced_structs=list(set(referenced_structs))
            )
            
            result.structs[struct_name] = struct_def
            
            if typedef_name and typedef_name != struct_name:
                result.typedefs[typedef_name] = TypeDef(
                    alias=typedef_name,
                    original=f"struct {struct_name}"
                )
    
    def _parse_struct_fields(self, body: str, base_line: int) -> List[StructField]:
        """解析结构体字段"""
        fields = []
        current_line = base_line
        
        for line in body.split('\n'):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('//'):
                current_line += 1
                continue
            
            # 函数指针: 返回类型 (*名称)(参数)
            func_ptr_match = re.match(
                r'(.+?)\s*\(\s*\*\s*(\w+)\s*\)\s*\(([^)]*)\)\s*;',
                line_stripped
            )
            if func_ptr_match:
                fields.append(StructField(
                    name=func_ptr_match.group(2),
                    type_name=f"{func_ptr_match.group(1)} (*)({func_ptr_match.group(3)})",
                    is_pointer=True,
                    is_function_ptr=True,
                    func_ptr_signature=f"{func_ptr_match.group(1)}({func_ptr_match.group(3)})",
                    location=Location(line=current_line)
                ))
                current_line += 1
                continue
            
            # 普通字段: 支持 struct xxx *name, int name, char name[32] 等
            # 匹配: 类型修饰符 + (struct/enum 类型名 | 普通类型) + 指针 + 字段名 + 可选数组
            field_match = re.match(
                r'((?:const\s+|volatile\s+|unsigned\s+|signed\s+)*'  # 类型修饰符
                r'(?:struct\s+\w+|enum\s+\w+|\w+)'  # struct xxx 或 enum xxx 或普通类型
                r'(?:\s*\*+)?)'  # 可选指针（支持 type* 或 type * 格式）
                r'\s*(\w+)'  # 字段名（前面可能有空格也可能没有）
                r'(?:\s*\[([^\]]*)\])?'  # 可选数组
                r'\s*;',
                line_stripped
            )
            if field_match:
                type_name = field_match.group(1).strip()
                field_name = field_match.group(2)
                array_size = field_match.group(3) or ""
                
                fields.append(StructField(
                    name=field_name,
                    type_name=type_name,
                    is_pointer='*' in type_name,
                    array_size=array_size,
                    location=Location(line=current_line)
                ))
            
            current_line += 1
        
        return fields
    
    def _extract_typedefs(self, content: str, result: ParseResult) -> None:
        """提取typedef定义"""
        typedef_pattern = r'typedef\s+(.+?)\s+(\w+)\s*;'
        
        for match in re.finditer(typedef_pattern, content):
            original = match.group(1).strip()
            alias = match.group(2)
            
            # 跳过struct定义
            if '{' in original:
                continue
            
            result.typedefs[alias] = TypeDef(
                alias=alias,
                original=original,
                location=Location(line=content[:match.start()].count('\n') + 1)
            )
    
    def _extract_functions(self, content: str, result: ParseResult) -> None:
        """提取函数定义"""
        # 先用简单模式找到函数开始位置，然后手动解析参数（处理嵌套括号）
        func_start_pattern = r'''
            (?:^|\n)\s*
            ((?:static\s+|inline\s+|__init\s+|__exit\s+|__always_inline\s+)*)
            ([\w\s\*]+?)
            \s+
            (\w+)
            \s*\(
        '''
        
        for match in re.finditer(func_start_pattern, content, re.VERBOSE):
            attrs_str = match.group(1).strip()
            return_type = match.group(2).strip()
            func_name = match.group(3)
            
            # 跳过关键字
            if func_name in ['if', 'while', 'for', 'switch', 'sizeof', 'typeof']:
                continue
            
            # 从 ( 开始找到匹配的 )，支持嵌套括号
            paren_start = match.end() - 1
            paren_end = self._find_matching_paren(content, paren_start)
            if paren_end < 0:
                continue
            
            params_str = content[paren_start + 1:paren_end].strip()
            
            # 检查参数后面是否是函数体 {
            after_paren = content[paren_end + 1:].lstrip()
            if not after_paren.startswith('{'):
                continue
            
            # 解析参数
            params = self._parse_params(params_str)
            
            # 找到函数体结束位置
            body_start = content.index('{', paren_end)
            end_pos = self._find_matching_brace(content, body_start)
            body = content[body_start:end_pos + 1] if end_pos > body_start else ""
            
            start_line = content[:match.start()].count('\n') + 1
            end_line = content[:end_pos].count('\n') + 1 if end_pos > 0 else start_line
            
            # 解析属性
            attributes = []
            for attr in ['static', '__init', '__exit', 'inline']:
                if attr in attrs_str:
                    attributes.append(attr)
            
            # 提取使用的结构体
            uses_structs = []
            for param in params:
                match_struct = re.search(r'struct\s+(\w+)', param.type_name)
                if match_struct:
                    uses_structs.append(match_struct.group(1))
            
            result.functions[func_name] = FunctionDef(
                name=func_name,
                return_type=return_type,
                params=params,
                body=body,
                location=Location(line=start_line, end_line=end_line),
                uses_structs=list(set(uses_structs)),
                attributes=attributes
            )
    
    def _parse_params(self, params_str: str) -> List[Parameter]:
        """解析函数参数"""
        if not params_str or params_str == 'void':
            return []
        
        params = []
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue
            
            match = re.match(r'(.+?)(\w+)\s*$', param)
            if match:
                params.append(Parameter(
                    name=match.group(2),
                    type_name=match.group(1).strip()
                ))
            else:
                params.append(Parameter(name='', type_name=param))
        
        return params
    
    def _find_matching_paren(self, content: str, start: int) -> int:
        """找到匹配的右括号，支持嵌套"""
        if start >= len(content) or content[start] != '(':
            return -1
        
        count = 1
        pos = start + 1
        in_string = False
        in_char = False
        
        while pos < len(content) and count > 0:
            c = content[pos]
            prev = content[pos - 1] if pos > 0 else ''
            
            if c == '"' and prev != '\\' and not in_char:
                in_string = not in_string
            elif c == "'" and prev != '\\' and not in_string:
                in_char = not in_char
            elif not in_string and not in_char:
                if c == '(':
                    count += 1
                elif c == ')':
                    count -= 1
            
            pos += 1
        
        return pos - 1 if count == 0 else -1
    
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
            prev = content[pos - 1] if pos > 0 else ''
            
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
    
    def _analyze_calls(self, result: ParseResult) -> None:
        """分析函数调用"""
        call_pattern = r'\b(\w+)\s*\('
        
        for func_name, func_def in result.functions.items():
            body = func_def.body
            calls = set()
            
            for match in re.finditer(call_pattern, body):
                called = match.group(1)
                if called not in ['if', 'while', 'for', 'switch', 'return',
                                 'sizeof', 'typeof', 'container_of',
                                 'offsetof', 'likely', 'unlikely']:
                    calls.add(called)
            
            func_def.calls = list(calls)
            
            # 更新 called_by
            for called in calls:
                if called in result.functions:
                    if func_name not in result.functions[called].called_by:
                        result.functions[called].called_by.append(func_name)
    
    def _identify_callbacks(self, content: str, result: ParseResult) -> None:
        """识别回调函数"""
        # 结构体初始化
        struct_init_pattern = r'''
            (?:static\s+)?
            (?:const\s+)?
            struct\s+(\w+)\s+
            (\w+)\s*=\s*\{
            ([^}]+)
            \}
        '''
        
        for match in re.finditer(struct_init_pattern, content, re.VERBOSE):
            struct_type = match.group(1)
            # var_name = match.group(2)  # 暂未使用
            init_content = match.group(3)
            
            field_pattern = r'\.(\w+)\s*=\s*(\w+)'
            for fm in re.finditer(field_pattern, init_content):
                field_name = fm.group(1)
                value = fm.group(2)
                
                if value in result.functions:
                    result.functions[value].is_callback = True
                    result.functions[value].callback_context = f"{struct_type}.{field_name}"
        
        # module_init/exit
        init_match = re.search(r'module_init\s*\(\s*(\w+)\s*\)', content)
        if init_match and init_match.group(1) in result.functions:
            result.functions[init_match.group(1)].is_callback = True
            result.functions[init_match.group(1)].callback_context = "module_init"
        
        exit_match = re.search(r'module_exit\s*\(\s*(\w+)\s*\)', content)
        if exit_match and exit_match.group(1) in result.functions:
            result.functions[exit_match.group(1)].is_callback = True
            result.functions[exit_match.group(1)].callback_context = "module_exit"


# 注册后端
BackendRegistry.register(RegexBackend)


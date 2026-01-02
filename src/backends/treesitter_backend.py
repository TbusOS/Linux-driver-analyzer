#!/usr/bin/env python3
"""
Tree-sitter 解析后端

使用 tree-sitter 进行精确的语法解析，相比正则匹配有以下优势：
- 基于真实的语法树，不会被注释/字符串干扰
- 精确的位置信息（行号、列号）
- 支持增量解析
- 可编译为 WASM 在浏览器运行

依赖安装：
    pip install tree-sitter tree-sitter-c
"""

import re
from typing import Dict, List, Set, Optional, Tuple, Any

from .base import (
    AnalyzerBackend, BackendCapability, BackendRegistry,
    ParseResult, FunctionDef, StructDef, StructField,
    FunctionCall, TypeDef, Parameter, Location,
    EnumDef, EnumValue, UnionDef
)


# Tree-sitter 可选导入
try:
    import tree_sitter_c as tsc
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Node = None


class TreeSitterBackend(AnalyzerBackend):
    """
    Tree-sitter C语言解析后端
    
    提供基于语法树的精确解析能力。
    """
    
    def __init__(self):
        self._parser = None
        self._source_bytes = b""
        self._source_lines = []
    
    @property
    def name(self) -> str:
        return "tree-sitter"
    
    @property
    def version(self) -> str:
        return "0.2.0"
    
    def is_available(self) -> bool:
        return TREE_SITTER_AVAILABLE
    
    def capabilities(self) -> Set[BackendCapability]:
        return {
            BackendCapability.PARSE_FUNCTIONS,
            BackendCapability.PARSE_STRUCTS,
            BackendCapability.PARSE_ENUMS,
            BackendCapability.PARSE_UNIONS,
            BackendCapability.PARSE_CALLS,
            BackendCapability.PARSE_TYPEDEFS,
            BackendCapability.PARSE_DECLARATIONS,
            BackendCapability.PRECISE_LOCATION,
            BackendCapability.BROWSER_COMPATIBLE,
            BackendCapability.INCREMENTAL,
        }
    
    def _get_parser(self) -> 'Parser':
        """获取或创建解析器"""
        if self._parser is None:
            if not TREE_SITTER_AVAILABLE:
                raise RuntimeError("tree-sitter 未安装，请运行: pip install tree-sitter tree-sitter-c")
            self._parser = Parser(Language(tsc.language()))
        return self._parser
    
    def _get_node_text(self, node: 'Node') -> str:
        """获取节点的文本内容"""
        return self._source_bytes[node.start_byte:node.end_byte].decode('utf-8')
    
    def _get_location(self, node: 'Node') -> Location:
        """获取节点的位置信息"""
        return Location(
            line=node.start_point[0] + 1,  # tree-sitter 行号从0开始
            column=node.start_point[1],
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1]
        )
    
    def parse(self, source_code: str, filename: str = "<string>") -> ParseResult:
        """解析源代码"""
        if not TREE_SITTER_AVAILABLE:
            return ParseResult(errors=["tree-sitter 未安装"])
        
        self._source_bytes = source_code.encode('utf-8')
        self._source_lines = source_code.split('\n')
        
        parser = self._get_parser()
        tree = parser.parse(self._source_bytes)
        
        result = ParseResult()
        
        # 遍历语法树提取信息
        self._extract_from_tree(tree.root_node, result)
        
        # 构建调用关系
        self._build_call_relations(result)
        
        return result
    
    def _extract_from_tree(self, node: 'Node', result: ParseResult) -> None:
        """递归遍历语法树提取信息"""
        
        if node.type == 'function_definition':
            func = self._extract_function(node)
            if func:
                result.functions[func.name] = func
        
        elif node.type == 'struct_specifier':
            # 检查是否是完整的结构体定义（有字段列表）
            body = node.child_by_field_name('body')
            if body:
                struct = self._extract_struct(node)
                if struct:
                    result.structs[struct.name] = struct
        
        elif node.type == 'enum_specifier':
            # 提取枚举定义（跳过 typedef 内部的，会在 type_definition 中处理）
            if node.parent and node.parent.type != 'type_definition':
                body = node.child_by_field_name('body')
                if body:
                    enum_def = self._extract_enum(node)
                    if enum_def:
                        result.enums[enum_def.name] = enum_def
        
        elif node.type == 'union_specifier':
            # 提取联合体定义（跳过 typedef 内部的，会在 type_definition 中处理）
            if node.parent and node.parent.type != 'type_definition':
                body = node.child_by_field_name('body')
                if body:
                    union_def = self._extract_union(node)
                    if union_def:
                        result.unions[union_def.name] = union_def
        
        elif node.type == 'type_definition':
            typedef = self._extract_typedef(node)
            if typedef:
                result.typedefs[typedef.alias] = typedef
            # 同时检查是否包含 enum/union/struct 定义
            self._extract_typedef_inner(node, result)
        
        elif node.type == 'declaration':
            # 检查是否是函数声明（非定义）
            self._check_function_declaration(node, result)
            # 检查是否是结构体初始化（如 static struct xxx yyy = {...}）
            self._check_struct_init(node, result)
        
        # 递归处理子节点
        for child in node.children:
            self._extract_from_tree(child, result)
    
    def _extract_function(self, node: 'Node') -> Optional[FunctionDef]:
        """提取函数定义"""
        # 获取返回类型
        return_type_node = node.child_by_field_name('type')
        return_type = self._get_node_text(return_type_node) if return_type_node else ""
        
        # 获取声明器（包含函数名和参数）
        declarator = node.child_by_field_name('declarator')
        if not declarator:
            return None
        
        # 提取函数名和参数
        func_name = None
        params = []
        attributes = []
        
        # 检查存储类说明符（static, inline 等）
        for child in node.children:
            if child.type == 'storage_class_specifier':
                attributes.append(self._get_node_text(child))
            elif child.type == 'type_qualifier':
                text = self._get_node_text(child)
                if text in ['__init', '__exit']:
                    attributes.append(text)
        
        # 处理函数声明器
        func_name, params = self._extract_function_declarator(declarator)
        
        if not func_name:
            return None
        
        # 获取函数体
        body_node = node.child_by_field_name('body')
        body = self._get_node_text(body_node) if body_node else ""
        
        # 提取函数调用
        calls = []
        if body_node:
            calls = self._extract_calls_from_body(body_node)
        
        # 提取使用的结构体
        uses_structs = self._extract_used_structs(params, body)
        
        return FunctionDef(
            name=func_name,
            return_type=return_type,
            params=params,
            body=body,
            location=self._get_location(node),
            calls=calls,
            uses_structs=uses_structs,
            attributes=attributes
        )
    
    def _extract_function_declarator(self, node: 'Node') -> Tuple[Optional[str], List[Parameter]]:
        """从声明器中提取函数名和参数"""
        func_name = None
        params = []
        
        if node.type == 'function_declarator':
            # 获取函数名
            name_node = node.child_by_field_name('declarator')
            if name_node:
                if name_node.type == 'identifier':
                    func_name = self._get_node_text(name_node)
                elif name_node.type == 'pointer_declarator':
                    # 指针函数，如 int *func()
                    inner = name_node.child_by_field_name('declarator')
                    if inner and inner.type == 'identifier':
                        func_name = self._get_node_text(inner)
            
            # 获取参数列表
            params_node = node.child_by_field_name('parameters')
            if params_node:
                params = self._extract_parameters(params_node)
        
        elif node.type == 'pointer_declarator':
            # 返回指针的函数
            inner = node.child_by_field_name('declarator')
            if inner:
                return self._extract_function_declarator(inner)
        
        return func_name, params
    
    def _extract_parameters(self, params_node: 'Node') -> List[Parameter]:
        """提取参数列表"""
        params = []
        
        for child in params_node.children:
            if child.type == 'parameter_declaration':
                param_type = ""
                param_name = ""
                
                type_node = child.child_by_field_name('type')
                if type_node:
                    param_type = self._get_node_text(type_node)
                
                decl_node = child.child_by_field_name('declarator')
                if decl_node:
                    # 处理指针等复杂声明
                    param_name = self._extract_declarator_name(decl_node)
                    # 如果声明器包含指针，添加到类型
                    if decl_node.type == 'pointer_declarator':
                        param_type += ' *'
                
                if param_type:
                    params.append(Parameter(name=param_name, type_name=param_type))
        
        return params
    
    def _extract_declarator_name(self, node: 'Node') -> str:
        """从声明器提取名称"""
        if node.type == 'identifier':
            return self._get_node_text(node)
        elif node.type == 'field_identifier':
            return self._get_node_text(node)
        elif node.type == 'pointer_declarator':
            inner = node.child_by_field_name('declarator')
            if inner:
                return self._extract_declarator_name(inner)
        elif node.type == 'array_declarator':
            inner = node.child_by_field_name('declarator')
            if inner:
                return self._extract_declarator_name(inner)
        return ""
    
    def _extract_pointer_field_name(self, node: 'Node') -> tuple:
        """
        从指针声明器提取字段名和额外的星号
        返回: (字段名, 额外星号字符串)
        """
        extra_stars = ""
        current = node
        
        while current and current.type == 'pointer_declarator':
            inner = current.child_by_field_name('declarator')
            if inner:
                if inner.type == 'field_identifier':
                    return self._get_node_text(inner), extra_stars
                elif inner.type == 'pointer_declarator':
                    extra_stars += '*'
                    current = inner
                else:
                    return self._extract_declarator_name(inner), extra_stars
            else:
                break
        
        return "", extra_stars
    
    def _extract_calls_from_body(self, body_node: 'Node') -> List[str]:
        """从函数体提取函数调用"""
        calls = set()
        
        def visit(node):
            if node.type == 'call_expression':
                func_node = node.child_by_field_name('function')
                if func_node:
                    if func_node.type == 'identifier':
                        call_name = self._get_node_text(func_node)
                        # 排除关键字和常见宏
                        if call_name not in ['if', 'while', 'for', 'switch', 'return',
                                            'sizeof', 'typeof', 'offsetof', 
                                            'container_of', 'likely', 'unlikely']:
                            calls.add(call_name)
            
            for child in node.children:
                visit(child)
        
        visit(body_node)
        return list(calls)
    
    def _extract_used_structs(self, params: List[Parameter], body: str) -> List[str]:
        """提取使用的结构体"""
        structs = set()
        
        # 从参数提取
        for param in params:
            match = re.search(r'struct\s+(\w+)', param.type_name)
            if match:
                structs.add(match.group(1))
        
        # 从函数体提取
        for match in re.finditer(r'struct\s+(\w+)', body):
            structs.add(match.group(1))
        
        return list(structs)
    
    def _extract_struct(self, node: 'Node') -> Optional[StructDef]:
        """提取结构体定义"""
        # 获取结构体名
        name_node = node.child_by_field_name('name')
        struct_name = self._get_node_text(name_node) if name_node else None
        
        if not struct_name:
            # 匿名结构体，生成临时名称
            struct_name = f"anonymous_{node.start_point[0]}"
        
        # 获取字段列表
        body_node = node.child_by_field_name('body')
        if not body_node:
            return None
        
        fields = []
        referenced_structs = set()
        
        for child in body_node.children:
            if child.type == 'field_declaration':
                field = self._extract_field(child)
                if field:
                    fields.append(field)
                    # 提取引用的结构体
                    match = re.search(r'struct\s+(\w+)', field.type_name)
                    if match:
                        referenced_structs.add(match.group(1))
        
        return StructDef(
            name=struct_name,
            fields=fields,
            location=self._get_location(node),
            referenced_structs=list(referenced_structs)
        )
    
    def _extract_field(self, node: 'Node') -> Optional[StructField]:
        """提取结构体字段"""
        type_node = node.child_by_field_name('type')
        type_name = self._get_node_text(type_node) if type_node else ""
        
        decl_node = node.child_by_field_name('declarator')
        if not decl_node:
            return None
        
        field_name = ""
        is_pointer = False
        is_function_ptr = False
        func_ptr_signature = ""
        array_size = ""
        
        # 处理不同类型的声明器
        if decl_node.type == 'field_identifier':
            field_name = self._get_node_text(decl_node)
        
        elif decl_node.type == 'pointer_declarator':
            is_pointer = True
            # 递归提取字段名，处理多级指针
            field_name, extra_stars = self._extract_pointer_field_name(decl_node)
            type_name += ' *' + extra_stars
        
        elif decl_node.type == 'array_declarator':
            inner = decl_node.child_by_field_name('declarator')
            if inner:
                if inner.type == 'field_identifier':
                    field_name = self._get_node_text(inner)
                else:
                    field_name = self._extract_declarator_name(inner)
            size_node = decl_node.child_by_field_name('size')
            if size_node:
                array_size = self._get_node_text(size_node)
        
        elif decl_node.type == 'function_declarator':
            # 函数指针字段
            is_function_ptr = True
            is_pointer = True
            # 这种情况比较复杂，直接获取完整文本
            full_text = self._get_node_text(node)
            # 尝试提取名称
            name_match = re.search(r'\(\s*\*\s*(\w+)\s*\)', full_text)
            if name_match:
                field_name = name_match.group(1)
            func_ptr_signature = full_text
        
        # 如果上述都没匹配到，尝试直接从节点文本提取
        if not field_name:
            # 尝试从完整字段声明中提取
            full_text = self._get_node_text(node).strip().rstrip(';')
            # 匹配最后一个标识符作为字段名
            match = re.search(r'(\w+)\s*$', full_text)
            if match:
                field_name = match.group(1)
        
        if not field_name:
            return None
        
        return StructField(
            name=field_name,
            type_name=type_name,
            is_pointer=is_pointer,
            is_function_ptr=is_function_ptr,
            func_ptr_signature=func_ptr_signature,
            array_size=array_size,
            location=self._get_location(node)
        )
    
    def _extract_typedef(self, node: 'Node') -> Optional[TypeDef]:
        """提取typedef定义"""
        # typedef 结构比较复杂，获取完整文本后解析
        full_text = self._get_node_text(node)
        
        # 简单typedef: typedef xxx yyy;
        match = re.match(r'typedef\s+(.+?)\s+(\w+)\s*;', full_text, re.DOTALL)
        if match:
            original = match.group(1).strip()
            alias = match.group(2)
            
            # 跳过结构体定义的typedef（会单独处理）
            if '{' in original:
                return None
            
            return TypeDef(
                alias=alias,
                original=original,
                location=self._get_location(node)
            )
        
        return None
    
    def _check_struct_init(self, node: 'Node', result: ParseResult) -> None:
        """检查结构体初始化，识别回调函数映射"""
        full_text = self._get_node_text(node)
        
        # 匹配 static struct xxx yyy = { .field = func, ... }
        match = re.match(
            r'(?:static\s+)?(?:const\s+)?struct\s+(\w+)\s+(\w+)\s*=\s*\{([^}]+)\}',
            full_text, re.DOTALL
        )
        
        if match:
            struct_type = match.group(1)
            var_name = match.group(2)
            init_content = match.group(3)
            
            # 提取字段赋值
            for fm in re.finditer(r'\.(\w+)\s*=\s*(\w+)', init_content):
                field_name = fm.group(1)
                value = fm.group(2)
                
                # 检查是否是函数
                if value in result.functions:
                    result.functions[value].is_callback = True
                    result.functions[value].callback_context = f"{struct_type}.{field_name}"
                    
                    # 添加函数调用记录
                    result.calls.append(FunctionCall(
                        caller=f"{struct_type}.{field_name}",
                        callee=value,
                        location=self._get_location(node),
                        is_indirect=True
                    ))
    
    def _extract_enum(self, node: 'Node') -> Optional[EnumDef]:
        """提取枚举定义（v0.2 新增）"""
        # 获取枚举名
        name_node = node.child_by_field_name('name')
        enum_name = self._get_node_text(name_node) if name_node else None
        
        if not enum_name:
            # 匿名枚举
            enum_name = f"anonymous_enum_{node.start_point[0]}"
        
        # 获取枚举值列表
        body_node = node.child_by_field_name('body')
        if not body_node:
            return None
        
        values = []
        for child in body_node.children:
            if child.type == 'enumerator':
                name_node = child.child_by_field_name('name')
                value_node = child.child_by_field_name('value')
                
                if name_node:
                    enum_value = EnumValue(
                        name=self._get_node_text(name_node),
                        value=self._get_node_text(value_node) if value_node else None,
                        location=self._get_location(child)
                    )
                    values.append(enum_value)
        
        return EnumDef(
            name=enum_name,
            values=values,
            location=self._get_location(node)
        )
    
    def _extract_union(self, node: 'Node') -> Optional[UnionDef]:
        """提取联合体定义（v0.2 新增）"""
        # 获取联合体名
        name_node = node.child_by_field_name('name')
        union_name = self._get_node_text(name_node) if name_node else None
        
        if not union_name:
            # 匿名联合体
            union_name = f"anonymous_union_{node.start_point[0]}"
        
        # 获取字段列表
        body_node = node.child_by_field_name('body')
        if not body_node:
            return None
        
        fields = []
        for child in body_node.children:
            if child.type == 'field_declaration':
                field = self._extract_field(child)
                if field:
                    fields.append(field)
        
        return UnionDef(
            name=union_name,
            fields=fields,
            location=self._get_location(node)
        )
    
    def _check_function_declaration(self, node: 'Node', result: ParseResult) -> None:
        """检查函数声明（非定义）（v0.2 新增）"""
        # 查找声明中的函数声明器
        for child in node.children:
            if child.type == 'function_declarator':
                # 这是一个函数声明
                func_name, params = self._extract_function_declarator(child)
                if func_name and func_name not in result.functions:
                    # 获取返回类型
                    return_type = ""
                    for type_child in node.children:
                        if type_child.type in ['primitive_type', 'type_identifier', 
                                               'sized_type_specifier', 'struct_specifier']:
                            return_type = self._get_node_text(type_child)
                            break
                    
                    # 创建函数定义（标记为声明）
                    result.functions[func_name] = FunctionDef(
                        name=func_name,
                        return_type=return_type,
                        params=params,
                        body="",  # 声明没有函数体
                        location=self._get_location(node),
                        attributes=["declaration"]  # 标记为声明
                    )
            
            # 处理带指针的函数声明
            elif child.type == 'pointer_declarator':
                inner = child.child_by_field_name('declarator')
                if inner and inner.type == 'function_declarator':
                    func_name, params = self._extract_function_declarator(inner)
                    if func_name and func_name not in result.functions:
                        return_type = ""
                        for type_child in node.children:
                            if type_child.type in ['primitive_type', 'type_identifier',
                                                   'sized_type_specifier', 'struct_specifier']:
                                return_type = self._get_node_text(type_child) + " *"
                                break
                        
                        result.functions[func_name] = FunctionDef(
                            name=func_name,
                            return_type=return_type,
                            params=params,
                            body="",
                            location=self._get_location(node),
                            attributes=["declaration"]
                        )
    
    def _extract_typedef_inner(self, node: 'Node', result: ParseResult) -> None:
        """从 typedef 中提取内部定义的 enum/union/struct（v0.2 新增）
        
        注意：这个方法只处理 typedef 内部的定义，并设置正确的名称和 typedef_name。
        主循环中的 enum_specifier/union_specifier 处理会被跳过（因为已在此处处理）。
        """
        # 处理 typedef enum { ... } Name;
        for child in node.children:
            if child.type == 'enum_specifier':
                body = child.child_by_field_name('body')
                if body:
                    # 获取 typedef 的别名
                    alias = self._find_typedef_alias(node)
                    enum_def = self._extract_enum(child)
                    if enum_def:
                        if alias:
                            enum_def.typedef_name = alias
                            # 如果是匿名枚举，用 typedef 名作为枚举名
                            if enum_def.name.startswith("anonymous_"):
                                # 先删除可能存在的匿名版本
                                old_name = enum_def.name
                                if old_name in result.enums:
                                    del result.enums[old_name]
                                enum_def.name = alias
                        result.enums[enum_def.name] = enum_def
            
            elif child.type == 'union_specifier':
                body = child.child_by_field_name('body')
                if body:
                    alias = self._find_typedef_alias(node)
                    union_def = self._extract_union(child)
                    if union_def:
                        if alias:
                            union_def.typedef_name = alias
                            if union_def.name.startswith("anonymous_"):
                                old_name = union_def.name
                                if old_name in result.unions:
                                    del result.unions[old_name]
                                union_def.name = alias
                        result.unions[union_def.name] = union_def
            
            elif child.type == 'struct_specifier':
                body = child.child_by_field_name('body')
                if body:
                    alias = self._find_typedef_alias(node)
                    struct_def = self._extract_struct(child)
                    if struct_def:
                        if alias:
                            struct_def.typedef_name = alias
                            if struct_def.name.startswith("anonymous_"):
                                old_name = struct_def.name
                                if old_name in result.structs:
                                    del result.structs[old_name]
                                struct_def.name = alias
                        result.structs[struct_def.name] = struct_def
    
    def _find_typedef_alias(self, node: 'Node') -> Optional[str]:
        """查找 typedef 的别名"""
        for child in node.children:
            if child.type == 'type_identifier':
                return self._get_node_text(child)
        return None
    
    def _build_call_relations(self, result: ParseResult) -> None:
        """构建函数调用关系"""
        # 更新 called_by 信息
        for func_name, func_def in result.functions.items():
            for called in func_def.calls:
                if called in result.functions:
                    if func_name not in result.functions[called].called_by:
                        result.functions[called].called_by.append(func_name)


# 注册后端
if TREE_SITTER_AVAILABLE:
    BackendRegistry.register(TreeSitterBackend)


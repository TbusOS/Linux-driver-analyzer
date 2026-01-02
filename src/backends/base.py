#!/usr/bin/env python3
"""
解析后端抽象基类

定义所有后端必须实现的统一接口，确保不同后端可以互换使用。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum, auto


class BackendCapability(Enum):
    """后端能力枚举"""
    PARSE_FUNCTIONS = auto()      # 解析函数定义
    PARSE_STRUCTS = auto()        # 解析结构体定义
    PARSE_ENUMS = auto()          # 解析枚举定义
    PARSE_UNIONS = auto()         # 解析联合体定义
    PARSE_CALLS = auto()          # 解析函数调用
    PARSE_TYPEDEFS = auto()       # 解析typedef
    PARSE_DECLARATIONS = auto()   # 解析函数声明（非定义）
    TYPE_INFERENCE = auto()       # 类型推导
    MACRO_EXPANSION = auto()      # 宏展开
    CROSS_FILE = auto()           # 跨文件分析
    BROWSER_COMPATIBLE = auto()   # 浏览器兼容
    INCREMENTAL = auto()          # 增量解析
    PRECISE_LOCATION = auto()     # 精确位置信息（列号、结束位置）


@dataclass
class Location:
    """代码位置"""
    line: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column
        }


@dataclass
class StructField:
    """结构体字段"""
    name: str
    type_name: str
    is_pointer: bool = False
    is_function_ptr: bool = False
    func_ptr_signature: str = ""
    array_size: str = ""
    location: Optional[Location] = None
    comment: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type_name": self.type_name,
            "is_pointer": self.is_pointer,
            "is_function_ptr": self.is_function_ptr,
            "func_ptr_signature": self.func_ptr_signature,
            "array_size": self.array_size,
            "line": self.location.line if self.location else 0,
            "comment": self.comment
        }


@dataclass
class StructDef:
    """结构体定义"""
    name: str
    fields: List[StructField] = field(default_factory=list)
    location: Optional[Location] = None
    typedef_name: str = ""
    referenced_structs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "fields": [f.to_dict() for f in self.fields],
            "start_line": self.location.line if self.location else 0,
            "end_line": self.location.end_line if self.location else 0,
            "typedef_name": self.typedef_name,
            "referenced_structs": self.referenced_structs
        }


@dataclass
class Parameter:
    """函数参数"""
    name: str
    type_name: str
    
    def to_tuple(self) -> Tuple[str, str]:
        return (self.type_name, self.name)


@dataclass
class FunctionDef:
    """函数定义"""
    name: str
    return_type: str
    params: List[Parameter] = field(default_factory=list)
    body: str = ""
    location: Optional[Location] = None
    calls: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)
    uses_structs: List[str] = field(default_factory=list)
    is_callback: bool = False
    callback_context: str = ""
    attributes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "return_type": self.return_type,
            "params": [p.to_tuple() for p in self.params],
            "start_line": self.location.line if self.location else 0,
            "end_line": self.location.end_line if self.location else 0,
            "calls": self.calls,
            "called_by": self.called_by,
            "uses_structs": self.uses_structs,
            "is_callback": self.is_callback,
            "callback_context": self.callback_context,
            "attributes": self.attributes
        }


@dataclass
class FunctionCall:
    """函数调用"""
    caller: str
    callee: str
    location: Optional[Location] = None
    is_indirect: bool = False  # 是否是间接调用（函数指针）
    
    def to_dict(self) -> Dict:
        return {
            "caller": self.caller,
            "callee": self.callee,
            "line": self.location.line if self.location else 0,
            "is_indirect": self.is_indirect
        }


@dataclass
class TypeDef:
    """typedef定义"""
    alias: str
    original: str
    location: Optional[Location] = None


@dataclass
class EnumValue:
    """枚举值"""
    name: str
    value: Optional[str] = None
    location: Optional[Location] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "line": self.location.line if self.location else 0
        }


@dataclass
class EnumDef:
    """枚举定义"""
    name: str
    values: List[EnumValue] = field(default_factory=list)
    location: Optional[Location] = None
    typedef_name: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "values": [v.to_dict() for v in self.values],
            "start_line": self.location.line if self.location else 0,
            "end_line": self.location.end_line if self.location else 0,
            "typedef_name": self.typedef_name
        }


@dataclass
class UnionDef:
    """联合体定义"""
    name: str
    fields: List[StructField] = field(default_factory=list)
    location: Optional[Location] = None
    typedef_name: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "fields": [f.to_dict() for f in self.fields],
            "start_line": self.location.line if self.location else 0,
            "end_line": self.location.end_line if self.location else 0,
            "typedef_name": self.typedef_name
        }


@dataclass
class ParseResult:
    """解析结果"""
    functions: Dict[str, FunctionDef] = field(default_factory=dict)
    structs: Dict[str, StructDef] = field(default_factory=dict)
    enums: Dict[str, EnumDef] = field(default_factory=dict)
    unions: Dict[str, UnionDef] = field(default_factory=dict)
    typedefs: Dict[str, TypeDef] = field(default_factory=dict)
    calls: List[FunctionCall] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "functions": {k: v.to_dict() for k, v in self.functions.items()},
            "structs": {k: v.to_dict() for k, v in self.structs.items()},
            "enums": {k: v.to_dict() for k, v in self.enums.items()},
            "unions": {k: v.to_dict() for k, v in self.unions.items()},
            "typedefs": {k: {"alias": v.alias, "original": v.original} 
                        for k, v in self.typedefs.items()},
            "errors": self.errors
        }


class AnalyzerBackend(ABC):
    """
    分析后端抽象基类
    
    所有后端（正则、tree-sitter、libclang等）都需要实现此接口
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """返回后端名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """返回后端版本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查后端是否可用（依赖是否已安装）
        
        Returns:
            bool: 如果后端可用返回True
        """
        pass
    
    @abstractmethod
    def capabilities(self) -> Set[BackendCapability]:
        """
        返回后端支持的能力集
        
        Returns:
            Set[BackendCapability]: 支持的能力集合
        """
        pass
    
    @abstractmethod
    def parse(self, source_code: str, filename: str = "<string>") -> ParseResult:
        """
        解析源代码
        
        Args:
            source_code: C源代码字符串
            filename: 源文件名（用于错误报告）
            
        Returns:
            ParseResult: 解析结果
        """
        pass
    
    def parse_file(self, filepath: str) -> ParseResult:
        """
        解析源文件
        
        Args:
            filepath: 源文件路径
            
        Returns:
            ParseResult: 解析结果
        """
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()
        return self.parse(source_code, filepath)
    
    def supports(self, capability: BackendCapability) -> bool:
        """
        检查是否支持特定能力
        
        Args:
            capability: 要检查的能力
            
        Returns:
            bool: 如果支持返回True
        """
        return capability in self.capabilities()


class BackendRegistry:
    """后端注册中心"""
    
    _backends: Dict[str, type] = {}
    _instances: Dict[str, AnalyzerBackend] = {}
    
    @classmethod
    def register(cls, backend_class: type) -> None:
        """
        注册后端类
        
        Args:
            backend_class: 后端类（需继承AnalyzerBackend）
        """
        # 创建临时实例获取名称
        instance = backend_class()
        cls._backends[instance.name] = backend_class
    
    @classmethod
    def get(cls, name: str) -> Optional[AnalyzerBackend]:
        """
        获取后端实例
        
        Args:
            name: 后端名称
            
        Returns:
            AnalyzerBackend: 后端实例，如果不存在返回None
        """
        if name not in cls._instances:
            if name in cls._backends:
                cls._instances[name] = cls._backends[name]()
        return cls._instances.get(name)
    
    @classmethod
    def list_available(cls) -> List[str]:
        """
        列出所有可用的后端
        
        Returns:
            List[str]: 可用后端名称列表
        """
        available = []
        for name, backend_class in cls._backends.items():
            try:
                instance = backend_class()
                if instance.is_available():
                    available.append(name)
            except Exception:
                pass
        return available
    
    @classmethod
    def get_best_available(cls) -> Optional[AnalyzerBackend]:
        """
        获取最佳可用后端（按优先级）
        
        优先级：clang > tree-sitter > regex
        
        Returns:
            AnalyzerBackend: 最佳可用后端
        """
        priority = ['clang', 'tree-sitter', 'regex']
        for name in priority:
            backend = cls.get(name)
            if backend and backend.is_available():
                return backend
        return None
    
    @classmethod
    def clear(cls) -> None:
        """清除所有注册的后端"""
        cls._backends.clear()
        cls._instances.clear()


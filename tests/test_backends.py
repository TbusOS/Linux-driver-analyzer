#!/usr/bin/env python3
"""
后端测试

测试不同解析后端的功能和一致性。
"""

import os
import sys
import pytest

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backends import (
    get_backend, list_backends, is_treesitter_available,
    RegexBackend, BackendCapability
)


# 测试用的简单驱动代码
SIMPLE_DRIVER = '''
#include <linux/module.h>
#include <linux/usb.h>

struct my_device {
    struct usb_device *udev;
    int status;
    char name[32];
};

static int my_probe(struct usb_interface *intf, 
                    const struct usb_device_id *id)
{
    struct my_device *dev;
    dev = kzalloc(sizeof(*dev), GFP_KERNEL);
    if (!dev)
        return -ENOMEM;
    
    dev->udev = interface_to_usbdev(intf);
    printk(KERN_INFO "Device connected\\n");
    return 0;
}

static void my_disconnect(struct usb_interface *intf)
{
    printk(KERN_INFO "Device disconnected\\n");
}

static struct usb_driver my_driver = {
    .name = "my_driver",
    .probe = my_probe,
    .disconnect = my_disconnect,
};

static int __init my_init(void)
{
    return usb_register(&my_driver);
}

static void __exit my_exit(void)
{
    usb_deregister(&my_driver);
}

module_init(my_init);
module_exit(my_exit);
'''


class TestRegexBackend:
    """RegexBackend 测试"""
    
    @pytest.fixture
    def backend(self):
        return RegexBackend()
    
    def test_is_available(self, backend):
        """测试后端总是可用"""
        assert backend.is_available() is True
    
    def test_name_and_version(self, backend):
        """测试名称和版本"""
        assert backend.name == "regex"
        assert backend.version == "0.1.0"
    
    def test_capabilities(self, backend):
        """测试能力"""
        caps = backend.capabilities()
        assert BackendCapability.PARSE_FUNCTIONS in caps
        assert BackendCapability.PARSE_STRUCTS in caps
        assert BackendCapability.PARSE_CALLS in caps
    
    def test_parse_functions(self, backend):
        """测试函数解析"""
        result = backend.parse(SIMPLE_DRIVER)
        
        assert 'my_probe' in result.functions
        assert 'my_disconnect' in result.functions
        assert 'my_init' in result.functions
        assert 'my_exit' in result.functions
        
        # 检查函数属性
        probe = result.functions['my_probe']
        assert 'static' in probe.attributes
        assert len(probe.params) == 2
    
    def test_parse_structs(self, backend):
        """测试结构体解析"""
        result = backend.parse(SIMPLE_DRIVER)
        
        assert 'my_device' in result.structs
        
        my_device = result.structs['my_device']
        field_names = [f.name for f in my_device.fields]
        assert 'udev' in field_names
        assert 'status' in field_names
        assert 'name' in field_names
    
    def test_parse_calls(self, backend):
        """测试函数调用解析"""
        result = backend.parse(SIMPLE_DRIVER)
        
        probe = result.functions['my_probe']
        assert 'kzalloc' in probe.calls
        assert 'printk' in probe.calls
        
        init_func = result.functions['my_init']
        assert 'usb_register' in init_func.calls
    
    def test_callback_detection(self, backend):
        """测试回调检测"""
        result = backend.parse(SIMPLE_DRIVER)
        
        # 检查 probe 回调
        probe = result.functions['my_probe']
        assert probe.is_callback is True
        assert 'usb_driver.probe' in probe.callback_context
        
        # 检查 module_init
        init_func = result.functions['my_init']
        assert init_func.is_callback is True
        assert init_func.callback_context == 'module_init'


@pytest.mark.skipif(
    not is_treesitter_available(),
    reason="tree-sitter 未安装"
)
class TestTreeSitterBackend:
    """TreeSitterBackend 测试"""
    
    @pytest.fixture
    def backend(self):
        from backends import TreeSitterBackend
        return TreeSitterBackend()
    
    def test_is_available(self, backend):
        """测试后端可用性"""
        assert backend.is_available() is True
    
    def test_name_and_version(self, backend):
        """测试名称和版本"""
        assert backend.name == "tree-sitter"
        assert backend.version == "0.2.0"
    
    def test_capabilities(self, backend):
        """测试能力"""
        caps = backend.capabilities()
        assert BackendCapability.PARSE_FUNCTIONS in caps
        assert BackendCapability.PARSE_STRUCTS in caps
        assert BackendCapability.INCREMENTAL in caps
    
    def test_parse_functions(self, backend):
        """测试函数解析"""
        result = backend.parse(SIMPLE_DRIVER)
        
        assert 'my_probe' in result.functions
        assert 'my_disconnect' in result.functions
        assert 'my_init' in result.functions
        assert 'my_exit' in result.functions
    
    def test_parse_structs(self, backend):
        """测试结构体解析"""
        result = backend.parse(SIMPLE_DRIVER)
        
        assert 'my_device' in result.structs
        
        my_device = result.structs['my_device']
        assert len(my_device.fields) >= 2
    
    def test_parse_calls(self, backend):
        """测试函数调用解析"""
        result = backend.parse(SIMPLE_DRIVER)
        
        probe = result.functions['my_probe']
        assert 'kzalloc' in probe.calls
    
    def test_location_info(self, backend):
        """测试位置信息"""
        result = backend.parse(SIMPLE_DRIVER)
        
        probe = result.functions['my_probe']
        assert probe.location is not None
        assert probe.location.line > 0
        assert probe.location.end_line >= probe.location.line


class TestBackendConsistency:
    """测试不同后端的结果一致性"""
    
    def test_function_names_consistency(self):
        """测试函数名称提取一致性"""
        regex_backend = RegexBackend()
        regex_result = regex_backend.parse(SIMPLE_DRIVER)
        regex_funcs = set(regex_result.functions.keys())
        
        if is_treesitter_available():
            from backends import TreeSitterBackend
            ts_backend = TreeSitterBackend()
            ts_result = ts_backend.parse(SIMPLE_DRIVER)
            ts_funcs = set(ts_result.functions.keys())
            
            # 核心函数应该被两个后端都识别
            core_funcs = {'my_probe', 'my_disconnect', 'my_init', 'my_exit'}
            assert core_funcs.issubset(regex_funcs)
            assert core_funcs.issubset(ts_funcs)
    
    def test_struct_names_consistency(self):
        """测试结构体名称提取一致性"""
        regex_backend = RegexBackend()
        regex_result = regex_backend.parse(SIMPLE_DRIVER)
        
        assert 'my_device' in regex_result.structs
        
        if is_treesitter_available():
            from backends import TreeSitterBackend
            ts_backend = TreeSitterBackend()
            ts_result = ts_backend.parse(SIMPLE_DRIVER)
            
            assert 'my_device' in ts_result.structs


class TestBackendRegistry:
    """测试后端注册中心"""
    
    def test_list_backends(self):
        """测试列出后端"""
        backends = list_backends()
        assert 'regex' in backends
    
    def test_get_regex_backend(self):
        """测试获取 regex 后端"""
        backend = get_backend('regex')
        assert backend is not None
        assert backend.name == 'regex'
    
    def test_get_default_backend(self):
        """测试获取默认后端"""
        backend = get_backend()
        assert backend is not None
        assert backend.is_available()
    
    def test_get_invalid_backend(self):
        """测试获取无效后端"""
        with pytest.raises(ValueError):
            get_backend('invalid-backend-name')


class TestComplexCode:
    """测试复杂代码场景"""
    
    COMPLEX_CODE = '''
/* 多行注释
   测试 */
struct ops_table {
    int (*open)(void);
    int (*read)(char *buf, size_t len);
    void (*close)(void);
};

typedef struct {
    int value;
} simple_t;

// 带有复杂参数的函数
static int complex_func(struct ops_table *ops, 
                        int (*callback)(int, void *),
                        void *user_data)
{
    // 内嵌注释 { 不应该干扰
    char str[] = "string with { braces }";
    if (ops->open) {
        ops->open();
    }
    return callback(42, user_data);
}
'''
    
    def test_regex_complex(self):
        """测试 regex 后端处理复杂代码"""
        backend = RegexBackend()
        result = backend.parse(self.COMPLEX_CODE)
        
        # 应该解析到结构体
        assert 'ops_table' in result.structs
        
        # 应该解析到函数
        assert 'complex_func' in result.functions
    
    @pytest.mark.skipif(
        not is_treesitter_available(),
        reason="tree-sitter 未安装"
    )
    def test_treesitter_complex(self):
        """测试 tree-sitter 后端处理复杂代码"""
        from backends import TreeSitterBackend
        backend = TreeSitterBackend()
        result = backend.parse(self.COMPLEX_CODE)
        
        # tree-sitter 应该能正确处理注释和字符串
        assert 'ops_table' in result.structs
        assert 'complex_func' in result.functions


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


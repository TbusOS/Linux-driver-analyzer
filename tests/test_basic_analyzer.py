#!/usr/bin/env python3
"""
基础分析器测试
"""

import json
import os
import sys
import tempfile
import pytest

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.basic_analyzer import CAnalyzer


class TestCAnalyzer:
    """CAnalyzer 测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        kb_path = os.path.join(os.path.dirname(__file__), 
                               '..', 'src', 'core', 'knowledge_base.json')
        return CAnalyzer(kb_path if os.path.exists(kb_path) else None)
    
    @pytest.fixture
    def simple_driver(self):
        """简单的驱动代码"""
        return '''
#include <linux/module.h>
#include <linux/usb.h>

static int my_probe(struct usb_interface *intf, 
                    const struct usb_device_id *id)
{
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
    
    def test_extract_functions(self, analyzer, simple_driver):
        """测试函数提取"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(simple_driver)
            f.flush()
            
            result = analyzer.analyze_file(f.name)
            
            # 清理
            os.unlink(f.name)
        
        # 验证函数提取
        functions = result['functions']
        assert 'my_probe' in functions
        assert 'my_disconnect' in functions
        assert 'my_init' in functions
        assert 'my_exit' in functions
    
    def test_extract_struct_ops(self, analyzer, simple_driver):
        """测试结构体操作表提取"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(simple_driver)
            f.flush()
            
            result = analyzer.analyze_file(f.name)
            
            os.unlink(f.name)
        
        # 验证结构体操作表
        struct_ops = result['struct_ops']
        assert len(struct_ops) >= 1
        
        usb_driver_ops = [s for s in struct_ops if s['struct_type'] == 'usb_driver']
        assert len(usb_driver_ops) == 1
        assert usb_driver_ops[0]['mappings']['probe'] == 'my_probe'
        assert usb_driver_ops[0]['mappings']['disconnect'] == 'my_disconnect'
    
    def test_callback_detection(self, analyzer, simple_driver):
        """测试回调函数检测"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(simple_driver)
            f.flush()
            
            result = analyzer.analyze_file(f.name)
            
            os.unlink(f.name)
        
        functions = result['functions']
        
        # my_probe 应该被标记为回调
        assert functions['my_probe']['is_callback'] == True
        assert 'usb_driver.probe' in functions['my_probe']['callback_context']
        
        # my_init 应该被标记为 module_init
        assert functions['my_init']['is_callback'] == True
        assert functions['my_init']['callback_context'] == 'module_init'
    
    def test_function_calls(self, analyzer, simple_driver):
        """测试函数调用提取"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(simple_driver)
            f.flush()
            
            result = analyzer.analyze_file(f.name)
            
            os.unlink(f.name)
        
        functions = result['functions']
        
        # my_init 应该调用 usb_register
        assert 'usb_register' in functions['my_init']['calls']
        
        # my_exit 应该调用 usb_deregister
        assert 'usb_deregister' in functions['my_exit']['calls']
        
        # my_probe 应该调用 printk
        assert 'printk' in functions['my_probe']['calls']


class TestAsyncHandlers:
    """异步处理函数测试"""
    
    @pytest.fixture
    def analyzer(self):
        kb_path = os.path.join(os.path.dirname(__file__), 
                               '..', 'src', 'core', 'knowledge_base.json')
        return CAnalyzer(kb_path if os.path.exists(kb_path) else None)
    
    @pytest.fixture
    def async_driver(self):
        """带异步机制的驱动代码"""
        return '''
#include <linux/workqueue.h>
#include <linux/timer.h>

struct my_device {
    struct work_struct work;
    struct timer_list timer;
};

static void my_work_handler(struct work_struct *work)
{
    printk("Work handler called\\n");
}

static void my_timer_callback(struct timer_list *t)
{
    printk("Timer callback\\n");
}

static int my_init(void)
{
    struct my_device *dev = kzalloc(sizeof(*dev), GFP_KERNEL);
    INIT_WORK(&dev->work, my_work_handler);
    timer_setup(&dev->timer, my_timer_callback, 0);
    return 0;
}
'''
    
    def test_work_queue_detection(self, analyzer, async_driver):
        """测试工作队列检测"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(async_driver)
            f.flush()
            
            result = analyzer.analyze_file(f.name)
            
            os.unlink(f.name)
        
        # 检查异步处理函数是否被识别
        summary = result['summary']
        async_handlers = summary.get('async_handlers_by_type', {})
        
        # 应该检测到工作队列
        assert 'work' in async_handlers
        work_handlers = [h['func'] for h in async_handlers['work']]
        assert 'my_work_handler' in work_handlers
    
    def test_timer_detection(self, analyzer, async_driver):
        """测试定时器检测"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(async_driver)
            f.flush()
            
            result = analyzer.analyze_file(f.name)
            
            os.unlink(f.name)
        
        summary = result['summary']
        async_handlers = summary.get('async_handlers_by_type', {})
        
        # 应该检测到定时器
        assert 'timer' in async_handlers
        timer_handlers = [h['func'] for h in async_handlers['timer']]
        assert 'my_timer_callback' in timer_handlers


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


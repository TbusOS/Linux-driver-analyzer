# 🧪 测试目录

本目录包含项目的测试代码。

## 📄 测试文件

| 文件 | 说明 |
|------|------|
| `test_basic_analyzer.py` | 基础分析器测试 |

## 🚀 运行测试

### 使用 pytest

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_basic_analyzer.py -v

# 运行特定测试用例
pytest tests/test_basic_analyzer.py::test_function_detection -v

# 显示覆盖率
pytest tests/ --cov=src/core --cov-report=html
```

### 使用 unittest

```bash
python -m unittest discover tests/
```

## 📝 编写测试

测试示例：

```python
import pytest
from src.core.basic_analyzer import CCallAnalyzer

def test_function_detection():
    code = '''
    int my_func(int a, int b) {
        return a + b;
    }
    '''
    analyzer = CCallAnalyzer(code)
    result = analyzer.analyze()
    
    assert 'my_func' in result['functions']
    assert result['functions']['my_func']['return_type'] == 'int'

def test_callback_detection():
    code = '''
    static struct usb_driver my_driver = {
        .probe = my_probe,
        .disconnect = my_disconnect,
    };
    '''
    analyzer = CCallAnalyzer(code)
    result = analyzer.analyze()
    
    assert len(result['ops_structs']) == 1
    assert result['ops_structs'][0]['struct_type'] == 'usb_driver'
```

## 📋 测试覆盖目标

- [ ] 函数识别
- [ ] 调用关系提取
- [ ] 回调函数映射
- [ ] 异步机制识别
- [ ] 结构体解析
- [ ] 边界情况处理


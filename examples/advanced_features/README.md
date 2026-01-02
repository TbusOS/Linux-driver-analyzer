# 高级特性示例

这个目录包含用于展示 v0.2 tree-sitter 后端增强功能的示例代码。

## 文件说明

- `advanced_driver.c` - 包含 enum、union、函数声明等高级特性的示例驱动

## 功能对比测试

运行以下命令查看 v0.1 和 v0.2 的功能差异：

```bash
cd /path/to/linux-driver-analyzer
make demo-compare
```

或手动运行：

```bash
.venv/bin/python -c "
import sys
sys.path.insert(0, 'src')
from backends import get_backend

file = 'examples/advanced_features/advanced_driver.c'

regex = get_backend('regex')
r1 = regex.parse_file(file)

ts = get_backend('tree-sitter')
r2 = ts.parse_file(file)

print('| 特性 | v0.1 (regex) | v0.2 (tree-sitter) |')
print('|------|-------------|-------------------|')
print(f'| 函数 | {len(r1.functions)} | {len(r2.functions)} |')
print(f'| 结构体 | {len(r1.structs)} | {len(r2.structs)} |')
print(f'| 枚举 | {len(r1.enums)} | {len(r2.enums)} ✨ |')
print(f'| 联合体 | {len(r1.unions)} | {len(r2.unions)} ✨ |')
"
```

## v0.2 增强功能

### 1. 枚举提取

```c
enum device_state {
    STATE_IDLE = 0,
    STATE_RUNNING,
    STATE_ERROR = -1
};
```

v0.2 可以提取：
- 枚举名称
- 每个枚举值的名称和值
- 精确的位置信息

### 2. 联合体提取

```c
union data_packet {
    uint8_t bytes[64];
    uint16_t words[32];
};
```

v0.2 可以提取：
- 联合体名称
- 所有字段信息
- 数组大小

### 3. 函数声明识别

```c
static int device_open(struct inode *inode, struct file *file);
```

v0.2 可以区分函数声明和函数定义。

### 4. 精确位置信息

v0.2 提供：
- 精确的列号
- 结束行和结束列
- 便于代码高亮和跳转


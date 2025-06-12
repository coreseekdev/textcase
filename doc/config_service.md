# Configuration Service (ConfigService)

配置服务提供了一个统一的配置管理系统，支持从多个来源加载配置，包括默认值、配置文件和环境变量。

## 概述

`ConfigService` 是一个可通过ZeroRPC调用的服务，用于管理应用程序的配置设置。它支持：

- **分层配置** - 默认值 → 配置文件 → 环境变量
- **动态配置** - 运行时修改配置值
- **服务特定配置** - 为不同服务提供专门的配置
- **配置持久化** - 保存配置到文件
- **全局配置实例** - 单例模式的全局配置管理

## 配置层次结构

配置按以下优先级加载（后者覆盖前者）：

1. **默认配置** - 硬编码的默认值
2. **配置文件** - JSON格式的配置文件
3. **环境变量** - 系统环境变量

## 默认配置

```json
{
  "vfs": {
    "root_path": "<current_working_directory>",
    "enable_git_repo": true,
    "max_file_size": 10485760,
    "session_timeout": 3600
  },
  "services": {
    "default_port": 8000,
    "bind_host": "localhost"
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

## 环境变量

支持的环境变量：

| 环境变量 | 配置键 | 描述 |
|---------|--------|------|
| `TEXTCASE_VFS_ROOT_PATH` | `vfs.root_path` | VFS根路径 |
| `TEXTCASE_VFS_MAX_FILE_SIZE` | `vfs.max_file_size` | 最大文件大小（字节） |
| `TEXTCASE_DEFAULT_PORT` | `services.default_port` | 默认服务端口 |
| `TEXTCASE_BIND_HOST` | `services.bind_host` | 绑定主机地址 |
| `TEXTCASE_LOG_LEVEL` | `logging.level` | 日志级别 |

## 配置文件

配置服务会自动查找以下位置的配置文件：

1. `./textcase.json`
2. `./.textcase.json`
3. `~/.textcase/config.json`

### 配置文件示例

```json
{
  "vfs": {
    "root_path": "/path/to/your/project",
    "enable_git_repo": true,
    "max_file_size": 10485760,
    "session_timeout": 3600
  },
  "services": {
    "default_port": 8000,
    "bind_host": "localhost",
    "vfs": {
      "timeout": 30,
      "retries": 3
    }
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "textcase.log"
  },
  "custom": {
    "app_name": "TextCase",
    "version": "1.0.0"
  }
}
```

## API 接口

### ConfigService 类方法

#### 基本操作

```python
from textcase.core import ConfigService

# 创建配置服务实例
config = ConfigService()  # 使用默认配置文件查找
config = ConfigService('/path/to/config.json')  # 指定配置文件

# 获取配置值
value = config.get('vfs.root_path')
value = config.get('nonexistent.key', 'default_value')

# 设置配置值
config.set('vfs.root_path', '/new/path')
config.set('custom.setting', 'value')

# 获取服务名称
name = config.name()  # 返回 "ConfigService"
```

#### 专用方法

```python
# 获取VFS根路径
root_path = config.get_vfs_root_path()

# 获取服务特定配置
vfs_config = config.get_service_config('vfs')
test_config = config.get_service_config('test')

# 获取完整配置字典
all_config = config.to_dict()

# 保存配置到文件
config.save_config('/path/to/save.json')
```

### 全局配置管理

```python
from textcase.core import get_config, set_config, ConfigService

# 获取全局配置实例（单例）
config = get_config()

# 设置自定义全局配置
custom_config = ConfigService('/custom/config.json')
set_config(custom_config)

# 后续调用将返回自定义配置
config = get_config()  # 返回 custom_config
```

### 服务工厂集成

配置服务已注册到服务工厂中：

```python
from textcase.core import service_registry

# 通过服务注册表获取配置服务
config_service_info = service_registry.get_service('config')

# 通过ZeroRPC连接
import zerorpc
client = zerorpc.Client()
client.connect(config_service_info.endpoint)
```

## VFS服务集成

VFS服务现在从配置服务获取根路径，而不是使用 `os.getcwd()`：

```python
# 旧的实现
def create_vfs_service(service_name: str) -> VFSService:
    root_path = os.getcwd()  # 硬编码使用当前目录
    return VFSService(root_path)

# 新的实现
def create_vfs_service(service_name: str) -> VFSService:
    config = get_config()  # 获取配置服务
    root_path = config.get_vfs_root_path()  # 从配置获取根路径
    return VFSService(root_path)
```

## CLI工具集成

VFS服务器CLI工具现在支持配置文件：

```bash
# 使用默认配置
python src/textcase/cli/vfs_server.py

# 指定配置文件
python src/textcase/cli/vfs_server.py --config /path/to/config.json

# 命令行参数覆盖配置文件
python src/textcase/cli/vfs_server.py /custom/root --port 9000 --config config.json
```

## 使用示例

### 基本配置管理

```python
from textcase.core import ConfigService

# 创建配置服务
config = ConfigService()

# 设置VFS根路径
config.set('vfs.root_path', '/my/project')

# 设置服务端口
config.set('services.default_port', 9000)

# 获取配置值
root_path = config.get_vfs_root_path()
port = config.get('services.default_port')

print(f"VFS Root: {root_path}")
print(f"Port: {port}")
```

### 环境变量配置

```bash
# 设置环境变量
export TEXTCASE_VFS_ROOT_PATH=/env/project
export TEXTCASE_DEFAULT_PORT=8080

# 启动应用（会自动使用环境变量）
python your_app.py
```

### 配置文件使用

```python
# 创建配置文件 textcase.json
{
  "vfs": {
    "root_path": "/file/project"
  },
  "services": {
    "default_port": 7000
  }
}

# 使用配置文件
config = ConfigService('textcase.json')
print(config.get_vfs_root_path())  # 输出: /file/project
```

### 服务特定配置

```python
config = ConfigService()

# 设置VFS服务特定配置
config.set('services.vfs.timeout', 30)
config.set('services.vfs.retries', 3)

# 获取VFS服务配置
vfs_config = config.get_service_config('vfs')
print(vfs_config)  # {'timeout': 30, 'retries': 3}
```

## 配置优先级示例

假设有以下配置源：

**默认配置:**
```json
{"services": {"default_port": 8000}}
```

**配置文件 (config.json):**
```json
{"services": {"default_port": 7000}}
```

**环境变量:**
```bash
TEXTCASE_DEFAULT_PORT=9000
```

**最终配置:**
```python
config = ConfigService('config.json')
port = config.get('services.default_port')  # 结果: 9000 (环境变量优先)
```

## 错误处理

配置服务具有良好的错误处理能力：

- **无效配置文件** - 警告并使用默认值
- **无效环境变量** - 忽略并使用默认值
- **不存在的配置键** - 返回默认值或None
- **无效JSON格式** - 警告并使用默认值

## 扩展配置

可以轻松添加新的配置项：

```python
# 添加自定义配置
config.set('custom.feature.enabled', True)
config.set('custom.feature.max_items', 100)

# 获取自定义配置
feature_enabled = config.get('custom.feature.enabled')
max_items = config.get('custom.feature.max_items')
```

## 最佳实践

1. **使用全局配置** - 通过 `get_config()` 获取全局配置实例
2. **环境变量优先** - 生产环境使用环境变量覆盖配置
3. **配置文件版本控制** - 将示例配置文件加入版本控制
4. **敏感信息** - 敏感配置通过环境变量提供
5. **配置验证** - 在应用启动时验证关键配置项
6. **文档同步** - 保持配置文档与代码同步

## 测试

运行配置服务测试：

```bash
# 运行单元测试
python tests/test_config_service.py

# 运行示例
python examples/config_service_example.py
```

## 注意事项

1. **配置修改** - 运行时修改配置不会影响已创建的服务实例
2. **线程安全** - 当前实现不保证线程安全
3. **配置持久化** - 只有显式调用 `save_config()` 才会保存配置
4. **环境变量类型** - 环境变量值会自动转换为适当的类型
5. **配置文件格式** - 目前只支持JSON格式的配置文件
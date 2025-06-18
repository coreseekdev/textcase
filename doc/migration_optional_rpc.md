# 迁移指南：可选 RPC 依赖

本文档描述了如何将项目从强制的 zerorpc/gevent 依赖迁移到可选依赖的架构。

## 概述

为了解决 zerorpc 和 gevent 与 Python 标准 asyncio 机制的兼容性问题，我们重构了服务注册和客户端系统，使 RPC 依赖变为可选。

## 架构变更

### 1. 服务注册系统

#### 旧实现
- `service_registry_impl.py` - 强制依赖 zerorpc 和 gevent
- 在模块加载时执行 `monkey.patch_all()`
- 所有服务都通过 zerorpc 提供

#### 新实现
- `service_registry_base.py` - 抽象基类，支持多种后端
- `service_registry_new.py` - 新的实现，自动选择后端
- `backends/zerorpc_backend.py` - ZeroRPC 后端（可选）
- `backends/direct_backend.py` - 直接调用后端（备选）

### 2. 客户端系统

#### 旧实现
- `vfs_client.py` - 强制依赖 zerorpc
- 只支持 RPC 通信

#### 新实现
- `vfs_client_new.py` - 支持多种后端
- 自动适配可用的通信方式

## 后端选择逻辑

系统会按以下优先级自动选择后端：

1. **ZeroRPC 后端** - 如果 zerorpc 和 gevent 可用
   - 支持进程间通信
   - 适合分布式部署
   - 性能较好

2. **直接后端** - 如果 RPC 依赖不可用
   - 直接函数调用
   - 适合单进程应用
   - 无额外依赖

## 安装选项

### 基础安装（无 RPC 支持）
```bash
poetry install
# 或
pip install textcase
```

### 完整安装（包含 RPC 支持）
```bash
poetry install --extras rpc
# 或
pip install textcase[rpc]
```

## 代码迁移

### 1. 服务注册

#### 旧代码
```python
from textcase.service.service_registry_impl import ServiceRegistryImpl

# 创建服务注册表
registry = ServiceRegistryImpl()
```

#### 新代码
```python
from textcase.service.service_registry_new import create_service_registry

# 创建服务注册表（自动选择后端）
registry = create_service_registry()

# 检查使用的后端类型
print(f"Using backend: {registry.backend_type}")
```

### 2. VFS 客户端

#### 旧代码
```python
from textcase.client.vfs_client import VFSClient

# 创建客户端
client = VFSClient("inproc://vfs")
```

#### 新代码
```python
from textcase.client.vfs_client_new import VFSClientNew
from textcase.service.service_registry_new import create_service_registry

# 创建服务注册表
registry = create_service_registry()

# 创建客户端（自动适配后端）
client = VFSClientNew("inproc://vfs", service_registry=registry)
```

### 3. 强制使用特定后端

```python
from textcase.service.service_registry_base import BaseServiceRegistry
from textcase.service.backends.direct_backend import DirectBackend

# 强制使用直接后端
backend = DirectBackend()
registry = BaseServiceRegistry(backend=backend)
```

## 兼容性说明

### 向后兼容
- 旧的 API 接口保持不变
- 现有代码可以继续使用旧实现
- 新实现提供相同的功能接口

### 功能差异

| 功能 | ZeroRPC 后端 | 直接后端 |
|------|-------------|----------|
| 进程间通信 | ✅ | ❌ |
| 分布式部署 | ✅ | ❌ |
| 异常处理 | 完整 | 完整 |
| 性能开销 | 中等 | 最低 |
| 依赖要求 | zerorpc, gevent | 无 |

## 最佳实践

### 1. 开发环境
- 使用完整安装以获得最佳功能
- 在开发时测试两种后端

### 2. 生产环境
- 根据部署需求选择安装方式
- 单进程应用可使用基础安装
- 分布式应用需要 RPC 支持

### 3. 错误处理
```python
try:
    from textcase.service.backends.zerorpc_backend import ZeroRPCBackend
    backend = ZeroRPCBackend()
    print("Using ZeroRPC backend")
except ImportError:
    from textcase.service.backends.direct_backend import DirectBackend
    backend = DirectBackend()
    print("Using direct backend")
```

## 故障排除

### 1. ImportError: zerorpc
**问题**: 尝试使用 RPC 功能但未安装依赖

**解决**: 
```bash
poetry install --extras rpc
```

### 2. 服务无法启动
**问题**: 后端选择错误或配置问题

**解决**: 检查后端类型和依赖安装
```python
print(f"Backend type: {registry.backend_type}")
print(f"Service running: {registry.is_service_running('vfs')}")
```

### 3. 客户端连接失败
**问题**: 端点类型与后端不匹配

**解决**: 确保端点格式正确
- ZeroRPC: `inproc://service-name` 或 `tcp://host:port`
- 直接: `direct://service-name`

## 未来计划

1. **AsyncIO 后端** - 支持原生 asyncio 通信
2. **HTTP 后端** - 基于 HTTP/REST 的通信
3. **配置驱动** - 通过配置文件选择后端
4. **性能优化** - 针对不同后端的性能调优

## 总结

通过这次重构，我们实现了：
- ✅ 可选的 RPC 依赖
- ✅ 与 asyncio 的兼容性
- ✅ 向后兼容的 API
- ✅ 灵活的后端选择
- ✅ 更好的错误处理

这使得项目可以在不同的环境和需求下灵活部署，同时保持代码的简洁性和可维护性。
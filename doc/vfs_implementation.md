# VFS (Virtual File System) Implementation

本文档描述了REQ019的VFS实现，提供了一个通过ZeroRPC调用的虚拟文件系统服务。

## 概述

VFS系统实现了以下核心组件：

1. **VFS接口** - 抽象的虚拟文件系统接口
2. **LocalFS** - 本地文件系统实现
3. **GitRepoFS** - Git仓库文件系统实现（支持git tree访问）
4. **VFSResolver** - VFS解析器，根据路径自动创建VFS实例
5. **PathResolver** - 路径解析器，管理VFS挂载和路径解析
6. **VFSService** - 通过ZeroRPC提供的VFS服务
7. **EditManager** - 编辑管理器，支持事务性文件编辑

## 核心功能

### VFS接口方法

- `name() -> str` - 获取VFS名称
- `readonly() -> bool` - 检查是否只读
- `info(path) -> dict` - 获取路径信息
- `list(path, option) -> list[PurePosixPath]` - 列出目录内容
- `get(path) -> bytes` - 获取文件内容
- `put(path, bytes)` - 写入文件内容
- `patch(path, range, bytes, session_id) -> op_id` - 应用补丁
- `commit(op_id, session_id) -> (bool, str)` - 提交编辑
- `abort(op_id, session_id) -> (bool, str)` - 放弃编辑

### VFS类型

#### LocalFS
- **名称格式**: `local:[path]`
- **功能**: 提供本地文件系统访问
- **特性**: 支持读写操作、补丁编辑

#### GitRepoFS
- **名称格式**: `repo:[path]`
- **功能**: Git仓库文件系统，结合了git和localfs
- **特性**: 
  - 常规文件访问（localfs模式）
  - Git tree访问（通过`.git/hash`路径）
  - 支持读写操作和补丁编辑（仅限非git tree路径）

### 路径解析

**VFSResolver** 根据路径自动判断VFS类型：
- 如果路径包含`.git`目录 → GitRepoFS
- 否则 → LocalFS

**PathResolver** 管理VFS挂载：
- `resolve_path(path)` - 解析路径到VFS和剩余路径
- `mount(path, local_path)` - 挂载VFS
- `unmount(path)` - 卸载VFS
- `mounts()` - 列出挂载点

### 编辑系统

**EditManager** 提供事务性编辑：
- **Session管理** - 支持编辑会话
- **Operation跟踪** - 记录所有编辑操作
- **补丁应用** - 在内存中应用补丁，不直接修改文件
- **事务提交** - 批量提交或放弃编辑

## 服务接口

### VFSService RPC方法

#### 路径解析
- `resolve_path(path: str) -> dict`

#### 挂载管理
- `mount(path: str, local_path: str) -> dict`
- `unmount(path: str) -> dict`
- `mounts() -> dict`

#### 文件系统操作
- `info(path: str) -> dict`
- `list(path: str, option: str) -> dict`
- `get(path: str) -> dict` - 返回base64编码的内容
- `get_text(path: str, encoding: str) -> dict` - 返回文本内容
- `put(path: str, content: str, encoding: str) -> dict`

#### 编辑操作
- `patch(path: str, start: int, end: int, content: str, session_id: str, encoding: str) -> dict`
- `commit(op_id: str, session_id: str) -> dict`
- `abort(op_id: str, session_id: str) -> dict`

#### 会话管理
- `create_session(session_name: str) -> dict`
- `list_sessions() -> dict`
- `close_session(session_id: str) -> dict`

## 使用示例

### 启动VFS服务器

```bash
# 启动本地文件系统VFS服务器
python src/textcase/cli/vfs_server.py /path/to/root --port 8000

# 启动Git仓库VFS服务器
python src/textcase/cli/vfs_server.py /path/to/git/repo --service git-repo --port 8001
```

### 通过ZeroRPC客户端使用

```python
import zerorpc

# 连接到VFS服务
client = zerorpc.Client()
client.connect("tcp://localhost:8000")

# 列出根目录
result = client.list("/")
print(result)

# 读取文件
content = client.get_text("/README.md")
print(content)

# 创建编辑会话
session = client.create_session("my_session")
session_id = session['session_id']

# 应用补丁
patch_result = client.patch("/test.txt", 0, 5, "Hello", session_id, "text")

# 提交更改
commit_result = client.commit(session_id=session_id)

client.close()
```

### 通过命令行使用

```bash
# 列出目录
zerorpc tcp://localhost:8000 list '/'

# 获取文件信息
zerorpc tcp://localhost:8000 info '/README.md'

# 读取文件内容
zerorpc tcp://localhost:8000 get_text '/README.md'
```

## Git Tree访问

GitRepoFS支持通过特殊路径访问git tree：

```python
# 访问特定commit的文件树
client.list("/repo/.git/abc123def")  # 列出commit abc123def的根目录

# 读取特定commit的文件
content = client.get_text("/repo/.git/abc123def/README.md")
```

路径格式：`/.git/{commit_hash}/{file_path}`

## 编辑日志

编辑操作记录在根文件系统的`.patches`目录中：
- 支持多个编辑会话
- 操作以JSONL格式存储
- 支持事务性提交和回滚

## 服务注册

VFS服务已注册到服务工厂中：
- `"vfs"` - 通用VFS服务
- `"localfs"` - LocalFS服务别名
- `"git-repo"` - GitRepoFS服务别名

可以通过`service_registry.get_service("vfs")`获取服务端点。

## 测试

运行测试：

```bash
# 运行单元测试
python tests/test_vfs_service.py

# 运行示例
python examples/vfs_example.py
```

## 限制和注意事项

1. **Git Tree只读** - 通过`.git/hash`访问的文件是只读的
2. **编辑事务** - 补丁操作不会立即修改文件，需要显式提交
3. **路径格式** - 使用POSIX路径格式（正斜杠分隔）
4. **二进制安全** - 文件内容通过base64编码传输以确保二进制安全
5. **并发访问** - 当前实现不支持多进程并发编辑

## 扩展性

系统设计支持扩展：
- 可以添加新的VFS实现（如S3FS、HTTPFS等）
- 可以扩展编辑管理器支持更复杂的操作
- 可以添加权限控制和访问日志
- 可以实现分布式VFS挂载
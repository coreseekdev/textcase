# These imports are not available
# from .vfs import VFS, LocalFS, GitRepoFS, EditManager, EditSession
from .vfs_resolver import VFSResolver, PathResolver
from .vfs_service import VFSService
from .config import ConfigService
from .services import TestService, DefaultService, register_service, get_service_factory
from .service_registry_impl import ServiceRegistryImpl, ServiceInfo, create_service_registry

__all__ = [
    # 'VFS', 'LocalFS', 'GitRepoFS', 'EditManager', 'EditSession',
    'VFSResolver', 'PathResolver', 'VFSService',
    'ConfigService',
    'TestService', 'DefaultService', 'register_service', 'get_service_factory',
    'ServiceRegistryImpl', 'ServiceInfo', 'create_service_registry',
]

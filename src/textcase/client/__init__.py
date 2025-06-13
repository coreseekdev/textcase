"""TextCase Client Module.

This module provides client interfaces for connecting to TextCase services.
"""

from .vfs_client import VFSClient, VFSClientException, get_vfs_client

__all__ = ['VFSClient', 'get_vfs_client']
#!/usr/bin/env python3
"""
Git repository utilities.

This module provides utilities for working with Git repositories,
including finding repository roots and handling submodules.
"""

import os
from pathlib import Path, PurePath
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class GitRepoInfo:
    """Information about a Git repository."""
    
    def __init__(self, repo_root: str, is_submodule: bool = False, 
                 submodule_info: Optional[Dict[str, Any]] = None):
        """
        Initialize Git repository information.
        
        Args:
            repo_root: Path to the repository root (where .git is located)
            is_submodule: Whether this is a submodule
            submodule_info: Additional submodule information if applicable
        """
        self.repo_root = os.path.abspath(repo_root)
        self.is_submodule = is_submodule
        self.submodule_info = submodule_info or {}
    
    def __repr__(self):
        return f"GitRepoInfo(repo_root='{self.repo_root}', is_submodule={self.is_submodule})"


def find_git_repo_root(path: str) -> Optional[GitRepoInfo]:
    """
    Find the Git repository root for a given path.
    
    This function first tries to use pygit2 for accurate Git repository detection.
    If pygit2 is not available, it falls back to directory-based detection.
    It also detects if the path is within a Git submodule.
    
    Args:
        path: Path to search from (file or directory)
        
    Returns:
        GitRepoInfo object with repository information, or None if not in a Git repo
    """
    # Convert to absolute path
    abs_path = os.path.abspath(path)
    
    # If path is a file, use its directory
    if os.path.isfile(abs_path):
        abs_path = os.path.dirname(abs_path)
    
    # Try pygit2 first
    try:
        return _find_git_repo_with_pygit2(abs_path)
    except ImportError:
        logger.debug("pygit2 not available, falling back to directory detection")
        return _find_git_repo_with_directory_search(abs_path)
    except Exception as e:
        logger.warning(f"pygit2 failed: {e}, falling back to directory detection")
        return _find_git_repo_with_directory_search(abs_path)


def _find_git_repo_with_pygit2(path: str) -> Optional[GitRepoInfo]:
    """
    Find Git repository using pygit2.
    
    Args:
        path: Directory path to search from
        
    Returns:
        GitRepoInfo object or None
        
    Raises:
        ImportError: If pygit2 is not available
    """
    import pygit2
    
    try:
        # Try to discover the repository
        repo_path = pygit2.discover_repository(path)
        if not repo_path:
            return None
        
        # Open the repository
        repo = pygit2.Repository(repo_path)
        
        # Get the working directory (repository root)
        repo_root = repo.workdir
        if not repo_root:
            # Bare repository, use the .git directory's parent
            repo_root = os.path.dirname(repo_path.rstrip('/'))
        else:
            # Remove trailing slash
            repo_root = repo_root.rstrip('/')
        
        # Check if this is a submodule
        is_submodule = False
        submodule_info = {}
        
        # Check if .git is a file (indicates submodule)
        git_path = os.path.join(repo_root, '.git')
        if os.path.isfile(git_path):
            is_submodule = True
            try:
                with open(git_path, 'r', encoding='utf-8') as f:
                    git_content = f.read().strip()
                    if git_content.startswith('gitdir: '):
                        git_dir = git_content[8:].strip()
                        submodule_info['git_dir'] = git_dir
                        
                        # Try to find parent repository
                        parent_repo_root = _find_parent_repo(repo_root)
                        if parent_repo_root:
                            submodule_info['parent_repo'] = parent_repo_root
                            
                            # Try to get submodule name from parent repo
                            try:
                                parent_repo = pygit2.Repository(parent_repo_root)
                                rel_path = os.path.relpath(repo_root, parent_repo_root)
                                submodule_info['submodule_path'] = rel_path
                                
                                # Check if this path is in .gitmodules
                                gitmodules_path = os.path.join(parent_repo_root, '.gitmodules')
                                if os.path.exists(gitmodules_path):
                                    submodule_info['gitmodules_exists'] = True
                            except Exception as e:
                                logger.debug(f"Could not get submodule info from parent repo: {e}")
            except Exception as e:
                logger.debug(f"Could not read .git file: {e}")
        
        return GitRepoInfo(repo_root, is_submodule, submodule_info)
        
    except pygit2.GitError as e:
        logger.debug(f"pygit2 GitError: {e}")
        return None


def _find_git_repo_with_directory_search(path: str) -> Optional[GitRepoInfo]:
    """
    Find Git repository using directory traversal.
    
    Args:
        path: Directory path to search from
        
    Returns:
        GitRepoInfo object or None
    """
    current_path = Path(path).resolve()
    
    # Traverse up the directory tree
    for parent in [current_path] + list(current_path.parents):
        git_path = parent / '.git'
        
        if git_path.exists():
            repo_root = str(parent)
            is_submodule = False
            submodule_info = {}
            
            # Check if .git is a file (indicates submodule)
            if git_path.is_file():
                is_submodule = True
                try:
                    with open(git_path, 'r', encoding='utf-8') as f:
                        git_content = f.read().strip()
                        if git_content.startswith('gitdir: '):
                            git_dir = git_content[8:].strip()
                            submodule_info['git_dir'] = git_dir
                            
                            # Try to find parent repository
                            parent_repo_root = _find_parent_repo(repo_root)
                            if parent_repo_root:
                                submodule_info['parent_repo'] = parent_repo_root
                                rel_path = os.path.relpath(repo_root, parent_repo_root)
                                submodule_info['submodule_path'] = rel_path
                                
                                # Check if .gitmodules exists in parent
                                gitmodules_path = os.path.join(parent_repo_root, '.gitmodules')
                                if os.path.exists(gitmodules_path):
                                    submodule_info['gitmodules_exists'] = True
                except Exception as e:
                    logger.debug(f"Could not read .git file: {e}")
            
            return GitRepoInfo(repo_root, is_submodule, submodule_info)
    
    return None


def _find_parent_repo(submodule_path: str) -> Optional[str]:
    """
    Find the parent repository of a submodule.
    
    Args:
        submodule_path: Path to the submodule
        
    Returns:
        Path to parent repository root, or None if not found
    """
    current_path = Path(submodule_path).resolve().parent
    
    # Traverse up to find a parent .git directory
    for parent in [current_path] + list(current_path.parents):
        git_path = parent / '.git'
        
        if git_path.exists() and git_path.is_dir():
            return str(parent)
    
    return None


def is_git_repo(path: str) -> bool:
    """
    Check if a path is within a Git repository.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is within a Git repository
    """
    return find_git_repo_root(path) is not None


def get_git_repo_root(path: str) -> Optional[str]:
    """
    Get the Git repository root path for a given path.
    
    Args:
        path: Path to search from
        
    Returns:
        Repository root path, or None if not in a Git repo
    """
    repo_info = find_git_repo_root(path)
    return repo_info.repo_root if repo_info else None


# Convenience functions for backward compatibility
def find_repo_root(path: str) -> Optional[str]:
    """
    Find Git repository root (backward compatibility).
    
    Args:
        path: Path to search from
        
    Returns:
        Repository root path, or None if not found
    """
    return get_git_repo_root(path)
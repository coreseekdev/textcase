#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Git 仓库根目录查找功能
包括 submodule 支持的测试
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from textcase.scm.git import (
    find_git_repo_root,
    get_git_repo_root,
    is_git_repo,
    find_repo_root,
    GitRepoInfo
)

def test_current_repo():
    """测试当前仓库"""
    print("=== 测试当前仓库 ===")
    current_dir = Path.cwd()
    
    # 测试当前目录
    result = find_git_repo_root(current_dir)
    print(f"当前目录: {current_dir}")
    print(f"仓库根目录: {result.repo_root}")
    print(f"是否为 submodule: {result.is_submodule}")
    if result.submodule_info:
        print(f"Submodule 信息: {result.submodule_info}")
    print()
    
    # 测试子目录
    src_dir = current_dir / "src"
    if src_dir.exists():
        result = find_git_repo_root(src_dir)
        print(f"src 目录: {src_dir}")
        print(f"仓库根目录: {result.repo_root}")
        print(f"是否为 submodule: {result.is_submodule}")
        print()
    
    # 测试便利函数
    print("=== 测试便利函数 ===")
    print(f"get_git_repo_root(): {get_git_repo_root(current_dir)}")
    print(f"is_git_repo(): {is_git_repo(current_dir)}")
    print(f"find_repo_root(): {find_repo_root(current_dir)}")
    print()

def test_with_temp_repo():
    """创建临时仓库进行测试"""
    print("=== 创建临时仓库测试 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建主仓库
        main_repo = temp_path / "main_repo"
        main_repo.mkdir()
        
        # 初始化 git 仓库
        subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=main_repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=main_repo, capture_output=True)
        
        # 创建一些文件和目录
        (main_repo / "README.md").write_text("# Test Repo")
        (main_repo / "src").mkdir()
        (main_repo / "src" / "main.py").write_text("print('hello')")
        
        # 提交文件
        subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=main_repo, capture_output=True)
        
        print(f"临时仓库路径: {main_repo}")
        
        # 测试根目录
        result = find_git_repo_root(main_repo)
        print(f"根目录测试 - 仓库根: {result.repo_root}")
        print(f"根目录测试 - 是否为 submodule: {result.is_submodule}")
        
        # 测试子目录
        src_dir = main_repo / "src"
        result = find_git_repo_root(src_dir)
        print(f"子目录测试 - 仓库根: {result.repo_root}")
        print(f"子目录测试 - 是否为 submodule: {result.is_submodule}")
        
        # 测试文件
        main_py = main_repo / "src" / "main.py"
        result = find_git_repo_root(main_py)
        print(f"文件测试 - 仓库根: {result.repo_root}")
        print(f"文件测试 - 是否为 submodule: {result.is_submodule}")
        print()

def test_real_submodule():
    """使用真实的 Git 命令创建和测试 submodule"""
    print("=== 真实 Submodule 测试 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建主仓库
        main_repo = temp_path / "main_repo"
        main_repo.mkdir()
        subprocess.run(["git", "init"], cwd=main_repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=main_repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=main_repo, capture_output=True)
        
        # 在主仓库中创建文件并提交
        (main_repo / "README.md").write_text("# Main Repo")
        subprocess.run(["git", "add", "."], cwd=main_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Main repo initial commit"], cwd=main_repo, capture_output=True)
        
        # 添加远程 submodule
        result = subprocess.run([
            "git", "submodule", "add", "https://gitee.com/lyw732/hello.git", "hello"
        ], cwd=main_repo, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"添加 submodule 失败: {result.stderr}")
            return
        
        # 提交 submodule 添加
        subprocess.run(["git", "commit", "-m", "Add submodule"], cwd=main_repo, capture_output=True)
        
        # 初始化和更新 submodule
        subprocess.run(["git", "submodule", "init"], cwd=main_repo, capture_output=True)
        subprocess.run(["git", "submodule", "update"], cwd=main_repo, capture_output=True)
        
        submodule_dir = main_repo / "hello"
        
        print(f"真实 submodule 路径: {submodule_dir}")
        print(f"主仓库 .git 目录存在: {(main_repo / '.git').exists()}")
        print(f"主仓库 .git 是目录: {(main_repo / '.git').is_dir()}")
        print(f"Submodule .git 文件存在: {(submodule_dir / '.git').exists()}")
        print(f"Submodule .git 是文件: {(submodule_dir / '.git').is_file()}")
        
        if (submodule_dir / '.git').exists():
            with open(submodule_dir / '.git', 'r') as f:
                git_content = f.read().strip()
                print(f"Submodule .git 内容: {git_content}")
        
        # 测试 submodule 检测
        print("\n--- 测试 find_git_repo_root ---")
        result = find_git_repo_root(submodule_dir)
        if result:
            print(f"✅ Submodule 测试 - 仓库根: {result.repo_root}")
            print(f"✅ Submodule 测试 - 根仓库: {result.root_repo}")
            print(f"✅ Submodule 测试 - 是否为 submodule: {result.is_submodule}")
            if result.submodule_info:
                print(f"✅ Submodule 信息: {result.submodule_info}")
        else:
            print("❌ Submodule 测试 - 未找到仓库根")
        
        # 测试 pygit2 是否能直接检测
        print("\n--- 测试 pygit2.discover_repository ---")
        try:
            import pygit2
            repo_path = pygit2.discover_repository(str(submodule_dir))
            if repo_path:
                print(f"✅ pygit2 发现仓库: {repo_path}")
                repo = pygit2.Repository(repo_path)
                print(f"✅ 工作目录: {repo.workdir}")
            else:
                print("❌ pygit2 未发现仓库")
        except ImportError:
            print("⚠️  pygit2 不可用")
        except Exception as e:
            print(f"❌ pygit2 错误: {e}")
        
        print()

def test_non_git_directory():
    """测试非 Git 目录"""
    print("=== 测试非 Git 目录 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        non_git_dir = temp_path / "not_a_repo"
        non_git_dir.mkdir()
        
        print(f"非 Git 目录: {non_git_dir}")
        
        try:
            result = find_git_repo_root(non_git_dir)
            print(f"结果: {result}")
        except Exception as e:
            print(f"预期的异常: {e}")
        
        print(f"is_git_repo(): {is_git_repo(non_git_dir)}")
        print()

def main():
    """主测试函数"""
    print("Git 仓库根目录查找功能测试")
    print("=" * 50)
    
    try:
        # 测试当前仓库
        test_current_repo()
        
        # 测试临时仓库
        test_with_temp_repo()
        
        # 测试真实 submodule
        test_real_submodule()
        
        # 测试非 Git 目录
        test_non_git_directory()
        
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
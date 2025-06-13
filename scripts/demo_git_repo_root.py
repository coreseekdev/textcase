#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git 仓库根目录查找功能演示
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from textcase.scm.git import (
    find_git_repo_root,
    get_git_repo_root,
    is_git_repo,
    find_repo_root
)

def demo_current_repo():
    """演示当前仓库的检测"""
    print("=== 当前仓库检测演示 ===")
    current_dir = Path.cwd()
    
    # 使用主要函数
    result = find_git_repo_root(current_dir)
    if result:
        print(f"📁 当前目录: {current_dir}")
        print(f"🏠 仓库根目录: {result.repo_root}")
        print(f"🏠 根仓库目录: {result.module_root}")
        print(f"📦 是否为 submodule: {'是' if result.is_submodule else '否'}")
        if result.submodule_info:
            print(f"ℹ️  Submodule 信息:")
            for key, value in result.submodule_info.items():
                print(f"   {key}: {value}")
    else:
        print("❌ 当前目录不在 Git 仓库中")
    print()
    
    # 测试子目录
    src_dir = current_dir / "src"
    if src_dir.exists():
        print(f"📁 测试子目录: {src_dir}")
        result = find_git_repo_root(src_dir)
        if result:
            print(f"🏠 仓库根目录: {result.repo_root}")
            print(f"📦 是否为 submodule: {'是' if result.is_submodule else '否'}")
        print()
    
    # 演示便利函数
    print("=== 便利函数演示 ===")
    print(f"get_git_repo_root(): {get_git_repo_root(current_dir)}")
    print(f"is_git_repo(): {is_git_repo(current_dir)}")
    print(f"find_repo_root(): {find_repo_root(current_dir)}")
    print()

def demo_file_detection():
    """演示文件路径的检测"""
    print("=== 文件路径检测演示 ===")
    
    # 测试当前脚本文件
    current_file = Path(__file__)
    print(f"📄 测试文件: {current_file}")
    
    result = find_git_repo_root(current_file)
    if result:
        print(f"🏠 仓库根目录: {result.repo_root}")
        print(f"📦 是否为 submodule: {'是' if result.is_submodule else '否'}")
    else:
        print("❌ 文件不在 Git 仓库中")
    print()

def demo_error_handling():
    """演示错误处理"""
    print("=== 错误处理演示 ===")
    
    # 测试不存在的路径
    non_existent = Path("/non/existent/path")
    print(f"📁 测试不存在的路径: {non_existent}")
    
    try:
        result = find_git_repo_root(non_existent)
        print(f"结果: {result}")
    except Exception as e:
        print(f"❌ 异常: {e}")
    
    print(f"is_git_repo(): {is_git_repo(non_existent)}")
    print()

def main():
    """主演示函数"""
    print("🚀 Git 仓库根目录查找功能演示")
    print("=" * 50)
    
    try:
        demo_current_repo()
        demo_file_detection()
        demo_error_handling()
        
        print("✅ 演示完成！")
        print()
        print("\n=== 功能说明 ===")
        print("1. find_git_repo_root(path) - 查找 Git 仓库根目录，返回 GitRepoInfo 对象")
        print("   - repo_root: 仓库根目录路径")
        print("   - root_repo: 根仓库目录路径（追踪到最顶层非 submodule 仓库）")
        print("   - is_submodule: 是否为 submodule")
        print("   - submodule_info: submodule 详细信息（如果适用）")
        print("\n2. get_git_repo_root(path) - 仅返回仓库根目录路径字符串")
        print("\n3. is_git_repo(path) - 检查路径是否在 Git 仓库中")
        print("\n4. find_repo_root(path) - 向后兼容的函数")
        print("\n特性:")
        print("- 🔍 支持 submodule 检测")
        print("- 🏠 自动追踪到根仓库（跨越 submodule 链）")
        print("- 🔄 pygit2 优先，目录搜索作为后备")
        print("- 📁 支持文件和目录路径")
        print("- ⚠️  完善的错误处理")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
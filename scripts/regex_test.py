#!/usr/bin/env python3
"""
验证正则表达式 (?i)(^|\[|`|\s)TC\\-0*4($|\]|`|:|\s|$).* 的匹配行为
"""

import re

# 测试的正则表达式
regex_pattern = r"(?i)(^|\[|`|\s)TC\\-0*4($|\]|`|:|\s|$).*"
                    

# 测试用例
test_cases = [
    "TC-4",                      # 基本匹配
    "tc-4",                      # 小写匹配
    "TC-04",                     # 带前导零
    "[TC-4]",                    # 方括号包围
    "`TC-4`",                    # 反引号包围
    "TC-4: 测试用例",             # 带冒号
    "TC-4 测试用例",              # 带空格
    "前缀 TC-4",                 # 前面有文本
    "TC-4后缀",                  # 后面有文本（无空格）
    "TC-41",                     # 不应匹配
    "TC-41: 相似编号测试",        # 不应匹配
    "包含TC-4的文本",             # 不应匹配
    "结尾包含 TC-4",              # 不应匹配
    "TC-4\nTC-41",               # 多行测试
    "hello world",               # 不应匹配
    "二级标题B",                   # 不应匹配
]

def test_regex(pattern, test_strings):
    """测试正则表达式对多个字符串的匹配情况"""
    compiled_pattern = re.compile(pattern)
    
    print(f"正则表达式: {pattern}\n")
    print("匹配结果:")
    print("-" * 60)
    
    for i, test_str in enumerate(test_strings):
        match = compiled_pattern.search(test_str)
        if match:
            print(f"{i+1:2d}. 匹配: '{test_str}'")
            print(f"    匹配组: {match.groups()}")
            print(f"    匹配范围: {match.span()}")
            print(f"    匹配文本: '{match.group()}'")
        else:
            print(f"{i+1:2d}. 不匹配: '{test_str}'")
        print("-" * 60)
    
    # 测试Tree-sitter风格的匹配（完全匹配整个字符串）
    print("\nTree-sitter风格匹配 (完全匹配):")
    print("-" * 60)
    for i, test_str in enumerate(test_strings):
        # Tree-sitter通常要求完全匹配，所以我们使用fullmatch或添加^$锚点
        match = re.fullmatch(pattern, test_str)
        if match:
            print(f"{i+1:2d}. 完全匹配: '{test_str}'")
        else:
            print(f"{i+1:2d}. 不完全匹配: '{test_str}'")
    print("-" * 60)

if __name__ == "__main__":
    test_regex(regex_pattern, test_cases)
    
    # 测试修改后的正则表达式，更严格的边界条件
    print("\n\n修改后的正则表达式测试（更严格的边界条件）:")
    strict_pattern = r"(?i)(^|\[|`|\s)TC\-0*4\b($|\]|`|:|\s)"
    test_regex(strict_pattern, test_cases)

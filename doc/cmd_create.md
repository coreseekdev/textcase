1. 可以通过命令行工具 初始化一个目录用于 textcase
   - 每个 被版本控制工具 管理的 repo ，仅能有一个 root text case dir
2. 初始化过的目录包括
   - .textcase.yml ，记录 meta 配置，包括 prefix | 分割符号 | 填充的0(默认为2)， 即 001 | 002 | 003 | ... 
   - index.yml ，记录 文件的排列顺序
   - PREFIX001.md | PREFIX002.md | ...  存储数据的文件
   - {$verb}.yml | ...  存储 tag <-> 文件的关系，如果文件或目录列出在 此，则被标记了 verb 作为 tag 


.textcase.yml  文件示例
settings:
  digits: 3
  prefix: REQ
  sep: ''    # 分割符号，常见选项是 - 默认为 '' 输入的内容更少些
  default_tag: 
    - tagName   # 不做任何配置的 默认 Tag 列表
tags:
  tagName: path/to/file_list.yml  # tag -> 文件

3. root text case dir 还包括目录

    - .llm/provider/$provider_name.yml  # llm provider 的配置
    - .llm/agent/$agent_name.yml  # llm agent 的配置

    这个目录为按需创建（默认不创建）

上面的内容，整理抽象为 protocol module / sub modules , 构造时，需要能够访问一个 vfs 对象

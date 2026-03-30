---
name: skill-L10n
description: skill-L10n 是一个面向 Agent Skill 的语境感知本地化工具，主要用于将英文的 Agent skill 文档（尤其 `SKILL.md`）和参考文件翻译为中文，同时按需翻译脚本中的注释。
---


# skill-L10n

## 简介
----
skill-L10n 是面向 Agent Skill 的语境感知本地化工具。它以 SKILL.md 为优先目标，结合上下文判断哪些段落需要翻译，并对 references 中的说明与 scripts 目录下的脚本注释进行有选择性的翻译。目标是尽量保留代码示例、参数名与命令行示例不被误翻，便于审阅与回滚。

## 主要特性
---
- 针对 Markdown / SKILL.md：段落级上下文判断（前后段落一并作为上下文），仅翻译模型判定为“用户可读/说明性文本”的段落。保留 code fence、表格、frontmatter、inline code。
- 针对脚本/代码文件：只处理注释行；默认保留原注释并在其下追加一行翻译（与原注释使用相同的注释前缀和缩进）。
- 可配置证书校验：通过环境变量 `SKILL_L10N_VERIFY` 控制 http 客户端的 SSL 验证（默认 false，以兼容企业自签/代理环境）。
- 简单缓存：避免对完全相同文本重复调用翻译 API，节省调用成本。
- 变更报告：为每个被修改的文件生成 unified diff（.diff）报告，便于审阅与回滚。
- 错误容忍：翻译失败时脚本会跳过并保留原文，同时在报告中标注（不会中断批量处理）。

## 快速开始
---
1. 安装依赖（示例）：
```bash
python3 -m pip install --upgrade openai httpx
```

2. 设置环境变量（必须）：
```bash
export DEEPSEEK_API_TOKEN="your_token_here"
# 默认为 false，若在安全公网环境或已配��受信根证书可设为 true
export SKILL_L10N_VERIFY=false
```

3. 运行（示例）：
```bash
# 在 skill-L10n 目录下对某个 skill 进行本地化并把 diff 报告写入 ./reports
python3 scripts/skill_l10n.py ./skills/your-skill ./reports

# 或使用包装脚本
scripts/run.sh ./skills/your-skill ./reports
```

## CLI 参数与模式
---------------
- `--src`：源语言（默认 `auto`）
- `--tgt`：目标语言（默认 `zh`）
- `--mode`：全局 Markdown 模式：`replace`（替换，默认）或 `append`（在原文后追加译文）
  - 注意：代码文件注释的默认处理遵循 `--preserve-original-for-code` 设置（见下）。
- `--preserve-original-for-code`：`yes`（默认）或 `no`。`yes` 时在原注释下追加翻译行；`no` 时直接替换注释。
- 环境变量 `SKILL_L10N_VERIFY`：`true` 或 `false`（默认 false）。控制 httpx.Client(verify=... )。

## 翻译策略与细节
----------------
- Markdown / SKILL.md：
  - 脚本会把正文按段落拆分，隐藏并保留 code fence，再对每个 prose 段落连同前后上下文询问模型“是否翻译 + 翻译��果”。
  - inline code（如 `my_func()`）、参数名、命令行示例与表格项通常被保护不翻译。
  - 默认行为：替换（即不保留英文原文）。可通过 `--mode append` 改为在原文后追加译文。

- 脚本与代码文件：
  - 仅对注释行翻译决策。若模型判定需要翻译且 `--preserve-original-for-code=yes`（默认），则保留原注释并在下一行添加同样注释前缀的译文（保持缩进）。
  - 示例：
    ```python
    # This function adds two numbers
    # 此函数用于将两个数字相加
    def add(a, b):
        return a + b
    ```

## 缓存与成本控制
---
- 内存级缓存用于避免相同文本的重复请求。对于大规模仓库建议先在小规模 demo 上跑通并查看 diff，再批量执行，控制 API 成本。

## 安全与注意事项
---
- 默认 `SKILL_L10N_VERIFY=false`，以兼容一些企业环境（自签或代理）。强烈建议在公网或生产环境将 `SKILL_L10N_VERIFY=true` 并确保系统根证书链完整。
- 请勿在代码中明文保存 API Token，使用环境变量（DEEPSEEK_API_TOKEN）。
- 脚本会原地修改目标目录下文件，请在 git 仓库中使用分支/暂存区进行变更，或先备份目标目录。每个修改会在 `report_dir` 生成 `.diff` 报告，便于审阅与回滚。

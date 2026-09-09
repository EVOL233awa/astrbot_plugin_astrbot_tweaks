# Astrbot Tweaks

运行时 tweak 插件，不修改 AstrBot 本体源码。它把多项 AstrBot 行为调整做成 WebUI 可配置开关，适合在 AstrBot 后续升级后继续复用。

- 版本：v0.2.1
- 兼容：AstrBot `>=4.27,<5`
- 仓库：<https://github.com/EVOL233awa/astrbot_plugin_astrbot_tweaks>

## 功能

| 配置项 | 默认值 | 行为 |
| --- | --- | --- |
| `enabled` | `true` | 总开关 |
| `context_compression_tweak` | `true` | 上下文压缩策略调整 |
| `remove_computer_use_warning` | `true` | 移除官方英文 Computer Use 提示 |
| `minimal_skill_rules` | `true` | 精简技能规则 |
| `llm_kwargs_passthrough` | `false` | 透传 `temperature` 与 `max_tokens` |
| `subagent_direct_return` | `false` | SubAgent 白名单工具结果直通主模型 |

## 项目结构

```text
astrbot_plugin_astrbot_tweaks/
  main.py                          AstrBot 插件入口
  astrbot_tweaks/
    compat.py                      AstrBot 版本与兼容性判断
    prompt_utils.py                纯提示词转换逻辑
    tool_result_cleaners.py        工具结果清洗与截断
    patches/
      context.py                   ContextManager 补丁
      skill_prompt.py              build_skills_prompt 补丁
      llm_kwargs.py                OpenAI-compatible kwargs 透传补丁
      subagent_bypass.py           SubAgent 直通拦截切面
    registry.py                    补丁配置、安装、恢复与状态管理
  tests/
    test_compat.py                 版本判断测试
    test_prompt_utils.py           提示词转换测试
    test_context_patch.py          上下文补丁逻辑测试
    test_skill_patch.py            技能提示词补丁逻辑测试
    test_registry.py               注册表与开关测试
    test_runtime_integration.py    AstrBot 环境集成测试
```

## 安装

### 从 GitHub 安装

```bash
git clone https://github.com/EVOL233awa/astrbot_plugin_astrbot_tweaks
```

把 `astrbot_plugin_astrbot_tweaks` 目录放入 AstrBot 的 `data/plugins/` 下，然后在 WebUI 插件管理中重载插件。

### 上传安装

将插件目录打包为 zip，确保 zip 内包含 `metadata.yaml`，然后在 AstrBot WebUI 插件管理中上传安装。

## 配置

在 WebUI 插件配置中修改开关并保存。AstrBot 会自动热重载插件，无需重启容器。

## 行为说明

### 上下文压缩

当 `context_compression_tweak` 开启时：

- LLM 压缩策略下不会先按轮次截断。
- 会话轮数超过 `enforce_max_turns` 时强制触发 LLM 压缩。

### Computer Use 提示

当 `remove_computer_use_warning` 开启时，会从 LLM system prompt 中移除 AstrBot 在 `runtime=none` 时追加的官方英文提示。

### 精简技能规则

当 `minimal_skill_rules` 开启时，保留 AstrBot 动态生成的技能列表，但用固定精简规则替换官方长规则：

1. 技能列表是完整清单；没有明确触发或明显匹配时不主动调用。
2. 执行技能前必须用当前可用工具读取对应的 `SKILL.md`，禁止凭描述脑补内容。
3. 只读 `SKILL.md` 直接引用的文件，禁止遍历或全量读取技能目录。
4. 技能执行失败时不得伪称成功，简短说明后继续。

### LLM kwargs 透传

`llm_kwargs_passthrough` 只处理 `temperature` 和 `max_tokens`。开启后，插件通过
`Context.llm_generate(..., **kwargs)` 显式传入的这两个参数会真正进入
OpenAI-compatible 请求，并覆盖 provider `custom_extra_body` 中的同名配置。

其他 kwargs、provider 基础配置和 `custom_extra_body` 中的非同名参数不会被修改。

### SubAgent 直通

`subagent_direct_return` 用于主模型把任务委派给本地小模型 SubAgent 的场景。命中
`subagent_bypass_tools` 白名单、且本轮只调用一个工具时，工具结果会由 CPU 侧清洗并
直接回传主模型，跳过小模型读取长文本后的第二轮推理。

默认白名单：

```text
fetch
web_search_tavily
read_text_file
astr_kb_search
list_directory
angel_note_read
browse_threads
search_threads
read_thread
get_sub_replies
```

`fetch` 默认返回 Markdown 或 JSON 时直接穿透；只有识别为 HTML 时才移除 `script`、
`style`、`svg`、注释等噪音。`web_search_tavily` 会格式化当前 AstrBot 返回的
`results[].title/url/snippet/index` 结构，并按 `subagent_search_top_k` 保留条目。
所有直通结果都会按 `subagent_direct_max_chars` 截断。

直通只把结果交回主模型继续组织答案，不会直接发送给用户。白名单只应包含只读工具；
不建议加入写文件、发消息、发帖或账号状态变更类工具。

## 兼容性与降级

- 插件启动时会检查 AstrBot 版本和核心 API 是否存在。
- 如果 AstrBot 版本不在支持范围内，或某个补丁所需的内部接口不存在，插件会记录 warning 并跳过对应补丁，不会导致插件加载失败或 AstrBot 崩溃。
- 上下文压缩补丁运行时遇到异常时，会回退到 AstrBot 官方压缩逻辑。
- 新增补丁依赖的 AstrBot 内部方法缺失时，对应补丁会跳过；插件本身仍可加载。
- 插件卸载或重载时会恢复 AstrBot 原始方法。

## 测试

```bash
python -m pytest tests
```

涉及 AstrBot 运行时 patch 的测试需要在 AstrBot 环境可导入时执行。

## 发布

发布前请确认：

- `metadata.yaml` 中的 `name`、`version`、`author`、`repo` 与实际仓库一致。
- 插件 zip 不包含 `__pycache__`、`.pytest_cache`、`.git` 等非必要文件。
- 插件 zip 大小不超过 16MB。

## 更新日志

### v0.2.1

### Fixed

- 修复透传参数上下文在 payload 准备完成后被提前清理，导致实际请求仍使用 provider 默认值的问题。
  补充 SubAgent 直通的端到端回归测试。

### v0.2.0

### Added

- 新增 OpenAI-compatible Provider 的 `temperature/max_tokens` kwargs 透传开关。
- 新增 SubAgent 白名单工具直通开关、默认工具白名单和独立开关。
- 新增 fetch HTML 清洗、Tavily 结果提纯、通用工具结果截断。
- 新增 LLM kwargs、SubAgent 直通与工具结果清洗测试。

### Fixed

- 修复插件显式传入的 `temperature/max_tokens` 被宿主 payload 准备逻辑丢弃的问题。

### v0.1.0

- 初始版本。
- 支持三项运行时 tweak 的独立开关。
- 插件卸载或重载时恢复 AstrBot 原始行为。

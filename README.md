# Astrbot Tweaks

运行时 tweak 插件，不修改 AstrBot 本体源码。它把三项 AstrBot 行为调整做成 WebUI 可配置开关，适合在 AstrBot 后续升级后继续复用。

- 版本：v0.1.0
- 兼容：AstrBot `>=4.27,<5`
- 仓库：<https://github.com/EVOL233awa/astrbot_plugin_astrbot_tweaks>

## 功能

| 配置项 | 默认值 | 行为 |
| --- | --- | --- |
| `enabled` | `true` | 总开关 |
| `context_compression_tweak` | `true` | 上下文压缩策略调整 |
| `remove_computer_use_warning` | `true` | 移除官方英文 Computer Use 提示 |
| `minimal_skill_rules` | `true` | 精简技能规则 |

## 项目结构

```text
astrbot_plugin_astrbot_tweaks/
  main.py                          AstrBot 插件入口
  astrbot_tweaks/
    compat.py                      AstrBot 版本与兼容性判断
    prompt_utils.py                纯提示词转换逻辑
    patches/
      context.py                   ContextManager 补丁
      skill_prompt.py              build_skills_prompt 补丁
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

## 兼容性与降级

- 插件启动时会检查 AstrBot 版本和核心 API 是否存在。
- 如果 AstrBot 版本不在支持范围内，或某个补丁所需的内部接口不存在，插件会记录 warning 并跳过对应补丁，不会导致插件加载失败或 AstrBot 崩溃。
- 上下文压缩补丁运行时遇到异常时，会回退到 AstrBot 官方压缩逻辑。
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

### v0.1.0

- 初始版本。
- 支持三项运行时 tweak 的独立开关。
- 插件卸载或重载时恢复 AstrBot 原始行为。

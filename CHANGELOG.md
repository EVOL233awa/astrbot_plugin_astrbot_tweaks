# Changelog

## v0.3.0

### Added

- 新增 `reasoning_only_guard`，默认拦截只有 `reasoning_content`、没有正文和工具调用的模型响应。
- 新增 `empty_output_retry_attempts`，可配置 reasoning-only 空正文的自动重试次数，范围 1-10。
- 新增 `llm_kwargs_allowlist`，可配置允许透传的 LLM 参数白名单。
- 对 `messages`、`model`、`tools`、`stream` 等结构参数增加强制禁止规则。
- 新增 reasoning-only、空正文重试和运行时安装恢复测试。

### Changed

- reasoning-only 响应统一抛出 `EmptyModelOutputError`，复用 AstrBot 自动重试链路，避免静默空回复。
- `llm_kwargs_passthrough` 从固定只支持 `temperature/max_tokens` 改为按白名单透传。

## v0.2.2

### Fixed

- 修复并行 SubAgent 直通结果因 `ContextVar` token 跨 Task reset 失败的问题。

## v0.2.1

### Fixed

- 修复透传参数上下文在 payload 准备完成后被提前清理，导致实际请求仍使用 provider 默认值的问题。

### Changed

- 补充 SubAgent 直通端到端回归测试。

## v0.2.0

### Added

- 新增 OpenAI-compatible Provider 的 `temperature/max_tokens` kwargs 透传开关。
- 新增 SubAgent 白名单工具直通开关、默认工具白名单和独立清洗开关。
- 新增 fetch HTML 清洗、Tavily 结果提纯与通用工具结果截断。
- 新增 LLM kwargs、SubAgent 直通与工具结果清洗测试。

### Fixed

- 修复插件显式传入的 `temperature/max_tokens` 被宿主 payload 准备逻辑丢弃的问题。
- 修复透传参数上下文在 payload 准备完成后被提前清理，导致实际请求仍使用 provider 默认值的问题。

## v0.1.0

- 初始版本。
- 支持上下文压缩、移除英文 Computer Use 提示、精简技能规则三个独立开关。
- 插件卸载或重载时恢复 AstrBot 原始行为。
- AstrBot 版本或内部 API 不兼容时自动降级，不影响插件加载。

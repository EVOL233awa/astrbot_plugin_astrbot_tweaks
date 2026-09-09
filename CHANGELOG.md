# Changelog

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

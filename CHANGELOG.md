# Changelog

## v0.1.0

- 初始版本。
- 支持上下文压缩、移除英文 Computer Use 提示、精简技能规则三个独立开关。
- 插件卸载或重载时恢复 AstrBot 原始行为。
- AstrBot 版本或内部 API 不兼容时自动降级，不影响插件加载。
- 内部迭代：按 compat、prompt、patch、registry 模块拆分实现，并按模块拆分 pytest。

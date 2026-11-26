# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式,
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-11-26

### 新增
- 平铺、角标、居中三种水印布局,支持透明度、旋转与字体回退
- 批量图片处理 CLI 与 Python 库接口
- 14 个单元测试及三系统 × Python 3.9 / 3.11 / 3.13 CI
- 干净虚拟环境 wheel 安装与完整水印流程冒烟
- 中文 README 与 MIT 许可证

### 修复
- 明确 Pillow >= 10.1.0 依赖,与字体 API 实际要求一致
- 拒绝负数字号、间距和边距,避免平铺死循环
- 禁止输出目录与输入目录相同,防止覆盖原图
- CLI 统一 UTF-8 输出,避免 Windows 传统编码下中文崩溃

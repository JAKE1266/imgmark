# imgmark

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-14%20passing-success)
![Dependencies](https://img.shields.io/badge/dependencies-Pillow%20%3E%3D%2010.1-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

批量图片水印工具 —— 一条命令给整个目录的照片加上平铺 / 角标 / 居中水印。

- **三种布局**：`tile` 45° 平铺（样片防盗图）、`corner` 四角角标（版权署名）、`center` 居中（预览图）
- **排版细节**：透明度、字号自适应（按图宽 1/14）、旋转角、间距、颜色、边距都可调
- **格式友好**：jpg / png / webp / bmp 输入，jpg 输出自动转 RGB 避免 alpha 报错
- **批量安全**：输出目录自动跳过不再二次处理；损坏文件跳过不中断；文字图层纯函数不碰原图；输出目录不能与输入目录相同
- **中文字体**：内置微软雅黑 / 黑体 / Arial / DejaVu / PingFang 回退链，找不到时兜底 Pillow 内置字体

依赖 Pillow >= 10.1.0，Python >= 3.9。

## 安装

```bash
python -m pip install .        # 自动安装 Pillow,获得 imgmark 命令
python -m imgmark --help       # 安装后也可用模块方式运行
```

## 真实运行示例

准备两张样片（720×480），三个模式各跑一次：

```console
$ python -m imgmark watermark demo/photos -t "样片 · 禁止商用"
已处理 2 张图片 → demo\photos\watermarked
  demo\photos\watermarked\lake.png
  demo\photos\watermarked\sunset.jpg

$ python -m imgmark watermark demo/photos -t "© 2026 摄影作品" --mode corner --corner br --opacity 0.6 --out demo/branded
已处理 2 张图片 → demo\branded
  ...

$ python -m imgmark watermark demo/photos -t "预 览" --mode center --opacity 0.5 --size 72 --out demo/preview
已处理 2 张图片 → demo\preview
  ...
```

平铺效果：半透明「样片 · 禁止商用」按 45° 斜排铺满全图；角标效果：右下角 60% 不透明度版权行。

## 常用参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `--mode` | `tile` / `corner` / `center` | tile |
| `--corner` | `tl` `tr` `bl` `br` | br（右下） |
| `--opacity` | 0~1，不透明度 | 0.35 |
| `--size` | 字号；0 = 图宽的 1/14 自适应 | 0 |
| `--rotate` | 平铺旋转角 | 45 |
| `--gap` | 平铺间距（像素），0 = 自动 | 0 |
| `--color` | `#FFFFFF` / `red` 等 | #FFFFFF |
| `--out` | 输出目录 | `<dir>/watermarked` |
| `--pattern` | 只处理匹配的文件，如 `*.jpg,*.png` | 全部支持格式 |

## 作为库使用

```python
from pathlib import Path
from PIL import Image
from imgmark import WatermarkOptions, apply_watermark, batch

img = Image.open("sunset.jpg")
out = apply_watermark(img, WatermarkOptions(text="样片", mode="tile"))
out.save("sunset_marked.jpg")

# 整个目录
batch(Path("photos"), Path("out"), WatermarkOptions(text="© 2026", mode="corner"))
```

## 设计取舍

- **图层合成**：水印画在独立 RGBA 图层上再 `alpha_composite`，透明度 / 旋转不污染原图
- **平铺旋转一次成型**：先旋转文字块再整版排布，效率高于逐字旋转
- **输出目录保护**：`batch` 显式排除输出目录，重复运行不会套娃水印
- **字体回退链**：跨平台找到第一个可用字体即停，全部失败仍可输出（内置字体）

## 运行测试

```bash
python -m pip install .
python -m unittest discover -s tests -v

# 发布包验证
python -m pip install build twine
python -m build
python -m twine check dist/*
python tests/smoke_installed.py
```

冒烟脚本会先下载 Pillow wheel,再在干净虚拟环境中离线安装并运行完整水印流程。


## 📁 项目结构

```
imgmark/
├── LICENSE
├── imgmark/
├── pyproject.toml
├── tests/
└── README.md
```

## License

MIT

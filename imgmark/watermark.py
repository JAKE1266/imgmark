"""水印核心：文字图层生成、三种布局（角标/居中/平铺）、批量处理。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# 字体回退链：跨平台的常见选择，最后兜底 Pillow 内置位图字体
FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",      # Windows 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",    # Windows 黑体
    "C:/Windows/Fonts/arial.ttf",     # Windows Arial
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # 常见 Linux
    "/System/Library/Fonts/PingFang.ttc",               # macOS
]


@dataclass
class WatermarkOptions:
    text: str
    mode: str = "tile"          # tile / corner / center
    corner: str = "br"          # tl / tr / bl / br（mode=corner 时生效）
    opacity: float = 0.35       # 0 ~ 1
    size: int = 0               # 字号；0 表示按图宽自适应（宽度的 1/14）
    rotate: float = 45.0        # 平铺文字旋转角
    gap: int = 0                # 平铺间距（像素）；0 表示自动（文字对角线 × 1.6）
    color: str = "#FFFFFF"
    margin: int = 24            # 角标模式边距

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("水印文字不能为空")
        if self.mode not in ("tile", "corner", "center"):
            raise ValueError(f"未知模式 {self.mode!r}（tile / corner / center）")
        if self.corner not in ("tl", "tr", "bl", "br"):
            raise ValueError(f"未知角标方位 {self.corner!r}")
        if not 0 < self.opacity <= 1:
            raise ValueError("opacity 需在 (0, 1] 区间")


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """按回退链找系统字体；都没有则用 Pillow 内置字体（新版本支持 size）。"""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def parse_color(spec: str) -> tuple[int, int, int]:
    """'#RRGGBB' / '#RGB' / 颜色名 → RGB 元组。"""
    s = spec.strip()
    try:
        return tuple(int(v) for v in Image.new("RGB", (1, 1), s).convert("RGB").getpixel((0, 0)))[:3]  # type: ignore
    except ValueError:
        raise ValueError(f"无法识别的颜色: {spec!r}") from None


def _text_layer(text: str, font, color: tuple[int, int, int], opacity: float,
                rotate: float) -> Image.Image:
    """生成只含水印文字的 RGBA 图层（已按需旋转）。"""
    alpha = max(1, min(255, int(round(opacity * 255))))
    # 先在足够大的画布上量取文字边界，再裁紧
    probe = Image.new("RGBA", (10, 10))
    bbox = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font)
    w, h = max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])
    layer = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((4 - bbox[0], 4 - bbox[1]), text,
                               font=font, fill=color + (alpha,))
    if rotate:
        layer = layer.rotate(rotate, expand=True, resample=Image.BICUBIC)
    return layer


def _auto_size(width: int, requested: int) -> int:
    return requested if requested > 0 else max(12, width // 14)


def apply_watermark(img: Image.Image, opt: WatermarkOptions) -> Image.Image:
    """在图片上叠加水印，返回新图（不修改原图）。"""
    size = _auto_size(img.width, opt.size)
    font = load_font(size)
    color = parse_color(opt.color)
    layer = _text_layer(opt.text, font, color, opt.opacity,
                        opt.rotate if opt.mode == "tile" else 0.0)

    if opt.mode == "center":
        base = img.convert("RGBA")
        pos = ((base.width - layer.width) // 2, (base.height - layer.height) // 2)
        base.alpha_composite(layer, dest=(max(0, pos[0]), max(0, pos[1])))

    elif opt.mode == "corner":
        base = img.convert("RGBA")
        x = opt.margin if opt.corner in ("tl", "bl") else base.width - layer.width - opt.margin
        y = opt.margin if opt.corner in ("tl", "tr") else base.height - layer.height - opt.margin
        base.alpha_composite(layer, dest=(max(0, x), max(0, y)))

    else:  # tile 平铺
        base = img.convert("RGBA")
        gap = opt.gap or max(60, int((layer.width + layer.height) * 0.8))
        sheet = Image.new("RGBA", (base.width + layer.width + gap,
                                   base.height + layer.height + gap), (0, 0, 0, 0))
        y = -layer.height // 2
        row = 0
        while y < sheet.height:
            x = -layer.width // 2 + (gap // 2 if row % 2 else 0)
            while x < sheet.width:
                sheet.alpha_composite(layer, dest=(x, y))
                x += gap
            y += gap
            row += 1
        sheet = sheet.crop((layer.width // 2, layer.height // 2,
                            layer.width // 2 + base.width,
                            layer.height // 2 + base.height))
        base.alpha_composite(sheet)

    return base.convert(img.mode if img.mode in ("RGB", "RGBA") else "RGBA")


def batch(src_dir: Path, out_dir: Path, opt: WatermarkOptions,
          pattern: str = "") -> list[Path]:
    """批量处理目录下的图片；返回输出文件列表。

    - 输出目录默认 ``<src>/watermarked``；输出目录不会再次被处理
    - ``pattern`` 逗号分隔的 glob 白名单；空表示处理所有支持的扩展名
    """
    src_dir, out_dir = Path(src_dir), Path(out_dir)
    if not src_dir.is_dir():
        raise NotADirectoryError(str(src_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir_resolved = out_dir.resolve()

    if pattern.strip():
        import fnmatch
        pats = [p.strip().lower() for p in pattern.split(",") if p.strip()]
        want = lambda p: any(fnmatch.fnmatchcase(p.name.lower(), g) for g in pats)
    else:
        want = lambda p: p.suffix.lower() in SUPPORTED_EXTS

    written: list[Path] = []
    for path in sorted(src_dir.iterdir()):
        if not path.is_file() or path.resolve() == out_dir_resolved:
            continue
        if not want(path):
            continue
        try:
            with Image.open(path) as im:
                im.load()
                img = im.copy()
        except Exception:  # 跳过损坏/不支持的文件
            continue
        out = apply_watermark(img, opt)
        dst = out_dir / path.name
        if dst.suffix.lower() in (".jpg", ".jpeg") and out.mode == "RGBA":
            out = out.convert("RGB")
        out.save(dst)
        written.append(dst)
    return written

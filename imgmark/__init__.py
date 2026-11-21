"""imgmark —— 批量图片水印工具。"""
from .watermark import SUPPORTED_EXTS, WatermarkOptions, apply_watermark, batch, load_font, parse_color

__version__ = "0.1.0"

__all__ = [
    "SUPPORTED_EXTS", "WatermarkOptions", "apply_watermark", "batch",
    "load_font", "parse_color", "__version__",
]

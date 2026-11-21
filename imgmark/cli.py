"""命令行入口：``python -m imgmark`` 或安装后 ``imgmark``。

用法：
    imgmark watermark <dir> -t "水印文字"                  # 平铺水印（默认）
    imgmark watermark <dir> -t "© 2026" --mode corner --corner br
    imgmark watermark <dir> -t "样片" --mode center --opacity 0.5
    imgmark watermark <dir> -t "X" --out 输出目录 --pattern *.jpg,*.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .watermark import SUPPORTED_EXTS, WatermarkOptions, batch


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="imgmark",
        description="批量图片水印：平铺 / 角标 / 居中，支持透明度、旋转与多格式",
    )
    ap.add_argument("--version", action="version", version=f"imgmark {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("watermark", help="给目录里的图片批量加水印")
    sp.add_argument("dir", help="图片目录")
    sp.add_argument("-t", "--text", required=True, help="水印文字")
    sp.add_argument("--mode", default="tile", choices=["tile", "corner", "center"],
                    help="布局：tile 平铺（默认）/ corner 角标 / center 居中")
    sp.add_argument("--corner", default="br", choices=["tl", "tr", "bl", "br"],
                    help="角标方位（默认 br 右下）")
    sp.add_argument("--opacity", type=float, default=0.35, help="不透明度 0~1（默认 0.35）")
    sp.add_argument("--size", type=int, default=0, help="字号；0=按图宽自适应（默认）")
    sp.add_argument("--rotate", type=float, default=45, help="平铺旋转角（默认 45）")
    sp.add_argument("--gap", type=int, default=0, help="平铺间距像素；0=自动")
    sp.add_argument("--color", default="#FFFFFF", help="颜色，如 #FFFFFF / red")
    sp.add_argument("--margin", type=int, default=24, help="角标边距（默认 24px）")
    sp.add_argument("--out", help="输出目录（默认 <dir>/watermarked）")
    sp.add_argument("--pattern", default="", help="只处理匹配的文件，如 *.jpg,*.png")
    args = ap.parse_args(argv)

    try:
        opt = WatermarkOptions(
            text=args.text, mode=args.mode, corner=args.corner, opacity=args.opacity,
            size=args.size, rotate=args.rotate, gap=args.gap, color=args.color,
            margin=args.margin,
        )
        src = Path(args.dir)
        out = Path(args.out) if args.out else src / "watermarked"
        written = batch(src, out, opt, pattern=args.pattern)
    except (ValueError, NotADirectoryError) as e:
        print(f"错误：{e}", file=sys.stderr)
        return 2

    if not written:
        print("没有找到可处理的图片"
              + ("" if args.pattern else f"（支持 {'/'.join(sorted(SUPPORTED_EXTS))}）"))
        return 1
    print(f"已处理 {len(written)} 张图片 → {out}")
    for p in written:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

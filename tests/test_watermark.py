import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from imgmark.watermark import (
    SUPPORTED_EXTS,
    WatermarkOptions,
    apply_watermark,
    batch,
    load_font,
    parse_color,
)


def solid(width=320, height=200, color=(40, 80, 160), mode="RGB"):
    return Image.new(mode, (width, height), color)


def make_jpg(path: Path, width=320, height=200):
    solid(width, height).save(path, quality=92)
    return path


class TestOptions(unittest.TestCase):
    def test_validation(self):
        with self.assertRaises(ValueError):
            WatermarkOptions(text="")
        with self.assertRaises(ValueError):
            WatermarkOptions(text="x", mode="diagonal")
        with self.assertRaises(ValueError):
            WatermarkOptions(text="x", opacity=0)
        with self.assertRaises(ValueError):
            WatermarkOptions(text="x", corner="middle")
        with self.assertRaises(ValueError):
            WatermarkOptions(text="x", size=-1)
        with self.assertRaises(ValueError):
            WatermarkOptions(text="x", gap=-1)
        with self.assertRaises(ValueError):
            WatermarkOptions(text="x", margin=-1)

    def test_parse_color(self):
        self.assertEqual(parse_color("#FFFFFF"), (255, 255, 255))
        self.assertEqual(parse_color("#abc"), (170, 187, 204))
        self.assertEqual(parse_color("red"), (255, 0, 0))
        with self.assertRaises(ValueError):
            parse_color("not-a-color")


class TestApply(unittest.TestCase):
    def test_mode_preserved_and_size_unchanged(self):
        img = solid()
        out = apply_watermark(img, WatermarkOptions(text="水印", mode="tile"))
        self.assertEqual(out.size, img.size)
        self.assertEqual(out.mode, "RGB")

    def test_tile_changes_many_pixels(self):
        img = solid(640, 480, color=(20, 20, 20))
        out = apply_watermark(img, WatermarkOptions(text="WATER", mode="tile", opacity=0.9))
        changed_channels = sum(value != 0 for value in ImageChops.difference(img, out).tobytes())
        self.assertGreater(changed_channels, 500)  # 平铺应显著改变画面

    def test_corner_only_changes_corner(self):
        img = solid(400, 300, color=(10, 10, 10))
        out = apply_watermark(img, WatermarkOptions(text="MARK", mode="corner",
                                                    corner="br", margin=10, opacity=1.0))
        self.assertEqual(img.getpixel((50, 50)), out.getpixel((50, 50)))  # 左上不动
        box = (out.width - 120, out.height - 60, out.width, out.height)
        self.assertIsNotNone(ImageChops.difference(img.crop(box), out.crop(box)).getbbox())

    def test_center_changes_middle(self):
        img = solid(400, 300, color=(0, 0, 0))
        out = apply_watermark(img, WatermarkOptions(text="CENTER", mode="center", opacity=1.0))
        box = (150, 100, 250, 200)
        self.assertIsNotNone(ImageChops.difference(img.crop(box), out.crop(box)).getbbox())

    def test_original_not_mutated(self):
        img = solid()
        before = img.tobytes()
        apply_watermark(img, WatermarkOptions(text="水印"))
        self.assertEqual(before, img.tobytes())


class TestBatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = Path(self.tmp.name)
        make_jpg(self.src / "a.jpg")
        solid().save(self.src / "b.png")
        (self.src / "notes.txt").write_text("skip me", encoding="utf-8")
        (self.src / "broken.jpg").write_bytes(b"not an image")

    def tearDown(self):
        self.tmp.cleanup()

    def test_batch_skips_outdir_and_unsupported(self):
        out = self.src / "watermarked"
        # 预放一张图到输出目录，验证不会被再次处理
        out.mkdir()
        make_jpg(out / "a.jpg")
        written = batch(self.src, out, WatermarkOptions(text="DEMO"))
        names = [p.name for p in written]
        self.assertEqual(sorted(names), ["a.jpg", "b.png"])  # broken.jpg / notes.txt 跳过
        self.assertTrue((out / "a.jpg").exists())
        with Image.open(out / "a.jpg") as img:
            self.assertEqual(img.mode, "RGB")  # jpg 输出自动转 RGB

    def test_batch_pattern_filter(self):
        out = self.src / "out2"
        written = batch(self.src, out, WatermarkOptions(text="D"), pattern="*.png")
        self.assertEqual([p.name for p in written], ["b.png"])

    def test_batch_rejects_same_output_directory(self):
        original = (self.src / "a.jpg").read_bytes()
        with self.assertRaises(ValueError):
            batch(self.src, self.src, WatermarkOptions(text="D"))
        self.assertEqual((self.src / "a.jpg").read_bytes(), original)

    def test_batch_missing_dir(self):
        with self.assertRaises(NotADirectoryError):
            batch(self.src / "nope", self.src / "o", WatermarkOptions(text="x"))


if __name__ == "__main__":
    unittest.main()

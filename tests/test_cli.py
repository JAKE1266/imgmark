import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from imgmark.cli import main


class CliTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.src = self.root / "photos"
        self.src.mkdir()
        self.image = self.src / "sample.jpg"
        Image.new("RGB", (320, 200), (20, 40, 80)).save(self.image, quality=92)

    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_watermark_workflow(self):
        original = self.image.read_bytes()
        out = self.root / "marked"
        code, stdout, stderr = self.run_cli(
            "watermark", str(self.src), "-t", "样片", "--mode", "center", "--out", str(out)
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("已处理 1 张图片", stdout)
        self.assertEqual(self.image.read_bytes(), original)
        with Image.open(out / "sample.jpg") as image:
            self.assertEqual(image.size, (320, 200))
            self.assertEqual(image.mode, "RGB")

    def test_negative_gap_returns_error(self):
        code, _, stderr = self.run_cli(
            "watermark", str(self.src), "-t", "样片", "--gap", "-1"
        )
        self.assertEqual(code, 2)
        self.assertIn("gap 不能为负数", stderr)

    def test_utf8_output_under_legacy_windows_encoding(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "cp1252"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "imgmark",
                "watermark",
                str(self.src),
                "-t",
                "水印",
                "--out",
                str(self.root / "marked"),
            ],
            capture_output=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertIn("已处理", result.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()

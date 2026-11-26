from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command, *, cwd: Path, env=None) -> str:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed: {}\n{}\n{}".format(
                " ".join(str(item) for item in command),
                result.stdout,
                result.stderr,
            )
        )
    return result.stdout


def main() -> int:
    wheels = sorted((ROOT / "dist").glob("imgmark-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one imgmark wheel in dist/, found {}".format(len(wheels)))
    wheel = wheels[0].resolve()

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        if "imgmark/watermark.py" not in names:
            raise RuntimeError("Wheel is missing imgmark/watermark.py")
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")
        requirements = [
            line.split(":", 1)[1].strip().replace(" ", "")
            for line in metadata.splitlines()
            if line.startswith("Requires-Dist:")
        ]
        if requirements != ["Pillow>=10.1.0"]:
            raise RuntimeError("Unexpected runtime dependencies: {}".format(requirements))

    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        work = base / "work"
        work.mkdir()
        dependencies = base / "dependencies"
        dependencies.mkdir()
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary=:all:",
                "--dest",
                dependencies,
                "Pillow>=10.1.0",
            ],
            cwd=work,
        )

        venv = base / "venv"
        scripts = venv / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        executable = scripts / ("imgmark.exe" if os.name == "nt" else "imgmark")
        run([sys.executable, "-m", "venv", str(venv)], cwd=work)
        run(
            [python, "-m", "pip", "install", "--no-index", "--find-links", dependencies, wheel],
            cwd=work,
        )

        module_info = run(
            [
                python,
                "-c",
                "import imgmark, PIL; print(imgmark.__file__); print(PIL.__file__); print(imgmark.__version__)",
            ],
            cwd=work,
        ).splitlines()
        if len(module_info) != 3 or any("site-packages" not in line for line in module_info[:2]):
            raise RuntimeError("Installed modules did not resolve from the clean virtual environment")

        version = run([executable, "--version"], cwd=work).strip()
        if version != "imgmark {}".format(module_info[2].strip()):
            raise RuntimeError("Console script version mismatch: {}".format(version))
        help_text = run([executable, "--help"], cwd=work)
        if "watermark" not in help_text:
            raise RuntimeError("Console script help output is incomplete")

        source = work / "source"
        source.mkdir()
        original = source / "sample.jpg"
        run(
            [
                python,
                "-c",
                "from PIL import Image; Image.new('RGB', (320, 200), (20, 40, 80)).save('source/sample.jpg', quality=92)",
            ],
            cwd=work,
        )
        before = hashlib.sha256(original.read_bytes()).hexdigest()
        output = work / "output" / "sample.jpg"
        run(
            [executable, "watermark", "source", "-t", "样片", "--mode", "center", "--out", "output"],
            cwd=work,
        )
        if not output.is_file():
            raise RuntimeError("Installed CLI did not create the watermarked image")
        if hashlib.sha256(original.read_bytes()).hexdigest() != before:
            raise RuntimeError("Installed CLI modified the original image")

        image_info = json.loads(
            run(
                [
                    python,
                    "-c",
                    "import json; from PIL import Image, ImageChops; "
                    "src=Image.open('source/sample.jpg'); out=Image.open('output/sample.jpg'); "
                    "print(json.dumps({'size': out.size, 'mode': out.mode, "
                    "'changed': ImageChops.difference(src.convert('RGB'), out.convert('RGB')).getbbox() is not None}))",
                ],
                cwd=work,
            )
        )
        if image_info != {"size": [320, 200], "mode": "RGB", "changed": True}:
            raise RuntimeError("Installed CLI produced an invalid image: {}".format(image_info))

    print("Installed wheel smoke test: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

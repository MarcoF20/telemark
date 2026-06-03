import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_VENV = ROOT / ".build" / "pyinstaller-venv"


def venv_python():
    if os.name == "nt":
        return BUILD_VENV / "Scripts" / "python.exe"
    return BUILD_VENV / "bin" / "python"


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def remove_output(path):
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def pyinstaller_ready(python):
    check = """
from importlib import metadata
try:
    version = metadata.version("pyinstaller")
except metadata.PackageNotFoundError:
    raise SystemExit(1)
major, minor, *_ = (int(part) for part in version.split(".")[:2])
raise SystemExit(0 if major == 6 and minor >= 20 else 1)
"""
    return subprocess.run([str(python), "-c", check], cwd=ROOT).returncode == 0


def main():
    if not BUILD_VENV.exists():
        venv.EnvBuilder(with_pip=True, clear=True).create(BUILD_VENV)

    python = venv_python()
    if not pyinstaller_ready(python):
        run([str(python), "-m", "pip", "install", "-r", "requirements-build.txt"])

    shutil.rmtree(ROOT / "build", ignore_errors=True)
    remove_output(ROOT / "dist" / "TeleAssist")
    remove_output(ROOT / "dist" / "TeleAssist.exe")
    run([
        str(python),
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "teleassist.spec",
    ])

    output_file = ROOT / "dist" / ("TeleAssist.exe" if os.name == "nt" else "TeleAssist")
    print(f"\nBuilt TeleAssist at: {output_file}")
    if os.name == "nt":
        print(f"Launch file: {output_file}")
    else:
        print(f"Launch file: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc

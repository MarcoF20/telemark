# Building TeleAssist

Build the clickable app from the repository root:

```bash
python scripts/build_app.py
```

The script creates an isolated build environment in `.build/pyinstaller-venv`,
installs PyInstaller there, and writes one clickable executable to `dist`.
Use Python 3.10 or newer to run the build.

Users launch:

- Windows: `dist/TeleAssist.exe`
- Linux/macOS: `dist/TeleAssist`

Build on the same operating system you want to distribute to. PyInstaller does
not cross-compile Windows `.exe` files from Linux or Linux binaries from
Windows.

Packaged builds keep the app database in a user-writable folder instead of
inside the bundled program files:

- Windows: `%APPDATA%\TeleAssist\teleassist.db`
- macOS: `~/Library/Application Support/TeleAssist/teleassist.db`
- Linux: `$XDG_DATA_HOME/teleassist/teleassist.db` or
  `~/.local/share/teleassist/teleassist.db`

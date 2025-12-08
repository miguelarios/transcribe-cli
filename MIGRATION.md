# Migration Guide: pyenv-virtualenv → uv

## Why Migrate?

The previous setup using pyenv-virtualenv had a catch-22:
- Virtual environments isolate dependencies ✅
- But `pip install -e .` only makes the tool available in that specific virtualenv ❌
- You'd need to activate the virtualenv every time to use `transcribe` ❌
- This defeats the purpose of a global CLI tool

uv solves this with `uv tool install`:
- Dependencies stay isolated ✅
- Command available globally without activation ✅
- Simpler setup (one tool instead of pyenv + virtualenv + pip) ✅

## Migration Steps

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
exec "$SHELL"
```

### 2. Clean up old pyenv setup (optional)

```bash
# Remove old virtualenv
pyenv virtualenv-delete transcribe-env

# You can keep pyenv for other projects if needed
```

### 3. Install with uv

```bash
cd ~/path/to/transcribe
uv tool install .
```

### 4. Test

```bash
cd ~/Desktop
transcribe --help
```

### 5. Update on work machine

```bash
# Same simple process
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/yourusername/transcribe.git
cd transcribe
uv tool install .
```

## What Changes?

| Task | Old (pyenv-virtualenv) | New (uv) |
|------|------------------------|----------|
| **Fresh setup** | `brew install pyenv pyenv-virtualenv`<br>Edit `.zshrc`<br>`pyenv install 3.11.14`<br>`pyenv virtualenv 3.11.14 transcribe-env`<br>`pyenv activate transcribe-env`<br>`pip install -e .`<br>`pyenv rehash` | `curl -LsSf https://astral.sh/uv/install.sh \| sh`<br>`cd transcribe`<br>`uv tool install .` |
| **Use tool** | `pyenv activate transcribe-env`<br>`transcribe audio.mp3` | `transcribe audio.mp3` |
| **Update tool** | `cd transcribe`<br>`git pull`<br>`pyenv activate transcribe-env`<br>`pip install -e .`<br>`pyenv rehash` | `cd transcribe`<br>`git pull`<br>`uv tool install . --force` |
| **Work on code** | `cd transcribe`<br>`pyenv activate transcribe-env`<br>`python transcribe.py` | `cd transcribe`<br>`uv run python transcribe.py` |

## Keeping Both (Transition Period)

You can use both during transition:

- Keep pyenv for other projects
- Use uv for this CLI tool
- No conflicts between them

## Rolling Back

If you need to revert:

```bash
uv tool uninstall transcribe
pyenv activate transcribe-env
pip install -e ~/path/to/transcribe
pyenv rehash
```

## Benefits of uv

1. **Faster**: uv is written in Rust and is significantly faster than pip
2. **Simpler**: One tool replaces pyenv + virtualenv + pip
3. **Modern**: Active development with frequent improvements
4. **Global CLI tools**: Designed for exactly this use case with `uv tool`
5. **Better dependency resolution**: More reliable than pip
6. **Cross-platform**: Works consistently on macOS, Linux, and Windows

## Troubleshooting

### "transcribe: command not found" after installation

```bash
# Restart your shell
exec "$SHELL"

# Or add uv bin directory to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Check if tool is installed

```bash
uv tool list
```

### Reinstall if needed

```bash
cd ~/path/to/transcribe
uv tool install . --force
```

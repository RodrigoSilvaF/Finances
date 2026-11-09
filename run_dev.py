"""Roda o app localmente lendo variáveis do arquivo .env (que não vai para o git)."""
import os
from pathlib import Path

env = Path(__file__).with_name(".env")
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

from finances import create_app  # noqa: E402

if __name__ == "__main__":
    create_app().run(port=int(os.environ.get("PORT", 5000)), debug=True)

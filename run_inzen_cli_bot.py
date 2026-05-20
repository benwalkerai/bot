"""PyInstaller entry point for Inzen CLI Bot.

Using a top-level launcher avoids relative-import issues that happen when
packaging bot/main.py directly as a script.
"""

from bot.main import cli


if __name__ == "__main__":
    cli()
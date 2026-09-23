import json
from dataclasses import dataclass
from pathlib import Path


SETTINGS_PATH = Path(__file__).parent.parent / "settings.local.json"
DEFAULT_OUT_DIR = Path(__file__).parent.parent / "out"


@dataclass
class Settings:
    directories: list[Path]


def load_settings() -> Settings:
    if not SETTINGS_PATH.exists():
        return Settings(directories=[DEFAULT_OUT_DIR])

    with open(SETTINGS_PATH, 'r') as f:
        raw_settings = json.load(f)
        settings = Settings(
            directories=[Path(d) for d in raw_settings["directories"]]
        )
        if DEFAULT_OUT_DIR not in settings.directories:
            settings.directories.insert(0, DEFAULT_OUT_DIR)
        return settings


def add_directory(directory: Path) -> None:
    if not directory.exists():
        directory.mkdir()

    if not directory.is_dir():
        raise ValueError(f"Path {directory} is not a directory")

    settings = load_settings()
    settings.directories.append(directory)
    _save_settings(settings)


def remove_directory(directory: Path) -> None:
    settings = load_settings()
    settings.directories.remove(directory)
    _save_settings(settings)


def _save_settings(settings: Settings) -> None:
    with open(SETTINGS_PATH, 'w') as f:
        raw_settings = {
            "directories": [d.as_posix() for d in settings.directories]
        }
        json.dump(raw_settings, f, indent=2)

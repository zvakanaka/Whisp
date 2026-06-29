import json
from pathlib import Path
from gi.repository import GLib

# Data directory configuration
CONFIG_DIR = Path(GLib.get_user_config_dir()) / "whisp"
CONFIG_FILE = CONFIG_DIR / "config.json"

class Config:
    def __init__(self):
        self.data = {
            "data_dir": str(Path(GLib.get_user_data_dir()) / "whisp" / "notes"),
            "window_width": 400,
            "window_height": 400,
            "is_maximized": False,
            "font_name": "Monospace 11",
            "paper_theme": "blank",
            "confirm_delete": True,
            "color_scheme": "system",
            "startup_behavior": "last_note",
            "first_run": True,
            "last_seen_version": "0.0.0",
            "run_in_background": False,
            "run_on_startup": False,
            "start_hidden": False,
            "show_command_toasts": True
        }
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                self.data.update(json.loads(CONFIG_FILE.read_text()))
            except:
                pass
        else:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.save()

    def save(self):
        CONFIG_FILE.write_text(json.dumps(self.data))

    @property
    def data_dir(self):
        return Path(self.data["data_dir"])

    @data_dir.setter
    def data_dir(self, value):
        self.data["data_dir"] = str(value)
        self.save()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

config = Config()
DATA_DIR = config.data_dir
TRASH_DIR = DATA_DIR / ".trash"

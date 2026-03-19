import json
import os

CONFIG_FILE = "server_config.json"
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "server_ip": "192.168.0.17",
    "port": 8765,
    "password": "default_pass",
    "output_device": "",
    "admin_password": "admin123",
    "cert_valid_days": 365,
    "rate_limit_per_ip": 20,
    "max_audio_queue_size": 20,
    "log_file": None,
    "cert_file": None,
    "key_file": None
}

def load_config():
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения конфигурации: {e}")
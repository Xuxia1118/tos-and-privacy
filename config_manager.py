import json
import os

CONFIG_FILE = "config.json"
config_data = {}

def load_config():
    global config_data
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    else:
        config_data = {}
    return config_data

def save_config(new_data):
    global config_data
    config_data.update(new_data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

# 啟動時先載入一次
load_config()

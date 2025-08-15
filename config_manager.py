import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """每次呼叫都重新讀取檔案"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(new_data):
    """覆蓋或更新設定"""
    config = load_config()  # 先讀取現有設定
    config.update(new_data) # 更新
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

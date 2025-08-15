import json

CONFIG_PATH = "config.json"
config_data = {
    "prefix": "!",
    "welcome_channel_id": 0,
    "welcome_message": ""
}

def load_config():
    global config_data
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except FileNotFoundError:
        save_config()

def save_config():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def update_config(new_data):
    global config_data
    config_data.update(new_data)
    save_config()

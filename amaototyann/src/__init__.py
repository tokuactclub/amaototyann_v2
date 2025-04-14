# loggerの設定
import json
import os
from logging import getLogger, config

with open("amaototyann/src/log_config.json", "r") as f:
    config.dictConfig(json.load(f))
logger = getLogger("logger")


is_render_server = os.getenv("IS_RENDER_SERVER")
if not is_render_server or is_render_server == "False":
    from dotenv import load_dotenv
    load_dotenv(override=True)
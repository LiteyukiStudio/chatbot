import os

import nonebot
import yaml
from pydantic import BaseModel

config = None


class BasicConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 20216
    superusers: list[str] = []
    command_start: list[str] = ["/", ""]
    nickname: set[str] = {"Liteyuki"}


def load_from_yaml(file: str) -> dict:
    nonebot.logger.debug("Loading config from %s" % file)
    global config
    if not os.path.exists(file):
        nonebot.logger.warning(f'Config file {file} not found, created default config, please modify it and restart')
        with open(file, 'w', encoding='utf-8') as f:
            yaml.dump(BasicConfig().dict(), f, default_flow_style=False)

    with open(file, 'r', encoding='utf-8') as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)
        config = conf
        if conf is None:
            nonebot.logger.warning(f'Config file {file} is empty, use default config. please modify it and restart')
            conf = BasicConfig().dict()
        return conf
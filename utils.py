import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
from PIL import Image, ImageColor
from requests.structures import CaseInsensitiveDict

import config


def get_a_logger(logger_name, level=1, allowed_handlers=0):
    logger = logging.getLogger(logger_name)
    if level != 1:
        logger_name = (logger_name or 'root') + logging.getLevelName(level).replace('Level ', '.')
    if len(logger.handlers) <= allowed_handlers:
        handler = RotatingFileHandler(
            f"logs/{logger_name or 'root'}.log", maxBytes=5000000, backupCount=1, encoding='UTF-8'
        )
        handler.setFormatter(config.FORMATTER)
        handler.setLevel(level)
        logger.addHandler(handler)
    return logger


def chunks(list_in, n):
    """Yield successive n-sized chunks from list_in."""
    for i in range(0, len(list_in), n):
        yield list_in[i:i + n]


def sleep_until(t, dry=False):
    rv = max(t - time.time(), 0)
    if not dry:
        time.sleep(max(t - time.time(), 0))
    return rv


class RequestsManager:
    def __init__(self):
        if os.path.exists('diskcache'):
            with open('diskcache') as json_in:
                cache = json.load(json_in)
                self._get_headers = cache['get']
                self._set_headers = cache['set']
        else:
            # TODO: requests.head
            get_h = requests.head("https://pixels.pythondiscord.com/get_pixels")
            self._get_headers = get_h.headers
            set_h = requests.head("https://pixels.pythondiscord.com/set_pixel")
            self._set_headers = set_h.headers
        self.canvas = None
        self.logger = get_a_logger('RequestsManager')
        self.last_get_pixels = 0

    @property
    def get_headers(self) -> CaseInsensitiveDict[str]:
        return self._get_headers

    @property
    def set_headers(self) -> CaseInsensitiveDict[str]:
        return self._set_headers

    @get_headers.setter
    def get_headers(self, value):
        self._get_headers = value
        with open('diskcache', 'w') as json_out:
            json.dump({'get': self._get_headers, 'set': self._set_headers}, json_out)

    @set_headers.setter
    def set_headers(self, value):
        self._set_headers = value
        with open('diskcache', 'w') as json_out:
            json.dump({'get': self._get_headers, 'set': self._set_headers}, json_out)

    def wait_for_get_pixels(self):
        t = 0
        if self.get_headers.get('Cooldown-Reset', None):
            self.logger.info(f"get_pixels is on cooldown!!!")
            t = int(self.get_headers['Cooldown-Reset'])
        elif int(self.get_headers['Requests-Remaining']) == 0:
            t = int(self.get_headers['Requests-Reset']) / int(self.get_headers['Requests-Limit'])
        if t:
            self.logger.debug(f"get_pixels is sleeping for {t}")
            time.sleep(t + config.SLEEP_LENIENCY)

    def get_pixels(self):
        if self.last_get_pixels < time.time() - 2:
            return self.canvas.copy()

        self.wait_for_get_pixels()

        size_r = requests.get("https://pixels.pythondiscord.com/get_size", headers=config.headers)
        self.logger.debug(size_r.headers)
        self.logger.debug(size_r.json())
        size_json = size_r.json()
        ww, hh = size_json["width"], size_json["height"]

        pixels_r = requests.get("https://pixels.pythondiscord.com/get_pixels", headers=config.headers)
        self.logger.debug(pixels_r.headers)
        self.logger.debug(pixels_r.content)
        self.get_headers = pixels_r.headers

        if pixels_r.status_code == 200:
            self.logger.debug("Got pixels. Saving 'current_canvas.png'")
            raw = pixels_r.content
            image_data = [tuple(map(int, r)) for r in chunks(raw, 3)]
            img = Image.new('RGBA', (ww, hh))
            img.putdata(image_data)
            img.save('current_canvas.png')
            self.canvas = img
            self.last_get_pixels = time.time()
            return img.copy()
        else:
            self.logger.error(f"get_pixels responded with {pixels_r.status_code}")
            self.logger.debug(pixels_r.content)

    def wait_for_set_pixel(self):
        t = 0
        if self.set_headers.get('Cooldown-Reset', None):
            self.logger.info(f"set_pixel is on cooldown!!!")
            t = int(self.set_headers['Cooldown-Reset'])
        elif int(self.set_headers['Requests-Remaining']) == 0:
            t = int(self.set_headers['Requests-Reset']) / int(self.set_headers['Requests-Limit'])
        if t:
            self.logger.debug(f"set_pixel is sleeping for {t}")
            time.sleep(t + config.SLEEP_LENIENCY)

    def can_set_pixel(self):
        return int(self.set_headers['Requests-Remaining']) > 0

    def set_pixel(self, x: int, y: int, rgb: str):
        self.wait_for_set_pixel()

        set_r = requests.post("https://pixels.pythondiscord.com/set_pixel",
                              json={'x': x, 'y': y, 'rgb': rgb},
                              headers=config.headers)

        self.logger.debug(set_r.json())
        self.logger.debug(set_r.headers)
        self.set_headers = set_r.headers
        if set_r.status_code == 200:
            self.logger.info(f"Successfully set ({x}, {y}) to #{rgb.upper()}")
            self.canvas.putpixel((x, y), ImageColor.getcolor(f"#{rgb}", "RGB"))
            self.canvas.save('current_canvas.png')
        else:
            self.logger.error(f"set_pixel responded with {set_r.status_code}")

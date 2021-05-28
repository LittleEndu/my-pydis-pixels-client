import logging
import time
from logging.handlers import RotatingFileHandler

import requests
from PIL import Image

import config


def get_a_logger(logger_name):
    logger = logging.getLogger(logger_name)
    if len(logger.handlers) == 0:
        handler = RotatingFileHandler(
            f"logs/{logger_name or 'root'}.log", maxBytes=5000000, backupCount=1, encoding='UTF-8'
        )
        handler.setFormatter(config.FORMATTER)
        handler.setLevel(1)
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


class Pixel:
    def __init__(self, data):
        self.data = data

    def to_rgb(self):
        return tuple(map(int, self.data))


class RequestsManager:
    def __init__(self):
        self.get_pixels_time = 0
        self.set_pixel_time = time.time() + 60
        self.canvas: Image = None
        self.logger = get_a_logger('RequestsManager')

    def get_pixels(self):
        sleep_until(self.get_pixels_time)
        size_r = requests.get("https://pixels.pythondiscord.com/get_size", headers=config.headers)
        size_json = size_r.json()
        ww, hh = size_json["width"], size_json["height"]
        pixels_r = requests.get("https://pixels.pythondiscord.com/get_pixels", headers=config.headers)
        self.logger.debug(pixels_r.headers)
        try:
            reset = int(pixels_r.headers['Requests-Reset'])
            limit = int(pixels_r.headers['Requests-Limit'])
            self.get_pixels_time = time.time() + (reset / limit) + config.LENIENCY
            if pixels_r.status_code == 200:
                self.logger.info("Got pixels. Saving 'current_canvas.png'")
                image_data = []
                raw = pixels_r.content
                for r in chunks(raw, 3):
                    pixel = Pixel(r)
                    image_data.append(pixel.to_rgb())
                img = Image.new('RGBA', (ww, hh))
                img.putdata(image_data)
                img.save('current_canvas.png')
                return img.copy()
            else:
                self.logger.error(f"get_pixels responded with {pixels_r.status_code}")
                self.logger.debug(pixels_r.content)
        except:
            self.logger.debug(pixels_r.content)
            raise

    def wait_for_set_pixel(self):
        self.logger.info(f"set_pixel is sleeping for {sleep_until(self.set_pixel_time, True)}")
        sleep_until(self.set_pixel_time)

    def set_pixel(self, x: int, y: int, rgb: str):
        sleep_until(self.set_pixel_time)
        set_r = requests.post("https://pixels.pythondiscord.com/set_pixel",
                              json={'x': x, 'y': y, 'rgb': rgb},
                              headers=config.headers)
        self.logger.debug(set_r.headers)
        try:
            try:
                reset = int(set_r.headers['Requests-Reset'])
                limit = int(set_r.headers['Requests-Limit'])
            except KeyError:
                self.set_pixel_time = time.time() + int(set_r.headers['Cooldown-Reset']) + config.LENIENCY
            else:
                self.set_pixel_time = time.time() + (reset / limit) + config.LENIENCY
                if set_r.status_code == 200:
                    self.logger.info(f"Successfully set {x}, {y} to #{rgb.upper()}")
                else:
                    self.logger.error(f"set_pixel responded with {set_r.status_code}")
                    self.logger.debug(set_r.json())
        except:
            self.logger.debug(set_r.json())
            raise

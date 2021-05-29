import logging
import time
from logging.handlers import RotatingFileHandler

import requests
from PIL import Image, ImageColor

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


def sleep_until(t):
    return max(t - time.time(), 0)


class RequestsManager:
    def __init__(self):
        self.next_get = []
        self.next_set = []
        get_h = requests.head("https://pixels.pythondiscord.com/get_pixels", headers=config.headers)
        self.get_headers = get_h.headers
        if get_h.headers.get('Requests-Reset'):
            self.next_get.append(time.time() + float(get_h.headers['Requests-Reset']))
        set_h = requests.head("https://pixels.pythondiscord.com/set_pixel", headers=config.headers)
        self.set_headers = set_h.headers
        if set_h.headers.get('Requests-Reset'):
            self.next_set.append(time.time() + float(set_h.headers['Requests-Reset']))
        self.canvas = None
        self.logger = get_a_logger('RequestsManager')
        self.last_get_pixels = 0

    def wait_for_ratelimit(self, endpoint, headers, next_one: list):
        self.logger.debug(f"WAIT FOR {endpoint}: {next_one}")
        if headers.get('Cooldown-Reset', None):
            self.logger.info(f"{endpoint} is on cooldown!!!")
            t = int(headers['Cooldown-Reset'])
            t += config.SLEEP_LENIENCY
            self.logger.debug(f"{endpoint} will sleep for {t}")
            time.sleep(t)
            headers = requests.head(f"https://pixels.pythondiscord.com/{endpoint}", headers=config.headers).headers
            next_one.append(time.time() + float(headers['Requests-Reset']))

        if not next_one:
            self.logger.debug('no next')
            return

        if int(headers['Requests-Remaining']) > 0:
            self.logger.debug('still remaining')
            return

        t = sleep_until(next_one.pop(0))
        if t:
            t += config.SLEEP_LENIENCY
            self.logger.debug(f"{endpoint} will sleep for {t}")
            time.sleep(t)
        else:
            self.logger.debug(f"no sleep necessary")

    def wait_for_get_pixels(self):
        self.wait_for_ratelimit('get_pixels', self.get_headers, self.next_get)

    def get_pixels(self):
        if self.last_get_pixels > time.time() - 2 and self.canvas:
            return self.canvas.copy()

        self.logger.debug("GET_PIXELS")
        self.wait_for_get_pixels()

        size_r = requests.get("https://pixels.pythondiscord.com/get_size", headers=config.headers)
        self.logger.debug(size_r.headers)
        # self.logger.debug(size_r.json())
        size_json = size_r.json()
        ww, hh = size_json["width"], size_json["height"]

        pixels_r = requests.get("https://pixels.pythondiscord.com/get_pixels", headers=config.headers)
        self.logger.debug(pixels_r.headers)
        # self.logger.debug(pixels_r.content)
        self.get_headers = pixels_r.headers
        if pixels_r.status_code == 200:
            self.next_get.append(time.time() + float(pixels_r.headers['Requests-Reset']))
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
            raise Exception

    def wait_for_set_pixel(self):
        self.wait_for_ratelimit('set_pixel', self.set_headers, self.next_set)

    def request_set_pixel_sleep(self):
        self.logger.debug("set_pixel requested to sleep")
        try:
            if int(self.set_headers['Requests-Remaining']) == 0:
                t = sleep_until(self.next_set[0])
                if t:
                    t += config.SLEEP_LENIENCY
                    self.logger.debug(f"set_pixel will sleep for {t}")
                    time.sleep(t)
        except KeyError:
            t = int(self.set_headers['Cooldown-Reset'])
            t += config.SLEEP_LENIENCY
            self.logger.info("set_pixel is on cooldown!!!")
            self.logger.debug(f"set_pixel will sleep for {t}")
            time.sleep(t)
            self.set_headers = requests.head(
                f"https://pixels.pythondiscord.com/set_pixel", headers=config.headers
            ).headers

    def set_pixel(self, x: int, y: int, rgb: str):
        self.logger.debug("SET_PIXEL")
        self.wait_for_set_pixel()

        set_r = requests.post("https://pixels.pythondiscord.com/set_pixel",
                              json={'x': x, 'y': y, 'rgb': rgb},
                              headers=config.headers)

        self.logger.debug(set_r.json())
        self.logger.debug(set_r.headers)
        self.set_headers = set_r.headers
        if set_r.status_code == 200:
            self.next_set.append(time.time() + float(set_r.headers['Requests-Reset']))
            current_pixel = self.canvas.getpixel((x, y))
            self.logger.info(f"Successfully set ({x}, {y}) to #{rgb.upper()} "
                             f"(from #{'%02x%02x%02x' % current_pixel[:3]})")
            self.canvas.putpixel((x, y), ImageColor.getcolor(f"#{rgb}", "RGB"))
            self.canvas.save('current_canvas.png')
        else:
            self.logger.error(f"set_pixel responded with {set_r.status_code}")
            raise Exception

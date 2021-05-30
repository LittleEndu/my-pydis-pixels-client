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


class RateLimitManager:
    def __init__(self, endpoint, last_headers):
        logger_name = f'{self.__class__.__name__}_{endpoint}'
        self.logger = get_a_logger(logger_name)
        self.logger.info(f"{logger_name} __init__")
        self.endpoint = endpoint

        self.next_allowed = []
        for _ in range(int(last_headers['Requests-Remaining'])):
            self.next_allowed.append(time.time())
        while len(self.next_allowed) < int(last_headers['Requests-Limit']):
            self.next_allowed.append(time.time() + float(last_headers['Requests-Reset']))

    def sleep(self):
        t = sleep_until(self.next_allowed[0] + config.SLEEP_LENIENCY)
        if t:
            self.logger.debug(f"{self.endpoint} will sleep for {t}")
            time.sleep(t)

    def set_next_allowed(self, headers):
        self.logger.debug(f"NEXT ALLOWED {[i - time.time() for i in self.next_allowed]}")
        if not headers.get('Requests-Reset'):
            self.logger.info(f"{self.endpoint} is on cooldown!!!")
            t = int(headers['Cooldown-Reset'])
            t += config.SLEEP_LENIENCY
            self.logger.debug(f"{self.endpoint} will sleep for {t}")
            time.sleep(t)
            head = requests.head(f"https://pixels.pythondiscord.com/{self.endpoint}", headers=config.headers).headers
            self.next_allowed = []
            for _ in range(int(head['Requests-Remaining'])):
                self.next_allowed.append(time.time())
            while len(self.next_allowed) < int(head['Requests-Limit']):
                self.next_allowed.append(time.time() + float(head['Requests-Reset']))
        else:
            while len(self.next_allowed) < int(headers['Requests-Limit']):
                self.next_allowed.append(time.time() + int(headers['Requests-Period']))
            while len(self.next_allowed) > int(headers['Requests-Limit']):
                self.next_allowed.pop(0)
            self.next_allowed.pop(0)
            self.next_allowed.append(time.time() + int(headers['Requests-Period']))
        self.logger.debug(f"next allowed has been set to: {[i - time.time() for i in self.next_allowed]}")

    def request(self, method, **kwargs):
        self.sleep()
        r = requests.request(method,
                             f"https://pixels.pythondiscord.com/{self.endpoint}",
                             headers=config.headers, **kwargs)
        self.logger.debug(r.headers)
        self.set_next_allowed(r.headers)
        return r

    def get(self, **kwargs):
        return self.request('get', **kwargs)

    def post(self, **kwargs):
        return self.request('post', **kwargs)


class RequestsManager:
    def __init__(self):
        self.logger = get_a_logger(f'{self.__class__.__name__}')
        self.logger.info("\n\n")
        self.logger.info(f"{self.__class__.__name__} __init__")
        self.get_manager = RateLimitManager('get_pixels', self.get_headers_for('get_pixels'))
        self.set_manager = RateLimitManager('set_pixel', self.get_headers_for('set_pixel'))
        self.canvas = None
        self.last_get_pixels = 0

    def get_headers_for(self, endpoint):
        h = requests.head(f"https://pixels.pythondiscord.com/{endpoint}", headers=config.headers).headers
        if not h.get('Requests-Reset'):
            self.logger.info(f"{endpoint} is on cooldown!!!")
            t = int(h['Cooldown-Reset'])
            t += config.SLEEP_LENIENCY
            self.logger.debug(f"{endpoint} will sleep for {t}")
            time.sleep(t)
            h = requests.head(f"https://pixels.pythondiscord.com/{endpoint}", headers=config.headers).headers
        return h

    def wait_for_get_pixels(self):
        self.get_manager.sleep()

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

        pixels_r = self.get_manager.get()
        self.logger.debug(pixels_r.headers)
        # self.logger.debug(pixels_r.content)
        if pixels_r.status_code == 200:
            self.logger.debug("Got pixels. Saving 'current_canvas.png'")
            raw = pixels_r.content
            img = Image.frombytes('RGB', (ww, hh), raw)
            img.save('current_canvas.png')
            self.canvas = img
            self.last_get_pixels = time.time()
            with open("raw_canvas_bytes", 'wb') as canvas_out:
                canvas_out.write(raw)
            return img.copy()
        else:
            self.logger.error(f"get_pixels responded with {pixels_r.status_code}")
            self.logger.debug(pixels_r.content)
            raise Exception

    def wait_for_set_pixel(self):
        self.set_manager.sleep()

    def request_set_pixel_sleep(self):
        self.wait_for_set_pixel()

    def set_pixel(self, x: int, y: int, rgb: str):
        self.logger.debug("SET_PIXEL")
        self.wait_for_set_pixel()

        set_r = self.set_manager.post(json={'x': x, 'y': y, 'rgb': rgb})

        self.logger.debug(set_r.json())
        self.logger.debug(set_r.headers)
        if set_r.status_code == 200:
            current_pixel = self.canvas.getpixel((x, y))
            self.logger.info(f"Successfully set ({x}, {y}) to #{rgb.upper()} "
                             f"(from #{'%02x%02x%02x' % current_pixel[:3]})")
            self.canvas.putpixel((x, y), ImageColor.getcolor(f"#{rgb}", "RGB"))
            self.canvas.save('current_canvas.png')
        else:
            self.logger.error(f"set_pixel responded with {set_r.status_code}")
            raise Exception

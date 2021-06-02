import logging
import os
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


intervals = (
    ('h', 60 * 60),
    ('m', 60),
    ('s', 1),
)


def display_time(seconds, granularity=2):
    seconds = int(seconds)
    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{}{}".format(value, name))
    return ''.join(result[:granularity])


def sleep_until(t):
    return max(t - time.time(), 0)


class RateLimitManager:
    def __init__(self, endpoint, last_headers):
        logger_name = f'{self.__class__.__name__}_{endpoint}'
        self.logger = get_a_logger(logger_name)
        self.logger.info(f"{logger_name} __init__")
        self.logger.debug(last_headers)
        self.endpoint = endpoint

        self.next_allowed = time.time()
        self.is_locked_until = 0

        if last_headers.get('endpoint-unlock'):
            self.is_locked_until = time.time() + float(last_headers['endpoint-unlock'])
            return

        if int(last_headers['Requests-Remaining']) == 0:
            self.next_allowed = time.time() + float(last_headers['Requests-Reset'])

        self.average_sleep = int(last_headers['Requests-Period']) / int(last_headers['Requests-Limit'])
        self.logger.debug(f"next allowed has been set to: {self.next_allowed - time.time()}")
        self.logged_no_sleep = False

    def sleep(self, addition=None, requester=None):
        if self.is_locked_until > time.time():
            return

        t = max(
            0,
            sleep_until(self.next_allowed + config.SLEEP_LENIENCY) + (addition or 0),
        )

        if t:
            if t > 2 or addition is None:
                self.logged_no_sleep = False
                self.logger.debug(f"requested by {requester} - {self.endpoint} will sleep for {t}")
            time.sleep(t)
        elif not self.logged_no_sleep:
            self.logged_no_sleep = True
            self.logger.debug(f"requested by {requester} - {self.endpoint} has no need to sleep")

    def set_next_allowed(self, headers):
        self.logger.debug(f"NEXT ALLOWED {self.next_allowed - time.time()}")
        if not headers.get('Requests-Reset'):
            self.logger.info(f"{self.endpoint} is on cooldown!!!")
            t = int(headers['Cooldown-Reset'])
            t += config.SLEEP_LENIENCY
            self.logger.debug(f"{self.endpoint} will sleep for {t}")
            time.sleep(t)
            headers = requests.head(f"https://pixels.pythondiscord.com/{self.endpoint}", headers=config.headers).headers
            self.next_allowed = time.time()
            self.logger.debug(f"next allowed reset to: {self.next_allowed - time.time()}")
        elif int(headers['Requests-Remaining']) > 0:
            self.next_allowed = time.time()
        else:
            self.next_allowed = time.time() + float(headers['Requests-Reset'])
        self.logger.debug(f"next allowed has been set to: {self.next_allowed - time.time()}")
        self.average_sleep = int(headers['Requests-Period']) / int(headers['Requests-Limit'])

    def request(self, method, **kwargs):
        self.sleep(requester='self')
        r = requests.request(method,
                             f"https://pixels.pythondiscord.com/{self.endpoint}",
                             headers=config.headers, **kwargs)
        self.logger.debug(r.headers)
        if self.is_locked_until < time.time():
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
        self.get_pixels_disabled_for = 0
        self.get_manager = RateLimitManager('get_pixels', self.get_headers_for('get_pixels'))
        self.set_manager = RateLimitManager('set_pixel', self.get_headers_for('set_pixel'))
        self.canvas = None
        self.last_get_pixels = 0

    @property
    def pixels_disabled(self):
        return self.get_pixels_disabled_for > time.time()

    def get_headers_for(self, endpoint):
        r = requests.head(f"https://pixels.pythondiscord.com/{endpoint}", headers=config.headers)
        if r.status_code == 410 and endpoint == 'get_pixels':
            self.get_pixels_disabled_for = time.time() + float(r.headers['endpoint-unlock'])
            return r.headers
        h = r.headers
        while not h.get('Requests-Reset'):
            self.logger.info(f"{endpoint} is on cooldown!!!")
            t = int(h['Cooldown-Reset'])
            t += config.SLEEP_LENIENCY
            self.logger.debug(f"{endpoint} will sleep for {t}")
            time.sleep(t)
            h = requests.head(f"https://pixels.pythondiscord.com/{endpoint}", headers=config.headers).headers
        return h

    def wait_for_get_pixels(self):
        if not self.pixels_disabled:
            self.get_manager.sleep()

    def get_pixels(self):
        if (self.last_get_pixels > time.time() - 2 or self.pixels_disabled) and self.canvas:
            return self.canvas.copy()

        self.logger.debug("GET_PIXELS")

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
            self.last_get_pixels = time.time()

            raw = pixels_r.content
            with open("raw_canvas_bytes", 'wb') as canvas_out:
                canvas_out.write(raw)

            img = Image.frombytes('RGB', (ww, hh), raw)
            img.save('current_canvas.png')
            self.canvas = img

        elif pixels_r.status_code == 410:
            self.logger.debug('canvas reading is disabled')
            img = Image.new('RGBA', (ww, hh))
            if os.path.isfile('current_canvas.png'):
                current = Image.open('current_canvas.png')
                img.paste(current)
            else:
                img.save('current_canvas.png')
            self.canvas = img.copy()
            self.get_pixels_disabled_for = time.time() + float(pixels_r.headers['endpoint-unlock'])
        else:
            self.logger.error(f"get_pixels responded with {pixels_r.status_code}")
            self.logger.debug(pixels_r.content)
            raise Exception

        return img.copy()

    def wait_for_set_pixel(self):
        self.set_manager.sleep(requester='manager')

    def request_set_pixel_sleep(self):
        self.set_manager.sleep(-1, requester='strategy')

    def set_pixel(self, x: int, y: int, rgb: str):
        self.logger.debug("SET_PIXEL")

        set_r = self.set_manager.post(json={'x': x, 'y': y, 'rgb': rgb})

        self.logger.debug(set_r.json())
        self.logger.debug(set_r.headers)
        if set_r.status_code == 200:
            current_pixel = self.canvas.getpixel((x, y))
            bb = bytes.fromhex(rgb)
            bb_before = bytes.fromhex('%02x%02x%02x' % current_pixel[:3])
            self.logger.info(f"Successfully set ({x}, {y}) "
                             f"from {bb_before}#{('%02x%02x%02x' % current_pixel[:3]).upper()} to {bb}#{rgb.upper()}")
            self.canvas.putpixel((x, y), ImageColor.getcolor(f"#{rgb}", "RGB"))
            self.canvas.save('current_canvas.png')
        else:
            self.logger.error(f"set_pixel responded with {set_r.status_code}")
            raise Exception

    def average_sleep_seconds(self):
        return int(self.set_manager.average_sleep)

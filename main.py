import logging
import os
import sys

import requests
from PIL import Image

import config
import utils

headers = {"Authorization": f"Bearer {config.TOKEN}"}


def save_current_canvas():
    size_r = requests.get("https://pixels.pythondiscord.com/get_size", headers=headers)
    size_json = size_r.json()
    ww, hh = size_json["width"], size_json["height"]
    pixels_r = requests.get("https://pixels.pythondiscord.com/get_pixels", headers=headers)
    image_data = []
    raw = pixels_r.content
    for r in utils.chunks(raw, 3):
        pixel = utils.Pixel(r)
        image_data.append(pixel.to_rgb())
    img = Image.new('RGBA', (ww, hh))
    img.putdata(image_data)
    img.save('current_canvas.png')


if __name__ == '__main__':
    for path in ['logs', 'maintain', 'ignore']:
        if not os.path.isdir(path):
            os.makedirs(path)

    root_logger = utils.get_a_logger(None)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(config.FORMATTER)

    root_logger.addHandler(sh)
    root_logger.setLevel(1)
    save_current_canvas()

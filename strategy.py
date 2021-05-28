import os
import random
import time

from PIL import Image

import utils

api = utils.RequestsManager()
on_exception_time = time.time() + 120
logger = utils.get_a_logger('strat')


def get_target_pixels(target_img: Image, x_step=1, y_step=1):
    rv = []
    current_canvas_img = api.get_pixels()
    ww, hh = current_canvas_img.size
    for xx in range(ww)[::x_step]:
        for yy in range(hh)[::y_step]:
            canvas_pixel = current_canvas_img.getpixel((xx, yy))
            try:
                target_pixel = target_img.getpixel((xx, yy))
            except IndexError:
                break
            if canvas_pixel[:3] != target_pixel[:3] and target_pixel[3] > 10:
                rv.append((xx, yy, '%02x%02x%02x' % target_pixel[:3]))
    return rv


def main_loop():
    global on_exception_time
    while True:
        try:
            for file_name in os.listdir('maintain'):
                img = Image.open(f'maintain/{file_name}')
                api.wait_for_set_pixel()
                target_pixels = get_target_pixels(img)
                if target_pixels:
                    logger.info(f"Working on {file_name}")
                    candidate = target_pixels[int(1 - random.random() ** 0.1 * len(target_pixels))]
                    api.set_pixel(*candidate)
                    break
        except Exception:
            logger.exception('Exception in main loop')
            logger.info(f"Main loop is sleeping for {utils.sleep_until(on_exception_time, True)}")
            utils.sleep_until(on_exception_time)
            on_exception_time = time.time() + 60

import os
import random
import time
from typing import Optional, Tuple

from PIL import Image

import config
import utils

api = utils.RequestsManager()
logger = utils.get_a_logger('strategy')
current_pixel_leniency = config.IMAGE_MAX_LENIENCY


def get_pixel_diff(first_pixel, second_pixel):
    return sum(abs(first_pixel[i] - second_pixel[i]) for i in range(3))


def get_target_pixels(target_filename, top_down=True):
    rv = []
    total = 1
    current_canvas_img = api.get_pixels()
    target_img = Image.open(target_filename)
    ww, hh = current_canvas_img.size

    def compare_pixel(x, y):
        nonlocal total
        canvas_pixel = current_canvas_img.getpixel((x, y))
        try:
            target_pixel = target_img.getpixel((x, y))
        except IndexError:
            return
        if target_pixel[3] > 10:
            total += 1
            if get_pixel_diff(canvas_pixel[:3], target_pixel[:3]) > current_pixel_leniency:
                rv.append((x, y, '%02x%02x%02x' % target_pixel[:3]))

    first, second = (ww, hh) if top_down else (hh, ww)
    for f in range(first):
        for s in range(second):
            compare_pixel(f, s) if top_down else compare_pixel(s, f)

    target_img.close()
    return rv, total


def main_loop():
    global current_pixel_leniency
    on_exception_time = time.time() + 120
    print_100 = False

    while True:
        # noinspection PyBroadException
        try:
            is_100 = True
            for rev, td in [(-1, True), (-1, False), (1, True), (1, False)]:
                api.request_set_pixel_sleep()
                for file_name in os.listdir('maintain'):
                    target_pixels, total = get_target_pixels(f'maintain/{file_name}', td)
                    left = len(target_pixels)
                    done = total - left
                    percent = done / total
                    if target_pixels:
                        is_100 = False
                        print_100 = False
                        logger.info(f"Working on {file_name} {int(percent * 100)}% "
                                    f"{done}/{left}/{total} d~{current_pixel_leniency}")
                        candidate = target_pixels[int(random.random() ** 0.1 * len(target_pixels) * rev)]
                        api.set_pixel(*candidate)
                        target_pixels.remove(candidate)
                        break  # because we worked on this file, we want to come back to in the next round
            if is_100:
                current_pixel_leniency = max(0, current_pixel_leniency - 1)
                if not print_100:
                    logger.info("All images 100% done")
                    print_100 = True
                time.sleep(5)
                api.wait_for_get_pixels()
            else:
                current_pixel_leniency = min(config.IMAGE_MAX_LENIENCY, current_pixel_leniency + 1)
        except Exception:
            logger.exception('Exception in main loop')
            t = utils.sleep_until(on_exception_time)
            logger.info(f"Main loop is sleeping for {t}")
            time.sleep(t)
            on_exception_time = time.time() + 60

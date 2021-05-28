import os
import random
import time

from PIL import Image

import config
import utils

api = utils.RequestsManager()
logger = utils.get_a_logger('strat')
current_pixel_leniency = config.IMAGE_MAX_LENIENCY


def get_pixel_diff(first_pixel, second_pixel):
    return sum(abs(first_pixel[i] - second_pixel[i]) for i in range(3))


def get_target_pixels(target_filename, td=True):
    rv = []
    total = 1
    current_canvas_img = api.get_pixels()
    target_img = Image.open(target_filename)
    ww, hh = current_canvas_img.size

    def compare_pixel(xx, yy):
        nonlocal total
        canvas_pixel = current_canvas_img.getpixel((xx, yy))
        try:
            target_pixel = target_img.getpixel((xx, yy))
        except IndexError:
            return
        if target_pixel[3] > 10:
            total += 1
            if get_pixel_diff(canvas_pixel[:3], target_pixel[:3]) > current_pixel_leniency:
                rv.append((xx, yy, '%02x%02x%02x' % target_pixel[:3]))

    if td:
        for xx in range(ww):
            for yy in range(hh):
                compare_pixel(xx, yy)
    else:
        for yy in range(hh):
            for xx in range(ww):
                compare_pixel(xx, yy)

    target_img.close()
    return rv, total


def main_loop():
    global current_pixel_leniency
    on_exception_time = time.time() + 120
    is_100 = True
    print_100 = False
    while True:
        try:
            for rev in (-1, 1):
                for td in (True, False):
                    api.wait_for_set_pixel()
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
                            for _ in range(2):
                                candidate = target_pixels[int((1 - random.random() ** 0.1) * len(target_pixels) * rev)]
                                api.set_pixel(*candidate)
                                target_pixels.remove(candidate)
                            break
                    if is_100:
                        current_pixel_leniency = max(0, current_pixel_leniency - 1)
                        if not print_100:
                            logger.info("All images 100% done")
                            print_100 = True
                    else:
                        current_pixel_leniency = min(config.IMAGE_MAX_LENIENCY, current_pixel_leniency + 1)
        except Exception:
            logger.exception('Exception in main loop')
            logger.info(f"Main loop is sleeping for {utils.sleep_until(on_exception_time, True)}")
            utils.sleep_until(on_exception_time)
            on_exception_time = time.time() + 60

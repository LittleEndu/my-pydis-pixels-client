import os
import random
import time

from PIL import Image

import utils

api = utils.RequestsManager()
logger = utils.get_a_logger('strategy')


def get_pixel_diff(first_pixel, second_pixel):
    return sum(abs(first_pixel[i] - second_pixel[i]) for i in range(3))


def get_target_pixels(target_filename, top_down=True):
    rv = []
    total = 0
    current_canvas_img = api.get_pixels()
    target_img = Image.open(target_filename)
    ww, hh = current_canvas_img.size

    def compare_pixel(x, y):
        nonlocal total
        canvas_pixel = current_canvas_img.getpixel((x, y))
        try:
            target_pixel = target_img.getpixel((x, y))
        except IndexError:
            return False
        if len(target_pixel) == 3 or target_pixel[3] > 50:
            total += 1
            if canvas_pixel[:3] != target_pixel[:3]:
                rv.append((x, y, '%02x%02x%02x' % target_pixel[:3]))
        return True

    first, second = (ww, hh) if top_down else (hh, ww)
    s = 0
    for f in range(first):
        for s in range(second):
            if not (compare_pixel(f, s) if top_down else compare_pixel(s, f)):
                break
        if s == 0:
            break

    target_img.close()
    return rv, total


def template_needed_work(template_name, top_down, is_reversed):
    target_pixels, total = get_target_pixels(f'maintain/{template_name}', top_down)
    left = len(target_pixels)
    done = total - left
    percent = done / total if total != 0 else 1
    if target_pixels:
        candidate = target_pixels[int(random.random() ** 0.5 * min(20, len(target_pixels)) * is_reversed)]
        logger.info(
            f"Working on {template_name} "
            f"({', '.join(map(lambda a: str(a).rjust(3, '0'), candidate[:2]))})"
            f" {str(int(percent * 100)).rjust(3,'0')}% {done}/{total} "
            f"{utils.display_time(left * api.average_sleep_seconds())} left "
        )
        api.set_pixel(*candidate)
        target_pixels.remove(candidate)
        return True
    return False


def main_loop():
    on_exception_time = time.time() + 120
    print_100 = False

    logger.info('starting main_loop')
    while True:
        # noinspection PyBroadException
        try:
            is_100 = True
            for rev, td in [(-1, True), (-1, False), (1, True), (1, False)]:
                api.request_set_pixel_sleep()
                templates_worked_on_this_round = 0
                for file_name in os.listdir('maintain'):
                    if template_needed_work(file_name, td, rev):
                        is_100 = False
                        print_100 = False
                        templates_worked_on_this_round += 1
                        if templates_worked_on_this_round >= 2:
                            break  # because we worked on this file, we want to come back to in the next round
            if is_100:
                if not print_100:
                    logger.info("All images 100% done")
                    print_100 = True
                time.sleep(5)
                api.wait_for_get_pixels()
        except Exception:
            logger.exception('Exception in main loop')
            t = utils.sleep_until(on_exception_time)
            logger.info(f"Main loop is sleeping for {t}")
            time.sleep(t)
            on_exception_time = time.time() + 60

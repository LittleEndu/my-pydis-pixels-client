import os
import random
import time

from PIL import Image

import template_manager
import utils

api = utils.RequestsManager()
logger = utils.get_a_logger('strategy')


def is_my_pixel(x, y, *_):
    if api.pixels_disabled:
        return (x + y) % 4 == 2
    return True


def get_template():
    to_maintain = list(os.listdir('maintain'))
    to_animate = list(os.listdir('animated_templates'))
    for i in to_maintain:
        yield os.path.join('maintain', i)
    for i in to_animate:
        directory = os.path.join('animated_templates', i)
        if os.path.isdir(directory):
            yield template_manager.Template(directory).get_current_frame_path()[0]


def get_blind_pixels():
    current_canvas_img = api.get_pixels()
    ww, hh = current_canvas_img.size
    already_yielded = 0
    for template_path in get_template():
        img = Image.open(template_path).convert('RGBA')
        random_pixels = []
        for x in range(ww):
            for y in range(hh):
                try:
                    pixel = img.getpixel((x, y))
                except IndexError:
                    break
                if pixel[3] > 10 and is_my_pixel(x, y):
                    random_pixels.append((x, y, '%02x%02x%02x' % pixel[:3]))
        if already_yielded < 9:
            pixel = random.choice(random_pixels)
            random_pixels.remove(pixel)
            yield pixel
            already_yielded += 1


def get_pixel_diff(first_pixel, second_pixel):
    return sum(abs(first_pixel[i] - second_pixel[i]) for i in range(3))


def get_target_pixels(target_filepath, top_down=True):
    rv = []
    total = 0
    current_canvas_img = api.get_pixels().convert('RGBA')
    target_img = Image.open(target_filepath).convert('RGBA')
    ww, hh = current_canvas_img.size

    def compare_pixel(x, y):
        nonlocal total
        canvas_pixel = current_canvas_img.getpixel((x, y))
        try:
            target_pixel = target_img.getpixel((x, y))
        except IndexError:
            return False
        if target_pixel[3] > 50:
            total += 1
            if canvas_pixel[:3] != target_pixel[:3] and is_my_pixel(x, y):
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


def template_needed_work(template_path, top_down, is_reversed):
    target_pixels, total = get_target_pixels(template_path, top_down)
    left = len(target_pixels)
    done = total - left
    percent = done / total if total != 0 else 1
    if target_pixels:
        candidate = target_pixels[int(random.random() ** 0.5 * min(20, len(target_pixels)) * is_reversed)]
        logger.info(
            f"Working on {os.path.relpath(template_path)} "
            f"({', '.join(map(lambda a: str(a).rjust(3, '0'), candidate[:2]))})"
            f" {str(int(percent * 100)).rjust(3, '0')}% {done}/{total} "
            f"{utils.display_time(left * api.average_sleep_seconds())} left "
        )
        api.set_pixel(*candidate)
        return True
    return False


def save_last_not_blacklisted_pixels():
    current_canvas_img = api.get_pixels()
    if os.path.exists('last_not_blacklisted.png'):
        not_blacklisted = Image.open('last_not_blacklisted.png')
    else:
        not_blacklisted = Image.new('RGBA', current_canvas_img.size)
    if current_canvas_img.size != not_blacklisted.size:
        t = Image.new('RGBA', current_canvas_img.size)
        t.paste(not_blacklisted)
        not_blacklisted = t.copy()

    for black_name in os.listdir('blacklisted'):
        black_img = Image.open(f'blacklisted/{black_name}')
        for x in range(current_canvas_img.size[0]):
            for y in range(current_canvas_img.size[1]):
                canvas_pixel = current_canvas_img.getpixel((x, y))
                try:
                    black_pixel = black_img.getpixel((x, y))
                except IndexError:
                    break
                if (
                        len(black_pixel) == 3 or black_pixel[3] > 50
                ) and canvas_pixel[:3] != black_pixel[:3]:
                    not_blacklisted.putpixel((x, y), canvas_pixel)
    not_blacklisted.save('last_not_blacklisted.png')


def main_loop():
    on_exception_time = time.time() + 120
    first_100 = False
    all_pixels_generator = get_blind_pixels()

    logger.info('starting main_loop')
    while True:
        # noinspection PyBroadException
        try:
            is_100 = True
            for rev, td in [(-1, True), (-1, False), (1, True), (1, False)]:
                templates_worked_on_this_round = 0
                for file_path in get_template():
                    api.request_set_pixel_sleep()
                    if template_needed_work(file_path, td, rev):
                        is_100 = False
                        first_100 = False
                        templates_worked_on_this_round += 1
                        if templates_worked_on_this_round >= 2:
                            break  # because we worked on this file, we want to come back to in the next round
                # save_last_not_blacklisted_pixels()
            if is_100:
                if not first_100:
                    first_100 = True
                    logger.info("All images 100% done")
                    all_pixels_generator = get_blind_pixels()
                time.sleep(5)
                api.wait_for_get_pixels()
                if api.pixels_disabled:
                    try:
                        candidate = next(all_pixels_generator)
                        while not is_my_pixel(*candidate):
                            candidate = next(all_pixels_generator)
                        api.set_pixel(*candidate)
                    except StopIteration:
                        all_pixels_generator = get_blind_pixels()
        except Exception:
            logger.exception('Exception in main loop')
            t = utils.sleep_until(on_exception_time)
            logger.info(f"Main loop is sleeping for {t}")
            time.sleep(t)
            on_exception_time = time.time() + 60

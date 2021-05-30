import os

from PIL import Image

read_image = Image.open('current_canvas.png')
current_canvas_img = read_image.copy()
read_image.close()


def get_pixel_diff(first_pixel, second_pixel):
    return sum(abs(first_pixel[i] - second_pixel[i]) for i in range(3))


def get_target_pixels(target_filename):
    rv = []
    total = 1
    target_img = Image.open(target_filename)
    ww, hh = current_canvas_img.size

    for x in range(ww):
        for y in range(hh):
            canvas_pixel = current_canvas_img.getpixel((x, y))
            try:
                target_pixel = target_img.getpixel((x, y))
            except IndexError:
                break
            if len(target_pixel) == 3 or target_pixel[3] > 10:
                total += 1
                if get_pixel_diff(canvas_pixel[:3], target_pixel[:3]) > 10:
                    rv.append((x, y, '%02x%02x%02x' % target_pixel[:3]))

    target_img.close()
    return rv, total


for p in ('maintain', 'ignore'):
    print("-" * 5 + f"\n{p}\n" + "-" * 5)
    for i in os.listdir(p):
        missing, total = get_target_pixels(f"{p}/{i}")
        left = len(missing)
        done = total - left
        percent = done / total
        print(f"filename: {i} {int(percent * 100)}% {done}/{left}/{total}")

import os

from PIL import Image, ImageOps

import utils

# OSU_PINKS_ORIGINAL = ("ffddeeff", "ff99ccff", "ff66aaff", "cc5288ff", "bb1177ff")
OSU_PINKS = ("ff66aaff", "CC5188FF")
OSU_TRIANGLE = Image.open('reference/triangle.png')  # 512x443
OSU_MASK = Image.open('reference/03_osu_mask.png')  # 241 pixels total
IMAGE_SIZE = 128  # NOT size of pydis canvas
WIGGLE_ROOM = 22


def hex2rgb(hexcode):
    return tuple(int(hex, 16) for hex in utils.chunks(hexcode, 2))


OSU_PINKS_RGB = list(map(hex2rgb, OSU_PINKS))


def get_pixel_diff(first_pixel, second_pixel):
    return sum(abs(first_pixel[i] - second_pixel[i]) for i in range(3))


def find_closest(data_in):
    diffs = [get_pixel_diff(data_in, i) for i in OSU_PINKS_RGB]
    minimum = min(diffs)
    min_diff = diffs.index(minimum)
    return OSU_PINKS_RGB[min_diff]


def push_to_closest(image_in):
    new_data = []
    for data in image_in.getdata():
        if data[3] == 0:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(find_closest(data))
    image_in.putdata(new_data)


class Triangle:
    def __init__(self, x, y, size=0.5, speed=1, flipped=False):
        self.x = int(x * IMAGE_SIZE)
        self.y = int(y * (IMAGE_SIZE + WIGGLE_ROOM))
        self.size = size
        self.speed = int(speed)
        self.flipped = flipped

    def next_frame(self):
        self.y -= self.speed
        if self.y < -WIGGLE_ROOM:
            self.y += IMAGE_SIZE + WIGGLE_ROOM

    def draw(self, image_in: Image):
        triangle = OSU_TRIANGLE.copy()
        if self.flipped:
            triangle = ImageOps.flip(triangle)
        width = int(IMAGE_SIZE * self.size)
        triangle.thumbnail((width, width))
        solid_color = Image.new('RGBA', triangle.size, hex2rgb('ffffffff'))
        image_in.paste(solid_color, (self.x, self.y), mask=triangle)
        image_in.paste(solid_color, (self.x, self.y - IMAGE_SIZE - WIGGLE_ROOM), mask=triangle)
        image_in.paste(solid_color, (self.x, self.y + IMAGE_SIZE + WIGGLE_ROOM), mask=triangle)


if __name__ == '__main__':
    if not os.path.isdir('osu_frames'):
        os.mkdir('osu_frames')
    triangles = [
        Triangle(-0.14, 0, 0.44, 3),
        Triangle(0.07, 0.86, 0.6, 2, True),
        Triangle(0.45, 0.25, 0.5, 4),
        Triangle(0.69, 0.34, 0.35, 3, True),
    ]
    max_frame = IMAGE_SIZE + WIGGLE_ROOM
    frame_to_str = lambda a: str(a).rjust(len(str(max_frame)), '0')
    for frame_index in range(max_frame):
        if frame_index % 10 == 0:
            print(f'Generating frame {frame_index}')
        img = Image.new('RGBA', (IMAGE_SIZE, IMAGE_SIZE), hex2rgb('000000ff'))
        for tri in triangles:
            tri.draw(img)
        img = img.resize((18, 18), resample=Image.LANCZOS)
        pasted = Image.new('RGBA', (18, 18))
        pasted.paste(img, mask=OSU_MASK)
        push_to_closest(pasted)
        pasted.save(f'osu_frames/osu_{frame_to_str(frame_index)}.png')
        for tri in triangles:
            tri.next_frame()

import os

from PIL import Image

calculate_sameness_of = 'campfire'

frames = [Image.open(f"animated_templates/{calculate_sameness_of}/{i}") for i in
          os.listdir(f"animated_templates/{calculate_sameness_of}") if i != 'canvas.json']

current_image = frames[0].copy().convert('RGBA')

for n, current_frame in enumerate(frames):
    for x in range(current_frame.size[0]):
        for y in range(current_frame.size[1]):
            if current_frame.getpixel((x, y)) != current_image.getpixel((x, y)):
                current_image.putpixel((x, y), (0, 0, 0, 0))

current_image.save('converted_sameness.png')

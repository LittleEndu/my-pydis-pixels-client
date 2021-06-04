import os

from PIL import Image

import strategy

canvas = Image.open('current_canvas.png')
size = canvas.size
canvas.close()
template = Image.new('RGBA', size)

for file_name in list(strategy.get_template())[::-1]:
    img = Image.open(f'{file_name}')
    template.paste(img, mask=img)
    img.close()

template.save("all_templates.png")

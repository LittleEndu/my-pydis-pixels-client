import os

from PIL import Image

canvas = Image.open('current_canvas.png')
size = canvas.size
canvas.close()
template = Image.new('RGBA', size)

for file_name in os.listdir('maintain')[::-1]:
    img = Image.open(f'maintain/{file_name}')
    template.paste(img, mask=img)
    img.close()

template.save("all_templates.png")

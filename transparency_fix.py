import os

from PIL import Image

for i in os.listdir('fix_transparency_of'):
    print(f"Fixing {i}")
    img = Image.open(f"fix_transparency_of/{i}")
    data = img.getdata()
    new_data = [
        (0, 0, 0, 0) if d[3] < 100 else (d[0], d[1], d[2], 255)
        for d in data
    ]

    img.putdata(new_data)
    img.save(f"fix_transparency_of/{i}")

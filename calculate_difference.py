import os

from PIL import Image

calculate_difference_of = 'campfire'

frames = [Image.open(f"animated_templates/{calculate_difference_of}/{i}") for i in
          os.listdir(f"animated_templates/{calculate_difference_of}") if i != 'canvas.json']
diffs = []

for n, current_frame in enumerate(frames):
    previous_frame = frames[n - 1]
    diff = 0
    for x in range(current_frame.size[0]):
        for y in range(current_frame.size[1]):
            if current_frame.getpixel((x,y)) != previous_frame.getpixel((x,y)):
                diff += 1
    diffs.append(diff)

print(diffs)
print(f"len:{len(frames)} min:{min(diffs)} max:{max(diffs)} avg:{sum(diffs)/len(diffs)}")
import os

from PIL import Image

calculate_difference_of = 'entire_cycle'

frames = [Image.open(f"{calculate_difference_of}/{i}") for i in
          os.listdir(f"{calculate_difference_of}") if i != 'canvas.json']
diffs = []

for n, current_frame in enumerate(frames):
    previous_frame = frames[n - 1]
    diff = 0
    for x in range(current_frame.size[0]):
        for y in range(current_frame.size[1]):
            current_pixel = current_frame.getpixel((x, y))
            previous_pixel = previous_frame.getpixel((x, y))
            if (
                current_pixel[3] > 10 or previous_pixel[3] > 10
            ) and current_pixel != previous_pixel:
                diff += 1
    diffs.append(diff)

print(diffs)
print(f"len:{len(frames)} min:{min(diffs)} max:{max(diffs)} avg:{sum(diffs) / len(diffs)}")
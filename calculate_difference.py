import os

from PIL import Image

calculate_difference_of = 'campfire'

frames = [Image.open(f"animated_templates/{calculate_difference_of}/{i}") for i in
          os.listdir(f"animated_templates/{calculate_difference_of}") if i != 'canvas.json']
diffs = []
IDS = 4
diffs_for_id = {x: [] for x in range(IDS)}

for n, current_frame in enumerate(frames):
    previous_frame = frames[n - 1]
    diff = 0
    diff_id = {x: 0 for x in range(IDS)}
    for x in range(current_frame.size[0]):
        for y in range(current_frame.size[1]):
            current_pixel = current_frame.getpixel((x, y))
            previous_pixel = previous_frame.getpixel((x, y))
            if (
                current_pixel[3] > 10 or previous_pixel[3] > 10
            ) and current_pixel != previous_pixel:
                diff += 1
                diff_id[(x + y) % IDS] += 1
    diffs.append(diff)
    for i in range(IDS):
        diffs_for_id[i].append(diff_id[i])

print(diffs)
print(diffs_for_id)
print(f"len:{len(frames)} min:{min(diffs)} max:{max(diffs)} avg:{sum(diffs) / len(diffs)}")
for i in range(IDS):
    diffs = diffs_for_id[i]
    print(f"id:{i} min:{min(diffs)} max:{max(diffs)} avg:{sum(diffs) / len(diffs)}")
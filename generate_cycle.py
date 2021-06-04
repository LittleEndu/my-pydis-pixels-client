from PIL import Image

NR_OF_FRAMES = 96
GRADIENT = Image.open('reference/gradient.png')
ALPHA = Image.open('reference/alpha.png')
ALPHA_MULTIPLIER = 0.66
GLOBAL_MASK = Image.open('reference/trees_background.png')
MIDNIGHT_BLUE = (4, 16, 62)
OFFSETS = [(x, y) for x in range(2) for y in range(2)]


def best_color_for(frame_index):
    ww = GRADIENT.size[0]
    xx = int(ww * frame_index / NR_OF_FRAMES)
    return GRADIENT.getpixel((xx, 0))


def best_alpha_for(frame_index):
    ww = ALPHA.size[0]
    xx = int(ww * frame_index / NR_OF_FRAMES)
    return int(ALPHA.getpixel((xx, 0)) * ALPHA_MULTIPLIER)


class Body:
    def __init__(self, offset=0, filepath='reference/the_sun.png'):
        self.offset = offset - 4
        self.filepath = filepath

    def draw(self, image_in, current_frame):
        x = int(self.offset + current_frame * 38 / 26)
        y = int(3 + (x / 9) ** 2)
        image_in.paste(Image.open(self.filepath), (x, y))


the_sun = Body()
the_moon = Body(-38 - 26, 'reference/the_moon.png')


def frame_to_str(a):
    return str(a).rjust(len(str(NR_OF_FRAMES)), '0')


permanent_last_frame = Image.open('better_example/cycle_95.png')

for f in range(NR_OF_FRAMES):
    img = Image.new('RGBA', GLOBAL_MASK.size, color=best_color_for(f))
    tree = Image.open('reference/trees_foreground.png')
    tree_mask = tree.copy()
    darkness = Image.new('RGBA', GLOBAL_MASK.size, color=MIDNIGHT_BLUE)
    darkness.putalpha(best_alpha_for(f))
    tree.alpha_composite(darkness)

    last_frame = Image.new('RGBA', GLOBAL_MASK.size)
    this_frame = Image.new('RGBA', GLOBAL_MASK.size)
    the_sun.draw(last_frame, (f - 1) % NR_OF_FRAMES)
    the_moon.draw(last_frame, (f - 1) % NR_OF_FRAMES)
    this_frame.paste(img, mask=last_frame)
    this_frame.save(f'testing_last_frame/sun_and_moon_{frame_to_str(f)}.png')
    the_sun.draw(this_frame, f)
    the_moon.draw(this_frame, f)
    masked_tree = Image.new('RGBA', GLOBAL_MASK.size)
    masked_tree.paste(tree, mask=this_frame)
    this_frame.alpha_composite(masked_tree)
    this_framed_masked = Image.new('RGBA', GLOBAL_MASK.size)
    this_framed_masked.paste(this_frame, mask=GLOBAL_MASK)
    this_framed_masked.save(f'sun_and_moon/sun_and_moon_{frame_to_str(f)}.png')

    the_sun.draw(img, f)
    the_moon.draw(img, f)

    img.paste(tree, mask=tree_mask)

    to_save = Image.new('RGBA', img.size)
    to_save.paste(img, mask=GLOBAL_MASK)
    to_save.save(f'entire_cycle/cycle_{frame_to_str(f)}.png')

    to_mask = Image.new('RGBA', img.size)
    this_mask = Image.new('RGBA', img.size)
    this_frame_offset = OFFSETS[f % 4]
    this_mask.paste(Image.open('reference/hex_mask.png'), (-this_frame_offset[0], -this_frame_offset[1]))
    to_mask.paste(to_save, mask=this_mask)
    to_mask.save(f'quarter_cycle/cycle_{frame_to_str(f)}.png')

    permanent_last_frame.alpha_composite(to_mask)
    permanent_last_frame.alpha_composite(this_framed_masked)
    permanent_last_frame.save(f'better_example/cycle_{frame_to_str(f)}.png')

    all_masked_templates = to_save.copy()
    all_masked_templates.alpha_composite(to_mask)
    all_masked_templates.alpha_composite( this_framed_masked)
    all_masked_templates.save(f'all_cycle_templates_check/cycle_{frame_to_str(f)}.png')

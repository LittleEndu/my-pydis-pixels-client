from PIL import Image

# TEXT_TO_CONVERT = "Big PP wholesome 100 bruh moment yametekudastop F  https://pydis.org/.env | 418 I'm a teapot" + "\n" * 18 * 3
# TEXT_TO_CONVERT = "HTTP418 I'm a teapot | Yametekudastop, don't print() the /get_pixels content, use Image.frombytes()"
# TEXT_TO_CONVERT = "Hi! PP kusa moment yametekudastop F in the chat\n  use Image.frombytes() not print()"
TEXT_TO_CONVERT = "Hi! PP kusa moment yametekudastop F in the chat\n"

while len(TEXT_TO_CONVERT) < 49 * 3:
    TEXT_TO_CONVERT += "\n"

text_bytes = TEXT_TO_CONVERT.encode('utf-8')
img = Image.frombytes('RGB', (len(TEXT_TO_CONVERT) // 3, 1), text_bytes)
img.save("converted_text.png")
print(text_bytes)

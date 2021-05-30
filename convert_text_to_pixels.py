from PIL import Image

TEXT_TO_CONVERT = "Big PP bruh moment wholesome 100 yametekudastop    https://pydis.org/.env | 403 Forbidden" + "\n"*10*5

while len(TEXT_TO_CONVERT) % 3 != 0:
    TEXT_TO_CONVERT += " "

text_bytes = TEXT_TO_CONVERT.encode('utf-8')
img = Image.frombytes('RGB', (len(TEXT_TO_CONVERT) // 3, 1), text_bytes)
img.save("converted_text.png")

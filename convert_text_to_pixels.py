from PIL import Image

TEXT_TO_CONVERT = "You are being ratelimited. yametekudastoppu. Read: https://pydis.org/.env | 403 Forbidden "

while len(TEXT_TO_CONVERT) % 3 != 0:
    TEXT_TO_CONVERT += " "

text_bytes = TEXT_TO_CONVERT.encode('utf-8')
img = Image.frombytes('RGB', (len(TEXT_TO_CONVERT) // 3, 1), text_bytes)
img.save("converter_text.png")

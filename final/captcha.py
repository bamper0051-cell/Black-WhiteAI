import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

class CaptchaGenerator:
    def __init__(self):
        self.font = ImageFont.load_default()

    def generate_captcha(self):
        # Генерация случайного текста
        captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        
        # Создание изображения
        image = Image.new('RGB', (200, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)

        # Рисование текста
        draw.text((10, 30), captcha_text, font=self.font, fill=(0, 0, 0))

        # Добавление шума
        for _ in range(100):
            x = random.randint(0, 200)
            y = random.randint(0, 100)
            draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

        # Сохранение в байты
        byte_arr = BytesIO()
        image.save(byte_arr, format='PNG')
        byte_arr.seek(0)

        return captcha_text, byte_arr
from captcha.image import ImageCaptcha
import random
import string

class CaptchaGenerator:
    def __init__(self):
        self.generator = ImageCaptcha(width=280, height=90)

    def generate_captcha(self):
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        image = self.generator.generate(chars)
        return chars, image

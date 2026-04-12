import random
from PIL import Image, ImageDraw

WIDTH = 256
HEIGHT = 256
NUM_SNOWFLAKES = 70
NUM_FRAMES = 36
BACKGROUND = (8, 16, 40)
SNOW = (255, 255, 255)


class Snowflake:
    def __init__(self):
        self.reset(initial=True)

    def reset(self, initial: bool = False):
        self.x = random.randint(0, WIDTH - 1)
        self.y = random.randint(0, HEIGHT - 1) if initial else random.randint(-30, 0)
        self.size = random.randint(1, 3)
        self.speed = random.uniform(1.0, 3.2)
        self.wind = random.uniform(-0.7, 0.7)

    def step(self):
        self.y += self.speed
        self.x += self.wind
        if self.y >= HEIGHT:
            self.reset(initial=False)
        if self.x < 0:
            self.x = WIDTH - 1
        elif self.x >= WIDTH:
            self.x = 0


def make_frame(snowflakes):
    img = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(img)
    for flake in snowflakes:
        x0 = flake.x - flake.size
        y0 = flake.y - flake.size
        x1 = flake.x + flake.size
        y1 = flake.y + flake.size
        draw.ellipse((x0, y0, x1, y1), fill=SNOW)
        flake.step()
    return img


def main():
    flakes = [Snowflake() for _ in range(NUM_SNOWFLAKES)]
    frames = [make_frame(flakes) for _ in range(NUM_FRAMES)]
    frames[0].save(
        "snowfall.gif",
        save_all=True,
        append_images=frames[1:],
        duration=70,
        loop=0,
    )
    print("saved snowfall.gif")


if __name__ == "__main__":
    main()

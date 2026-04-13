import random
import shutil
import sys
import time

CHARS = "01アイウエオカキクケコサシスセソ"


def clear():
    sys.stdout.write("\x1b[2J\x1b[H")


def frame(width: int, height: int) -> str:
    rows = []
    for _ in range(height):
        row = "".join(random.choice(CHARS) if random.random() > 0.82 else " " for _ in range(width))
        rows.append(row)
    return "\n".join(rows)


def main() -> None:
    size = shutil.get_terminal_size((80, 24))
    width, height = min(size.columns, 100), min(size.lines - 1, 28)
    for _ in range(60):
        clear()
        print(frame(width, height))
        time.sleep(0.08)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

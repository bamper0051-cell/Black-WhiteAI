import os
import subprocess
from PIL import Image, ImageDraw, ImageFont
import zipfile
import json

# Создаем папку для анимаций
output_dir = "matrix_animations"
os.makedirs(output_dir, exist_ok=True)

# Параметры для всех анимаций
WIDTH, HEIGHT = 400, 300
FPS = 20
DURATION = 3  # секунд
TOTAL_FRAMES = FPS * DURATION

# Попробуем найти системный шрифт для матрицы
try:
    font = ImageFont.truetype("DejaVuSansMono.ttf", 20)
except:
    font = ImageFont.load_default()

# Символы матрицы
MATRIX_CHARS = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"

def create_matrix_rain(frames, variant=1):
    """Создает кадры с дождем из символов матрицы"""
    chars_per_column = 20
    columns = []
    
    # Инициализируем колонки
    for _ in range(WIDTH // 20):
        col = {
            'speed': variant + 1,
            'length': 5 + variant * 2,
            'chars': [MATRIX_CHARS[i % len(MATRIX_CHARS)] for i in range(chars_per_column)],
            'positions': [-i * 20 for i in range(chars_per_column)],
            'brightness': [max(0, 255 - i * 20) for i in range(chars_per_column)]
        }
        columns.append(col)
    
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        for col_idx, col in enumerate(columns):
            x = col_idx * 20
            for i in range(len(col['positions'])):
                y = col['positions'][i]
                if 0 <= y < HEIGHT:
                    # Цвет: ярко-зеленый для первых символов, темнее для остальных
                    color = (0, min(255, col['brightness'][i] + 100), 0)
                    draw.text((x, y), col['chars'][i], fill=color, font=font)
                
                # Двигаем символы вниз
                col['positions'][i] += col['speed']
                
                # Если символ ушел за экран, сбрасываем его
                if col['positions'][i] > HEIGHT:
                    col['positions'][i] = -20
                    col['chars'][i] = MATRIX_CHARS[(frame_idx + i) % len(MATRIX_CHARS)]
        
        yield img

def create_matrix_grid(frames):
    """Создает сетку с мигающими символами"""
    grid_size = 15
    cell_width = WIDTH // grid_size
    cell_height = HEIGHT // grid_size
    
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        # Рисуем сетку
        for x in range(0, WIDTH, cell_width):
            draw.line([(x, 0), (x, HEIGHT)], fill=(0, 50, 0), width=1)
        for y in range(0, HEIGHT, cell_height):
            draw.line([(0, y), (WIDTH, y)], fill=(0, 50, 0), width=1)
        
        # Случайные мигающие символы
        for _ in range(30):
            x = (frame_idx * 7 + _ * 13) % grid_size
            y = (frame_idx * 3 + _ * 5) % grid_size
            char = MATRIX_CHARS[(x + y + frame_idx) % len(MATRIX_CHARS)]
            color = (0, 150 + (frame_idx + _) % 100, 0)
            draw.text((x * cell_width + 5, y * cell_height + 5), 
                     char, fill=color, font=font)
        
        yield img

def create_matrix_spiral(frames):
    """Спираль из символов матрицы"""
    center_x, center_y = WIDTH // 2, HEIGHT // 2
    
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        # Рисуем спираль
        for i in range(100):
            angle = i * 0.2 + frame_idx * 0.1
            radius = i * 2
            x = center_x + radius * (0.8 ** i) * (angle * 0.3)
            y = center_y + radius * (0.8 ** i) * (angle * 0.2)
            
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                char = MATRIX_CHARS[(i + frame_idx) % len(MATRIX_CHARS)]
                brightness = min(255, 100 + i * 3)
                color = (0, brightness, 0)
                draw.text((x, y), char, fill=color, font=font)
        
        yield img

def create_matrix_wave(frames):
    """Волна из символов"""
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        for x in range(0, WIDTH, 25):
            for y in range(0, HEIGHT, 25):
                wave = 20 * ((x + frame_idx * 10) % 50) / 50
                char_y = y + wave
                
                if 0 <= char_y < HEIGHT:
                    char_idx = (x // 25 + y // 25 + frame_idx) % len(MATRIX_CHARS)
                    char = MATRIX_CHARS[char_idx]
                    brightness = 100 + int(100 * abs(wave) / 20)
                    color = (0, brightness, 0)
                    draw.text((x, char_y), char, fill=color, font=font)
        
        yield img

def create_matrix_pulse(frames):
    """Пульсирующие круги с символами"""
    center_x, center_y = WIDTH // 2, HEIGHT // 2
    
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        # Пульсирующие круги
        for i in range(3):
            radius = 30 + 20 * i + 10 * ((frame_idx + i * 10) % 20) / 20
            draw.ellipse([center_x - radius, center_y - radius,
                         center_x + radius, center_y + radius],
                        outline=(0, 100, 0), width=2)
        
        # Символы по кругу
        for i in range(24):
            angle = i * 15 + frame_idx * 5
            rad = angle * 3.14159 / 180
            x = center_x + 80 * (0.9 ** i) * (angle * 0.01)
            y = center_y + 60 * (0.9 ** i) * (angle * 0.015)
            
            char = MATRIX_CHARS[(i + frame_idx) % len(MATRIX_CHARS)]
            brightness = 150 + (frame_idx * 3) % 100
            color = (0, brightness, 0)
            draw.text((x, y), char, fill=color, font=font)
        
        yield img

def create_matrix_tunnel(frames):
    """Туннель в матрице"""
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        # Создаем туннельный эффект
        for ring in range(1, 10):
            radius = ring * 15 + (frame_idx * 2) % 30
            for angle in range(0, 360, 15):
                rad = angle * 3.14159 / 180
                x = WIDTH // 2 + radius * (0.9 ** ring) * (rad * 0.5)
                y = HEIGHT // 2 + radius * (0.9 ** ring) * (rad * 0.3)
                
                if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                    char_idx = (angle // 15 + ring + frame_idx) % len(MATRIX_CHARS)
                    char = MATRIX_CHARS[char_idx]
                    brightness = 100 + ring * 15
                    color = (0, brightness, 0)
                    draw.text((x, y), char, fill=color, font=font)
        
        yield img

def create_matrix_scroll(frames):
    """Прокрутка текста матрицы"""
    text = "MATRIX " * 10
    
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        # Прокручивающийся текст
        scroll_pos = frame_idx * 3 % (len(text) * 20)
        
        for i, char in enumerate(text):
            x = i * 20 - scroll_pos
            if 0 <= x < WIDTH:
                brightness = 100 + (i * 10) % 150
                color = (0, brightness, 0)
                draw.text((x, HEIGHT // 2 - 10), char, fill=color, font=font)
        
        # Фоновые символы
        for _ in range(50):
            x = (frame_idx * 2 + _ * 7) % WIDTH
            y = (frame_idx * 3 + _ * 11) % HEIGHT
            char = MATRIX_CHARS[(_ + frame_idx) % len(MATRIX_CHARS)]
            draw.text((x, y), char, fill=(0, 50, 0), font=font)
        
        yield img

def create_matrix_scan(frames):
    """Сканирующая линия"""
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        # Сканирующая линия
        scan_y = (frame_idx * 10) % HEIGHT
        draw.line([(0, scan_y), (WIDTH, scan_y)], fill=(0, 255, 0), width=2)
        
        # Символы выше и ниже линии
        for x in range(0, WIDTH, 25):
            for y in range(0, HEIGHT, 25):
                distance = abs(y - scan_y)
                if distance < 50:
                    char_idx = (x // 25 + y // 25 + frame_idx) % len(MATRIX_CHARS)
                    char = MATRIX_CHARS[char_idx]
                    brightness = max(50, 255 - distance * 5)
                    color = (0, brightness, 0)
                    draw.text((x, y), char, fill=color, font=font)
        
        yield img

def create_matrix_hex(frames):
    """Шестиугольная сетка"""
    hex_size = 30
    
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        # Шестиугольная сетка
        for y in range(0, HEIGHT, hex_size):
            for x in range(0, WIDTH, hex_size * 2):
                # Символ в центре шестиугольника
                center_x = x + (y // hex_size % 2) * hex_size
                center_y = y + hex_size // 2
                
                if 0 <= center_x < WIDTH and 0 <= center_y < HEIGHT:
                    char_idx = (x // hex_size + y // hex_size + frame_idx) % len(MATRIX_CHARS)
                    char = MATRIX_CHARS[char_idx]
                    
                    # Мигающий эффект
                    brightness = 100 + 100 * ((x + y + frame_idx * 5) % 20) / 20
                    color = (0, int(brightness), 0)
                    
                    draw.text((center_x - 5, center_y - 10), char, fill=color, font=font)
        
        yield img

def create_matrix_fractal(frames):
    """Фрактальная структура"""
    for frame_idx in range(frames):
        img = Image.new('RGB', (WIDTH, HEIGHT), 'black')
        draw = ImageDraw.Draw(img)
        
        # Рекурсивные ветви
        def draw_branch(x, y, length, angle, depth):
            if depth > 4 or length < 5:
                return
            
            # Вычисляем конечную точку ветви
            end_x = x + length * (0.8 ** depth) * (angle * 0.01)
            end_y = y + length * (0.8 ** depth) * (angle * 0.015)
            
            # Рисуем ветвь
            draw.line([(x, y), (end_x, end_y)], fill=(0, 100 + depth * 30, 0), width=2)
            
            # Символ на конце ветви
            char = MATRIX_CHARS[(depth + frame_idx) % len(MATRIX_CHARS)]
            draw.text((end_x - 5, end_y - 10), char, fill=(0, 200, 0), font=font)
            
            # Рекурсивно рисуем подветви
            for new_angle in [angle - 30, angle + 30]:
                draw_branch(end_x, end_y, length * 0.7, new_angle + frame_idx * 2, depth + 1)
        
        # Начинаем с центра
        draw_branch(WIDTH // 2, HEIGHT // 2, 80, frame_idx * 5, 0)
        
        yield img

# Создаем 10 разных анимаций
animations = [
    ("matrix_rain", create_matrix_rain(TOTAL_FRAMES, variant=1)),
    ("matrix_grid", create_matrix_grid(TOTAL_FRAMES)),
    ("matrix_spiral", create_matrix_spiral(TOTAL_FRAMES)),
    ("matrix_wave", create_matrix_wave(TOTAL_FRAMES)),
    ("matrix_pulse", create_matrix_pulse(TOTAL_FRAMES)),
    ("matrix_tunnel", create_matrix_tunnel(TOTAL_FRAMES)),
    ("matrix_scroll", create_matrix_scroll(TOTAL_FRAMES)),
    ("matrix_scan", create_matrix_scan(TOTAL_FRAMES)),
    ("matrix_hex", create_matrix_hex(TOTAL_FRAMES)),
    ("matrix_fractal", create_matrix_fractal(TOTAL_FRAMES))
]

# Сохраняем анимации как GIF
gif_paths = []
for i, (name, frames_gen) in enumerate(animations, 1):
    frames = list(frames_gen)
    gif_path = os.path.join(output_dir, f"animation_{i:02d}.gif")
    
    # Сохраняем как GIF
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=1000//FPS,
        loop=0,
        optimize=True
    )
    
    gif_paths.append(gif_path)
    print(f"Создана анимация {i}: {name} -> {gif_path}")

# Создаем видео из всех GIF
print("\nСобираю видео из всех анимаций...")

# Создаем текстовый файл со списком GIF для ffmpeg
list_file = os.path.join(output_dir, "filelist.txt")
with open(list_file, "w") as f:
    for gif_path in gif_paths:
        f.write(f"file '{os.path.abspath(gif_path)}'\n")
        f.write(f"duration 3\n")  # 3 секунды на каждую анимацию

# Пробуем создать видео с помощью ffmpeg
video_path = os.path.join(output_dir, "matrix_video.mp4")
try:
    # Проверяем, установлен ли ffmpeg
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    
    # Создаем видео
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-vf", "fps=20,scale=800:600",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        video_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Видео создано: {video_path}")
        print(f"Размер файла: {os.path.getsize(video_path) // 1024} KB")
    else:
        print("⚠️ Не удалось создать видео с помощью ffmpeg")
        print("Создаю ZIP-архив с GIF-анимациями вместо видео...")
        
        # Создаем ZIP-архив как запасной вариант
        zip_path = os.path.join(output_dir, "matrix_animations.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for gif_path in gif_paths:
                zipf.write(gif_path, os.path.basename(gif_path))
        
        print(f"✅ Создан ZIP-архив: {zip_path}")
        
except (subprocess.CalledProcessError, FileNotFoundError):
    print("⚠️ ffmpeg не найден. Создаю ZIP-архив с GIF-анимациями...")
    
    # Создаем ZIP-архив
    zip_path = os.path.join(output_dir, "matrix_animations.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for gif_path in gif_paths:
            zipf.write(gif_path, os.path.basename(gif_path))
    
    print(f"✅ Создан ZIP-архив: {zip_path}")

# Создаем JSON с информацией об анимациях
info = {
    "total_animations": len(gif_paths),
    "resolution": f"{WIDTH}x{HEIGHT}",
    "fps": FPS,
    "duration_per_animation": DURATION,
    "animations": [
        {
            "id": i,
            "name": name,
            "file": os.path.basename(gif_path),
            "size_kb": os.path.getsize(gif_path) // 1024
        }
        for i, ((name, _), gif_path) in enumerate(zip(animations, gif_paths), 1)
    ]
}

info_path = os.path.join(output_dir, "animations_info.json")
with open(info_path, "w") as f:
    json.dump(info, f, indent=2)

print(f"\n📊 Информация об анимациях сохранена в: {info_path}")
print(f"📁 Все файлы находятся в папке: {os.path.abspath(output_dir)}")

# Показываем пути к созданным файлам
if os.path.exists(video_path):
    print(f"\n🎬 VIDEO: {os.path.abspath(video_path)}")
else:
    print(f"\n📦 ARCHIVE: {os.path.abspath(zip_path)}")

print("\n✅ Готово! Создано 10 разных анимаций на тему Matrix.")
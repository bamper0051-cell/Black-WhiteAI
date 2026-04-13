"""
BlackBugsAI — Video Tools
Обёртка над MoviePy и ffmpeg.
"""
import os, time, subprocess, shutil
import config

BASE = config.BASE_DIR


def assemble(images: list, audio: str = None, output: str = None,
             duration_per_image: float = 3.0, on_status=None) -> tuple[bool, str]:
    """Слайд-шоу из картинок + аудио."""
    out = output or os.path.join(BASE, 'agent_projects', f'video_{int(time.time())}.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if on_status: on_status(f"🎬 Собираю видео из {len(images)} кадров...")
    try:
        from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
        clips = [ImageClip(img, duration=duration_per_image).resize((1280, 720))
                 for img in images if os.path.exists(img)]
        if not clips:
            return False, "❌ Нет доступных изображений"
        video = concatenate_videoclips(clips, method='compose')
        if audio and os.path.exists(audio):
            ac = AudioFileClip(audio)
            if ac.duration > video.duration:
                ac = ac.subclip(0, video.duration)
            video = video.set_audio(ac)
        video.write_videofile(out, fps=25, logger=None, codec='libx264', audio_codec='aac')
        for c in clips: c.close()
        return True, out
    except ImportError:
        pass
    # ffmpeg fallback
    return _ffmpeg_slideshow(images, audio, out, duration_per_image, on_status)


def _ffmpeg_slideshow(images, audio, output, duration, on_status):
    import tempfile
    if not shutil.which('ffmpeg'):
        return False, "❌ Ни MoviePy, ни ffmpeg не установлены"
    lst = tempfile.mktemp(suffix='.txt')
    with open(lst, 'w') as f:
        for img in images:
            if os.path.exists(img):
                f.write(f"file '{img}'\nduration {duration}\n")
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', lst]
    if audio and os.path.exists(audio):
        cmd += ['-i', audio, '-shortest']
    cmd += ['-vf', 'scale=1280:720', '-r', '25', output]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try: os.unlink(lst)
    except: pass
    if r.returncode == 0:
        return True, output
    return False, f"❌ ffmpeg: {r.stderr[-500:]}"


def cut(input_path: str, start: float, end: float,
        output: str = None, on_status=None) -> tuple[bool, str]:
    """Нарезка видео."""
    out = output or input_path.rsplit('.', 1)[0] + f'_cut.mp4'
    if on_status: on_status(f"✂️ Нарезаю {start}с–{end}с...")
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(input_path).subclip(start, end or None)
        clip.write_videofile(out, logger=None, codec='libx264', audio_codec='aac')
        clip.close()
        return True, out
    except Exception as e:
        return False, f"❌ cut error: {e}"


def add_audio(video_path: str, audio_path: str,
              output: str = None, on_status=None) -> tuple[bool, str]:
    """Наложить аудио на видео."""
    out = output or video_path.rsplit('.', 1)[0] + '_audio.mp4'
    if on_status: on_status("🎵 Накладываю аудио...")
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        if audio.duration > video.duration:
            audio = audio.subclip(0, video.duration)
        video = video.set_audio(audio)
        video.write_videofile(out, logger=None, codec='libx264', audio_codec='aac')
        video.close(); audio.close()
        return True, out
    except Exception as e:
        return False, f"❌ add_audio error: {e}"

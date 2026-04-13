tools = [
    {
        "name": "text_to_speech",
        "description": "Озвучивает текст и возвращает аудиофайл",
        "function": lambda text, voice=None: tts_engine.synthesize(text, voice),
        "parameters": {...}  # описание для LLM
    },
    {
        "name": "generate_image",
        "description": "Генерирует изображение по описанию",
        "function": image_gen.generate_image,
        "parameters": {...}
    },
    {
        "name": "create_video",
        "description": "Создаёт видео из набора слайдов/изображений с голосом за кадром",
        "function": None,  # пока нет реализации — агент должен написать код
        "requires_code": True
    },
    # ... остальные
]
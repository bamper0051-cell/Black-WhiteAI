class TelegramEntity:
    def __init__(self, entity_type, entity_id, data):
        self.type = entity_type
        self.id = entity_id
        self.data = data

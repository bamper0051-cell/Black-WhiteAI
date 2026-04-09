from app.parsers.telegram_parser import TelegramParser
from utils.db_utils import init_db

if __name__ == "__main__":
    init_db()
    parser = TelegramParser()
    result = parser.parse_entity("channel", "123456789")
    print(result)

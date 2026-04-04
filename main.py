import os
import config

if __name__ == "__main__":
    # Redirect to the full bot entry point
    import runpy
    runpy.run_path(os.path.join(config.BASE_DIR, 'bot.py'), run_name='__main__')

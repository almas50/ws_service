import os

class Config:
    HOST = os.getenv('HOST', 'localhost')
    PORT = int(os.getenv('PORT', 8765))
    MAX_CHUNK_SIZE = 1024 * 1024  # 1MB
    PROCESSING_DELAY_MIN = 0.5
    PROCESSING_DELAY_MAX = 2.0 
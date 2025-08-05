import time
import uuid
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class AudioChunk:
    client_id: str
    audio_data: bytes
    chunk_id: str = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.chunk_id is None:
            self.chunk_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self):
        return {
            'client_id': self.client_id,
            'chunk_id': self.chunk_id,
            'audio_data': self.audio_data,
            'timestamp': self.timestamp
        }

@dataclass
class TranscriptionResult:
    client_id: str
    chunk_id: str
    transcript: str
    status: str = "success"
    error: Optional[str] = None
    processing_time: float = 0.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self):
        return asdict(self) 
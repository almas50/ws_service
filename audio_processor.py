import time
import random
import multiprocessing
import os
from queue import Empty
from models import TranscriptionResult

class AudioProcessor:
    def __init__(self, num_workers=3):
        self.num_workers = num_workers
        self.mock_transcripts = [
            "Hello, this is a mock transcription",
            "Audio chunk processed successfully", 
            "Sample speech recognition result",
            "Test transcription from audio data",
            "Mock AI transcription service output",
            "Real-time audio processing complete"
        ]
    
    def start_workers(self, task_queue, result_queue):
        """Запуск пула воркеров для параллельной обработки"""
        print(f"🎵 Starting {self.num_workers} audio processor workers")
        
        workers = []
        for worker_id in range(self.num_workers):
            worker = multiprocessing.Process(
                target=self._worker_process,
                args=(worker_id, task_queue, result_queue)
            )
            worker.start()
            workers.append(worker)
        
        return workers
    
    def _worker_process(self, worker_id, task_queue, result_queue):
        """Процесс-воркер для обработки аудио"""
        print(f"🔧 Worker {worker_id} started (PID: {os.getpid()})")
        
        while True:
            try:
                # Получаем задачу из очереди
                task_data = task_queue.get(timeout=1.0)
                
                if task_data is None:  # Сигнал остановки
                    break
                
                # Обрабатываем аудио
                result = self._process_audio_chunk(task_data, worker_id)
                
                # Отправляем результат
                result_queue.put(result.to_dict())
                
            except Empty:
                continue
            except Exception as e:
                print(f"❌ Worker {worker_id} error: {e}")
        
        print(f"🛑 Worker {worker_id} stopped")
    
    def _process_audio_chunk(self, task_data, worker_id):
        """Имитация обработки аудио чанка"""
        start_time = time.time()
        
        # Извлекаем данные
        client_id = task_data['client_id']
        chunk_id = task_data['chunk_id']
        audio_data = task_data['audio_data']
        
        print(f"🔄 Worker {worker_id} processing chunk {chunk_id} for client {client_id} ({len(audio_data)} bytes)")
        
        # Имитация времени обработки
        from config import Config
        delay = random.uniform(Config.PROCESSING_DELAY_MIN, Config.PROCESSING_DELAY_MAX)
        time.sleep(delay)
        
        # Генерируем mock результат
        transcript = random.choice(self.mock_transcripts)
        processing_time = time.time() - start_time
        
        result = TranscriptionResult(
            client_id=client_id,
            chunk_id=chunk_id,
            transcript=f"[Worker {worker_id}] {transcript}",  # Показываем какой воркер обработал
            processing_time=processing_time
        )
        
        print(f"✅ Worker {worker_id} completed chunk {chunk_id} in {processing_time:.2f}s")
        return result 
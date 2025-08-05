import json
import asyncio
import websockets
import multiprocessing
from queue import Empty
from typing import Dict, Set
from models import AudioChunk
from audio_processor import AudioProcessor
from config import Config
import time

class WebSocketServer:
    def __init__(self):
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.client_ids: Set[str] = set()
        
        # IPC очереди
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        
        # Пул воркеров для обработки аудио
        self.audio_processor = AudioProcessor()
        self.worker_processes = []
        
    async def start_server(self):
        """Запуск WebSocket сервера"""
        # Запускаем пул воркеров для параллельной обработки
        self.worker_processes = self.audio_processor.start_workers(
            self.task_queue, 
            self.result_queue
        )
        
        # Запускаем задачу обработки результатов
        asyncio.create_task(self._handle_results())
        
        print(f"🚀 WebSocket server starting on {Config.HOST}:{Config.PORT}")
        
        # Запускаем WebSocket сервер
        async with websockets.serve(
            self._handle_client, 
            Config.HOST, 
            Config.PORT,
            max_size=Config.MAX_CHUNK_SIZE * 2  # Увеличиваем лимит для WebSocket
        ):
            print(f"✅ Server running on ws://{Config.HOST}:{Config.PORT}")
            await asyncio.Future()  # Бесконечное ожидание
    
    async def _handle_client(self, websocket, path):
        """Обработка подключения клиента"""
        # Генерируем уникальный ID клиента
        client_id = f"client_{len(self.clients)}_{int(asyncio.get_event_loop().time())}"
        
        # Регистрируем клиента
        self.clients[client_id] = websocket
        self.client_ids.add(client_id)
        
        print(f"🔌 Client {client_id} connected from {websocket.remote_address}")
        
        try:
            # Отправляем приветственное сообщение
            await websocket.send(json.dumps({
                "type": "connection",
                "client_id": client_id,
                "message": "Connected to audio transcription service"
            }))
            
            # Обрабатываем сообщения от клиента
            async for message in websocket:
                await self._handle_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Client {client_id} disconnected")
        except Exception as e:
            print(f"❌ Error handling client {client_id}: {e}")
            await self._send_error(client_id, str(e))
        finally:
            # Очищаем клиента
            self._cleanup_client(client_id)
    
    async def _handle_message(self, client_id: str, message):
        """Обработка сообщения от клиента"""
        try:
            if isinstance(message, bytes):
                # Бинарные аудио данные
                await self._process_audio_chunk(client_id, message)
            else:
                # JSON сообщения (для будущего расширения)
                data = json.loads(message)
                await self._handle_json_message(client_id, data)
                
        except json.JSONDecodeError:
            await self._send_error(client_id, "Invalid JSON message")
        except Exception as e:
            await self._send_error(client_id, f"Error processing message: {str(e)}")
    
    async def _process_audio_chunk(self, client_id: str, audio_data: bytes):
        """Обработка аудио чанка"""
        # Проверяем размер
        if len(audio_data) > Config.MAX_CHUNK_SIZE:
            await self._send_error(client_id, f"Audio chunk too large. Max size: {Config.MAX_CHUNK_SIZE} bytes")
            return
        
        # Создаем задачу
        chunk = AudioChunk(client_id=client_id, audio_data=audio_data)
        
        # Отправляем в очередь обработки
        try:
            self.task_queue.put(chunk.to_dict(), timeout=1.0)
        except multiprocessing.queues.Full:
            print(f"⚠️ Queue full, dropping chunk from {client_id}")
            await self._send_error(client_id, "Service overloaded")
            return
        
        print(f"📨 Queued audio chunk {chunk.chunk_id} from {client_id} ({len(audio_data)} bytes)")
    
    async def _handle_json_message(self, client_id: str, data: dict):
        """Обработка JSON сообщений"""
        message_type = data.get('type', 'unknown')
        
        if message_type == 'ping':
            await self._send_json(client_id, {'type': 'pong', 'timestamp': data.get('timestamp')})
        elif message_type == 'status':
            await self._send_json(client_id, {
                'type': 'status',
                'client_id': client_id,
                'connected_clients': len(self.clients),
                'queue_size': self.task_queue.qsize()
            })
        else:
            await self._send_error(client_id, f"Unknown message type: {message_type}")
    
    async def _handle_results(self):
        """Обработка результатов от аудио процессора"""
        print("📡 Starting result handler")
        
        while True:
            try:
                # Проверяем результаты без блокировки
                try:
                    result_data = self.result_queue.get_nowait()
                    await self._send_result_to_client(result_data)
                except:
                    # Нет результатов - ждем немного
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"❌ Error in result handler: {e}")
                await asyncio.sleep(1)
    
    async def _send_result_to_client(self, result_data: dict):
        """Отправка результата конкретному клиенту"""
        client_id = result_data['client_id']
        
        if client_id in self.clients:
            try:
                websocket = self.clients[client_id]
                await websocket.send(json.dumps({
                    'type': 'transcription',
                    **result_data
                }))
                print(f"📤 Sent result to {client_id}")
            except Exception as e:
                print(f"❌ Failed to send result to {client_id}: {e}")
                self._cleanup_client(client_id)
        else:
            print(f"⚠️ Client {client_id} not found for result")
    
    async def _send_json(self, client_id: str, data: dict):
        """Отправка JSON сообщения клиенту"""
        if client_id in self.clients:
            try:
                await self.clients[client_id].send(json.dumps(data))
            except Exception as e:
                print(f"❌ Failed to send JSON to {client_id}: {e}")
                self._cleanup_client(client_id)
    
    async def _send_error(self, client_id: str, error_message: str):
        """Отправка сообщения об ошибке"""
        await self._send_json(client_id, {
            'type': 'error',
            'error': error_message,
            'timestamp': time.time()
        })
    
    def _cleanup_client(self, client_id: str):
        """Очистка данных клиента"""
        if client_id in self.clients:
            del self.clients[client_id]
        if client_id in self.client_ids:
            self.client_ids.remove(client_id)
        print(f"🧹 Cleaned up client {client_id}")
    
    def stop(self):
        """Остановка сервера"""
        print("🛑 Stopping server...")
        
        # Останавливаем все воркеры
        for _ in self.worker_processes:
            self.task_queue.put(None)  # Сигнал остановки для каждого воркера
        
        # Ждем завершения воркеров
        for worker in self.worker_processes:
            worker.join(timeout=5)
            if worker.is_alive():
                worker.terminate()
        
        print("✅ All workers stopped") 
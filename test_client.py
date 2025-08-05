import asyncio
import websockets
import json
import random
import time
from typing import List, Dict

class TestStats:
    def __init__(self):
        self.start_time = time.time()
        self.sent_chunks: Dict[str, int] = {}
        self.received_results: Dict[str, int] = {}
        self.processing_times: List[float] = []
        self.worker_distribution: Dict[str, int] = {}
    
    def chunk_sent(self, client_name: str):
        self.sent_chunks[client_name] = self.sent_chunks.get(client_name, 0) + 1
    
    def result_received(self, client_name: str, processing_time: float, transcript: str):
        self.received_results[client_name] = self.received_results.get(client_name, 0) + 1
        self.processing_times.append(processing_time)
        
        # Извлекаем номер воркера из транскрипта
        if "[Worker" in transcript:
            worker_info = transcript.split("]")[0] + "]"
            self.worker_distribution[worker_info] = self.worker_distribution.get(worker_info, 0) + 1
    
    def print_summary(self):
        total_time = time.time() - self.start_time
        total_sent = sum(self.sent_chunks.values())
        total_received = sum(self.received_results.values())
        
        print("\n" + "="*50)
        print("📊 TEST RESULTS SUMMARY")
        print("="*50)
        print(f"⏱️  Total test time: {total_time:.2f}s")
        print(f"📨 Total chunks sent: {total_sent}")
        print(f"📥 Total results received: {total_received}")
        print(f"✅ Success rate: {(total_received/total_sent)*100:.1f}%")
        
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            min_time = min(self.processing_times)
            max_time = max(self.processing_times)
            print(f"⚡ Avg processing time: {avg_time:.2f}s")
            print(f"⚡ Min processing time: {min_time:.2f}s")
            print(f"⚡ Max processing time: {max_time:.2f}s")
        
        print("\n🔧 Worker Distribution:")
        for worker, count in sorted(self.worker_distribution.items()):
            print(f"   {worker}: {count} chunks ({(count/total_received)*100:.1f}%)")
        
        print("\n👥 Per Client Stats:")
        for client in self.sent_chunks:
            sent = self.sent_chunks.get(client, 0)
            received = self.received_results.get(client, 0)
            print(f"   {client}: {received}/{sent} chunks ({(received/sent)*100:.1f}%)")
        
        # Проверяем параллельность
        unique_workers = len(self.worker_distribution)
        print(f"\n🚀 Parallelism Check:")
        print(f"   Unique workers used: {unique_workers}")
        print(f"   Parallel processing: {'✅ YES' if unique_workers > 1 else '❌ NO'}")

# Глобальная статистика
stats = TestStats()

async def test_client(client_name: str, num_chunks: int = 8):
    """Тестовый клиент для проверки сервиса"""
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"🔌 {client_name} connected")
            
            # Слушаем сообщения от сервера
            async def listen():
                try:
                    async for message in websocket:
                        data = json.loads(message)
                        if data['type'] == 'transcription':
                            transcript = data['transcript']
                            processing_time = data['processing_time']
                            
                            print(f"📝 {client_name} received: '{transcript}' "
                                  f"(processed in {processing_time:.2f}s)")
                            
                            stats.result_received(client_name, processing_time, transcript)
                            
                        elif data['type'] == 'connection':
                            print(f"✅ {client_name} got client_id: {data['client_id']}")
                        elif data['type'] == 'error':
                            print(f"❌ {client_name} error: {data['error']}")
                except websockets.exceptions.ConnectionClosed:
                    print(f"🔌 {client_name} connection closed")
            
            # Запускаем слушателя
            listen_task = asyncio.create_task(listen())
            
            # Отправляем тестовые аудио чанки
            for i in range(num_chunks):
                # Генерируем fake аудио данные
                fake_audio = bytes([random.randint(0, 255) for _ in range(random.randint(512, 2048))])
                
                await websocket.send(fake_audio)
                print(f"📨 {client_name} sent audio chunk {i+1}/{num_chunks}")
                stats.chunk_sent(client_name)
                
                # Случайная задержка между отправками
                await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # Ждем для получения всех результатов
            await asyncio.sleep(15)
            
            listen_task.cancel()
            
    except Exception as e:
        print(f"❌ {client_name} error: {e}")

async def run_parallel_test():
    """Запуск теста параллельной обработки"""
    print("🧪 Starting PARALLEL PROCESSING test...")
    print("🎯 Goal: Verify multiple workers process chunks simultaneously\n")
    
    # Запускаем больше клиентов с большим количеством чанков
    clients = [
        test_client("Alice", 6),
        test_client("Bob", 6), 
        test_client("Charlie", 6),
        test_client("Diana", 6),
        test_client("Eve", 6)
    ]
    
    # Запускаем всех клиентов одновременно
    await asyncio.gather(*clients)
    
    # Выводим статистику
    stats.print_summary()

if __name__ == "__main__":
    asyncio.run(run_parallel_test()) 
import asyncio
from websocket_server import WebSocketServer

def main():
    server = WebSocketServer()
    
    try:
        # Запускаем сервер
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    finally:
        server.stop()

if __name__ == "__main__":
    main() 
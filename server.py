import asyncio
import json
import ssl
import time
import logging
import websockets
import numpy as np
from security import SecurityManager
from audio_processor import AudioProcessor
from clients_manager import ClientsManager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VoiceBridgeServer:
    def __init__(self, config):
        self.config = config
        self.host = config["host"]
        self.port = config["port"]
        self.password = config["password"]
        self.security = SecurityManager(config)
        self.audio = AudioProcessor(
            device_name=config.get("output_device"),
            device_index=None,  # можно добавить поддержку индекса в конфиг
            queue_size=config.get("max_audio_queue_size", 20)
        )
        self.clients = ClientsManager(self.security)
        self.running = False
        self.server = None
        self.admin_password = config.get("admin_password", "admin123")

    async def authenticate(self, websocket, client_ip):
        server_nonce = str(time.time()).encode()
        await websocket.send(json.dumps({"type": "auth_challenge", "nonce": server_nonce.decode()}))
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        except asyncio.TimeoutError:
            return False
        data = json.loads(msg)
        if data.get("type") != "auth_response":
            return False
        client_nonce = data.get("client_nonce")
        hmac_value = data.get("hmac")
        if not client_nonce or not hmac_value:
            return False
        if not self.security.authenticate_client(hmac_value, client_nonce, server_nonce.decode(), self.password):
            await websocket.send(json.dumps({"type": "error", "message": "Authentication failed"}))
            return False
        await websocket.send(json.dumps({"type": "auth_success"}))
        return True

    async def handler(self, websocket):
        client_ip = websocket.remote_address[0]
        logger.info(f"Новое соединение от {client_ip}")

        # Rate limit на подключения
        if not self.security.check_rate_limit(client_ip, "conn"):
            logger.warning(f"Rate limit превышен для {client_ip}")
            await websocket.close(1008, "Rate limit exceeded")
            return
        if not self.security.is_ip_allowed(client_ip):
            logger.warning(f"IP {client_ip} не разрешён")
            await websocket.close(1008, "IP not allowed")
            return

        if not await self.authenticate(websocket, client_ip):
            await websocket.close(1008, "Authentication failed")
            return

        logger.info(f"Клиент {client_ip} успешно аутентифицирован")

        device_name = "Unknown"
        is_admin = False
        try:
            init_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(init_msg)
            if data.get("type") == "init":
                device_name = data.get("device_name", device_name)
                logger.info(f"Получен init от {device_name}")
        except asyncio.TimeoutError:
            logger.warning(f"Клиент {client_ip} не прислал init в течение 5 секунд")
            await websocket.close(1008, "Init message timeout")
            return
        except Exception as e:
            logger.error(f"Ошибка получения init: {e}")
            await websocket.close(1008, "Invalid init message")
            return

        client = self.clients.add_client(websocket, client_ip, device_name)
        client.authenticated = True
        logger.info(f"Клиент {device_name} ({client_ip}) зарегистрирован и готов.")

        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    try:
                        audio_array = np.frombuffer(message, dtype=np.float32).reshape(-1, 1)
                        self.audio.feed_audio(websocket, audio_array)
                        self.clients.update_bytes(websocket, len(message))
                    except Exception as e:
                        logger.error(f"Ошибка обработки аудио: {e}")
                else:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "pong":
                            latency = time.time() - data.get("timestamp", time.time())
                            self.clients.update_latency(websocket, latency)
                        elif data.get("type") == "effect":
                            client.effect = data.get("effect", "none")
                        elif data.get("type") == "admin":
                            await self.handle_admin_command(websocket, data, client_ip)
                    except:
                        pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove_client(websocket)
            logger.info(f"Клиент {device_name} отключился.")

    async def handle_admin_command(self, websocket, data, client_ip):
        command = data.get("command")
        if command == "login":
            # Rate limit для неудачных попыток входа
            password = data.get("password")
            if password == self.admin_password:
                await websocket.send(json.dumps({
                    "type": "admin_response",
                    "command": "login",
                    "success": True,
                    "message": "Admin login successful"
                }))
            else:
                # Фиксируем неудачную попытку
                self.security.check_rate_limit(client_ip, "admin")  # просто добавляем запись
                await websocket.send(json.dumps({
                    "type": "admin_response",
                    "command": "login",
                    "success": False,
                    "message": "Invalid admin password"
                }))
        elif command == "get_clients":
            clients_list = []
            for c in self.clients.get_all_clients():
                clients_list.append({
                    "ip": c.ip,
                    "device_name": c.device_name
                })
            await websocket.send(json.dumps({
                "type": "admin_response",
                "command": "get_clients",
                "clients": clients_list
            }))
        elif command == "ban":
            ip = data.get("ip")
            self.security.add_to_blacklist(ip)
            for client in self.clients.get_all_clients():
                if client.ip == ip:
                    await client.websocket.close(1008, "You are banned")
                    break
            await websocket.send(json.dumps({
                "type": "admin_response",
                "command": "ban",
                "success": True,
                "message": f"IP {ip} banned"
            }))
        else:
            await websocket.send(json.dumps({
                "type": "admin_response",
                "command": command,
                "success": False,
                "message": "Unknown admin command"
            }))

    async def start(self):
        cert, key = self.security.load_or_create_cert()
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
        ssl_context.load_cert_chain(self.security.cert_file, self.security.key_file)

        self.server = await websockets.serve(
            self.handler,
            self.host,
            self.port,
            ssl=ssl_context,
            max_size=1024 * 1024,  # 1 МБ
        )
        self.running = True
        self.audio.start()
        logger.info(f"Сервер запущен на {self.host}:{self.port} (TLS 1.3)")

    async def stop(self):
        self.running = False
        self.audio.stop()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            await asyncio.sleep(0.5)

    def get_stats(self):
        return {
            "clients": [
                {
                    "ip": c.ip,
                    "device_name": c.device_name,
                    "latency": c.latency,
                    "bytes": c.bytes_received,
                    "connected": c.connected_at,
                }
                for c in self.clients.get_all_clients()
            ],
            "total_clients": len(self.clients.clients),
            "total_traffic": sum(c.bytes_received for c in self.clients.get_all_clients()),
        }
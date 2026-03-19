import time

class Client:
    def __init__(self, websocket, ip, device_name):
        self.websocket = websocket
        self.ip = ip
        self.device_name = device_name
        self.connected_at = time.time()
        self.last_seen = time.time()
        self.authenticated = False
        self.latency = 0.0
        self.bytes_received = 0
        self.effect = "none"

class ClientsManager:
    def __init__(self, security):
        self.clients = {}
        self.security = security

    def add_client(self, websocket, ip, device_name):
        client = Client(websocket, ip, device_name)
        self.clients[websocket] = client
        return client

    def remove_client(self, websocket):
        if websocket in self.clients:
            del self.clients[websocket]

    def get_client(self, websocket):
        return self.clients.get(websocket)

    def get_all_clients(self):
        return list(self.clients.values())

    def update_latency(self, websocket, latency):
        if websocket in self.clients:
            self.clients[websocket].latency = latency
            self.clients[websocket].last_seen = time.time()

    def update_bytes(self, websocket, size):
        if websocket in self.clients:
            self.clients[websocket].bytes_received += size
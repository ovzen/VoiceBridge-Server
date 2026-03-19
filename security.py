import os
import time
import hmac
import hashlib
import ipaddress
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

class SecurityManager:
    def __init__(self, config):
        self.config = config
        self.cert_dir = "certs"
        self.password = config["password"].encode() if isinstance(config["password"], str) else config["password"]
        self.cert_file = config.get("cert_file") or os.path.join(self.cert_dir, "server.crt")
        self.key_file = config.get("key_file") or os.path.join(self.cert_dir, "server.key")
        self.blacklist = set()
        self.whitelist = set()
        self.rate_limit_conn = {}  # для новых подключений
        self.rate_limit_admin = {}  # для админ-команд (неудачные попытки)
        self.max_requests_per_sec = config.get("rate_limit_per_ip", 20)
        self.admin_fail_limit = 5      # макс. неудачных попыток в минуту
        self.server_ip = config.get("server_ip")
        os.makedirs(self.cert_dir, exist_ok=True)

    def generate_ec_cert(self, valid_days=365):
        private_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"VoiceBridge Server"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"OVZEN Project"),
        ])

        alt_names = [x509.DNSName(u"localhost")]
        if self.server_ip:
            try:
                ip = ipaddress.ip_address(self.server_ip)
                alt_names.append(x509.IPAddress(ip))
            except ValueError:
                print(f"Некорректный IP для SAN: {self.server_ip}")
        san_extension = x509.SubjectAlternativeName(alt_names)

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=valid_days))
            .add_extension(san_extension, critical=False)
            .sign(private_key, hashes.SHA384(), default_backend())
        )
        with open(self.cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        with open(self.key_file, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        return cert, private_key

    def load_or_create_cert(self):
        # Если указаны собственные файлы сертификата и они существуют — используем их
        if self.config.get("cert_file") and self.config.get("key_file"):
            if os.path.exists(self.config["cert_file"]) and os.path.exists(self.config["key_file"]):
                with open(self.config["cert_file"], "rb") as f:
                    cert = x509.load_pem_x509_certificate(f.read(), default_backend())
                with open(self.config["key_file"], "rb") as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(), password=None, backend=default_backend()
                    )
                print(f"✅ Загружен собственный сертификат: {self.config['cert_file']}")
                return cert, private_key
            else:
                print("⚠️ Указаны пути к сертификатам, но файлы не найдены. Будет сгенерирован новый.")

        # Иначе работаем с сертификатами в папке certs
        if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
            with open(self.cert_file, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            with open(self.key_file, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            if datetime.now(timezone.utc) < cert.not_valid_after_utc:
                return cert, private_key
        return self.generate_ec_cert(self.config.get("cert_valid_days", 365))

    def authenticate_client(self, received_hmac, client_nonce, server_nonce, shared_key):
        expected = hmac.new(shared_key.encode(), f"{client_nonce}:{server_nonce}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(received_hmac, expected)

    def check_rate_limit(self, ip, limit_type="conn"):
        """limit_type: 'conn' для подключений, 'admin' для админ-команд"""
        now = time.time()
        rate_dict = self.rate_limit_conn if limit_type == "conn" else self.rate_limit_admin
        if ip not in rate_dict:
            rate_dict[ip] = []
        # Очищаем записи старше 60 секунд для admin, и старше 1 секунды для conn
        window = 1.0 if limit_type == "conn" else 60.0
        rate_dict[ip] = [t for t in rate_dict[ip] if now - t < window]
        limit = self.max_requests_per_sec if limit_type == "conn" else self.admin_fail_limit
        if len(rate_dict[ip]) >= limit:
            return False
        rate_dict[ip].append(now)
        return True

    def is_ip_allowed(self, ip):
        ip_obj = ipaddress.ip_address(ip)
        if self.whitelist and ip_obj not in self.whitelist:
            return False
        if ip_obj in self.blacklist:
            return False
        return True

    def add_to_blacklist(self, ip):
        self.blacklist.add(ipaddress.ip_address(ip))

    def add_to_whitelist(self, ip):
        self.whitelist.add(ipaddress.ip_address(ip))

    def get_certificate_pem(self):
        with open(self.cert_file, "rb") as f:
            cert_data = f.read()
        return cert_data.decode('utf-8')
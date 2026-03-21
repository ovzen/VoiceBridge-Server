# 🎙️ VoiceBridge Server

Сервер для приёма аудио с Android-клиента и вывода на звуковое устройство (например, виртуальный аудиокабель).

## Возможности
- Приём аудио по защищённому WebSocket (TLS 1.3) с Android-клиента.
- Аутентификация клиентов по паролю (HMAC-SHA256).
- Управление белым и чёрным списками IP.
- Администрирование через клиент (бан клиентов).
- Выбор устройства вывода звука.
- Автоматическая генерация самоподписанного ECDSA сертификата (или использование собственного).
- Rate limiting для защиты от DoS.
- Логирование в файл (опционально).

## Требования
- Python 3.13+
- Windows / Linux / macOS (звуковой вывод тестировался на Windows)

## Установка и запуск

1. **Установите Python 3.13+** с [официального сайта](https://www.python.org/).
2. **Склонируйте репозиторий** или скачайте архив.
3. **Установите зависимости**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Запустите сервер**:
   ```bash
   python gui.py
   ```
   или используйте готовые исполняемые файлы из раздела Releases.

## ⚠️ Важно: ложные срабатывания антивирусов
Некоторые антивирусные программы могут ложно определять EXE-файл сервера (`VoiceBridgeServer.exe`) как угрозу.  
Это не является признаком вредоносного кода, а связано с особенностями упаковки Python-приложений (PyInstaller).

Исходный код полностью открыт и безопасен. Вы можете проверить файлы на VirusTotal:

- 🐧 **Linux-версия**: [анализ](https://www.virustotal.com/gui/file/c8072bbfb91158f1d101d3c544da7d9052f57d11a8542861b4c25f826d5116f6/detection)
- 🪟 **Windows-версия**: [анализ](https://www.virustotal.com/gui/file/a87a254f91ece046d9110c2ddbd198353bac2c4d66e087c81bd99e6d3a39939e/detection)

Если антивирус блокирует запуск, добавьте файл в исключения.

## ⚙️ Конфигурация
Файл `server_config.json` создаётся автоматически при первом запуске. Пример содержимого:

```json
{
  "host": "0.0.0.0",
  "server_ip": "192.168.1.10",
  "port": 8765,
  "password": "your_password_here",
  "output_device": "CABLE Input",
  "admin_password": "your_admin_password_here",
  "cert_valid_days": 365,
  "rate_limit_per_ip": 20,
  "max_audio_queue_size": 20,
  "log_file": "server.log",
  "cert_file": null,
  "key_file": null,
  "output_device_index": null
}
```

## 📦 Репозитории

| Компонент | Ссылка |
|-----------|--------|
| 📱 Android-клиент | [VoiceBridge-Client](https://github.com/ovzen/VoiceBridge-Client) |
| 💻 Сервер | [VoiceBridge-Server](https://github.com/ovzen/VoiceBridge-Server) |

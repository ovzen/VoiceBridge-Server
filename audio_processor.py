import numpy as np
import sounddevice as sd
import queue
import threading
import time

class AudioProcessor:
    def __init__(self, device_name=None, device_index=None, sample_rate=48000, channels=1, queue_size=20):
        self.device_name = device_name
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue = queue.Queue(maxsize=queue_size)
        self.running = False
        self.thread = None
        self.stream = None
        self.current_sr = None
        self.current_ch = None
        self.current_dtype = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._output_loop, daemon=True)
        self.thread.start()
        print("🎵 AudioProcessor запущен (sounddevice)")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        if self.stream:
            self.stream.close()

    def _output_loop(self):
        print("🔍 Поиск рабочего аудиоустройства...")

        devices = sd.query_devices()
        test_configs = [
            (44100, 2, 'float32'),
            (48000, 2, 'float32'),
            (44100, 2, 'int16'),
            (48000, 2, 'int16'),
            (44100, 1, 'float32'),
            (48000, 1, 'float32'),
            (44100, 1, 'int16'),
            (48000, 1, 'int16'),
        ]

        device_index = None
        found = False

        # Поиск по индексу, если задан
        if self.device_index is not None:
            try:
                dev = devices[self.device_index]
                if dev['max_output_channels'] > 0:
                    print(f"Попытка открыть устройство по индексу {self.device_index}: {dev['name']}")
                    try_sr = int(dev['default_samplerate'])
                    try_ch = dev['max_output_channels']
                    for dtype in ['float32', 'int16']:
                        try:
                            with sd.OutputStream(device=self.device_index, samplerate=try_sr, channels=try_ch, dtype=dtype, blocksize=1024):
                                print(f"✅ УСТРОЙСТВО ПО ИНДЕКСУ РАБОТАЕТ (родные): {dev['name']} | {try_sr}Hz/{try_ch}ch/{dtype}")
                                device_index = self.device_index
                                self.current_sr, self.current_ch, self.current_dtype = try_sr, try_ch, dtype
                                found = True
                                break
                        except Exception as e:
                            print(f"   Не подошло родное: {try_sr}/{try_ch}/{dtype} -> {e}")
                    if not found:
                        for sr, ch, dtype in test_configs:
                            if ch > dev['max_output_channels']:
                                continue
                            try:
                                with sd.OutputStream(device=self.device_index, samplerate=sr, channels=ch, dtype=dtype, blocksize=1024):
                                    print(f"✅ УСТРОЙСТВО ПО ИНДЕКСУ РАБОТАЕТ: {dev['name']} | {sr}Hz/{ch}ch/{dtype}")
                                    device_index = self.device_index
                                    self.current_sr, self.current_ch, self.current_dtype = sr, ch, dtype
                                    found = True
                                    break
                            except Exception as e:
                                print(f"   Не подошло: {sr}/{ch}/{dtype} -> {e}")
            except Exception as e:
                print(f"❌ Устройство с индексом {self.device_index} не найдено: {e}")

        # Поиск по точному имени, если индекс не сработал или не задан
        if not found and self.device_name:
            print(f"Поиск устройства по точному имени: '{self.device_name}'")
            for i, dev in enumerate(devices):
                if dev['name'].strip() == self.device_name.strip():
                    print(f"Найдено точное совпадение: индекс {i}, имя '{dev['name']}'")
                    try_sr = int(dev['default_samplerate'])
                    try_ch = dev['max_output_channels']
                    for dtype in ['float32', 'int16']:
                        try:
                            with sd.OutputStream(device=i, samplerate=try_sr, channels=try_ch, dtype=dtype, blocksize=1024):
                                print(f"✅ УСТРОЙСТВО ПО ИМЕНИ РАБОТАЕТ (родные): {dev['name']} | {try_sr}Hz/{try_ch}ch/{dtype}")
                                device_index = i
                                self.current_sr, self.current_ch, self.current_dtype = try_sr, try_ch, dtype
                                found = True
                                break
                        except Exception as e:
                            print(f"   Не подошло родное: {try_sr}/{try_ch}/{dtype} -> {e}")
                    if not found:
                        for sr, ch, dtype in test_configs:
                            if ch > dev['max_output_channels']:
                                continue
                            try:
                                with sd.OutputStream(device=i, samplerate=sr, channels=ch, dtype=dtype, blocksize=1024):
                                    print(f"✅ УСТРОЙСТВО ПО ИМЕНИ РАБОТАЕТ: {dev['name']} | {sr}Hz/{ch}ch/{dtype}")
                                    device_index = i
                                    self.current_sr, self.current_ch, self.current_dtype = sr, ch, dtype
                                    found = True
                                    break
                            except Exception as e:
                                print(f"   Не подошло: {sr}/{ch}/{dtype} -> {e}")
                    if found:
                        break

        # Если ничего не найдено, пробуем любое устройство
        if not found:
            print("🔁 Поиск любого работающего устройства...")
            for i, dev in enumerate(devices):
                if dev['max_output_channels'] == 0:
                    continue
                print(f"Тест устройства {i}: {dev['name']}")
                try_sr = int(dev['default_samplerate'])
                try_ch = dev['max_output_channels']
                for dtype in ['float32', 'int16']:
                    try:
                        with sd.OutputStream(device=i, samplerate=try_sr, channels=try_ch, dtype=dtype, blocksize=1024):
                            print(f"✅ РАБОТАЕТ (родные): {dev['name']} | {try_sr}Hz/{try_ch}ch/{dtype}")
                            device_index = i
                            self.current_sr, self.current_ch, self.current_dtype = try_sr, try_ch, dtype
                            found = True
                            break
                    except:
                        continue
                if found:
                    break
                for sr, ch, dtype in test_configs:
                    if ch > dev['max_output_channels']:
                        continue
                    try:
                        with sd.OutputStream(device=i, samplerate=sr, channels=ch, dtype=dtype, blocksize=1024):
                            print(f"✅ РАБОТАЕТ: {dev['name']} | {sr}Hz/{ch}ch/{dtype}")
                            device_index = i
                            self.current_sr, self.current_ch, self.current_dtype = sr, ch, dtype
                            found = True
                            break
                    except:
                        continue
                if found:
                    break

        if not found:
            print("❌ АУДИОУСТРОЙСТВА НЕ НАЙДЕНЫ! Сервер работает БЕЗ ЗВУКА")
            while self.running:
                time.sleep(0.1)
            return

        print(f"🎉 ИСПОЛЬЗУЕТСЯ: устройство {device_index} | {self.current_sr}Hz/{self.current_ch}ch/{self.current_dtype}")

        try:
            self.stream = sd.OutputStream(
                device=device_index,
                samplerate=self.current_sr,
                channels=self.current_ch,
                dtype=self.current_dtype,
                blocksize=int(self.current_sr * 0.02)
            )
            self.stream.start()

            with self.stream:
                while self.running:
                    try:
                        data = self.audio_queue.get(timeout=0.05)
                        if data.ndim == 1:
                            data = data.reshape(-1, 1)
                        if self.current_ch > data.shape[1]:
                            data = np.repeat(data, self.current_ch, axis=1)
                        elif self.current_ch < data.shape[1]:
                            data = data[:, :self.current_ch]
                        if self.current_dtype == 'int16':
                            data = np.clip(data * 32767, -32768, 32767).astype(np.int16)
                        self.stream.write(data)
                    except queue.Empty:
                        silence_len = int(self.current_sr * 0.05)
                        if self.current_dtype == 'int16':
                            silence = np.zeros((silence_len, self.current_ch), dtype=np.int16)
                        else:
                            silence = np.zeros((silence_len, self.current_ch), dtype=np.float32)
                        self.stream.write(silence)

        except Exception as e:
            print(f"💥 КРИТИЧЕСКАЯ ОШИБКА АУДИО: {e}")
            print("🔇 АУДИО ОТКЛЮЧЕНО, сервер продолжает работу")

    def feed_audio(self, client_id, audio_data):
        try:
            if self.audio_queue.full():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    pass
            self.audio_queue.put_nowait(audio_data)
        except:
            pass
import pyaudio

p = pyaudio.PyAudio()
print("Доступные устройства вывода:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxOutputChannels'] > 0:
        print(f"Индекс: {i} | Имя: {info['name']} | Каналов: {info['maxOutputChannels']} | Частота по умолчанию: {info['defaultSampleRate']}")
p.terminate()
input("Нажмите Enter для выхода...")
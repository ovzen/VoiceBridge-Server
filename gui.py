import customtkinter as ctk
import asyncio
import threading
import time
import sys
import sounddevice as sd
import ipaddress
import webbrowser
from tkinter import messagebox, scrolledtext
from server import VoiceBridgeServer
import config_manager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ServerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VoiceBridge Server 2026")
        self.geometry("1300x750")
        self.server = None
        self.loop = None
        self.thread = None
        self.running = False
        self.start_error = None

        self.config = config_manager.load_config()

        # Создаём вкладки
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_main = self.tabview.add("Главная")
        self.tab_clients = self.tabview.add("Клиенты")
        self.tab_logs = self.tabview.add("Логи")
        self.tab_settings = self.tabview.add("Настройки")
        self.tab_security = self.tabview.add("Безопасность")

        # ===== Вкладка Главная =====
        self.create_main_tab()

        # ===== Вкладка Клиенты =====
        self.create_clients_tab()

        # ===== Вкладка Логи =====
        self.create_logs_tab()

        # ===== Вкладка Настройки =====
        self.create_settings_tab()

        # ===== Вкладка Безопасность =====
        self.create_security_tab()

        # Футер с ссылкой на разработчика
        self.footer_frame = ctk.CTkFrame(self, height=30)
        self.footer_frame.pack(side="bottom", fill="x", padx=10, pady=(0,5))
        self.footer_label = ctk.CTkLabel(
            self.footer_frame,
            text="Разработано https://vk.com/ovzen",
            font=("Arial", 10),
            cursor="hand2"
        )
        self.footer_label.pack()
        self.footer_label.bind("<Button-1>", lambda e: webbrowser.open("https://vk.com/ovzen"))

        # Перенаправляем stdout в лог
        self.original_stdout = None
        self.redirect_stdout()

        # Загружаем сохранённые настройки в поля
        self.load_config_to_ui()

        self.update_stats()

    def create_main_tab(self):
        self.main_left = ctk.CTkFrame(self.tab_main)
        self.main_left.pack(side="left", fill="y", padx=10, pady=10)

        self.main_right = ctk.CTkFrame(self.tab_main)
        self.main_right.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        self.ip_label = ctk.CTkLabel(self.main_left, text="IP сервера (слушать):")
        self.ip_label.pack(pady=5)
        self.ip_entry = ctk.CTkEntry(self.main_left, placeholder_text="0.0.0.0")
        self.ip_entry.pack(pady=5)

        self.port_label = ctk.CTkLabel(self.main_left, text="Порт:")
        self.port_label.pack(pady=5)
        self.port_entry = ctk.CTkEntry(self.main_left, placeholder_text="8765")
        self.port_entry.pack(pady=5)

        self.pass_label = ctk.CTkLabel(self.main_left, text="Пароль:")
        self.pass_label.pack(pady=5)
        self.pass_entry = ctk.CTkEntry(self.main_left, placeholder_text="Пароль", show="*")
        self.pass_entry.pack(pady=5)

        self.start_button = ctk.CTkButton(self.main_left, text="Запустить сервер", command=self.toggle_server)
        self.start_button.pack(pady=10)

        self.view_cert_button = ctk.CTkButton(self.main_left, text="Показать сертификат", command=self.show_certificate, state="disabled")
        self.view_cert_button.pack(pady=5)

        self.copy_cert_button = ctk.CTkButton(self.main_left, text="Копировать сертификат", command=self.copy_certificate, state="disabled")
        self.copy_cert_button.pack(pady=5)

        self.stats_label = ctk.CTkLabel(self.main_right, text="Статистика", font=("Arial", 16))
        self.stats_label.pack(pady=10)
        self.stats_text = ctk.CTkTextbox(self.main_right, height=200)
        self.stats_text.pack(fill="both", expand=True, pady=5)

    def create_clients_tab(self):
        self.clients_frame = ctk.CTkFrame(self.tab_clients)
        self.clients_frame.pack(fill="both", expand=True, padx=10, pady=10)

        header = ctk.CTkFrame(self.clients_frame, fg_color="transparent")
        header.pack(fill="x", pady=5)
        ctk.CTkLabel(header, text="IP", width=150).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Устройство", width=150).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Трафик", width=100).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Действия", width=200).pack(side="left", padx=5)

        self.clients_list_frame = ctk.CTkScrollableFrame(self.clients_frame)
        self.clients_list_frame.pack(fill="both", expand=True)

    def create_logs_tab(self):
        self.log_text = ctk.CTkTextbox(self.tab_logs, height=500)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.copy_log_button = ctk.CTkButton(self.tab_logs, text="Копировать логи", command=self.copy_logs)
        self.copy_log_button.pack(pady=5)

    def create_settings_tab(self):
        self.cert_ip_label = ctk.CTkLabel(self.tab_settings, text="IP для сертификата (реальный IP):")
        self.cert_ip_label.pack(pady=5)
        self.cert_ip_entry = ctk.CTkEntry(self.tab_settings, placeholder_text="192.168.1.10")
        self.cert_ip_entry.pack(pady=5)

        self.device_label = ctk.CTkLabel(self.tab_settings, text="Устройство вывода (по имени):")
        self.device_label.pack(pady=5)

        self.devices = self.get_audio_devices()
        self.device_var = ctk.StringVar(value="")
        self.device_combo = ctk.CTkComboBox(self.tab_settings, values=self.devices, variable=self.device_var)
        self.device_combo.pack(pady=5)

        self.use_index_var = ctk.BooleanVar(value=False)
        self.use_index_check = ctk.CTkCheckBox(
            self.tab_settings, text="Использовать индекс устройства",
            variable=self.use_index_var, command=self.toggle_index_entry
        )
        self.use_index_check.pack(pady=5)

        self.index_entry = ctk.CTkEntry(self.tab_settings, placeholder_text="Индекс устройства (например, 25)", state="disabled")
        self.index_entry.pack(pady=5)

        self.save_config_button = ctk.CTkButton(self.tab_settings, text="Сохранить настройки", command=self.save_current_config)
        self.save_config_button.pack(pady=10)

    def create_security_tab(self):
        self.whitelist_frame = ctk.CTkFrame(self.tab_security)
        self.whitelist_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.whitelist_frame, text="Белый список (разрешённые IP):", font=("Arial", 14)).pack(pady=5)
        self.whitelist_text = ctk.CTkTextbox(self.whitelist_frame, height=100)
        self.whitelist_text.pack(fill="x", padx=10, pady=5)
        self.whitelist_text.insert("1.0", "")
        self.whitelist_text.configure(state="normal")

        self.update_whitelist_btn = ctk.CTkButton(self.whitelist_frame, text="Обновить белый список", command=self.update_whitelist)
        self.update_whitelist_btn.pack(pady=5)

        self.blacklist_frame = ctk.CTkFrame(self.tab_security)
        self.blacklist_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.blacklist_frame, text="Чёрный список (забаненные IP):", font=("Arial", 14)).pack(pady=5)
        self.blacklist_text = ctk.CTkTextbox(self.blacklist_frame, height=100)
        self.blacklist_text.pack(fill="x", padx=10, pady=5)
        self.blacklist_text.insert("1.0", "")
        self.blacklist_text.configure(state="normal")

        self.update_blacklist_btn = ctk.CTkButton(self.blacklist_frame, text="Обновить чёрный список", command=self.update_blacklist)
        self.update_blacklist_btn.pack(pady=5)

    def redirect_stdout(self):
        class TextRedirector:
            def __init__(self, widget):
                self.widget = widget
            def write(self, str):
                self.widget.insert("end", str)
                self.widget.see("end")
            def flush(self):
                pass
        self.original_stdout = sys.stdout
        sys.stdout = TextRedirector(self.log_text)

    def get_audio_devices(self):
        devices = sd.query_devices()
        out_devices = []
        for i, dev in enumerate(devices):
            if dev['max_output_channels'] > 0:
                out_devices.append(f"{dev['name']} (индекс {i})")
        return out_devices if out_devices else ["CABLE Input (индекс -1)"]

    def toggle_index_entry(self):
        if self.use_index_var.get():
            self.index_entry.configure(state="normal")
        else:
            self.index_entry.configure(state="disabled")
            self.index_entry.delete(0, "end")

    def load_config_to_ui(self):
        self.ip_entry.insert(0, self.config.get("host", "0.0.0.0"))
        self.port_entry.insert(0, str(self.config.get("port", "8765")))
        self.pass_entry.insert(0, self.config.get("password", "default_pass"))
        self.cert_ip_entry.insert(0, self.config.get("server_ip", "192.168.1.10"))

        # Загрузка индекса устройства
        index = self.config.get("output_device_index")
        if index is not None:
            self.use_index_var.set(True)
            self.index_entry.configure(state="normal")
            self.index_entry.delete(0, "end")
            self.index_entry.insert(0, str(index))
        else:
            self.use_index_var.set(False)
            self.index_entry.configure(state="disabled")

        saved_device = self.config.get("output_device", "")
        if saved_device:
            for item in self.devices:
                if item.startswith(saved_device + " (индекс"):
                    self.device_var.set(item)
                    break
            else:
                if self.devices:
                    self.device_var.set(self.devices[0])
        elif self.devices:
            self.device_var.set(self.devices[0])

    def save_current_config(self):
        self.config['host'] = self.ip_entry.get()
        self.config['server_ip'] = self.cert_ip_entry.get()
        self.config['port'] = int(self.port_entry.get())
        self.config['password'] = self.pass_entry.get()

        # Сохраняем имя устройства (без индекса)
        device_full = self.device_var.get()
        device_name = device_full.split(" (индекс")[0].strip()
        self.config['output_device'] = device_name

        # Сохраняем индекс устройства, если включён
        if self.use_index_var.get():
            try:
                self.config['output_device_index'] = int(self.index_entry.get())
            except ValueError:
                self.config['output_device_index'] = None
        else:
            self.config['output_device_index'] = None

        config_manager.save_config(self.config)
        self.log("✅ Настройки сохранены")

    def toggle_server(self):
        if not self.running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        host = self.ip_entry.get()
        port = int(self.port_entry.get())
        password = self.pass_entry.get()
        server_ip = self.cert_ip_entry.get()

        output_device_name = None
        output_device_index = None
        if self.use_index_var.get():
            try:
                output_device_index = int(self.index_entry.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректный индекс устройства")
                return
        else:
            # Сохраняем настройки, чтобы обновить конфиг с чистым именем
            self.save_current_config()
            output_device_name = self.config['output_device']  # уже чистое имя

        # Обновляем конфиг перед запуском (уже обновлён в save_current_config)
        # self.config уже содержит новые значения

        if self.server and self.running:
            self.stop_server()
            time.sleep(1)

        self.server = VoiceBridgeServer(self.config)  # Передаём весь конфиг
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_server, daemon=True)
        self.thread.start()
        self.running = True
        self.start_button.configure(text="Остановить сервер")
        self.view_cert_button.configure(state="normal")
        self.copy_cert_button.configure(state="normal")
        self.log("🚀 Сервер запущен...")

    def run_server(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.server.start())
        except Exception as e:
            self.start_error = str(e)
            asyncio.run_coroutine_threadsafe(self.server.stop(), self.loop)
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.after(0, self.handle_start_error)
        else:
            self.loop.run_forever()

    def handle_start_error(self):
        messagebox.showerror("Ошибка запуска", f"Не удалось запустить сервер: {self.start_error}")
        self.start_button.configure(text="Запустить сервер")
        self.view_cert_button.configure(state="disabled")
        self.copy_cert_button.configure(state="disabled")
        self.running = False
        self.server = None
        self.start_error = None

    def stop_server(self):
        if self.server:
            future = asyncio.run_coroutine_threadsafe(self.server.stop(), self.loop)
            try:
                future.result(timeout=5)
            except Exception as e:
                print(f"Ошибка при остановке сервера: {e}")
            finally:
                self.loop.call_soon_threadsafe(self.loop.stop)
                if self.thread and self.thread.is_alive():
                    self.thread.join(timeout=2)
        self.running = False
        self.start_button.configure(text="Запустить сервер")
        self.view_cert_button.configure(state="disabled")
        self.copy_cert_button.configure(state="disabled")
        self.log("🛑 Сервер остановлен.")

    def copy_certificate(self):
        if self.server and self.running:
            pem = self.server.security.get_certificate_pem()
            self.clipboard_clear()
            self.clipboard_append(pem)
            self.update()
            messagebox.showinfo("Успех", "Сертификат скопирован в буфер обмена")
        else:
            messagebox.showerror("Ошибка", "Сервер не запущен")

    def copy_logs(self):
        logs = self.log_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(logs)
        self.update()
        messagebox.showinfo("Скопировано", "Логи скопированы в буфер обмена")

    def show_certificate(self):
        if self.server and self.running:
            pem = self.server.security.get_certificate_pem()
            top = ctk.CTkToplevel(self)
            top.title("Сертификат сервера (PEM)")
            top.geometry("600x400")
            top.transient(self)

            text_area = scrolledtext.ScrolledText(top, wrap="word", font=("Courier", 10))
            text_area.pack(fill="both", expand=True, padx=10, pady=10)
            text_area.insert("1.0", pem)
            text_area.configure(state="normal")

            def copy_to_clipboard():
                top.clipboard_clear()
                top.clipboard_append(pem)
                top.update()
                messagebox.showinfo("Скопировано", "Сертификат скопирован в буфер обмена")

            copy_btn = ctk.CTkButton(top, text="Копировать", command=copy_to_clipboard)
            copy_btn.pack(pady=5)
        else:
            messagebox.showerror("Ошибка", "Сервер не запущен")

    def update_whitelist(self):
        if not self.server:
            messagebox.showerror("Ошибка", "Сервер не запущен")
            return
        text = self.whitelist_text.get("1.0", "end-1c").strip()
        raw_ips = [part.strip() for part in text.split(',') if part.strip()]
        valid_ips = []
        for ip_str in raw_ips:
            try:
                ip = ipaddress.ip_address(ip_str)
                valid_ips.append(str(ip))
            except ValueError:
                self.log(f"⚠️ Некорректный IP '{ip_str}' пропущен")
        self.server.security.whitelist.clear()
        for ip in valid_ips:
            self.server.security.add_to_whitelist(ip)
        self.log(f"✅ Белый список обновлён: {valid_ips}")
        messagebox.showinfo("Успех", "Белый список обновлён")

    def update_blacklist(self):
        if not self.server:
            messagebox.showerror("Ошибка", "Сервер не запущен")
            return
        text = self.blacklist_text.get("1.0", "end-1c").strip()
        raw_ips = [part.strip() for part in text.split(',') if part.strip()]
        valid_ips = []
        for ip_str in raw_ips:
            try:
                ip = ipaddress.ip_address(ip_str)
                valid_ips.append(str(ip))
            except ValueError:
                self.log(f"⚠️ Некорректный IP '{ip_str}' пропущен")
        self.server.security.blacklist.clear()
        for ip in valid_ips:
            self.server.security.add_to_blacklist(ip)
        self.log(f"✅ Чёрный список обновлён: {valid_ips}")
        messagebox.showinfo("Успех", "Чёрный список обновлён")
        for client in self.server.clients.get_all_clients():
            if client.ip in self.server.security.blacklist:
                asyncio.run_coroutine_threadsafe(client.websocket.close(1008, "You are banned"), self.loop)

    def ban_client(self, ip):
        if not self.server:
            return
        self.server.security.add_to_blacklist(ip)
        self.log(f"🔨 Клиент {ip} забанен")
        for client in self.server.clients.get_all_clients():
            if client.ip == ip:
                asyncio.run_coroutine_threadsafe(client.websocket.close(1008, "You are banned"), self.loop)
                break
        self.update_security_texts()

    def whitelist_client(self, ip):
        if not self.server:
            return
        self.server.security.add_to_whitelist(ip)
        self.log(f"✅ Клиент {ip} добавлен в белый список")
        self.update_security_texts()

    def update_security_texts(self):
        if self.server:
            whitelist = ', '.join(str(ip) for ip in self.server.security.whitelist)
            self.whitelist_text.delete("1.0", "end")
            self.whitelist_text.insert("1.0", whitelist)
            blacklist = ', '.join(str(ip) for ip in self.server.security.blacklist)
            self.blacklist_text.delete("1.0", "end")
            self.blacklist_text.insert("1.0", blacklist)

    def log(self, message):
        self.log_text.insert("end", f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see("end")

    def update_stats(self):
        if self.server and self.running:
            stats = self.server.get_stats()
            for widget in self.clients_list_frame.winfo_children():
                widget.destroy()
            for client in stats["clients"]:
                frame = ctk.CTkFrame(self.clients_list_frame)
                frame.pack(fill="x", pady=2)
                ctk.CTkLabel(frame, text=client['ip'], width=150).pack(side="left", padx=5)
                ctk.CTkLabel(frame, text=client['device_name'], width=150).pack(side="left", padx=5)
                ctk.CTkLabel(frame, text=f"{client['bytes']/1024:.1f} KB", width=100).pack(side="left", padx=5)
                btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
                btn_frame.pack(side="left", padx=5)
                ctk.CTkButton(btn_frame, text="Забанить", command=lambda ip=client['ip']: self.ban_client(ip), width=80).pack(side="left", padx=2)
                ctk.CTkButton(btn_frame, text="Доверять", command=lambda ip=client['ip']: self.whitelist_client(ip), width=80).pack(side="left", padx=2)
            self.stats_text.delete("1.0", "end")
            self.stats_text.insert("end",
                                   f"Всего клиентов: {stats['total_clients']}\n"
                                   f"Трафик: {stats['total_traffic']/1024:.1f} KB\n"
                                   )
        self.after(500, self.update_stats)

if __name__ == "__main__":
    app = ServerGUI()
    app.mainloop()
    if app.original_stdout:
        sys.stdout = app.original_stdout
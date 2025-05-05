import socket
import threading
import tkinter as tk
from tkinter import ttk
import sounddevice as sd
import numpy as np
import struct

SAMPLE_RATE = 48000
CHUNK_SIZE = 1024
AUDIO_FORMAT = np.int16  # يجب أن يتطابق مع تنسيق تسجيل الهاتف
CHANNELS = 1

class UdpMicReceiverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mic Receiver")

        self.lang = "en"
        self.is_listening = False
        self.port = 5005
        self.sock = None
        self.thread = None
        self.stream = None
        self.volume_multiplier = 1.0  # قيمة بين 0.0 و 1.0

        self.init_ui()

    def init_ui(self):
        self.root.geometry("400x350")  # زيادة الارتفاع لاستيعاب عناصر التحكم الجديدة
        self.root.configure(bg="#0f172a")

        self.title_label = tk.Label(self.root, text="Mic Receiver", fg="white", bg="#0f172a", font=("Arial", 18))
        self.title_label.pack(pady=10)

        self.port_label = tk.Label(self.root, text="Port:", fg="white", bg="#0f172a")
        self.port_label.pack()

        self.port_entry = tk.Entry(self.root)
        self.port_entry.insert(0, str(self.port))
        self.port_entry.pack(pady=5)

        self.status_label = tk.Label(self.root, text="Status: Stopped", fg="white", bg="#0f172a")
        self.status_label.pack(pady=10)

        self.toggle_btn = ttk.Button(self.root, text="Start Listening", command=self.toggle_stream)
        self.toggle_btn.pack(pady=10)

        self.volume_label = tk.Label(self.root, text="Volume:", fg="white", bg="#0f172a")
        self.volume_label.pack()

        self.volume_scale = tk.Scale(self.root, from_=0, to=100, orient=tk.HORIZONTAL,
                                     label="Volume (%)", fg="white", bg="#0f172a", troughcolor="#334155",
                                     highlightbackground="#0f172a", command=self.set_volume)
        self.volume_scale.set(100)  # ابدأ بمستوى صوت كامل
        self.volume_scale.pack(pady=5)

        self.lang_switch = ttk.Checkbutton(self.root, text="Arabic", command=self.toggle_language)
        self.lang_switch.pack(pady=5)

    def set_volume(self, value):
        self.volume_multiplier = int(value) / 100.0

    def toggle_language(self):
        self.lang = "ar" if self.lang == "en" else "en"
        self.update_texts()

    def update_texts(self):
        if self.lang == "ar":
            self.title_label.config(text="استقبال الميكروفون")
            self.port_label.config(text="المنفذ:")
            self.status_label.config(text="الحالة: متوقف" if not self.is_listening else "الحالة: يستقبل")
            self.toggle_btn.config(text="ابدأ الاستقبال" if not self.is_listening else "أوقف الاستقبال")
            self.volume_label.config(text="مستوى الصوت:")
            self.lang_switch.config(text="إنجليزي")
        else:
            self.title_label.config(text="Mic Receiver")
            self.port_label.config(text="Port:")
            self.status_label.config(text="Status: Stopped" if not self.is_listening else "Status: Receiving")
            self.toggle_btn.config(text="Start Listening" if not self.is_listening else "Stop Listening")
            self.volume_label.config(text="Volume:")
            self.lang_switch.config(text="Arabic")

    def toggle_stream(self):
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()

    def start_listening(self):
        try:
            self.port = int(self.port_entry.get())
        except ValueError:
            self.status_label.config(text="Invalid port!")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(("0.0.0.0", self.port))
            self.is_listening = True
            self.update_texts()
            self.status_label.config(fg="green")
            self.toggle_btn.config(text="Stop Listening" if self.lang == "en" else "أوقف الاستقبال")

            self.stream = sd.OutputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=AUDIO_FORMAT,
                blocksize=CHUNK_SIZE
            )
            self.stream.start()

            self.thread = threading.Thread(target=self.receive_audio)
            self.thread.daemon = True
            self.thread.start()
        except Exception as e:
            self.status_label.config(text=f"Error starting listener: {e}", fg="red")
            self.is_listening = False
            self.update_texts()
            if self.sock:
                self.sock.close()
            self.sock = None

    def stop_listening(self):
        self.is_listening = False
        self.update_texts()
        self.status_label.config(text="Status: Stopped" if self.lang == "en" else "الحالة: متوقف", fg="white")
        self.toggle_btn.config(text="Start Listening" if self.lang == "en" else "ابدأ الاستقبال")
        if self.sock:
            self.sock.close()
            self.sock = None
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.thread and self.thread.is_alive():
            self.thread.join()
            self.thread = None

    def receive_audio(self):
        while self.is_listening:
            try:
                data, _ = self.sock.recvfrom(CHUNK_SIZE * np.dtype(AUDIO_FORMAT).itemsize * CHANNELS)
                audio_data = np.frombuffer(data, dtype=AUDIO_FORMAT)
                if self.stream and self.stream.active:
                    # تطبيق مستوى الصوت
                    adjusted_audio = (audio_data * self.volume_multiplier).astype(AUDIO_FORMAT)
                    self.stream.write(adjusted_audio)
            except socket.error as e:
                if self.is_listening:
                    print(f"Socket error: {e}")
                    self.status_label.config(text=f"Socket error: {e}", fg="red")
                    self.stop_listening()
                break
            except Exception as e:
                print(f"Error receiving audio: {e}")
                self.status_label.config(text=f"Error receiving audio: {e}", fg="red")
                self.stop_listening()
                break

        if self.stream and self.stream.active:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.sock:
            self.sock.close()
            self.sock = None
        self.is_listening = False
        self.update_texts()
        self.status_label.config(text="Status: Stopped" if self.lang == "en" else "الحالة: متوقف", fg="white")
        self.toggle_btn.config(text="Start Listening" if self.lang == "en" else "ابدأ الاستقبال")


if __name__ == "__main__":
    root = tk.Tk()
    app = UdpMicReceiverApp(root)
    root.protocol("WM_DELETE_WINDOW", app.stop_listening) # إيقاف الاستماع عند إغلاق النافذة
    root.mainloop()
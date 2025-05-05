import socket
import threading
import tkinter as tk
from tkinter import ttk
import pyaudio

# إعدادات UDP
UDP_IP = "0.0.0.0"
UDP_PORT = 12345

# إعدادات الصوت
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# حالة الاتصال
connection_status = {"connected": False, "type": "wifi"}  # "wifi" or "usb"
connection_lock = threading.Lock()

# تحديد نوع الاتصال بناءً على الـ IP
def detect_connection_type(sender_ip):
    if sender_ip.startswith("192.") or sender_ip.startswith("10.") or sender_ip.startswith("172."):
        return "wifi"
    elif sender_ip.startswith("127.") or sender_ip == "localhost":
        return "usb"
    else:
        return "غير معروف"

# اللغات
LANGUAGES = {
    "ar": {
        "title": "🎙️ تطبيق ميكروفون سطح المكتب",
        "status_label": "الحالة: ",
        "waiting": "في انتظار الاتصال...",
        "receiving": "يتم استقبال الصوت عبر {type} 📡",
        "switch_language": "تبديل اللغة",
        "exit": "خروج"
    },
    "en": {
        "title": "🎙️ MicStream Desktop App",
        "status_label": "Status: ",
        "waiting": "Waiting for connection...",
        "receiving": "Receiving audio via {type} 📡",
        "switch_language": "Switch Language",
        "exit": "Exit"
    }
}

current_lang = "ar"

# تحديث الحالة في الواجهة
def update_status(text):
    status_label.config(text=f"{LANGUAGES[current_lang]['status_label']}{text}")

# الاستماع للصوت
def listen_for_audio():
    global connection_status  # يجب أن يكون global هنا أولاً
    stream = None  # تهيئة المتغير stream هنا لتجنب الوصول إليه قبل تعريفه

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # السماح بإعادة استخدام المنفذ
        sock.bind((UDP_IP, UDP_PORT))

        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        output=True,
                        frames_per_buffer=CHUNK)

        update_status(LANGUAGES[current_lang]["waiting"])

        while True:
            data, addr = sock.recvfrom(CHUNK * 2)
            connection_type = detect_connection_type(addr[0])

            # قفل لتحديث الحالة بشكل آمن
            with connection_lock:
                connection_status["connected"] = True
                connection_status["type"] = connection_type

            update_status(LANGUAGES[current_lang]["receiving"].format(type=connection_type.upper()))
            stream.write(data)

    except Exception as e:
        update_status(f"Error: {e}")
    finally:
        # التحقق من أن المتغير stream قد تم تهيئته
        if stream:
            stream.stop_stream()
            stream.close()
        # إغلاق الـ socket عند الخروج
        sock.close()

# التبديل بين اللغات
def switch_language():
    global current_lang
    current_lang = "en" if current_lang == "ar" else "ar"
    root.title(LANGUAGES[current_lang]["title"])
    lang_btn.config(text=LANGUAGES[current_lang]["switch_language"])
    exit_btn.config(text=LANGUAGES[current_lang]["exit"])
    update_status(LANGUAGES[current_lang]["waiting"])

# واجهة المستخدم
root = tk.Tk()
root.title(LANGUAGES[current_lang]["title"])
root.geometry("450x250")
root.configure(bg="#f0f0f0")

style = ttk.Style()
style.configure("TButton", font=("Arial", 12), padding=10)

status_label = tk.Label(root, text="", font=("Arial", 14), bg="#f0f0f0", fg="#333")
status_label.pack(pady=30)

lang_btn = ttk.Button(root, text=LANGUAGES[current_lang]["switch_language"], command=switch_language)
lang_btn.pack(pady=10)

exit_btn = ttk.Button(root, text=LANGUAGES[current_lang]["exit"], command=root.destroy)
exit_btn.pack(pady=10)

# بدء استقبال الصوت في Thread منفصل
thread = threading.Thread(target=listen_for_audio, daemon=True)
thread.start()

# تشغيل التطبيق
update_status(LANGUAGES[current_lang]["waiting"])
root.mainloop()

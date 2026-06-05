import io
import base64
import requests
import telebot
from PIL import Image
from flask import Flask, request

# 🔴 ضع توكن البوت هنا (أو الأفضل ENV في Render)
TELEGRAM_BOT_TOKEN = "8820755267:AAHMUktr3XDN_0RjFDM79NExy7ORssx-MdI"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

API_URL = "https://imageprompt.online/api/generate"
BASE_URL = "https://imageprompt.online/"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Origin": "https://imageprompt.online",
    "Referer": "https://imageprompt.online/"
}

# ===== Session =====
def create_fresh_session():
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    try:
        session.get(BASE_URL, timeout=10)
    except:
        pass
    return session


# ===== API REQUEST =====
def send_request(prompt, image_base64=""):
    session = create_fresh_session()

    payload = {
        "prompt": prompt,
        "imageBase64": image_base64,
        "format": "nanobanana2",
        "language": "en"
    }

    try:
        res = session.post(API_URL, json=payload, timeout=60)

        if res.status_code == 200:
            data = res.json()
            return data.get("imageBase64")
    except:
        return None

    return None


# ===== TEXT MESSAGE =====
@bot.message_handler(content_types=['text'])
def handle_text(message):
    bot.send_message(message.chat.id, "⏳ جاري توليد الصورة...")

    result = send_request(message.text)

    if result:
        img = base64.b64decode(result.split(",")[-1])
        bot.send_photo(message.chat.id, io.BytesIO(img))
    else:
        bot.send_message(message.chat.id, "❌ فشل في التوليد")


# ===== PHOTO MESSAGE =====
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_message(message.chat.id, "⏳ جاري معالجة الصورة...")

    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)

    img = Image.open(io.BytesIO(downloaded)).convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")

    encoded = base64.b64encode(buffer.getvalue()).decode()

    result = send_request(message.caption or "edit image", encoded)

    if result:
        img = base64.b64decode(result.split(",")[-1])
        bot.send_photo(message.chat.id, io.BytesIO(img))
    else:
        bot.send_message(message.chat.id, "❌ خطأ في تعديل الصورة")


# ===== WEBHOOK =====
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"


@app.route("/")
def home():
    return "Bot is running"


# ===== START =====
if __name__ == "__main__":
    bot.remove_webhook()

    # ⚠️ غيّر هذا بعد ما تنشر في Render
    bot.set_webhook(url=f"https://YOUR-RENDER-URL/{TELEGRAM_BOT_TOKEN}")

    app.run(host="0.0.0.0", port=10000)

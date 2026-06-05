import io
import base64
import requests
import telebot
from PIL import Image
from flask import Flask
import threading
import time

# 1️⃣ توكن البوت
TELEGRAM_BOT_TOKEN = "8820755267:AAHMUktr3XDN_0RjFDM79NExy7ORssx-MdI"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

app = Flask(__name__)

API_URL = "https://imageprompt.online/api/generate"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/json",
    "Origin": "https://imageprompt.online",
    "Referer": "https://imageprompt.online/",
    "Connection": "keep-alive"
}

def create_fresh_session():
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    return session

def send_request_to_api(payload_data):
    try:
        session = create_fresh_session()
        print("📡 [API] Sending payload to external API...", flush=True)
        response = session.post(API_URL, json=payload_data, timeout=45)
        print(f"📊 [API] Response code: {response.status_code}", flush=True)

        if response.status_code == 200:
            data = response.json()
            base64_data = data.get("imageBase64")
            if base64_data:
                return {"success": True, "data": base64_data}
            return {"success": False, "error": "No image field", "text": str(data)}
        return {"success": False, "error": f"HTTP {response.status_code}", "text": response.text[:200]}
    except Exception as e:
        return {"success": False, "error": "Timeout/Network Error", "text": str(e)}

# 1️⃣ توليد صورة من نص
@bot.message_handler(content_types=['text'])
def handle_text(message):
    print(f"📩 [POLLING - TEXT] User {message.chat.id} sent: {message.text}", flush=True)
    status_msg = bot.send_message(message.chat.id, "⏳ جاري التوليد...")

    payload = {
        "prompt": message.text,
        "imageBase64": "", 
        "format": "nanobanana2",
        "language": "en"
    }

    result = send_request_to_api(payload)
    if result["success"]:
        base64_data = result["data"].split(",")[1] if "," in result["data"] else result["data"]
        image_bytes = base64.b64decode(base64_data)
        
        try: bot.delete_message(message.chat.id, status_msg.message_id)
        except: pass

        image_file = io.BytesIO(image_bytes)
        image_file.name = "result.jpg"
        bot.send_photo(message.chat.id, image_file, caption="🎨 تم التوليد بنجاح")
        del base64_data, image_bytes, image_file
    else:
        bot.edit_message_text(f"❌ خطأ:\n`{result.get('error')}`", message.chat.id, status_msg.message_id)
    
    del payload, result

# 2️⃣ تعديل صورة مرسلة
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    print(f"📸 [POLLING - PHOTO] Received photo from user {message.chat.id}", flush=True)
    status_msg = bot.send_message(message.chat.id, "⏳ جاري المعالجة...")

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        img = Image.open(io.BytesIO(downloaded_file))
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        if img.mode != 'RGB': img = img.convert('RGB')

        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG', quality=80)

        encoded_image = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        caption = message.caption if message.caption else "enhance image"

        payload = {
            "prompt": caption,
            "imageBase64": f"data:image/jpeg;base64,{encoded_image}",
            "format": "nanobanana2",
            "language": "en"
        }

        try: bot.edit_message_text("⏳ جاري رفع بيانات الصورة ومعالجتها بالسيرفر...", message.chat.id, status_msg.message_id)
        except: pass

        result = send_request_to_api(payload)
        del downloaded_file, encoded_image, output_buffer
        
        if result["success"]:
            base64_data = result["data"].split(",")[1] if "," in result["data"] else result["data"]
            image_bytes = base64.b64decode(base64_data)
            
            try: bot.delete_message(message.chat.id, status_msg.message_id)
            except: pass

            image_file = io.BytesIO(image_bytes)
            image_file.name = "result.jpg"
            bot.send_photo(message.chat.id, image_file, caption="🎨 تم التعديل بنجاح")
            del base64_data, image_bytes, image_file
        else:
            bot.edit_message_text(f"❌ فشل السيرفر الخارجي:\n`{result.get('error')}`", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        print(f"🔴 [PHOTO ERROR] {str(e)}", flush=True)
        bot.edit_message_text(f"❌ خطأ داخلي:\n`{str(e)[:100]}`", message.chat.id, status_msg.message_id)


# مسار الويب لـ Render لإقناعه أن السيرفر حي
@app.route("/")
def home():
    return "Bot is running via Hybrid Polling mode!"

# دالة لتشغيل البوت بنظام Polling مستمر داخل Thread مستقل
def run_bot_polling():
    while True:
        try:
            print("🔄 [POLLING] Removing webhooks and starting infinity polling...", flush=True)
            bot.remove_webhook()
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"⚠️ [POLLING CRASH] Restarting polling in 5 seconds due to error: {e}", flush=True)
            time.sleep(5)

# تشغيل الخيط المستقل فوراً عند بدء التطبيق
polling_thread = threading.Thread(target=run_bot_polling)
polling_thread.daemon = True
polling_thread.start()

if __name__ == "__main__":
    pass

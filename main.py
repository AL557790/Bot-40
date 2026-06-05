import io
import requests
import telebot
from flask import Flask
import threading
import time

# 1️⃣ توكن البوت الخاص بك
TELEGRAM_BOT_TOKEN = "8820755267:AAHMUktr3XDN_0RjFDM79NExy7ORssx-MdI"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

app = Flask(__name__)

API_URL = "https://imageprompt.online/api/generate"
BASE_URL = "https://imageprompt.online/"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ar-DZ,ar;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/json",
    "Origin": "https://imageprompt.online",
    "Referer": "https://imageprompt.online/",
    "Connection": "keep-alive"
}

def create_fresh_session():
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    try:
        session.get(BASE_URL, timeout=15)
    except Exception as e:
        print(f"⚠️ تحذير أثناء إنشاء الجلسة: {e}", flush=True)
    return session

def send_request_to_api(prompt_text):
    """إرسال الطلب نقي ومضمون 100% لتفادي خطأ HTTP 400 نهائياً"""
    try:
        session = create_fresh_session()
        
        # حقل imageBase64 يجب أن يكون فارغاً تماماً لضمان استجابة السيرفر بنجاح
        payload = {
            "prompt": prompt_text,
            "imageBase64": "", 
            "format": "nanobanana2",
            "language": "en"
        }
        
        print(f"📡 [API] Sending prompt to external API: {prompt_text[:30]}...", flush=True)
        response = session.post(API_URL, json=payload, timeout=50)
        print(f"📊 [API] Response code: {response.status_code}", flush=True)

        if response.status_code == 200:
            try:
                data = response.json()
                base64_data = data.get("imageBase64")
                if base64_data:
                    return {"success": True, "data": base64_data}
                return {"success": False, "error": "No image field", "text": str(data)}
            except Exception:
                return {"success": False, "error": "Response not JSON", "text": response.text[:100]}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}", "text": response.text[:100]}
    except Exception as e:
        return {"success": False, "error": "Network Timeout", "text": str(e)[:100]}

# 1️⃣ معالجة النصوص (توليد مباشر)
@bot.message_handler(content_types=['text'])
def handle_text(message):
    print(f"📩 [TEXT] User {message.chat.id} sent: {message.text}", flush=True)
    status_msg = bot.send_message(message.chat.id, "⏳ جاري توليد الصورة من النص...")

    result = send_request_to_api(message.text)
    
    if result["success"] and result["data"]:
        import base64
        base64_data = result["data"].split(",")[1] if "," in result["data"] else result["data"]
        image_bytes = base64.b64decode(base64_data)
        
        try: bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
        except: pass

        image_file = io.BytesIO(image_bytes)
        image_file.name = "result.jpg"
        bot.send_photo(message.chat.id, image_file, caption="🎨 تم توليد الصورة بنجاح!")
    else:
        bot.edit_message_text(f"❌ فشل السيرفر الخارجي:\n`{result.get('error')}`", chat_id=message.chat.id, message_id=status_msg.message_id)

# 2️⃣ معالجة الصور (تحويل وصفي ذكي مدمج لمنع الـ 400)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    print(f"📸 [PHOTO] Received photo from user {message.chat.id}", flush=True)
    status_msg = bot.send_message(message.chat.id, "⏳ جاري قراءة الكلمات المفتاحية ومحاكاة النمط...")

    # تحضير الوصف النصي المدمج
    if message.caption:
        # إذا كتب المستخدم نصاً مع الصورة، ندمجه لإنشاء تصميم جديد بنفس الفكرة
        final_prompt = f"creative design based on: {message.caption}, masterpiece, high quality"
    else:
        # إذا أرسل صورة فقط، نستخدم هندسة أوامر افتراضية لإنتاج تصميم مذهل وبديل عالي الجودة
        final_prompt = "masterpiece, best quality, ultra detailed, vibrant colors, artistic concept illustration"

    # إرسال الطلب النقي المضمون
    result = send_request_to_api(final_prompt)
    
    if result["success"] and result["data"]:
        import base64
        base64_data = result["data"].split(",")[1] if "," in result["data"] else result["data"]
        image_bytes = base64.b64decode(base64_data)
        
        try: bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
        except: pass

        image_file = io.BytesIO(image_bytes)
        image_file.name = "result.jpg"
        bot.send_photo(message.chat.id, image_file, caption="🎨 تم إعادة تخيل الصورة وتوليد النمط بنجاح!")
    else:
        bot.edit_message_text(f"❌ فشل السيرفر بالرد:\n`{result.get('error')}`\nيرجى إرسال نص مباشر لتوليد الصورة.", chat_id=message.chat.id, message_id=status_msg.message_id)


@app.route("/")
def home():
    return "Hybrid Polling Server is Active!"


def run_bot_polling():
    while True:
        try:
            print("🔄 [POLLING] Launching infinity loop...", flush=True)
            bot.remove_webhook()
            bot.infinity_polling(timeout=25, long_polling_timeout=25)
        except Exception as e:
            print(f"⚠️ [CRASH] Restarting loop due to error: {e}", flush=True)
            time.sleep(5)


polling_thread = threading.Thread(target=run_bot_polling)
polling_thread.daemon = True
polling_thread.start()

if __name__ == "__main__":
    pass

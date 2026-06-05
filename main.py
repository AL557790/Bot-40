import io
import base64
import requests
import telebot
from PIL import Image
from flask import Flask
import threading
import time

# 1️⃣ توكن البوت الخاص بك
TELEGRAM_BOT_TOKEN = "8820755267:AAHMUktr3XDN_0RjFDM79NExy7ORssx-MdI"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

app = Flask(__name__)

API_URL = "https://imageprompt.online/api/generate"
BASE_URL = "https://imageprompt.online/"

# الهيدرز الأساسية لمحاكاة المتصفح بالكامل لتخطي حظر السيرفرات
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ar-DZ,ar;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/json",
    "Origin": "https://imageprompt.online",
    "Referer": "https://imageprompt.online/?utm_source=chatgpt.com",
    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Connection": "keep-alive"
}

def create_fresh_session():
    """زيارة الصفحة الرئيسية أولاً لإنشاء وتثبيت الكوكيز التلقائية وتفادي الـ 403"""
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    try:
        session.get(BASE_URL, timeout=15)
    except Exception as e:
        print(f"⚠️ تحذير أثناء إنشاء الجلسة التلقائية: {e}", flush=True)
    return session

def send_request_to_api(payload_data):
    try:
        session = create_fresh_session()
        print("📡 [API] Sending payload to external API...", flush=True)
        response = session.post(API_URL, json=payload_data, timeout=50)
        print(f"📊 [API] Response code: {response.status_code}", flush=True)

        if response.status_code == 200:
            try:
                data = response.json()
                base64_data = data.get("imageBase64")
                if base64_data:
                    return {"success": True, "data": base64_data}
                else:
                    return {"success": False, "error": "No image field", "text": str(data)}
            except Exception:
                return {"success": False, "error": "Response not JSON", "text": response.text[:100]}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}", "text": response.text[:100]}
    except Exception as e:
        return {"success": False, "error": "Network Timeout", "text": str(e)[:100]}

# 1️⃣ توليد صورة من نص
@bot.message_handler(content_types=['text'])
def handle_text(message):
    print(f"📩 [TEXT] User {message.chat.id} sent: {message.text}", flush=True)
    status_msg = bot.send_message(message.chat.id, "⏳ جاري توليد الصورة عبر جلسة جديدة...")

    payload = {
        "prompt": message.text,
        "imageBase64": "", 
        "format": "nanobanana2",
        "language": "en"
    }

    result = send_request_to_api(payload)
    
    if result["success"] and result["data"]:
        base64_data = result["data"].split(",")[1] if "," in result["data"] else result["data"]
        image_bytes = base64.b64decode(base64_data)
        
        try: bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
        except: pass

        image_file = io.BytesIO(image_bytes)
        image_file.name = "result.jpg"
        bot.send_photo(message.chat.id, image_file, caption="🎨 تم توليد الصورة بنجاح!")
        del base64_data, image_bytes, image_file
    else:
        bot.edit_message_text(f"❌ خطأ من السيرفر الخارجي:\n`{result.get('error')}`\n`{result.get('text', '')}`", chat_id=message.chat.id, message_id=status_msg.message_id)
    
    del payload, result

# 2️⃣ تعديل صورة مرسلة (النسخة المصححة والمؤمنة بالكامل)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    print(f"📸 [PHOTO] Received photo from user {message.chat.id}", flush=True)
    status_msg = bot.send_message(message.chat.id, "⏳ جاري تهيئة ومعالجة أبعاد الصورة واختراق الحماية...")

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        img = Image.open(io.BytesIO(downloaded_file))
        
        # تصغير حجم الصورة قليلاً لعدم تخطي الرام المسموح في سيرفر Render المجاني
        max_size = 600
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
        if img.mode != 'RGB': 
            img = img.convert('RGB')

        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG', quality=80)

        encoded_image = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        # إذا لم يكتب كابشن، نضع هذا الوصف الافتراضي المتوافق مع موديل التعديل
        caption = message.caption if message.caption else "enhance quality, detailed, realistic"

        # 💡 الإصلاح الجوهري: إضافة الداتا بريفيكس ليفهمها السيرفر فوراً ولا يعطي 400
        payload = {
            "prompt": caption,
            "imageBase64": f"data:image/jpeg;base64,{encoded_image}",
            "format": "nanobanana2",
            "language": "en"
        }

        try: bot.edit_message_text("⏳ جاري إنشاء الجلسة ورفع بيانات الصورة المشفرة...", chat_id=message.chat.id, message_id=status_msg.message_id)
        except: pass

        result = send_request_to_api(payload)
        
        del downloaded_file, output_buffer, img, encoded_image, payload
        
        if result["success"] and result["data"]:
            base64_data = result["data"].split(",")[1] if "," in result["data"] else result["data"]
            image_bytes = base64.b64decode(base64_data)
            
            try: bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            except: pass

            image_file = io.BytesIO(image_bytes)
            image_file.name = "result.jpg"
            bot.send_photo(message.chat.id, image_file, caption="🎨 تم تعديل ومعالجة صورتك بنجاح!")
            del base64_data, image_bytes, image_file
        else:
            bot.edit_message_text(f"❌ فشل السيرفر الخارجي:\n`{result.get('error')}`\n`{result.get('text', '')[:100]}`", chat_id=message.chat.id, message_id=status_msg.message_id)
            
    except Exception as e:
        print(f"🔴 [PHOTO ERROR] {str(e)}", flush=True)
        try: bot.edit_message_text(f"❌ خطأ داخلي أثناء المعالجة:\n`{str(e)[:100]}`", chat_id=message.chat.id, message_id=status_msg.message_id)
        except: pass


# مسار الويب الأساسي الذي يضمن استمرار تشغيل الخدمة على موقع Render دون إغلاق
@app.route("/")
def home():
    return "Hybrid Polling Server is Active!"


# دالة لتشغيل البوت بنظام Polling مستمر داخل خيط معالجة (Thread) مستقل ومتوازي
def run_bot_polling():
    while True:
        try:
            print("🔄 [POLLING] Resetting updates and launching infinity loop...", flush=True)
            bot.remove_webhook()
            bot.infinity_polling(timeout=25, long_polling_timeout=25)
        except Exception as e:
            print(f"⚠️ [CRASH] Restarting loop due to error: {e}", flush=True)
            time.sleep(5)


# تفعيل تشغيل البوت في الخلفية بالتوازي مع سيرفر الويب
polling_thread = threading.Thread(target=run_bot_polling)
polling_thread.daemon = True
polling_thread.start()

if __name__ == "__main__":
    pass

import io
import base64
import requests
import telebot
from PIL import Image
from flask import Flask, request

# 1️⃣ ضع توكن البوت الحقيقي الخاص بك هنا
TELEGRAM_BOT_TOKEN = "8820755267:AAHMUktr3XDN_0RjFDM79NExy7ORssx-MdI"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 2️⃣ ضع رابط السيرفر الخاص بك على Render هنا ليتم ربطه تلقائياً
RENDER_WEB_URL = "https://bot-40-sm1k.onrender.com"

app = Flask(__name__)

API_URL = "https://imageprompt.online/api/generate"
BASE_URL = "https://imageprompt.online/"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ar-DZ,ar;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://imageprompt.online",
    "Referer": "https://imageprompt.online/?utm_source=chatgpt.com",
    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

def create_fresh_session():
    """دالة لإنشاء جلسة جديدة وجلب كوكيز حية ومباشرة من الموقع تلقائياً"""
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    try:
        session.get(BASE_URL, timeout=15)
    except Exception as e:
        print(f"⚠️ تحذير أثناء إنشاء الجلسة التلقائية: {e}")
    return session

def send_request_to_api(payload_data):
    """دالة ترسل الطلب باستخدام جلسة برمجية جديدة بالكامل في كل مرة"""
    try:
        session = create_fresh_session()
        response = session.post(API_URL, json=payload_data, timeout=45)
        
        if response.status_code == 200:
            try:
                data = response.json()
                base64_data = data.get("imageBase64")
                if base64_data:
                    return {"success": True, "data": base64_data}
                else:
                    return {"success": False, "error": "السيرفر لم يرسل الصورة. الرد المستلم:", "text": str(data)}
            except Exception:
                return {"success": False, "error": "رد السيرفر ليس بصيغة JSON. الرد النصي:", "text": response.text[:200]}
        else:
            clean_text = response.text[:150] + "..." if len(response.text) > 150 else response.text
            return {"success": False, "error": f"كود الحالة: {response.status_code}", "text": clean_text}
    except Exception as e:
        return {"success": False, "error": "خطأ في الاتصال بالشبكة:", "text": str(e)[:100]}


# 1️⃣ توليد صورة من نص
@bot.message_handler(content_types=['text'])
def handle_text(message):
    status_msg = bot.send_message(message.chat.id, "⏳ جاري إنشاء جلسة تلقائية وتوليد الصورة...")
    
    payload = {
        "prompt": message.text,
        "imageBase64": "", 
        "format": "nanobanana2",
        "language": "en"
    }
    
    result = send_request_to_api(payload)
    
    if result["success"] and result["data"]:
        base64_data = result["data"]
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
            
        image_bytes = base64.b64decode(base64_data)
        del base64_data, result, payload
        
        try: bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
        except: pass
            
        image_file = io.BytesIO(image_bytes)
        image_file.name = "result.jpg"
        bot.send_photo(message.chat.id, image_file, caption="🎨 تم توليد الصورة بنجاح عبر جلسة جديدة!")
    else:
        error_title = result.get('error', 'خطأ غير معروف')
        error_details = result.get('text', '')
        del result, payload
        bot.edit_message_text(f"❌ {error_title}\n`{error_details}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")


# 2️⃣ تعديل صورة مرسلة (معدلة لتتوافق مع بيئة استضافة Render)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    status_msg = bot.send_message(message.chat.id, "⏳ جاري تهيئة ومعالجة أبعاد الصورة...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        img = Image.open(io.BytesIO(downloaded_file))
        max_size = 800  # تقليص طفيف للأبعاد لضمان معالجة سريعة على السيرفر بدون Timeout
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG', quality=85)
        jpg_bytes = output_buffer.getvalue()
        
        encoded_image = base64.b64encode(jpg_bytes).decode('utf-8')
        caption = message.caption if message.caption else "enhance image"
        
        # 🔥 هنا التعديل: إرسال صيغة Data URI السليمة ليفهمها السيرفر عند الطلب من Render
        payload = {
            "prompt": caption,
            "imageBase64": f"data:image/jpeg;base64,{encoded_image}",
            "format": "nanobanana2",
            "language": "en"
        }
        
        del downloaded_file, jpg_bytes, output_buffer
        bot.edit_message_text("⏳ جاري إنشاء الجلسة ورفع بيانات الصورة للسيرفر...", chat_id=message.chat.id, message_id=status_msg.message_id)
        
        result = send_request_to_api(payload)
        del payload, encoded_image
        
        if result["success"] and result["data"]:
            base64_data = result["data"]
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            
            image_bytes = base64.b64decode(base64_data)
            del base64_data, result
            
            try: bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            except: pass
                
            image_file = io.BytesIO(image_bytes)
            image_file.name = "result.jpg"
            bot.send_photo(message.chat.id, image_file, caption="🎨 تم معالجة وتعديل صورتك بنجاح!")
        else:
            error_title = result.get('error', 'خطأ غير معروف')
            error_details = result.get('text', '')
            del result
            bot.edit_message_text(f"❌ {error_title}\n`{error_details}`", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ داخلي في البوت: {str(e)[:100]}", chat_id=message.chat.id, message_id=status_msg.message_id)


# 🔴 مسارات Flask الضرورية للـ Webhook والـ live check على Render
@app.route("/")
def home():
    return "Bot is running perfectly!"

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"

# 🔥 الإعداد الذاتي لإزالة الـ Polling القديم وربط الـ Webhook تلقائياً عند التشغيل على السيرفر
if __name__ == "__main__":
    print("🔄 Removing old configuration...")
    bot.remove_webhook()
    
    webhook_url = f"{RENDER_WEB_URL}/{TELEGRAM_BOT_TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"🚀 Webhook configured successfully: {webhook_url}")

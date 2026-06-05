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

# 🔥 خدعة: هيدرز متقدمة جداً تحاكي متصفح أندرويد حقيقي لتفادي حظر السيرفرات
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Origin": "https://imageprompt.online",
    "Referer": "https://imageprompt.online/",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": '"Android"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Connection": "keep-alive"
}

def create_fresh_session():
    """خدعة إنشاء جلسة حية وسحب الكوكيز تلقائياً قبل إرسال طلب الصورة"""
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    try:
        # زيارة الموقع أولاً كزائر عادي للحصول على كوكيز الحماية
        init_res = session.get(BASE_URL, timeout=15)
        if init_res.status_code == 200:
            print("✅ Session cookies fetched successfully!")
    except Exception as e:
        print(f"⚠️ Warning during session backup: {e}")
    return session

def send_request_to_api(payload_data):
    """إرسال البيانات عبر الجلسة المحمية"""
    try:
        session = create_fresh_session()
        response = session.post(API_URL, json=payload_data, timeout=50)
        
        print(f"📊 [Server Response] Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                base64_data = data.get("imageBase64")
                if base64_data:
                    return {"success": True, "data": base64_data}
                else:
                    return {"success": False, "error": "السيرفر لم يرسل الصورة.", "text": str(data)}
            except Exception:
                return {"success": False, "error": "الرد ليس بصيغة JSON.", "text": response.text[:150]}
        else:
            # إذا أرجع 403 أو 503 يعني أن السيرفر محظور من حماية الموقع
            return {"success": False, "error": f"خطأ حماية (كود {response.status_code})", "text": "تم حظر خادم الاستضافة من قِبل الموقع الخارجي."}
    except Exception as e:
        return {"success": False, "error": "انتهت مهلة الاتصال بالشبكة (Timeout)", "text": str(e)[:100]}


# 1️⃣ توليد صورة من نص
@bot.message_handler(content_types=['text'])
def handle_text(message):
    status_msg = bot.send_message(message.chat.id, "⏳ جاري محاكاة المتصفح وتوليد الصورة...")
    
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
        bot.send_photo(message.chat.id, image_file, caption="🎨 تم توليد الصورة بنجاح!")
    else:
        error_title = result.get('error', 'خطأ غير معروف')
        error_details = result.get('text', '')
        del result, payload
        bot.edit_message_text(f"❌ {error_title}\n`{error_details}`", chat_id=message.chat.id, message_id=status_msg.message_id)


# 2️⃣ تعديل صورة مرسلة
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    status_msg = bot.send_message(message.chat.id, "⏳ جاري سحب ومعالجة أبعاد الصورة...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        img = Image.open(io.BytesIO(downloaded_file))
        max_size = 800  # تصغير الأبعاد قليلاً لمنع تهنيج سيرفر Render المجاني
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG', quality=85)
        jpg_bytes = output_buffer.getvalue()
        
        encoded_image = base64.b64encode(jpg_bytes).decode('utf-8')
        caption = message.caption if message.caption else "enhance image"
        
        # صيغة الـ Base64 مضافة إليها الميتا داتا الخاصة بالصور
        payload = {
            "prompt": caption,
            "imageBase64": f"data:image/jpeg;base64,{encoded_image}",
            "format": "nanobanana2",
            "language": "en"
        }
        
        del downloaded_file, jpg_bytes, output_buffer
        bot.edit_message_text("⏳ جاري كسر الحماية ورفع بيانات الصورة...", chat_id=message.chat.id, message_id=status_msg.message_id)
        
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
            error_title = result.get('error', 'خطأ')
            error_details = result.get('text', '')
            del result
            bot.edit_message_text(f"❌ {error_title}\n`{error_details}`", chat_id=message.chat.id, message_id=status_msg.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ داخلي في البوت: {str(e)[:100]}", chat_id=message.chat.id, message_id=status_msg.message_id)


# 🔴 مسارات Flask الضرورية للعمل بنظام الـ Webhook على Render
@app.route("/")
def home():
    return "Bot is running perfectly!"

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"


if __name__ == "__main__":
    print("🔄 Configuring Telegram Webhook...")
    bot.remove_webhook()
    webhook_url = f"{RENDER_WEB_URL}/{TELEGRAM_BOT_TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"🚀 Webhook configured successfully to: {webhook_url}")

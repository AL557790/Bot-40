import io
import base64
import requests
import telebot
from PIL import Image
from flask import Flask
import threading
import time

# 1. ضع توكن البوت الحقيقي الخاص بك هنا
TELEGRAM_BOT_TOKEN = "8820755267:AAHMUktr3XDN_0RjFDM79NExy7ORssx-MdI"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# إنشاء سيرفر ويب وهمي لـ Render لمنع خطأ الـ Port
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
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    try:
        session.get(BASE_URL, timeout=15)
    except Exception as e:
        print(f"⚠️ تحذير أثناء إنشاء الجلسة: {e}", flush=True)
    return session

def extract_prompt_from_image(payload_data):
    try:
        session = create_fresh_session()
        response = session.post(API_URL, json=payload_data, timeout=45)
        
        if response.status_code == 200:
            try:
                data = response.json()
                prompt_data = data.get("prompt")
                if prompt_data:
                    return {"success": True, "prompt": prompt_data}
                else:
                    return {"success": False, "error": "السيرفر لم يقم بتحليل الصورة. الرد المستلم:", "text": str(data)}
            except Exception:
                return {"success": False, "error": "رد السيرفر ليس بصيغة JSON. الرد النصي:", "text": response.text[:200]}
        else:
            return {"success": False, "error": f"كود الحالة: {response.status_code}", "text": response.text[:150]}
    except Exception as e:
        return {"success": False, "error": "خطأ في الاتصال بالشبكة:", "text": str(e)[:100]}


# 1️⃣ معالجة الصور واستخراج الوصف
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    status_msg = bot.send_message(message.chat.id, "⏳ جاري رفع الصورة وتحليل ملامحها واستخراج الوصف الاحترافي...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        img = Image.open(io.BytesIO(downloaded_file))
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG', quality=90)
        jpg_bytes = output_buffer.getvalue()
        
        encoded_image = base64.b64encode(jpg_bytes).decode('utf-8')
        caption = message.caption if message.caption else "describe this image in ultra detail"
        
        payload = {
            "prompt": caption,
            "imageBase64": encoded_image,
            "format": "nanobanana2",
            "language": "en"
        }
        
        result = extract_prompt_from_image(payload)
        
        try: bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
        except: pass
        
        if result["success"]:
            response_text = f"📋 **تم استخراج وصف الصورة بنجاح!**\n\n" \
                            f"💡 **البرومبت الاحترافي (اضغط للنسخ):**\n" \
                            f"`{result['prompt']}`"
            bot.send_message(message.chat.id, response_text, parse_mode="Markdown")
        else:
            error_title = result.get('error', 'خطأ غير معروف')
            error_details = result.get('text', '')
            bot.send_message(message.chat.id, f"❌ {error_title}\n`{error_details}`", parse_mode="Markdown")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ داخلي في البوت: {str(e)[:100]}")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    bot.reply_to(message, "📸 من فضلك أرسل لي **صورة** لأقوم بتحليلها واستخراج الوصف الخاص بها!")


# 🌐 مسار الويب لـ Render للحفاظ على استقرار السيرفر مجاناً
@app.route("/")
def home():
    return "Image-to-Prompt Core is Online!"

def run_bot_polling():
    while True:
        try:
            print("🔄 [POLLING] Loop is running perfectly...", flush=True)
            bot.remove_webhook()
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f"⚠️ [CRASH] Loop reset due to error: {e}", flush=True)
            time.sleep(5)

# تشغيل البوت في الخلفية بالتوازي مع سيرفر الويب المتوافق مع Render
polling_thread = threading.Thread(target=run_bot_polling)
polling_thread.daemon = True
polling_thread.start()

if __name__ == "__main__":
    # تشغيل السيرفر على بورت 10000 وهو الافتراضي لـ Render
    app.run(host="0.0.0.0", port=10000)

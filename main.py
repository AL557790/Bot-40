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
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    try:
        session.get(BASE_URL, timeout=15)
    except Exception as e:
        print(f"⚠️ تحذير أثناء إنشاء الجلسة: {e}", flush=True)
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
                base64_data = data.get("imageBase64") or data.get("image")
                if base64_data:
                    return {"success": True, "data": base64_data}
                else:
                    return {"success": False, "error": "No image field", "text": str(data)}
            except Exception:
                return {"success": False, "error": "Response not JSON", "text": response.text[:100]}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}", "text": response.text[:150]}
    except Exception as e:
        return {"success": False, "error": "Network Timeout", "text": str(e)[:100]}

# 1️⃣ توليد صورة من نص
@bot.message_handler(content_types=['text'])
def handle_text(message):
    print(f"📩 [TEXT] User {message.chat.id} sent: {message.text}", flush=True)
    status_msg = bot.send_message(message.chat.id, "⏳ جاري توليد الصورة...")

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

# 2️⃣ تعديل صورة مرسلة (النسخة الشاملة لجميع احتمالات الحقول)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    print(f"📸 [PHOTO] Received photo from user {message.chat.id}", flush=True)
    status_msg = bot.send_message(message.chat.id, "⏳ جاري تهيئة ومطابقة حقول معالجة الصور...")

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        raw_img = Image.open(io.BytesIO(downloaded_file))
        img = Image.new("RGB", raw_img.size, (255, 255, 255))
        img.paste(raw_img)

        # جعل الصورة خفيفة جداً لسرعة الرفع وتفادي مشاكل الحقول
        max_size = 512
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG', quality=80)

        encoded_image = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        caption = message.caption if message.caption else "masterpiece, best quality, ultra detailed"
        
        full_base64_string = f"data:image/jpeg;base64,{encoded_image}"

        # 💡 الخدعة الكبرى: تغذية السيرفر بجميع مسميات الحقول المحتملة في طلب واحد 
        # لكي يجد الحقل الذي يبحث عنه مهما كان نظامه البرمجي الداخلي
        payload = {
            "prompt": caption,
            "imageBase64": full_base64_string,
            "image": full_base64_string,
            "init_image": full_base64_string,
            "format": "nanobanana2",
            "language": "en"
        }

        try: bot.edit_message_text("⏳ جاري إرسال البيانات الموحدة وانتظار استجابة الذكاء الاصطناعي...", chat_id=message.chat.id, message_id=status_msg.message_id)
        except: pass

        result = send_request_to_api(payload)
        
        del downloaded_file, output_buffer, img, raw_img, encoded_image, payload
        
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
            bot.edit_message_text(f"❌ خطأ في معالجة الصورة:\n`{result.get('error')}`\nالسيرفر لم يتمكن من دمج الصورة مع هذا الوصف الحجمي.", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        print(f"🔴 [PHOTO ERROR] {str(e)}", flush=True)
        try: bot.edit_message_text(f"❌ خطأ داخلي أثناء المعالجة:\n`{str(e)[:100]}`", message.chat.id, status_msg.message_id)
        except: pass


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

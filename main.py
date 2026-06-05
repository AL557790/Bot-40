import io
import base64
import requests
import telebot
from PIL import Image
from flask import Flask, request

# 1️⃣ توكن البوت
TELEGRAM_BOT_TOKEN = "8820755267:AAHMUktr3XDN_0RjFDM79NExy7ORssx-MdI"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 2️⃣ رابط سيرفر Render الخاص بك
RENDER_WEB_URL = "https://bot-40-sm1k.onrender.com"

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

webhook_initialized = False

def create_fresh_session():
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    return session

def send_request_to_api(payload_data):
    try:
        session = create_fresh_session()
        print("Base64 📡 [LOG] Sending payload to external API...", flush=True)
        response = session.post(API_URL, json=payload_data, timeout=45)
        print(f"📊 [LOG] External API responded with status code: {response.status_code}", flush=True)

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
    print(f"📩 [NEW TEXT] User {message.chat.id} sent: {message.text}", flush=True)
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
    print(f"📸 [NEW PHOTO] Received photo from user {message.chat.id}", flush=True)
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
            bot.edit_message_text(f"❌ فشل السيرفر الخارجي:\n`{result.get('error')}`\n{result.get('text', '')[:100]}", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        print(f"🔴 [PHOTO ERROR] {str(e)}", flush=True)
        bot.edit_message_text(f"❌ خطأ داخلي:\n`{str(e)[:100]}`", message.chat.id, status_msg.message_id)


@app.route("/")
def home():
    return "Bot status: ONLINE"


@app.route("/webhook", methods=["POST"])
def webhook():
    print("📥 [WEBHOOK ENTRY] Telegram just pinged the server!", flush=True)
    try:
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        print(f"🔴 [WEBHOOK ERROR] Failed processing update: {e}", flush=True)
        return "Error", 500


# 🔥 الخدعة الأكثر أماناً: تفعيل الـ Webhook تلقائياً مع أول طلب (Live check) يستقبله Flask من Render مجبراً
@app.before_request
def setup_webhook_on_first_run():
    global webhook_initialized
    if not webhook_initialized:
        print("🔄 [WEBHOOK SETUP] Initializing webhook deployment...", flush=True)
        try:
            bot.remove_webhook()
            webhook_url = f"{RENDER_WEB_URL}/webhook"
            bot.set_webhook(url=webhook_url)
            print(f"🚀 [WEBHOOK SETUP] Success! Live at: {webhook_url}", flush=True)
            webhook_initialized = True
        except Exception as init_err:
            print(f"🔴 [WEBHOOK SETUP] Failed to register webhook: {init_err}", flush=True)


if __name__ == "__main__":
    pass

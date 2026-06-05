import io
import base64
import requests
import telebot
from PIL import Image
from flask import Flask, request

# 1️⃣ ضع توكن البوت الحقيقي الخاص بك هنا
TELEGRAM_BOT_TOKEN = "8820755267:AAHMUktr3XDN_0RjFDM79NExy7ORssx-MdI"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 2️⃣ ضع رابط السيرفر الخاص بك على Render هنا (ليقوم الكود بربط الـ Webhook تلقائياً)
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
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    try:
        session.get(BASE_URL, timeout=15)
    except Exception as e:
        print(f"⚠️ session error: {e}")
    return session


def send_request_to_api(payload_data):
    try:
        session = create_fresh_session()
        response = session.post(API_URL, json=payload_data, timeout=45)

        if response.status_code == 200:
            data = response.json()
            base64_data = data.get("imageBase64")
            if base64_data:
                return {"success": True, "data": base64_data}
            else:
                return {"success": False, "error": "No image returned", "text": str(data)}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}", "text": response.text[:200]}
    except Exception as e:
        return {"success": False, "error": "Request error", "text": str(e)[:100]}


# 1️⃣ توليد صورة من نص
@bot.message_handler(content_types=['text'])
def handle_text(message):
    status_msg = bot.send_message(message.chat.id, "⏳ جاري إنشاء جلسة وتوليد الصورة...")

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

        try:
            bot.delete_message(message.chat.id, status_msg.message_id)
        except:
            pass

        image_file = io.BytesIO(image_bytes)
        image_file.name = "result.jpg"
        bot.send_photo(message.chat.id, image_file, caption="🎨 تم التوليد بنجاح")
    else:
        bot.edit_message_text(
            f"❌ {result.get('error','Error')}\n{result.get('text','')}",
            message.chat.id,
            status_msg.message_id
        )


# 2️⃣ تعديل صورة مرسلة (معالجة حجم الصورة وصيغة الميتا داتا)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    status_msg = bot.send_message(message.chat.id, "⏳ جاري تحميل ومعالجة الصورة... قد يستغرق ذلك دقيقة.")

    try:
        # تحميل الصورة من سيرفرات تيليجرام
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        img = Image.open(io.BytesIO(downloaded_file))
        
        # تقليص الحجم لـ 800px لمنع حدوث تجميد أو Timeout على Render
        max_size = 800
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        # ضغط جودة الصورة قليلاً لتسريع الرفع
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG', quality=80)
        jpg_bytes = output_buffer.getvalue()

        # تشفير الصورة وإضافة الـ Data URI اللازم للـ API
        encoded_image = base64.b64encode(jpg_bytes).decode('utf-8')
        caption = message.caption if message.caption else "enhance image"

        payload = {
            "prompt": caption,
            "imageBase64": f"data:image/jpeg;base64,{encoded_image}",
            "format": "nanobanana2",
            "language": "en"
        }

        print("📡 Sending image to API...")
        result = send_request_to_api(payload)
        print(f"📥 API Response Success: {result['success']}")

        if result["success"] and result["data"]:
            base64_data = result["data"]
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            image_bytes = base64.b64decode(base64_data)

            try:
                bot.delete_message(message.chat.id, status_msg.message_id)
            except:
                pass

            image_file = io.BytesIO(image_bytes)
            image_file.name = "result.jpg"
            bot.send_photo(message.chat.id, image_file, caption="🎨 تم التعديل بنجاح")
        else:
            bot.edit_message_text(
                f"❌ فشل السيرفر في معالجة الصورة:\n{result.get('error','Error')}\nالتفاصيل: {result.get('text','')[:100]}",
                message.chat.id,
                status_msg.message_id
            )

    except Exception as e:
        print(f"🔴 Critical Error in handle_photo: {str(e)}")
        bot.edit_message_text(
            f"❌ خطأ داخلي أثناء المعالجة: {str(e)[:100]}",
            message.chat.id,
            status_msg.message_id
        )


# 🔴 مسارات الـ Flask المطلوبة للـ Webhook والتشغيل على Render
@app.route("/")
def home():
    return "Bot is running perfectly!"


@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"


# 🔥 التفعيل الذكي: ضبط الـ Webhook ذاتياً فور تشغيل السيرفر
if __name__ == "__main__":
    print("🔄 Removing old webhook/polling configuration...")
    bot.remove_webhook()
    
    # ربط البوت برابط سيرفر Render تلقائياً
    webhook_url = f"{RENDER_WEB_URL}/{TELEGRAM_BOT_TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"🚀 Webhook successfully configured to: {webhook_url}")

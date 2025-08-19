import telebot
from telebot import types
import logging
import os
import threading
import time
import requests
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Bot configuration - Get TOKEN from environment variable
TOKEN = os.environ.get('TOKEN', '8221110385:AAHnbPhxpNlLhEaRVXtqf0C5j4RtiIkzglQ')
if not TOKEN:
    logging.critical("No TOKEN provided. Set the TOKEN environment variable.")
    exit(1)

CHANNEL_LINK = 'https://t.me/+W0lpVpFhNLxjNTM0'
CHANNEL_ID = -1002860781709
CHANNEL_TITLE = "عيادات الحروف"

bot = telebot.TeleBot(TOKEN)

# Flask app setup
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/ping')
def ping():
    return "pong", 200

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def start_keepalive():
    """Start a background thread to keep the service alive"""
    def keepalive():
        while True:
            try:
                # Get the Render app URL from environment variable
                app_url = os.environ.get('RENDER_EXTERNAL_URL', '')
                if app_url:
                    # Send a ping to the /ping endpoint
                    response = requests.get(f"{app_url}/ping")
                    logging.info(f"Keepalive ping: {response.status_code}")
                else:
                    logging.warning("RENDER_EXTERNAL_URL not set, skipping ping")
                
                # Sleep for 10 minutes
                time.sleep(600)
                
            except Exception as e:
                logging.error(f"Keepalive error: {str(e)}")
                time.sleep(60)
    
    thread = threading.Thread(target=keepalive)
    thread.daemon = True
    thread.start()
    logging.info("Keepalive thread started")

def check_bot_permissions():
    """Verify bot has admin permissions in channel"""
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, bot.get_me().id)
        if chat_member.status not in ['administrator', 'creator']:
            logging.error("Bot is not admin in the channel!")
            return False
        
        logging.info(f"Bot has {chat_member.status} permissions in {CHANNEL_TITLE}")
        return True
        
    except Exception as e:
        logging.error(f"Permission check failed: {str(e)}")
        return False

@bot.message_handler(commands=['myid'])
def get_my_id(message):
    user = message.from_user
    bot.reply_to(
        message,
        f"🆔 معرفك الشخصي:\n"
        f"- الرقم: `{user.id}`\n"
        f"- الاسم: {user.first_name}\n"
        f"- اليوزر: @{user.username or 'غير متوفر'}",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Enhanced welcome message with channel info"""
    welcome_msg = f"""
    السلام عليكم ورحمة الله وبركاته 🌸

    أهلاً بكِ يا {message.from_user.first_name} في بوت {CHANNEL_TITLE}.

    📌 لإرسال تسجيل قرآن:
    1. اضغط على ميكروفون
    2. سجلي الوجه المطلوب
    3. اكتبي اسمك في نص الرسالة

    سيتم مراجعة التسجيل في: [قناة {CHANNEL_TITLE}]({CHANNEL_LINK})
    """
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Process voice messages with enhanced error handling"""
    if not check_bot_permissions():
        bot.reply_to(
            message,
            "⚠️ البوت لا يملك الصلاحيات الكافية في القناة. يرجى إضافته كمسؤول.",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(
                    text="إضافة البوت إلى القناة",
                    url=f"https://t.me/{bot.get_me().username}?startchannel=true"
                )
            )
        )
        return

    try:
        # إرسال الصوت مع بيانات المستخدم
        user = message.from_user
        caption = (
            f"تسجيل جديد من: {user.first_name}\n"
            f"Username: @{user.username}\n"
            f"User ID: {user.id}"
        )

        bot.send_voice(
            chat_id=CHANNEL_ID,
            voice=message.voice.file_id,
            caption=caption,
            parse_mode="Markdown"
        )

        # إرسال إشعار للمستخدمة
        bot.reply_to(
            message,
            "✅ تم استلام تسجيلكِ بنجاح وسيتم مراجعته قريباً.",
            reply_markup=types.ForceReply(selective=True)
        )

    except Exception as e:
        error_msg = "❌ تعذر إرسال التسجيل. يرجى:"
        if "Forbidden" in str(e):
            error_msg += "\n- التأكد من إضافة البوت كمسؤول"
        elif "Bad Request" in str(e):
            error_msg += "\n- التحقق من اتصال الإنترنت"
        
        bot.reply_to(message, error_msg)
        logging.error(f"Voice processing error: {str(e)}")

if __name__ == '__main__':
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start keepalive thread
    start_keepalive()
    
    try:
        logging.info(f"Starting bot for channel: {CHANNEL_TITLE} (ID: {CHANNEL_ID})")
        
        if check_bot_permissions():
            bot.polling(none_stop=True, interval=2, timeout=60)
        else:
            logging.critical("Bot doesn't have required permissions! Shutting down.")
            
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
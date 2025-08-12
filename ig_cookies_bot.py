import requests
import json
import telegram
from telegram.ext import Updater, CommandHandler

# ===== CONFIGURASI =====
IG_USERNAME = "vinzskieee3"
IG_PASSWORD = "LIMBOTO123"

TELEGRAM_TOKEN = "8404055922:AAFrFQdHnGNRmwSLW4f0F-xXoDclqG_-Rz0"
TELEGRAM_CHAT_ID = "7813060570"

LOGIN_URL = "https://www.instagram.com/accounts/login/ajax/"

# ===== FUNGSI LOGIN IG & AMBIL COOKIES =====
def get_instagram_cookies():
    session = requests.Session()

    # Ambil CSRF token awal
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.instagram.com/"
    })
    session.get("https://www.instagram.com/")
    csrf_token = session.cookies.get("csrftoken")

    # Update headers untuk login
    session.headers.update({
        "X-CSRFToken": csrf_token
    })

    payload = {
        "username": IG_USERNAME,
        "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:0:{IG_PASSWORD}",
        "optIntoOneTap": "false"
    }

    res = session.post(LOGIN_URL, data=payload, allow_redirects=True)

    if res.status_code == 200:
        data = res.json()
        if data.get("authenticated"):
            cookies_dict = session.cookies.get_dict()

            # Simpan JSON
            with open("ig_cookies.json", "w") as f:
                json.dump(cookies_dict, f, indent=4)

            # Format string
            cookies_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])

            return cookies_dict, cookies_str
        else:
            return None, f"❌ Login gagal: {data}"
    else:
        return None, f"❌ Gagal request: {res.status_code} - {res.text}"

# ===== FUNGSI KIRIM KE TELEGRAM =====
def send_to_telegram(cookies_dict, cookies_str):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    # Kirim file JSON
    with open("ig_cookies.json", "rb") as f:
        bot.send_document(chat_id=TELEGRAM_CHAT_ID, document=f, caption="📂 Cookies IG (JSON)")
    # Kirim string cookies
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🍪 Cookies String:\n```\n{cookies_str}\n```", parse_mode="Markdown")

# ===== COMMAND /getcookies =====
def getcookies_command(update, context):
    update.message.reply_text("🔍 Sedang login & ambil cookies IG...")
    cookies_dict, cookies_str = get_instagram_cookies()

    if cookies_dict:
        send_to_telegram(cookies_dict, cookies_str)
        update.message.reply_text("✅ Cookies berhasil diambil & dikirim ke Telegram!")
    else:
        update.message.reply_text(cookies_str)

# ===== MAIN BOT =====
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("getcookies", getcookies_command))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

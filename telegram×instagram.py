#!/usr/bin/env python3
import json
import logging
import tempfile
import os
from PIL import Image
import instaloader
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====
TELEGRAM_TOKEN = "8404055922:AAFrFQdHnGNRmwSLW4f0F-xXoDclqG_-Rz0"
IG_USERNAME = "vinzskieee3"  # Akun IG yang login
COOKIES_FILE = "cookies.json"  # File cookies Instagram
MAX_POSTS = 2
IMG_MAX_SIZE = (1080, 1080)
# ==================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resize_image(path, max_size=IMG_MAX_SIZE):
    """Resize gambar agar tidak terlalu besar sebelum dikirim."""
    try:
        img = Image.open(path)
        img.thumbnail(max_size)
        img.save(path, quality=85)
        logger.info(f"✅ Foto di-resize: {path}")
    except Exception as e:
        logger.warning(f"❌ Gagal resize {path}: {e}")


async def request_new_cookies(update: Update):
    """Kirim pesan ke Telegram untuk minta cookies baru."""
    await update.message.reply_text(
        "⚠️ Cookies Instagram sudah expired atau tidak valid.\n"
        "Silakan kirim file cookies.json yang baru (format JSON minimal: domain, name, value, path)."
    )


def clean_cookies(cookies):
    """Bersihkan cookies agar aman dipakai Instaloader."""
    for cookie in cookies:
        if "path" not in cookie:
            cookie["path"] = "/"
        # Hapus field tanggal kalau None
        for key in ["expiry", "expires", "expirationDate"]:
            if key in cookie and cookie[key] is None:
                del cookie[key]
    return cookies


def login_with_cookies():
    """Login Instagram pakai cookies JSON."""
    loader = instaloader.Instaloader(
        download_videos=False,
        save_metadata=False,
        quiet=True
    )
    try:
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        cookies = clean_cookies(cookies)

        for cookie in cookies:
            if ".instagram.com" in cookie["domain"]:
                loader.context._session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie["domain"],
                    path=cookie["path"]
                )

        # Tes login
        instaloader.Profile.from_username(loader.context, IG_USERNAME)
        logger.info("✅ Login Instagram via cookies sukses!")
        return loader

    except FileNotFoundError:
        raise RuntimeError(f"❌ File {COOKIES_FILE} tidak ditemukan.")
    except instaloader.exceptions.LoginRequiredException:
        raise RuntimeError("⚠️ Cookies expired. Kirim cookies.json baru.")
    except Exception as e:
        raise RuntimeError(f"❌ Gagal login cookies: {e}")


async def stalkakun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ambil info profil IG + foto profil + postingan terbaru."""
    if not context.args:
        await update.message.reply_text("Gunakan: /stalkakun username_ig")
        return

    target_username = context.args[0].lstrip("@")
    msg = await update.message.reply_text(f"🔍 Mengambil data profil @{target_username}...")

    try:
        loader = login_with_cookies()
        profile = instaloader.Profile.from_username(loader.context, target_username)

        text = (
            "🔍 *PROFILING INSTAGRAM*\n"
            f"👤 Username: @{profile.username}\n"
            f"🆔 ID: `{profile.userid}`\n"
            f"📛 Nama: {profile.full_name or '-'}\n"
            f"🔒 Private: {'Ya' if profile.is_private else 'Tidak'}\n"
            f"✅ Verified: {'Ya' if profile.is_verified else 'Tidak'}\n\n"
            "📊 *PROFILE DATA*\n"
            f"Followers: {profile.followers}\n"
            f"Following: {profile.followees}\n"
            f"Postingan: {profile.mediacount}\n\n"
            f"✏️ *Bio:*\n{profile.biography or '-'}"
        )

        tmpdir = tempfile.mkdtemp()
        profile_pic_path = os.path.join(tmpdir, "profile_pic.jpg")
        loader.download_pic(profile_pic_path, profile.profile_pic_url, mtime=None)
        resize_image(profile_pic_path)

        with open(profile_pic_path, "rb") as img:
            await update.message.reply_photo(photo=img, caption=text, parse_mode="Markdown")

        count = 0
        for post in profile.get_posts():
            if count >= MAX_POSTS:
                break
            post_path = os.path.join(tmpdir, f"post_{count+1}.jpg")
            loader.download_pic(post_path, post.url, mtime=None)
            resize_image(post_path)
            with open(post_path, "rb") as img:
                await update.message.reply_photo(photo=img)
            count += 1

        await msg.edit_text(f"✅ Selesai ambil data @{target_username}")

    except instaloader.exceptions.ProfileNotExistsException:
        await msg.edit_text("❌ Username tidak ditemukan.")
    except Exception as e:
        logger.exception(e)
        if "Cookies expired" in str(e):
            await request_new_cookies(update)
        else:
            await msg.edit_text(f"❌ Terjadi error: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Perintah:\n"
        "/stalkakun username — cek profil IG.\n"
        "Kirim file cookies.json untuk update cookies."
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Terima file cookies.json dari user."""
    document = update.message.document
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("❌ Harus file .json")
        return

    file_path = await document.get_file()
    await file_path.download_to_drive(COOKIES_FILE)
    await update.message.reply_text("✅ Cookies.json berhasil disimpan!")


def main():
    app = ApplicationBuilder()\
        .token(TELEGRAM_TOKEN)\
        .read_timeout(60)\
        .write_timeout(60)\
        .connect_timeout(30)\
        .build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stalkakun", stalkakun))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.run_polling()


if __name__ == "__main__":
    main()

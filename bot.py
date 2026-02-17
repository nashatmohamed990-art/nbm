import os
import logging
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────────
#  إعدادات - بتيجي من Environment Variables
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DOWNLOAD_DIR = "/tmp/downloads"      # Railway بيستخدم /tmp للملفات المؤقتة
MAX_FILE_SIZE_MB = 50

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────
#  تنزيل الفيديو
# ─────────────────────────────────────────────
def download_video(url: str) -> str:
    ydl_opts = {
        "format": "bestvideo[ext=mp4][filesize<50M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<50M]/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info:
            info = info["entries"][0]
        filepath = ydl.prepare_filename(info)
        if not os.path.exists(filepath):
            filepath = filepath.rsplit(".", 1)[0] + ".mp4"
        return filepath


# ─────────────────────────────────────────────
#  هاندلرز
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 أهلاً! أنا بوت تنزيل الفيديوهات.\n\n"
        "📌 *المواقع المدعومة:*\n"
        "• Instagram  🟣\n"
        "• Facebook   🔵\n"
        "• TikTok     ⚫\n"
        "• YouTube    🔴\n"
        "• Twitter/X  🐦\n"
        "• وأكتر من 1000 موقع!\n\n"
        "✅ *الاستخدام:* ابعتلي رابط الفيديو مباشرة."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🆘 *المساعدة*\n\n"
        "1️⃣ انسخ رابط الفيديو\n"
        "2️⃣ ابعته هنا\n"
        "3️⃣ استنى شوية وهيتنزل ✅\n\n"
        "⚠️ *ملاحظات:*\n"
        "- الحد الأقصى للحجم 50MB\n"
        "- بعض الفيديوهات الخاصة مش هتتنزل\n"
        "- للإنستجرام الخاص محتاج ملف cookies"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()

    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("❌ ابعتلي رابط صحيح يبدأ بـ https://")
        return

    status_msg = await update.message.reply_text("⏳ بجيب الفيديو... استنى!")
    filepath = None

    try:
        loop = asyncio.get_event_loop()
        filepath = await loop.run_in_executor(None, download_video, url)

        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"❌ الفيديو كبير جداً ({size_mb:.1f}MB).\n"
                f"الحد المسموح {MAX_FILE_SIZE_MB}MB."
            )
            return

        await status_msg.edit_text("📤 بيترفع على تليجرام...")

        with open(filepath, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="✅ تم التنزيل بنجاح! 🎉",
                supports_streaming=True,
            )

        await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"DownloadError: {e}")
        await status_msg.edit_text(
            "❌ مش قادر أنزل الفيديو ده.\n\n"
            "ممكن يكون:\n"
            "• الحساب خاص\n"
            "• الرابط غلط\n"
            "• المحتوى اتحذف"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await status_msg.edit_text("⚠️ حصل خطأ غير متوقع، حاول تاني.")

    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)


# ─────────────────────────────────────────────
#  تشغيل
# ─────────────────────────────────────────────
def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN مش موجود في Environment Variables!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    logger.info("✅ البوت شغال على Railway!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

import logging
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from backend.cracker import ZipCracker
from backend.models import CrackRequest, CrackResult

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handler
UPLOAD, PROCESSING = range(2)

class ZipCrackerBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.active_jobs = {}  # user_id: job
        self.setup_handlers()

    def setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                UPLOAD: [
                    MessageHandler(filters.Document.FileExtension("zip"), self.handle_zip),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.unknown_input),
                ],
                PROCESSING: [
                    CommandHandler("cancel", self.cancel_job),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_job)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("crack", self.start_crack))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message and prompt for ZIP file."""
        user = update.effective_user
        reply_text = (
            f"👋 Hello {user.first_name}!\n\n"
            "I can help you recover passwords for ZIP files. "
            "Please upload your password-protected ZIP file (max 5MB).\n\n"
            "Note: I can only crack passwords up to 10 characters long."
        )
        
        keyboard = [["Crack ZIP Password 🔓"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
        return UPLOAD

    async def start_crack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Alternative entry point via /crack command."""
        await self.start(update, context)

    async def handle_zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the uploaded ZIP file."""
        user = update.effective_user
        file = await update.message.document.get_file()
        
        # Check file size (max 5MB)
        if file.file_size > 5 * 1024 * 1024:
            await update.message.reply_text(
                "❌ File is too large. Maximum size is 5MB."
            )
            return ConversationHandler.END
        
        # Download the file
        file_path = f"tmp/{user.id}_{update.message.document.file_name}"
        await file.download_to_drive(file_path)
        
        # Start cracking
        await update.message.reply_text(
            "✅ File received. Cracking in progress. Please wait...\n"
            "I'll update you every 5 minutes.\n\n"
            "You can cancel with /cancel"
        )
        
        # Create and start cracking job
        cracker = ZipCracker(file_path)
        job = context.job_queue.run_repeating(
            self.send_progress_update,
            interval=300,  # 5 minutes
            first=300,
            user_id=user.id,
            chat_id=update.message.chat_id,
            data={"cracker": cracker, "file_path": file_path},
        )
        
        self.active_jobs[user.id] = {
            "job": job,
            "cracker": cracker,
            "file_path": file_path,
        }
        
        # Run cracking in background
        context.application.create_task(
            self.run_cracking(
                cracker,
                user.id,
                update.message.chat_id,
                file_path,
            )
        )
        
        return PROCESSING

    async def run_cracking(
        self,
        cracker: ZipCracker,
        user_id: int,
        chat_id: int,
        file_path: str,
    ):
        """Run the cracking process in background."""
        try:
            result = cracker.crack()
            
            if result.success:
                message = (
                    "✅ Password Found!\n\n"
                    f"🔑 Password: `{result.password}`\n"
                    f"⏱ Time Taken: {result.time_taken}\n"
                    f"🔁 Total Attempts: {result.attempts:,}"
                )
            else:
                message = (
                    "❌ Unable to crack file within the time limit.\n"
                    "Try again with a simpler password or shorter length."
                )
            
            await self.application.bot.send_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"Cracking failed for user {user_id}: {str(e)}")
            await self.application.bot.send_message(
                chat_id,
                "❌ An error occurred during cracking. Please try again.",
            )
        
        finally:
            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)
            if user_id in self.active_jobs:
                self.active_jobs[user_id]["job"].schedule_removal()
                del self.active_jobs[user_id]

    async def send_progress_update(self, context: ContextTypes.DEFAULT_TYPE):
        """Send periodic progress updates."""
        job = context.job
        cracker = job.data["cracker"]
        
        stats = cracker.get_progress()
        message = (
            "⌛ Cracking Progress Update:\n\n"
            f"⏱ Elapsed Time: {stats['elapsed']}\n"
            f"🔁 Attempts: {stats['attempts']:,}\n"
            f"⚡ Speed: {stats['speed']:,} attempts/sec\n"
            f"🔍 Current Length: {stats['current_length']}\n"
            f"🔠 Current Prefix: {stats['current_prefix']}"
        )
        
        await context.bot.send_message(job.chat_id, message)

    async def cancel_job(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the current cracking job."""
        user = update.effective_user
        if user.id not in self.active_jobs:
            await update.message.reply_text("No active job to cancel.")
            return ConversationHandler.END
        
        job_data = self.active_jobs[user.id]
        job_data["job"].schedule_removal()
        job_data["cracker"].stop()
        
        if os.path.exists(job_data["file_path"]):
            os.remove(job_data["file_path"])
        
        del self.active_jobs[user.id]
        await update.message.reply_text("❌ Cracking job cancelled.")
        return ConversationHandler.END

    async def unknown_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unexpected input."""
        await update.message.reply_text(
            "Please upload a ZIP file or use /cancel to stop."
        )
        return UPLOAD

    def run(self):
        """Run the bot."""
        self.application.run_polling()
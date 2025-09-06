import os
import logging
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.ext import JobQueue
from dotenv import load_dotenv

from src.scraper import MenuScraper
from src.pdf_parser import MenuParser
from src.data_organizer import DataOrganizer

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class KlopasBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.group_id = os.getenv('TELEGRAM_GROUP_ID')
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN nije postavljen u .env fajlu")
            
        self.application = Application.builder().token(self.token).build()
        
        # Komponente za rad sa jelovnikom
        self.scraper = MenuScraper()
        self.parser = MenuParser()
        self.organizer = DataOrganizer()
        
        # Putanja do markdown fajlova
        self.daily_dir = Path("data/daily")
        
    def setup_handlers(self):
        """Postavi sve handlere za bot komande"""
        
        # Komande
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("jelovnik", self.menu_command))
        self.application.add_handler(CommandHandler("sutra", self.tomorrow_command))
        self.application.add_handler(CommandHandler("danas", self.today_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Message handler za mention poruke (@KlopasBOT) - samo u grupama  
        self.application.add_handler(MessageHandler(
            filters.TEXT & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP), 
            self.handle_group_message
        ))
        
        # Message handler za dugmiće sa tastature (samo u privatnom chatu)
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
            self.handle_keyboard_button
        ))
        
        # Callback za inline dugmad
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
    def get_main_keyboard(self):
        """Kreira glavnu tastaturu koja je uvek vidljiva"""
        keyboard = [
            [
                KeyboardButton("🍽️ Danas"),
                KeyboardButton("📅 Sutra")
            ],
            [
                KeyboardButton("🔄 Novi mesec"),
                KeyboardButton("ℹ️ Pomoć")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /start komandu"""
        
        await update.message.reply_text(
            "🍽️ *Klopas Bot - Jelovnik vrtića*\n\n"
            "Dobrodošli! Ovaj bot vam šalje dnevni jelovnik iz vrtića.\n\n"
            "Koristite dugmiće ispod za navigaciju:",
            parse_mode='Markdown',
            reply_markup=self.get_main_keyboard()
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /help komandu"""
        help_text = """
🍽️ *Klopas Bot - Pomoć*

*Dostupne komande:*
/start - Početni meni sa opcijama
/danas - Jelovnik za danas
/sutra - Jelovnik za sutra  
/jelovnik - Prikaži opcije za jelovnik
/help - Ova poruka

*U grupama (tagovi):*
@klopasbot danas - Jelovnik za danas
@klopasbot sutra - Jelovnik za sutra
@klopasbot novi mesec - Preuzmi najnoviji jelovnik
@klopasbot pomoć - Prikaži pomoć

*Dugmići (privatni chat):*
🍽️ Danas - Prikaži današnji jelovnik
📅 Sutra - Prikaži sutrašnji jelovnik
🔄 Novi mesec - Preuzmi najnoviji jelovnik
ℹ️ Pomoć - Ova poruka

*Automatsko slanje:*
Bot automatski šalje jelovnik za sledeći dan svaki radni dan u 20:00h.

*Dugme "Novi mesec":*
Koristi ovo dugme početkom meseca za preuzimanje najnovijeg jelovnika sa sajta vrtića.
        """
        await update.message.reply_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=self.get_main_keyboard()
        )
        
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /jelovnik komandu"""
        keyboard = [
            [
                InlineKeyboardButton("🍽️ Danas", callback_data='today'),
                InlineKeyboardButton("📅 Sutra", callback_data='tomorrow')
            ],
            [
                InlineKeyboardButton("🔄 Novi mesec", callback_data='new_month')
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Izaberite opciju:",
            reply_markup=reply_markup
        )
        
    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /danas komandu"""
        await self.send_menu_for_date(update, datetime.now())
        
    async def tomorrow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /sutra komandu"""
        tomorrow = datetime.now() + timedelta(days=1)
        await self.send_menu_for_date(update, tomorrow)
        
    async def handle_keyboard_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za dugmiće sa tastature"""
        text = update.message.text
        
        if text == "🍽️ Danas":
            await self.send_menu_for_date(update, datetime.now())
        elif text == "📅 Sutra":
            tomorrow = datetime.now() + timedelta(days=1)
            await self.send_menu_for_date(update, tomorrow)
        elif text == "🔄 Novi mesec":
            await self.download_new_month_menu(update)
        elif text == "ℹ️ Pomoć":
            await self.help_command(update, context)
    
    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za mention poruke (@KlopasBOT danas/sutra)"""
        logger.info(f"=== GROUP MESSAGE HANDLER TRIGGERED ===")
        logger.info(f"Chat ID: {update.message.chat.id}")
        logger.info(f"Chat type: {update.message.chat.type}")
        logger.info(f"From user: {update.message.from_user.username if update.message.from_user else 'Unknown'}")
        
        message_text = update.message.text
        if not message_text:
            logger.info("No message text, ignoring")
            return
            
        logger.info(f"Message text: '{message_text}'")
        
        # Proveri da li bot username postoji u mention entities
        bot_mentioned = False
        bot_username = context.bot.username.lower()
        logger.info(f"Bot username: @{bot_username}")
        
        # Proveri mention entities
        if update.message.entities:
            logger.info(f"Found {len(update.message.entities)} entities")
            for entity in update.message.entities:
                logger.info(f"Entity type: {entity.type}, offset: {entity.offset}, length: {entity.length}")
                if entity.type == 'mention':
                    mentioned_username = message_text[entity.offset:entity.offset + entity.length].lower()
                    logger.info(f"Found mention: {mentioned_username}")
                    if mentioned_username == f"@{bot_username}":
                        bot_mentioned = True
                        logger.info("BOT WAS MENTIONED!")
                        break
        else:
            logger.info("No entities in message")
        
        if not bot_mentioned:
            logger.info(f"Bot @{bot_username} not mentioned, ignoring")
            return
            
        logger.info("Bot mentioned! Processing command...")
        message_text_lower = message_text.lower()
            
        # Izvuci komandu iz poruke
        if "danas" in message_text_lower or "today" in message_text_lower:
            await self.send_menu_for_date(update, datetime.now())
        elif "sutra" in message_text_lower or "tomorrow" in message_text_lower:
            tomorrow = datetime.now() + timedelta(days=1)
            await self.send_menu_for_date(update, tomorrow)
        elif "jelovnik" in message_text_lower or "menu" in message_text_lower:
            await self.menu_command(update, context)
        elif "pomoć" in message_text_lower or "help" in message_text_lower:
            await self.help_command(update, context)
        elif "novi mesec" in message_text_lower or "new month" in message_text_lower:
            await self.download_new_month_menu(update)
        else:
            # Ako nema specifičnu komandu, pokaži opcije
            await update.message.reply_text(
                "🍽️ Klopas Bot\n\n"
                "Mogu da vam pomožem sa:\n"
                f"@{bot_username} danas - jelovnik za danas\n"
                f"@{bot_username} sutra - jelovnik za sutra\n"
                f"@{bot_username} novi mesec - preuzmi najnoviji jelovnik\n"
                f"@{bot_username} pomoć - sve dostupne opcije"
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za callback dugmad"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'today':
            await self.send_menu_for_date(update, datetime.now(), is_callback=True)
        elif query.data == 'tomorrow':
            tomorrow = datetime.now() + timedelta(days=1)
            await self.send_menu_for_date(update, tomorrow, is_callback=True)
        elif query.data == 'new_month':
            await self.download_new_month_menu(update, is_callback=True)
            
    async def send_menu_for_date(self, update: Update, date: datetime, is_callback: bool = False):
        """Pošalji jelovnik za određeni datum"""
        
        # Formatiraj datum za ime fajla
        date_str = date.strftime('%Y-%m-%d')
        file_path = self.daily_dir / f"{date_str}.md"
        
        # Proveri da li je radni dan
        if date.weekday() >= 5:  # Subota ili nedelja
            message = "🚫 Za vikend nema jelovnika u vrtiću."
            if is_callback:
                await update.callback_query.message.reply_text(message)
            else:
                await update.message.reply_text(message)
            return
            
        # Proveri da li fajl postoji
        if not file_path.exists():
            message = f"⚠️ Jelovnik za {date.strftime('%d.%m.%Y.')} nije pronađen.\n\n"
            message += "Koristite dugme '🔄 Novi mesec' za preuzimanje najnovijeg jelovnika."
            if is_callback:
                await update.callback_query.message.reply_text(message)
            else:
                await update.message.reply_text(message)
            return
            
        # Pročitaj jelovnik
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Formatiraj poruku
        message = self._format_menu_message(content, date)
        
        # Pošalji poruku
        if is_callback:
            await update.callback_query.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=self.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=self.get_main_keyboard()
            )
            
    def _format_menu_message(self, markdown_content: str, date: datetime) -> str:
        """Formatira markdown sadržaj u Telegram poruku"""
        
        lines = markdown_content.split('\n')
        
        # Dani na srpskom
        days_sr = {
            0: 'Ponedeljak', 1: 'Utorak', 2: 'Sreda',
            3: 'Četvrtak', 4: 'Petak', 5: 'Subota', 6: 'Nedelja'
        }
        
        day_name = days_sr[date.weekday()]
        formatted_date = date.strftime('%d.%m.%Y.')
        
        message = f"🍽️ *Jelovnik za {day_name}, {formatted_date}*\n\n"
        
        current_meal = None
        for line in lines:
            line = line.strip()
            
            if line.startswith('## Doručak'):
                current_meal = '🥐 *Doručak:*\n'
                message += current_meal
            elif line.startswith('## Užina I'):
                current_meal = '🍎 *Užina I:*\n'
                message += '\n' + current_meal
            elif line.startswith('## Ručak'):
                current_meal = '🍲 *Ručak:*\n'
                message += '\n' + current_meal
            elif line.startswith('## Užina II'):
                current_meal = '🍪 *Užina II:*\n'
                message += '\n' + current_meal
            elif line.startswith('- ') and current_meal:
                # Ukloni "- " i dodaj sa boljim formatiranjem
                item = line[2:]
                # Skrati ako je predugačko
                if len(item) > 100:
                    item = item[:100] + '...'
                message += f"   • {item}\n"
                
        return message
        
    async def download_new_month_menu(self, update: Update, is_callback: bool = False):
        """Preuzmi novi jelovnik sa sajta"""
        
        # Pošalji poruku da počinje preuzimanje
        loading_message = "⏳ Preuzimam najnoviji jelovnik sa sajta vrtića..."
        if is_callback:
            msg = await update.callback_query.message.reply_text(loading_message)
        else:
            msg = await update.message.reply_text(loading_message)
            
        try:
            # Preuzmi PDF
            pdf_path = self.scraper.get_current_month_menu()
            
            if not pdf_path:
                await msg.edit_text(
                    "❌ Nije pronađen jelovnik za trenutni mesec na sajtu.\n"
                    "Proverite da li je objavljen na:\n"
                    "https://www.nasaradost.edu.rs/jelovnik/"
                )
                return
                
            # Parsiraj PDF
            menu_data = self.parser.parse_pdf(pdf_path)
            
            if not menu_data:
                await msg.edit_text("❌ Greška pri čitanju PDF fajla.")
                return
                
            # Kreiraj markdown fajlove
            created_files = self.organizer.create_daily_markdown_files(menu_data)
            
            # Kreiraj mesečni sumarni fajl
            current_date = datetime.now()
            self.organizer.create_monthly_summary(
                menu_data,
                current_date.month,
                current_date.year
            )
            
            await msg.edit_text(
                f"✅ *Uspešno preuzet jelovnik!*\n\n"
                f"📄 Parsiran PDF za {current_date.strftime('%B %Y.')}\n"
                f"📁 Kreirano {created_files} dnevnih fajlova\n\n"
                f"Sada možete koristiti komande /danas ili /sutra za prikaz jelovnika.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Greška pri preuzimanju jelovnika: {e}")
            await msg.edit_text(
                "❌ Greška pri preuzimanju jelovnika.\n"
                f"Detalji: {str(e)}"
            )
            
    async def scheduled_daily_menu(self, context: ContextTypes.DEFAULT_TYPE):
        """Funkcija koja se poziva svaki radni dan u 20:00"""
        
        tomorrow = datetime.now() + timedelta(days=1)
        
        # Proveri da li je sutra radni dan
        if tomorrow.weekday() >= 5:  # Vikend
            logger.info("Sutra je vikend, ne šaljem jelovnik")
            return
            
        # Formatiraj datum za ime fajla
        date_str = tomorrow.strftime('%Y-%m-%d')
        file_path = self.daily_dir / f"{date_str}.md"
        
        # Proveri da li fajl postoji
        if not file_path.exists():
            logger.warning(f"Jelovnik za {date_str} ne postoji")
            return
            
        # Pročitaj jelovnik
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Formatiraj poruku
        message = "🔔 *Podsetnik za sutra*\n\n"
        message += self._format_menu_message(content, tomorrow)
        
        # Pošalji u grupu
        if self.group_id:
            try:
                await context.bot.send_message(
                    chat_id=self.group_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"Poslat jelovnik za {date_str} u grupu")
            except Exception as e:
                logger.error(f"Greška pri slanju u grupu: {e}")
                
    def run(self):
        """Pokreni bot"""
        
        # Postavi handlere
        self.setup_handlers()
        
        # Postavi daily job - svaki dan u 20:00 (8 PM)
        job_queue = self.application.job_queue
        job_queue.run_daily(
            self.scheduled_daily_menu,
            time(hour=20, minute=0),  # 20:00
            name='daily_menu_notification'
        )
        logger.info("Scheduler pokrenut - slanje jelovnika svaki dan u 20:00")
        
        # Pokreni bot
        logger.info("Bot pokrenut...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

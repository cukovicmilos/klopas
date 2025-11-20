import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Optional
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.ext import JobQueue
from dotenv import load_dotenv

from src.scraper import MenuScraper
from src.pdf_parser import MenuParser
from src.data_organizer import DataOrganizer
from src.user_stats import UserStatsTracker

load_dotenv()

# Setup log rotation - max 5MB per file, keep 5 backup files
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler with rotation
file_handler = RotatingFileHandler(
    'bot.log', 
    maxBytes=5*1024*1024,  # 5MB
    backupCount=5          # Keep 5 old log files
)
file_handler.setFormatter(log_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Disable verbose logging from httpx (Telegram API requests)
logging.getLogger('httpx').setLevel(logging.WARNING)
# Disable verbose logging from apscheduler
logging.getLogger('apscheduler').setLevel(logging.WARNING)


class KlopasBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN nije postavljen u .env fajlu")
        
        # Admin user ID - samo admin može koristiti "Novi mesec" opciju
        admin_id = os.getenv('TELEGRAM_ADMIN_ID')
        self.admin_id = int(admin_id) if admin_id else None
            
        self.application = Application.builder().token(self.token).build()
        
        # Komponente za rad sa jelovnikom
        self.scraper = MenuScraper()
        self.parser = MenuParser()
        self.organizer = DataOrganizer()
        
        # Tracker za statistiku korisnika
        self.stats_tracker = UserStatsTracker()
        
        # Putanja do markdown fajlova
        self.daily_dir = Path("data/daily")
    
    def _is_admin(self, user_id: int) -> bool:
        """Proveri da li je korisnik admin"""
        return self.admin_id is not None and user_id == self.admin_id
        
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
        
    def _track_user(self, update: Update, action: str = "command"):
        """Helper metoda za praćenje aktivnosti korisnika"""
        try:
            if update.message and update.message.from_user:
                user = update.message.from_user
                self.stats_tracker.track_user_activity(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    action=action
                )
            elif update.callback_query and update.callback_query.from_user:
                user = update.callback_query.from_user
                self.stats_tracker.track_user_activity(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    action="callback"
                )
        except Exception as e:
            logger.error(f"Greška pri praćenju korisnika: {e}")
    
    def get_main_keyboard(self, user_id: Optional[int] = None):
        """Kreira glavnu tastaturu koja je uvek vidljiva"""
        keyboard = [
            [
                KeyboardButton("🍽️ Danas"),
                KeyboardButton("📅 Sutra")
            ]
        ]
        
        # Dodaj "Novi mesec" dugme samo za admina
        if user_id and self._is_admin(user_id):
            keyboard.append([
                KeyboardButton("🔄 Novi mesec"),
                KeyboardButton("⚙️ Podešavanja")
            ])
        else:
            keyboard.append([
                KeyboardButton("⚙️ Podešavanja")
            ])
        
        keyboard.append([
            KeyboardButton("ℹ️ Pomoć")
        ])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /start komandu"""
        self._track_user(update, "start")
        
        user_id = update.message.from_user.id
        await update.message.reply_text(
            "🍽️ *Klopas Bot - Jelovnik vrtića*\n\n"
            "Dobrodošli! Ovaj bot vam šalje dnevni jelovnik iz vrtića.\n\n"
            "Koristite dugmiće ispod za navigaciju:",
            parse_mode='Markdown',
            reply_markup=self.get_main_keyboard(user_id)
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /help komandu"""
        self._track_user(update, "help")
        
        user_id = update.message.from_user.id
        is_admin = self._is_admin(user_id)
        
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
@klopasbot pomoć - Prikaži pomoć

*Dugmići (privatni chat):*
🍽️ Danas - Prikaži današnji jelovnik
📅 Sutra - Prikaži sutrašnji jelovnik
⚙️ Podešavanja - Upravljaj automatskim obaveštenjima
ℹ️ Pomoć - Ova poruka

*Automatsko slanje:*
Bot može da ti automatski šalje jelovnik za sutra svaki radni dan u 20:00h.
Možeš uključiti/isključiti obaveštenja u podešavanjima.
        """
        
        # Dodaj admin informacije ako je korisnik admin
        if is_admin:
            help_text += """
*Admin opcije:*
🔄 Novi mesec - Preuzmi najnoviji jelovnik sa sajta vrtića (samo za admina)
            """
        
        await update.message.reply_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=self.get_main_keyboard(user_id)
        )
        
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /jelovnik komandu"""
        self._track_user(update, "menu")
        
        user_id = update.message.from_user.id
        
        keyboard = [
            [
                InlineKeyboardButton("🍽️ Danas", callback_data='today'),
                InlineKeyboardButton("📅 Sutra", callback_data='tomorrow')
            ]
        ]
        
        # Dodaj "Novi mesec" dugme samo za admina
        if self._is_admin(user_id):
            keyboard.append([
                InlineKeyboardButton("🔄 Novi mesec", callback_data='new_month')
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Izaberite opciju:",
            reply_markup=reply_markup
        )
        
    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /danas komandu"""
        self._track_user(update, "today")
        await self.send_menu_for_date(update, datetime.now())
        
    async def tomorrow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za /sutra komandu"""
        self._track_user(update, "tomorrow")
        tomorrow = datetime.now() + timedelta(days=1)
        await self.send_menu_for_date(update, tomorrow)
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za podešavanja"""
        self._track_user(update, "settings")
        
        user_id = update.message.from_user.id
        notifications = self.stats_tracker.get_notifications(user_id)
        
        # Emoji za status
        status_emoji = "🔔" if notifications else "🔕"
        button_text = "🔕 Isključi obaveštenja" if notifications else "🔔 Uključi obaveštenja"
        
        keyboard = [
            [InlineKeyboardButton(button_text, callback_data='toggle_notifications')]
        ]
        
        message = (
            f"⚙️ *Podešavanja*\n\n"
            f"{status_emoji} *Automatska obaveštenja:* {'Uključena' if notifications else 'Isključena'}\n\n"
            f"Bot šalje jelovnik za sutra svaki radni dan u 20:00h."
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        
    async def handle_keyboard_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za dugmiće sa tastature"""
        self._track_user(update, "keyboard")
        text = update.message.text
        user_id = update.message.from_user.id
        
        if text == "🍽️ Danas":
            await self.send_menu_for_date(update, datetime.now())
        elif text == "📅 Sutra":
            tomorrow = datetime.now() + timedelta(days=1)
            await self.send_menu_for_date(update, tomorrow)
        elif text == "🔄 Novi mesec":
            # Proveri da li je korisnik admin
            if not self._is_admin(user_id):
                await update.message.reply_text(
                    "⛔ Ova opcija je dostupna samo za administratora bota.",
                    reply_markup=self.get_main_keyboard(user_id)
                )
                return
            await self.download_new_month_menu(update)
        elif text == "⚙️ Podešavanja":
            await self.settings_command(update, context)
        elif text == "ℹ️ Pomoć":
            await self.help_command(update, context)
    
    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za mention poruke (@KlopasBOT danas/sutra)"""
        self._track_user(update, "group_mention")
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
        user_id = update.message.from_user.id
        
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
            # Proveri da li je korisnik admin
            if not self._is_admin(user_id):
                await update.message.reply_text(
                    "⛔ Ova opcija je dostupna samo za administratora bota."
                )
                return
            await self.download_new_month_menu(update)
        else:
            # Ako nema specifičnu komandu, pokaži opcije
            help_text = (
                "🍽️ Klopas Bot\n\n"
                "Mogu da vam pomožem sa:\n"
                f"@{bot_username} danas - jelovnik za danas\n"
                f"@{bot_username} sutra - jelovnik za sutra\n"
                f"@{bot_username} pomoć - sve dostupne opcije"
            )
            
            # Dodaj admin opcije ako je korisnik admin
            if self._is_admin(user_id):
                help_text += f"\n@{bot_username} novi mesec - preuzmi najnoviji jelovnik (samo admin)"
                
            await update.message.reply_text(help_text)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler za callback dugmad"""
        self._track_user(update, "callback")
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == 'today':
            await self.send_menu_for_date(update, datetime.now(), is_callback=True)
        elif query.data == 'tomorrow':
            tomorrow = datetime.now() + timedelta(days=1)
            await self.send_menu_for_date(update, tomorrow, is_callback=True)
        elif query.data == 'new_month':
            # Proveri da li je korisnik admin
            if not self._is_admin(user_id):
                await query.message.reply_text(
                    "⛔ Ova opcija je dostupna samo za administratora bota.",
                    reply_markup=self.get_main_keyboard(user_id)
                )
                return
            await self.download_new_month_menu(update, is_callback=True)
        elif query.data == 'toggle_notifications':
            await self.toggle_notifications_callback(update, context)
    
    async def toggle_notifications_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle notifications za korisnika"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Toggle status
        current = self.stats_tracker.get_notifications(user_id)
        new_status = not current
        self.stats_tracker.set_notifications(user_id, new_status)
        
        # Ažuriraj poruku
        status_emoji = "🔔" if new_status else "🔕"
        button_text = "🔕 Isključi obaveštenja" if new_status else "🔔 Uključi obaveštenja"
        
        keyboard = [
            [InlineKeyboardButton(button_text, callback_data='toggle_notifications')]
        ]
        
        message = (
            f"⚙️ *Podešavanja*\n\n"
            f"{status_emoji} *Automatska obaveštenja:* {'Uključena' if new_status else 'Isključena'}\n\n"
            f"Bot šalje jelovnik za sutra svaki radni dan u 20:00h."
        )
        
        await query.message.edit_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await query.answer(
            f"✅ Obaveštenja {'uključena' if new_status else 'isključena'}!"
        )
            
    async def send_menu_for_date(self, update: Update, date: datetime, is_callback: bool = False):
        """Pošalji jelovnik za određeni datum"""
        
        # Dobavi user_id za tastaturu
        if is_callback:
            user_id = update.callback_query.from_user.id
        else:
            user_id = update.message.from_user.id
        
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
            if self._is_admin(user_id):
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
                reply_markup=self.get_main_keyboard(user_id)
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=self.get_main_keyboard(user_id)
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
            
    async def update_bot_short_description(self, context: ContextTypes.DEFAULT_TYPE):
        """Ažuriraj short description bota sa statistikom aktivnih korisnika"""
        try:
            stats = self.stats_tracker.get_current_month_stats()
            current_active = stats["current_month_active"]
            peak_active = stats["peak_monthly_active"]
            
            # Koristi trenutni mesečni ili peak broj korisnika
            user_count = max(current_active, peak_active)
            
            if user_count == 0:
                description = "Jelovnik vrtića Naša Radost Subotica - svaki dan!"
            elif user_count == 1:
                description = "Jelovnik vrtića Naša Radost Subotica - 1 aktivan korisnik"
            else:
                description = f"Jelovnik vrtića Naša Radost Subotica - {user_count} aktivnih korisnika"
            
            # Ažuriraj short description
            await context.bot.set_my_short_description(
                short_description=description
            )
            
            logger.info(f"✅ Ažuriran bot short description: '{description}'")
            
        except Exception as e:
            logger.error(f"❌ Greška pri ažuriranju short description: {e}")
    
    async def check_and_send_menu(self, context: ContextTypes.DEFAULT_TYPE):
        """Proverava svakih 5 minuta da li je vreme (19:55-20:05) za slanje jelovnika"""
        import pytz
        belgrade_tz = pytz.timezone('Europe/Belgrade')
        now = datetime.now(belgrade_tz)

        # Proveri da li je između 19:55 i 20:05
        if not (19 <= now.hour <= 20):
            return  # Nije vreme

        if now.hour == 19 and now.minute < 55:
            return  # Pre 19:55

        if now.hour == 20 and now.minute > 5:
            return  # Posle 20:05

        # Proveri da li je već poslato danas
        today_str = now.strftime('%Y-%m-%d')
        marker_file = Path(f"data/.sent_{today_str}")

        if marker_file.exists():
            return  # Već poslato danas

        logger.info(f"⏰ Vreme je {now.strftime('%H:%M')} - vreme za slanje jelovnika!")

        # Pozovi funkciju za slanje i proveri uspešnost
        success = await self.scheduled_daily_menu(context)

        # Označi da je poslato SAMO ako je slanje bilo uspešno
        if success:
            marker_file.touch()
            logger.info(f"✅ Marker postavljen: {marker_file}")
        else:
            logger.warning(f"⚠️ Slanje nije uspelo, marker NIJE postavljen. Ponoviću pokušaj u sledećem ciklusu.")

    async def scheduled_daily_menu(self, context: ContextTypes.DEFAULT_TYPE):
        """Funkcija koja se poziva svaki radni dan u 20:00
        Šalje jelovnik svim aktivnim korisnicima u privatnom chatu

        Returns:
            bool: True ako je poruka uspešno poslata bar jednom korisniku, False inače
        """

        logger.info("=" * 50)
        logger.info("SCHEDULER TRIGGERED - scheduled_daily_menu started")
        logger.info("=" * 50)

        now = datetime.now()
        tomorrow = now + timedelta(days=1)

        logger.info(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Tomorrow: {tomorrow.strftime('%Y-%m-%d %H:%M:%S')} (weekday: {tomorrow.weekday()})")

        # Proveri da li je sutra radni dan
        if tomorrow.weekday() >= 5:  # Vikend
            logger.info("Sutra je vikend, ne šaljem jelovnik")
            return False

        # Formatiraj datum za ime fajla
        date_str = tomorrow.strftime('%Y-%m-%d')
        file_path = self.daily_dir / f"{date_str}.md"

        logger.info(f"Looking for menu file: {file_path}")

        # Proveri da li fajl postoji
        if not file_path.exists():
            logger.warning(f"Jelovnik za {date_str} ne postoji")
            return False

        logger.info(f"Menu file found! Reading content...")

        # Pročitaj jelovnik
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.info(f"Menu content read ({len(content)} chars)")

        # Formatiraj poruku
        message = "🔔 *Podsetnik za sutra*\n\n"
        message += self._format_menu_message(content, tomorrow)

        logger.info(f"Message formatted ({len(message)} chars)")

        # Dobavi korisnike sa uključenim notifikacijama
        users_with_notifications = self.stats_tracker.get_users_with_notifications_enabled()
        logger.info(f"Found {len(users_with_notifications)} users with notifications enabled")

        if not users_with_notifications:
            logger.warning("Nema korisnika sa uključenim notifikacijama")
            return False

        # Pošalji korisnicima sa uključenim notifikacijama
        success_count = 0
        fail_count = 0

        for user_id in users_with_notifications:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
                success_count += 1
                logger.info(f"✅ Poslato korisniku {user_id}")
            except Exception as e:
                fail_count += 1
                logger.warning(f"❌ Greška pri slanju korisniku {user_id}: {e}")

        logger.info(f"SLANJE ZAVRŠENO: {success_count} uspešno, {fail_count} neuspešno")
        logger.info("=" * 50)

        # Uspeh ako je bar jednom korisniku poslato
        return success_count > 0


    def run(self):
        """Pokreni bot"""
        
        # Postavi handlere
        self.setup_handlers()
        
        # Postavi check job - provera svakih 5 minuta da li treba poslati jelovnik
        # Ovo je pouzdanije od run_daily jer radi i kada se sistem probudi iz sleep-a
        job_queue = self.application.job_queue

        job_queue.run_repeating(
            self.check_and_send_menu,
            interval=300,  # 5 minuta
            first=10,      # Pokreni prvi put nakon 10 sekundi
            name='menu_check_repeating'
        )

        # Postavi job za ažuriranje short description - jednom dnevno u 9:00
        job_queue.run_daily(
            self.update_bot_short_description,
            time=time(hour=9, minute=0),
            name='update_description_daily'
        )
        
        # Ažuriraj short description odmah pri pokretanju
        job_queue.run_once(
            self.update_bot_short_description,
            when=5  # Nakon 5 sekundi
        )

        logger.info("Scheduler pokrenut - provera svakih 5 minuta da li je 20:00 za slanje jelovnika")
        logger.info("Scheduler pokrenut - ažuriranje short description svaki dan u 9:00")

        # Pokreni bot sa error handling
        logger.info("Bot pokrenut...")
        self._run_bot_with_retry()

    def _run_bot_with_retry(self):
        """Pokreni bot sa automatskim retry logikom"""
        import time
        retry_count = 0
        max_retries = 5
        base_delay = 30  # sekundi

        while retry_count < max_retries:
            try:
                logger.info(f"Pokušaj pokretanja bota #{retry_count + 1}")
                self.application.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,  # Ignoriši stare poruke
                    connect_timeout=60,  # 60 sekundi timeout za connection
                    read_timeout=60,     # 60 sekundi timeout za čitanje
                    write_timeout=60     # 60 sekundi timeout za pisanje
                )
                # Ako dođemo do ovde, bot je uspešno završen
                logger.info("Bot je uspešno završen")
                break

            except Exception as e:
                retry_count += 1
                delay = base_delay * (2 ** (retry_count - 1))  # Exponential backoff

                logger.error(f"Greška pri radu bota (pokušaj {retry_count}/{max_retries}): {e}")

                if retry_count < max_retries:
                    logger.info(f"Restartovanje bota za {delay} sekundi...")
                    time.sleep(delay)
                else:
                    logger.error("Maksimalni broj pokušaja dostignut. Bot se zaustavlja.")
                    raise

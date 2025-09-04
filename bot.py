#!/usr/bin/env python3
"""
Klopas Bot - Telegram bot za jelovnik vrtića
"""

import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Dodaj src direktorijum u Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.telegram_bot import KlopasBot

# Učitaj environment varijable
load_dotenv()

# Postavi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def main():
    """Glavna funkcija za pokretanje bota"""
    
    # Proveri da li je token postavljen
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        logger.error(
            "TELEGRAM_BOT_TOKEN nije postavljen!\n"
            "Kreiraj .env fajl na osnovu .env.example i postavi token."
        )
        sys.exit(1)
        
    try:
        # Kreiraj i pokreni bot
        bot = KlopasBot()
        logger.info("Pokrećem Klopas Bot...")
        bot.run()
        
    except Exception as e:
        logger.error(f"Greška pri pokretanju bota: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
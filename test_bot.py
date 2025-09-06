#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from telegram.ext import Application

load_dotenv()

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("TELEGRAM_BOT_TOKEN nije postavljen!")
        return
    
    print(f"Token: {token[:10]}...")
    
    try:
        application = Application.builder().token(token).build()
        print("Application uspešno kreiran!")
        print("Bot test prošao uspešno!")
    except Exception as e:
        print(f"Greška: {e}")

if __name__ == "__main__":
    main()

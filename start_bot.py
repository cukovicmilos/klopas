#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

async def clear_webhook_and_start():
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Explicit webhook deletion
    bot = Bot(token=token)
    try:
        result = await bot.delete_webhook(drop_pending_updates=True)
        print(f"Webhook cleared: {result}")
        await bot.close()
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Now start the actual bot
        from bot import main
        main()
        
    except Exception as e:
        print(f"Error clearing webhook: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(clear_webhook_and_start())

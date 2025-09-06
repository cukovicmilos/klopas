#!/usr/bin/env python3
import os
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Simulacija handle_group_message funkcije
async def test_handle_group_message():
    # Simulacija poruke "@KlopasBOT danas"
    message_text = "@KlopasBOT danas"
    bot_username = "klopasbot"  # Ili kako god se zove bot
    
    print(f"Testing message: '{message_text}'")
    print(f"Bot username: @{bot_username}")
    
    # Logika iz handle_group_message
    bot_mentioned = False
    
    # Simulacija mention entity
    # U realnoj telegram porući, mention ima entity tipa 'mention'
    # sa offset=0 i length=10 za "@KlopasBOT"
    mention_offset = 0
    mention_length = len("@KlopasBOT")
    mentioned_username = message_text[mention_offset:mention_offset + mention_length].lower()
    
    print(f"Found mention: {mentioned_username}")
    if mentioned_username == f"@{bot_username}":
        bot_mentioned = True
        print("Bot mentioned!")
    else:
        print(f"Bot @{bot_username} not mentioned")
    
    if not bot_mentioned:
        print("Would ignore message")
        return
    
    print("Would process command...")
    message_text_lower = message_text.lower()
    
    if "danas" in message_text_lower or "today" in message_text_lower:
        print("Would send today's menu")
        
        # Test da li postoji fajl za danas
        today = datetime.now()
        date_str = today.strftime('%Y-%m-%d')
        file_path = Path("data/daily") / f"{date_str}.md"
        
        if file_path.exists():
            print(f"Menu file exists: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print("Content preview:")
            print(content[:200] + "...")
        else:
            print(f"Menu file not found: {file_path}")

if __name__ == "__main__":
    asyncio.run(test_handle_group_message())
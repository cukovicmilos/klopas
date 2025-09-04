#!/usr/bin/env python3
import logging
from pathlib import Path
from datetime import datetime
import sys

from src.scraper import MenuScraper
from src.pdf_parser import MenuParser
from src.data_organizer import DataOrganizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/klopas.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def process_current_month_menu():
    """Glavni proces - preuzmi PDF, parsiraj ga i kreiraj markdown fajlove"""
    
    try:
        Path("logs").mkdir(exist_ok=True)
        
        print("\n" + "="*60)
        print("KLOPAS - Procesiranje jelovnika za tekući mesec")
        print("="*60 + "\n")
        
        current_date = datetime.now()
        month_names = {
            1: 'januar', 2: 'februar', 3: 'mart', 4: 'april',
            5: 'maj', 6: 'jun', 7: 'jul', 8: 'avgust',
            9: 'septembar', 10: 'oktobar', 11: 'novembar', 12: 'decembar'
        }
        
        print(f"Tekući mesec: {month_names[current_date.month].capitalize()} {current_date.year}")
        print("-" * 60)
        
        print("\n📥 KORAK 1: Preuzimanje PDF-a sa sajta...")
        scraper = MenuScraper()
        pdf_path = scraper.get_current_month_menu()
        
        if not pdf_path:
            logger.error("❌ PDF nije pronađen ili preuzet!")
            print("\n⚠️  PDF za tekući mesec nije dostupan na sajtu.")
            print("Proverite da li je jelovnik objavljen na:")
            print("https://www.nasaradost.edu.rs/jelovnik/")
            return False
        
        print(f"✅ PDF uspešno preuzet: {pdf_path}")
        
        print("\n📄 KORAK 2: Parsiranje PDF fajla...")
        parser = MenuParser()
        menu_data = parser.parse_pdf(pdf_path)
        
        if not menu_data:
            logger.error("❌ Neuspešno parsiranje PDF-a!")
            print("\n⚠️  PDF ne sadrži prepoznatljive podatke o jelovniku.")
            return False
            
        print(f"✅ Pronađeno {len(menu_data)} radnih dana u jelovniku")
        
        print("\n📝 KORAK 3: Kreiranje markdown fajlova...")
        organizer = DataOrganizer()
        
        created_files = organizer.create_daily_markdown_files(menu_data)
        print(f"✅ Kreirano {created_files} dnevnih markdown fajlova")
        
        monthly_file = organizer.create_monthly_summary(
            menu_data, 
            current_date.month, 
            current_date.year
        )
        print(f"✅ Kreiran mesečni sumarni fajl: {monthly_file}")
        
        print("\n" + "="*60)
        print("✨ USPEŠNO ZAVRŠENO!")
        print("="*60)
        
        print(f"\n📁 Fajlovi su sačuvani u:")
        print(f"   - Dnevni fajlovi: data/daily/")
        print(f"   - Mesečni sumar: {monthly_file}")
        print(f"   - PDF original: {pdf_path}\n")
        
        print("📋 Primer strukture jednog dana:")
        first_date = sorted(menu_data.keys())[0] if menu_data else None
        if first_date:
            example_data = menu_data[first_date]
            print(f"\n   Dan: {example_data['day_name'].capitalize()}, {first_date}")
            if example_data['meals']:
                for meal_type, items in example_data['meals'].items():
                    if items:
                        meal_name = meal_type.replace('_', ' ').upper()
                        print(f"   - {meal_name}: {items[0][:50]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Kritična greška: {e}")
        print(f"\n❌ Greška u procesiranju: {e}")
        return False


if __name__ == "__main__":
    success = process_current_month_menu()
    sys.exit(0 if success else 1)
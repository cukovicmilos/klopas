from pathlib import Path
import logging
from typing import Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataOrganizer:
    def __init__(self, output_dir: Path = Path("data/daily")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_daily_markdown_files(self, menu_data: Dict[str, Dict]) -> int:
        """Kreira individualne Markdown fajlove za svaki dan"""
        created_files = 0
        
        for date_str, day_data in menu_data.items():
            try:
                self._create_single_day_file(date_str, day_data)
                created_files += 1
            except Exception as e:
                logger.error(f"Greška pri kreiranju fajla za {date_str}: {e}")
                
        logger.info(f"Kreirano {created_files} markdown fajlova")
        return created_files
    
    def _create_single_day_file(self, date_str: str, day_data: Dict):
        """Kreira pojedinačni markdown fajl za jedan dan"""
        # Koristi datum u formatu YYYY-MM-DD za ime fajla
        if date_str.startswith('20'):  # Ako je već u YYYY-MM-DD formatu
            filename = f"{date_str}.md"
        else:  # Ako je u DD.MM.YYYY formatu
            filename = f"{date_str}.md"
        filepath = self.output_dir / filename
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = self._format_date_serbian(date_obj)
        except:
            formatted_date = date_str
            
        day_name = day_data.get('day_name', '').capitalize()
        
        content = f"# Jelovnik - {day_name}, {formatted_date}\n\n"
        
        meals = day_data.get('meals', {})
        
        if meals.get('doručak'):
            content += "## Doručak\n"
            for item in meals['doručak']:
                if item:
                    content += f"- {item}\n"
            content += "\n"
            
        if meals.get('užina_i'):
            content += "## Užina I\n"
            for item in meals['užina_i']:
                if item:
                    content += f"- {item}\n"
            content += "\n"
            
        if meals.get('ručak'):
            content += "## Ručak\n"
            for item in meals['ručak']:
                if item:
                    content += f"- {item}\n"
            content += "\n"
            
        if meals.get('užina_ii'):
            content += "## Užina II\n"
            for item in meals['užina_ii']:
                if item:
                    content += f"- {item}\n"
            content += "\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Kreiran fajl: {filepath}")
        
    def _format_date_serbian(self, date_obj: datetime) -> str:
        """Formatira datum na srpski način"""
        month_names = {
            1: 'januar', 2: 'februar', 3: 'mart', 4: 'april',
            5: 'maj', 6: 'jun', 7: 'jul', 8: 'avgust',
            9: 'septembar', 10: 'oktobar', 11: 'novembar', 12: 'decembar'
        }
        
        day = date_obj.day
        month = month_names[date_obj.month]
        year = date_obj.year
        
        return f"{day}. {month} {year}."
    
    def create_monthly_summary(self, menu_data: Dict[str, Dict], month: int, year: int) -> Path:
        """Kreira sumarni markdown fajl za ceo mesec"""
        filename = f"{year:04d}-{month:02d}.md"
        filepath = self.output_dir.parent / filename
        
        month_names = {
            1: 'Januar', 2: 'Februar', 3: 'Mart', 4: 'April',
            5: 'Maj', 6: 'Jun', 7: 'Jul', 8: 'Avgust',
            9: 'Septembar', 10: 'Oktobar', 11: 'Novembar', 12: 'Decembar'
        }
        
        content = f"# Jelovnik - {month_names[month]} {year}\n\n"
        
        sorted_dates = sorted(menu_data.keys())
        
        for date_str in sorted_dates:
            day_data = menu_data[date_str]
            
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                if date_obj.month != month or date_obj.year != year:
                    continue
                    
                formatted_date = self._format_date_serbian(date_obj)
                day_name = day_data.get('day_name', '').upper()
                
                content += f"## {day_name} {formatted_date}\n\n"
                
                meals = day_data.get('meals', {})
                
                if meals.get('doručak'):
                    content += f"**DORUČAK**: {', '.join(meals['doručak'])}\n\n"
                    
                if meals.get('užina_i'):
                    content += f"**UŽINA I**: {', '.join(meals['užina_i'])}\n\n"
                    
                if meals.get('ručak'):
                    content += f"**RUČAK**: {', '.join(meals['ručak'])}\n\n"
                    
                if meals.get('užina_ii'):
                    content += f"**UŽINA II**: {', '.join(meals['užina_ii'])}\n\n"
                    
                content += "---\n\n"
                
            except Exception as e:
                logger.error(f"Greška pri obradi datuma {date_str}: {e}")
                
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Kreiran mesečni sumarni fajl: {filepath}")
        return filepath
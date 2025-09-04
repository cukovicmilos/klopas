import pdfplumber
import PyPDF2
from pathlib import Path
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MenuParser:
    def __init__(self):
        self.month_names_sr = {
            'januar': 1, 'februar': 2, 'mart': 3, 'april': 4,
            'maj': 5, 'jun': 6, 'jul': 7, 'avgust': 8,
            'septembar': 9, 'oktobar': 10, 'novembar': 11, 'decembar': 12
        }
        self.day_names = {
            'ponedeljak': 1, 'utorak': 2, 'sreda': 3, 
            'četvrtak': 4, 'petak': 5
        }
        
    def parse_pdf(self, pdf_path: Path) -> Dict[str, Dict]:
        """Parsira PDF koristeći tabelarnu strukturu"""
        menu_data = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Obrađujem stranicu {page_num + 1}")
                    
                    # Ekstraktuj tabele sa stranice
                    tables = page.extract_tables()
                    
                    if not tables:
                        table = page.extract_table()
                        if table:
                            tables = [table]
                    
                    # Obradi svaku tabelu
                    for table in tables:
                        if table:
                            self._parse_table(table, menu_data)
                
                logger.info(f"Uspešno parsirano {len(menu_data)} dana")
                
        except Exception as e:
            logger.error(f"Greška pri parsiranju PDF-a: {e}")
            
        return menu_data
    
    def _parse_table(self, table: List[List[str]], menu_data: Dict):
        """Parsira tabelu - svaki red je jedan dan"""
        
        for row in table:
            if not row or len(row) < 2:
                continue
                
            # Prva kolona sadrži dan, datum i obroke
            meals_column = row[0] if row[0] else ""
            # Druga kolona sadrži sastojke (koje ćemo ignorisati za sada)
            ingredients_column = row[1] if len(row) > 1 and row[1] else ""
            
            if not meals_column:
                continue
            
            # Parsira podatke iz prve kolone
            day_data = self._parse_day_column(meals_column, ingredients_column)
            
            if day_data and day_data.get('date'):
                menu_data[day_data['date']] = day_data
    
    def _parse_day_column(self, meals_text: str, ingredients_text: str) -> Optional[Dict]:
        """Parsira kolonu sa danom i obrocima"""
        
        lines = meals_text.split('\n')
        
        # Pronađi dan i datum
        day_pattern = r'(PONEDELJAK|UTORAK|SREDA|ČETVRTAK|PETAK)\s+(\d{1,2}\.\d{1,2}\.\d{4})'
        
        day_name = None
        date_str = None
        
        for line in lines:
            day_match = re.search(day_pattern, line, re.IGNORECASE)
            if day_match:
                day_name = day_match.group(1).lower()
                date_str = day_match.group(2).rstrip('.')
                break
        
        if not day_name or not date_str:
            return None
        
        # Konvertuj datum u YYYY-MM-DD format
        try:
            date_obj = datetime.strptime(date_str, '%d.%m.%Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')
        except:
            formatted_date = date_str
        
        # Ekstraktuj obroke
        meals = {
            'doručak': [],
            'užina_i': [],
            'ručak': [],
            'užina_ii': []
        }
        
        current_meal = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # Detektuj tip obroka
            if 'doručak' in line_lower:
                current_meal = 'doručak'
                content = self._extract_meal_from_line(line, 'doručak')
                if content:
                    meals['doručak'] = [content]
                    
            elif 'užina i' in line_lower and 'užina ii' not in line_lower:
                current_meal = 'užina_i'
                content = self._extract_meal_from_line(line, 'užina i')
                if content:
                    meals['užina_i'] = [content]
                    
            elif 'ručak' in line_lower:
                current_meal = 'ručak'
                content = self._extract_meal_from_line(line, 'ručak')
                if content:
                    meals['ručak'] = [content]
                    
            elif 'užina ii' in line_lower:
                current_meal = 'užina_ii'
                content = self._extract_meal_from_line(line, 'užina ii')
                if content:
                    meals['užina_ii'] = [content]
        
        # Dodaj glavna jela iz kolone sa sastojcima (prva linija svakog jela)
        if ingredients_text:
            ingredient_lines = ingredients_text.split('\n')
            
            # Prva linija je obično naziv glavnog jela
            main_dishes = []
            for line in ingredient_lines:
                line = line.strip()
                if line and not any(word in line.lower() for word in 
                                   ['brašno', 'ulje', 'so', 'šećer', 'mleko', 
                                    'jaje', 'dodatak', 'paprika', 'crni luk', 
                                    'beli luk', 'voda', 'peršun']):
                    # Ovo je verovatno naziv jela, ne sastojak
                    if all(c.isupper() or c.isspace() for c in line):
                        main_dishes.append(line)
            
            # Dodaj glavna jela ručku ako postoje
            if main_dishes and meals['ručak']:
                # Dodaj naziv glavnog jela na početak opisa ručka
                for dish in main_dishes[:1]:  # Uzmi samo prvo glavno jelo
                    if dish not in meals['ručak'][0]:
                        meals['ručak'][0] = f"{dish} - {meals['ručak'][0]}"
        
        return {
            'day_name': day_name,
            'date': formatted_date,
            'meals': meals
        }
    
    def _extract_meal_from_line(self, line: str, meal_type: str) -> str:
        """Ekstraktuje sadržaj obroka iz linije"""
        line_lower = line.lower()
        
        # Pronađi poziciju meal_type u liniji
        idx = line_lower.find(meal_type)
        if idx != -1:
            # Uzmi sve nakon meal_type
            content = line[idx + len(meal_type):].strip()
            # Ukloni interpunkciju na početku
            content = re.sub(r'^[–\-\s:]+', '', content)
            return content
        
        return ""
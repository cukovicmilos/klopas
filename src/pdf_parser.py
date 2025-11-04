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
            if not row or len(row) < 1:
                continue

            # Prva kolona sadrži dan, datum i obroke - to je sve što nam treba
            meals_column = row[0] if row[0] else ""

            if not meals_column:
                continue

            # Parsira podatke samo iz leve kolone (ignorišemo desnu kolonu potpuno)
            day_data = self._parse_day_column(meals_column)

            if day_data and day_data.get('date'):
                menu_data[day_data['date']] = day_data
    
    def _parse_day_column(self, meals_text: str) -> Optional[Dict]:
        """Parsira kolonu sa danom i obrocima - samo leva strana PDF-a"""

        # Pronađi dan i datum
        day_pattern = r'(PONEDELJAK|UTORAK|SREDA|ČETVRTAK|PETAK)\s+(\d{1,2}\.\d{1,2}\.\d{4})'
        day_match = re.search(day_pattern, meals_text, re.IGNORECASE)

        if not day_match:
            return None

        day_name = day_match.group(1).lower()
        date_str = day_match.group(2).rstrip('.')

        # Konvertuj datum u YYYY-MM-DD format
        try:
            date_obj = datetime.strptime(date_str, '%d.%m.%Y')
            formatted_date = date_obj.strftime('%Y-%m-%d')
        except:
            return None

        # Ekstraktuj obroke koristeći regex da nađemo pozicije svih obroka
        # Ovo omogućava da uhvatimo sadržaj koji se prostire na više linija
        # VAŽNO: Koristimo \b za word boundary da izbegnemo da "RUČAK" matchuje "DORUČAK"
        doručak_pattern = r'\bDORUČAK\s*[–-]\s*(.+?)(?=UŽINA\s*I|$)'
        užina_i_pattern = r'\bUŽINA\s*I\s*[–-]\s*(.+?)(?=\bRUČAK|$)'
        ručak_pattern = r'\bRUČAK\s*[–-]\s*(.+?)(?=UŽINA\s*II|$)'
        užina_ii_pattern = r'\bUŽINA\s*II\s*[–-]\s*(.+?)(?=PONEDELJAK|UTORAK|SREDA|ČETVRTAK|PETAK|$)'

        meals = {
            'doručak': [],
            'užina_i': [],
            'ručak': [],
            'užina_ii': []
        }

        # Ekstraktuj svaki obrok
        doručak_match = re.search(doručak_pattern, meals_text, re.IGNORECASE | re.DOTALL)
        if doručak_match:
            content = self._clean_meal_content(doručak_match.group(1))
            if content:
                meals['doručak'] = [content]

        užina_i_match = re.search(užina_i_pattern, meals_text, re.IGNORECASE | re.DOTALL)
        if užina_i_match:
            content = self._clean_meal_content(užina_i_match.group(1))
            if content:
                meals['užina_i'] = [content]

        ručak_match = re.search(ručak_pattern, meals_text, re.IGNORECASE | re.DOTALL)
        if ručak_match:
            content = self._clean_meal_content(ručak_match.group(1))
            if content:
                meals['ručak'] = [content]

        užina_ii_match = re.search(užina_ii_pattern, meals_text, re.IGNORECASE | re.DOTALL)
        if užina_ii_match:
            content = self._clean_meal_content(užina_ii_match.group(1))
            if content:
                meals['užina_ii'] = [content]

        return {
            'day_name': day_name,
            'date': formatted_date,
            'meals': meals
        }

    def _clean_meal_content(self, content: str) -> str:
        """Očisti sadržaj obroka od višak whitespace-a i newline-ova"""
        # Zameni višestruke spaces i newlines sa jednim space-om
        content = re.sub(r'\s+', ' ', content)
        # Ukloni whitespace na početku i kraju
        content = content.strip()
        # Ukloni trailing zareze i crtice
        content = content.rstrip(',-–')
        return content
    
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
import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path
from datetime import datetime
import logging
import re
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MenuScraper:
    def __init__(self, base_url: str = "https://www.nasaradost.edu.rs/jelovnik/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def find_current_month_pdf_url(self) -> Optional[str]:
        """Pronađi URL PDF-a za trenutni mesec - prvi koji ima 'jelovnik' u nazivu"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            current_date = datetime.now()
            month_names_sr = {
                1: 'januar', 2: 'februar', 3: 'mart', 4: 'april',
                5: 'maj', 6: 'jun', 7: 'jul', 8: 'avgust',
                9: 'septembar', 10: 'oktobar', 11: 'novembar', 12: 'decembar'
            }

            # Ako smo u poslednjih 5 dana meseca, traži sledeći mesec
            if current_date.day >= 25:
                target_month = current_date.month + 1 if current_date.month < 12 else 1
                target_year = current_date.year if current_date.month < 12 else current_date.year + 1
            else:
                target_month = current_date.month
                target_year = current_date.year

            current_month_name = month_names_sr[target_month]
            current_year = target_year
            
            links = soup.find_all('a', href=True)
            
            # Traži prvi PDF koji ima "jelovnik" u nazivu i trenutni mesec
            for link in links:
                href = link['href']
                link_text = link.get_text(strip=True).lower()
                
                if href.endswith('.pdf'):
                    # Mora imati "jelovnik" u tekstu linka
                    if 'jelovnik' in link_text:
                        # Mora imati naziv trenutnog meseca
                        if current_month_name in link_text:
                            # Ne sme imati "lanč" ili "užina"
                            if 'lanč' not in link_text and 'užina' not in link_text:
                                logger.info(f"Pronađen jelovnik: {link_text}")
                                if href.startswith('http'):
                                    return href
                                elif href.startswith('/'):
                                    return f"https://www.nasaradost.edu.rs{href}"
                                else:
                                    return f"https://www.nasaradost.edu.rs/{href}"
                            
            logger.warning(f"Nije pronađen PDF jelovnika za {current_month_name} {current_year}")
            return None
            
        except Exception as e:
            logger.error(f"Greška pri traženju PDF linka: {e}")
            return None
    
    def download_pdf(self, url: str, save_path: Optional[Path] = None) -> Optional[Path]:
        """Preuzmi PDF sa date URL adrese"""
        try:
            if save_path is None:
                current_date = datetime.now()
                filename = f"{current_date.year:04d}-{current_date.month:02d}.pdf"
                save_path = Path("data/pdfs") / filename
                
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Preuzimanje PDF-a sa: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"PDF uspešno preuzet: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Greška pri preuzimanju PDF-a: {e}")
            return None
    
    def get_current_month_menu(self) -> Optional[Path]:
        """Glavna metoda - pronađi i preuzmi PDF za trenutni mesec"""
        pdf_url = self.find_current_month_pdf_url()
        
        if not pdf_url:
            logger.error("PDF URL nije pronađen")
            return None
            
        logger.info(f"Pronađen PDF URL: {pdf_url}")
        return self.download_pdf(pdf_url)
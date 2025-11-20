"""
Modul za praćenje aktivnosti korisnika Klopas bota
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class UserStatsTracker:
    """Klasa za praćenje i analizu aktivnosti korisnika"""
    
    def __init__(self, stats_file: str = "data/user_stats.json"):
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats = self._load_stats()
        
    def _load_stats(self) -> Dict:
        """Učitaj statistiku iz fajla"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Greška pri učitavanju statistike: {e}")
                return {"users": {}, "daily_active": {}, "monthly_active": {}}
        return {"users": {}, "daily_active": {}, "monthly_active": {}}
    
    def _save_stats(self):
        """Sačuvaj statistiku u fajl"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Greška pri čuvanju statistike: {e}")
    
    def track_user_activity(self, user_id: int, username: Optional[str] = None, 
                           first_name: Optional[str] = None, action: str = "command"):
        """
        Prati aktivnost korisnika
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            first_name: Ime korisnika
            action: Tip akcije (command, callback, etc.)
        """
        user_id_str = str(user_id)
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        current_month = now.strftime('%Y-%m')
        
        # Inicijalizuj korisnika ako ne postoji
        if user_id_str not in self.stats["users"]:
            self.stats["users"][user_id_str] = {
                "first_seen": today,
                "last_seen": today,
                "username": username,
                "first_name": first_name,
                "total_interactions": 0,
                "daily_interactions": {},
                "notifications_enabled": True  # Podrazumevano uključeno
            }
        
        # Ažuriraj korisničke podatke
        user_data = self.stats["users"][user_id_str]
        user_data["last_seen"] = today
        user_data["total_interactions"] += 1
        
        # Ažuriraj username i ime ako su dostupni
        if username:
            user_data["username"] = username
        if first_name:
            user_data["first_name"] = first_name
        
        # Prati dnevne interakcije
        if today not in user_data["daily_interactions"]:
            user_data["daily_interactions"][today] = 0
        user_data["daily_interactions"][today] += 1
        
        # Prati dnevno aktivne korisnike
        if today not in self.stats["daily_active"]:
            self.stats["daily_active"][today] = []
        if user_id_str not in self.stats["daily_active"][today]:
            self.stats["daily_active"][today].append(user_id_str)
        
        # Prati mesečno aktivne korisnike
        if current_month not in self.stats["monthly_active"]:
            self.stats["monthly_active"][current_month] = []
        if user_id_str not in self.stats["monthly_active"][current_month]:
            self.stats["monthly_active"][current_month].append(user_id_str)
        
        self._save_stats()
        logger.info(f"Praćena aktivnost: user_id={user_id}, action={action}")
    
    def get_monthly_active_users(self, year: Optional[int] = None, month: Optional[int] = None) -> int:
        """
        Dobavi broj aktivnih korisnika za mesec
        
        Args:
            year: Godina (None za trenutni mesec)
            month: Mesec (None za trenutni mesec)
            
        Returns:
            Broj aktivnih korisnika
        """
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month
        
        month_key = f"{year}-{month:02d}"
        return len(self.stats["monthly_active"].get(month_key, []))
    
    def get_peak_monthly_users(self) -> int:
        """
        Dobavi maksimalan broj aktivnih korisnika u bilo kom mesecu
        
        Returns:
            Maksimalan broj aktivnih korisnika
        """
        if not self.stats["monthly_active"]:
            return 0
        
        return max(len(users) for users in self.stats["monthly_active"].values())
    
    def get_current_month_stats(self) -> Dict:
        """
        Dobavi statistiku za trenutni mesec
        
        Returns:
            Dict sa statistikom
        """
        now = datetime.now()
        current_month = now.strftime('%Y-%m')
        
        active_users = len(self.stats["monthly_active"].get(current_month, []))
        peak_users = self.get_peak_monthly_users()
        total_users = len(self.stats["users"])
        
        return {
            "current_month_active": active_users,
            "peak_monthly_active": peak_users,
            "total_users_ever": total_users,
            "month": current_month
        }
    
    def get_daily_active_users(self, date: Optional[str] = None) -> int:
        """
        Dobavi broj aktivnih korisnika za dan
        
        Args:
            date: Datum u formatu YYYY-MM-DD (None za danas)
            
        Returns:
            Broj aktivnih korisnika
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        return len(self.stats["daily_active"].get(date, []))
    
    def get_average_monthly_users(self, months: int = 3) -> float:
        """
        Dobavi prosečan broj aktivnih korisnika za poslednjih N meseci
        
        Args:
            months: Broj meseci za analizu
            
        Returns:
            Prosečan broj aktivnih korisnika
        """
        now = datetime.now()
        month_keys = []
        
        for i in range(months):
            month_date = now - timedelta(days=30 * i)
            month_key = month_date.strftime('%Y-%m')
            month_keys.append(month_key)
        
        active_counts = [
            len(self.stats["monthly_active"].get(key, []))
            for key in month_keys
            if key in self.stats["monthly_active"]
        ]
        
        if not active_counts:
            return 0.0
        
        return sum(active_counts) / len(active_counts)
    
    def get_active_user_ids(self, days: int = 30) -> list:
        """
        Dobavi IDs aktivnih korisnika za poslednjih N dana
        
        Args:
            days: Broj dana za analizu (default 30)
            
        Returns:
            Lista user IDs (kao int)
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        active_users = set()
        
        # Proveri kroz sve korisnike da li su bili aktivni u poslednjih N dana
        for user_id_str, user_data in self.stats["users"].items():
            last_seen = user_data.get("last_seen", "")
            if last_seen >= cutoff_str:
                active_users.add(int(user_id_str))
        
        return list(active_users)
    
    def set_notifications(self, user_id: int, enabled: bool):
        """
        Postavi notification preference za korisnika
        
        Args:
            user_id: Telegram user ID
            enabled: True za uključeno, False za isključeno
        """
        user_id_str = str(user_id)
        
        # Ako korisnik ne postoji, kreiraj ga
        if user_id_str not in self.stats["users"]:
            today = datetime.now().strftime('%Y-%m-%d')
            self.stats["users"][user_id_str] = {
                "first_seen": today,
                "last_seen": today,
                "username": None,
                "first_name": None,
                "total_interactions": 0,
                "daily_interactions": {},
                "notifications_enabled": enabled
            }
        else:
            self.stats["users"][user_id_str]["notifications_enabled"] = enabled
        
        self._save_stats()
        logger.info(f"Notifikacije {'uključene' if enabled else 'isključene'} za korisnika {user_id}")
    
    def get_notifications(self, user_id: int) -> bool:
        """
        Dobavi notification preference za korisnika
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True ako su notifikacije uključene, False inače (default True)
        """
        user_id_str = str(user_id)
        
        if user_id_str not in self.stats["users"]:
            return True  # Podrazumevano uključeno za nove korisnike
        
        # Vrati notification status, default True ako polje ne postoji
        return self.stats["users"][user_id_str].get("notifications_enabled", True)
    
    def get_users_with_notifications_enabled(self) -> list:
        """
        Dobavi IDs svih korisnika koji imaju uključene notifikacije
        
        Returns:
            Lista user IDs (kao int)
        """
        users_with_notifications = []
        
        for user_id_str, user_data in self.stats["users"].items():
            # Default je True ako polje ne postoji
            if user_data.get("notifications_enabled", True):
                users_with_notifications.append(int(user_id_str))
        
        return users_with_notifications
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Očisti stare dnevne podatke
        
        Args:
            days_to_keep: Broj dana za zadržavanje
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        # Očisti dnevne aktivne korisnike
        keys_to_remove = [
            key for key in self.stats["daily_active"].keys()
            if key < cutoff_str
        ]
        
        for key in keys_to_remove:
            del self.stats["daily_active"][key]
        
        # Očisti dnevne interakcije iz korisničkih podataka
        for user_data in self.stats["users"].values():
            daily_keys_to_remove = [
                key for key in user_data.get("daily_interactions", {}).keys()
                if key < cutoff_str
            ]
            for key in daily_keys_to_remove:
                del user_data["daily_interactions"][key]
        
        if keys_to_remove:
            logger.info(f"Očišćeno {len(keys_to_remove)} dnevnih zapisa starijih od {days_to_keep} dana")
            self._save_stats()

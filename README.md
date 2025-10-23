# Klopas Bot 🍽️

**Verzija 1.0**

Telegram bot za automatsko obaveštavanje o jelovniku u vrtiću "Naša Radost" Subotica.

## Funkcionalnosti

- 📅 Prikaz jelovnika za danas i sutra
- 🔄 Automatsko preuzimanje najnovijeg jelovnika sa sajta vrtića (preko `/update` komande)
- ⏰ Automatsko slanje jelovnika svaki radni dan u 20:00h (Belgrade timezone)
- 📱 Rad u Telegram grupama
- 🔁 Log rotation - automatsko čišćenje logova (max 5MB po fajlu, 5 backup fajlova)
- ✅ Pametno praćenje poslatih poruka (marker fajlovi sprečavaju duplikate)

## Instalacija

### 1. Kloniraj repozitorijum

```bash
git clone <repo-url>
cd klopas
```

### 2. Kreiraj virtual environment i instaliraj zavisnosti

```bash
python3 -m venv venv
source venv/bin/activate  # Na Linux/Mac
pip install -r requirements.txt
```

### 3. Kreiraj Telegram Bot

1. Otvori Telegram i pronađi [@BotFather](https://t.me/botfather)
2. Pošalji komandu `/newbot`
3. Sledi uputstva i daj ime svom botu
4. Sačuvaj token koji ćeš dobiti

### 4. Konfiguriši environment varijable

Kreiraj `.env` fajl na osnovu `.env.example`:

```bash
cp .env.example .env
```

Edituj `.env` fajl i postavi:
- `TELEGRAM_BOT_TOKEN` - token koji si dobio od BotFather
- `TELEGRAM_GROUP_ID` - ID grupe gde bot treba da šalje poruke (opcionalno)

### Kako pronaći Group ID

1. Dodaj bota u grupu
2. Pošalji poruku u grupi
3. Otvori u browseru: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Pronađi `"chat":{"id":-123456789,"type":"group"}`
5. Kopiraj ID (uključujući minus ako postoji)

## Pokretanje

### Pokretanje bota

```bash
python bot.py
```

Bot će početi da radi i čekaće komande.

### Ažuriranje jelovnika

Korisnici mogu ažurirati jelovnik direktno iz Telegram-a pomoću `/update` komande.
Bot će automatski preuzeti najnoviji PDF sa sajta vrtića i parsirati ga.

## Dostupne komande

- `/start` - Početni meni sa opcijama
- `/danas` - Jelovnik za danas
- `/sutra` - Jelovnik za sutra
- `/jelovnik` - Prikaži meni sa opcijama
- `/update` - Preuzmi najnoviji jelovnik sa sajta vrtića
- `/help` - Pomoć

## Struktura projekta

```
klopas/
├── src/
│   ├── scraper.py          # Preuzimanje PDF-a sa sajta
│   ├── pdf_parser.py       # Parsiranje PDF jelovnika
│   ├── data_organizer.py   # Organizacija podataka u .md fajlove
│   └── telegram_bot.py     # Telegram bot logika
├── data/
│   ├── pdfs/              # Preuzeti PDF fajlovi
│   └── daily/             # Markdown fajlovi po danima (YYYY-MM-DD.md format)
├── venv/                  # Python virtual environment
├── bot.py                 # Glavna skripta za pokretanje bota
├── start_bot.py           # Bot starter sa webhook clearing-om
├── klopas-bot.service     # Systemd service fajl
├── requirements.txt       # Python zavisnosti
├── .env                   # Environment varijable (ne commit-ovati!)
└── bot.log                # Log fajl (sa automatskom rotacijom)
```

## Automatizacija - Systemd Service (Linux)

Bot može raditi kao systemd service i automatski se pokretati prilikom boot-a sistema.

### Instalacija systemd servisa

1. **Kopiraj service fajl:**

```bash
sudo cp klopas-bot.service /etc/systemd/system/
```

2. **Edituj service fajl** i prilagodi putanje za tvoj sistem:

```bash
sudo nano /etc/systemd/system/klopas-bot.service
```

Primer konfiguracije:

```ini
[Unit]
Description=Klopas Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/klopas
Environment="PATH=/path/to/klopas/venv/bin:/usr/bin"
ExecStart=/path/to/klopas/venv/bin/python /path/to/klopas/bot.py
Restart=always
RestartSec=10
StandardOutput=append:/path/to/klopas/bot.log
StandardError=append:/path/to/klopas/bot.log

[Install]
WantedBy=multi-user.target
```

3. **Enable i pokreni servis:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable autostart na boot-u
sudo systemctl enable klopas-bot.service

# Pokreni servis
sudo systemctl start klopas-bot.service

# Proveri status
sudo systemctl status klopas-bot.service
```

### Korisne komande za upravljanje servisom

```bash
# Zaustavi bot
sudo systemctl stop klopas-bot.service

# Restartuj bot
sudo systemctl restart klopas-bot.service

# Pogledaj logove
sudo journalctl -u klopas-bot.service -f

# Proveri da li je enabled
systemctl is-enabled klopas-bot.service
```

## Logovanje

Bot koristi automatsku log rotaciju:
- **Maksimalna veličina fajla**: 5MB
- **Broj backup fajlova**: 5 (bot.log.1, bot.log.2, itd.)
- **Location**: `bot.log` u root direktorijumu projekta

Logovi za `httpx` (Telegram API requests) i `apscheduler` su podešeni na WARNING level da spreče prekomerno logovanje.

### Praćenje logova

```bash
# Real-time praćenje
tail -f bot.log

# Poslednji 50 redova
tail -n 50 bot.log

# Systemd logovi
sudo journalctl -u klopas-bot.service -f
```

## Troubleshooting

### Bot se ne pokreće

1. Proveri da li je TOKEN postavljen u `.env`
2. Proveri logove: `tail -f bot.log`
3. Proveri systemd status: `sudo systemctl status klopas-bot.service`

### Automatsko slanje ne radi

1. Proveri da li je `TELEGRAM_GROUP_ID` postavljen u `.env`
2. Proveri logove oko 20:00h
3. Proveri da li postoje marker fajlovi u `data/` koji blokiraju ponovno slanje

### Jelovnik se ne parsira

1. Pokušaj `/update` komandu u Telegram-u
2. Proveri da li je PDF dostupan na sajtu vrtića
3. Proveri logove za greške tokom parsiranja

## Licenca

MIT

## Autor

Kreirao sa ❤️ za roditelje i decu
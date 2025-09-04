# Klopas Bot 🍽️

Telegram bot za automatsko obaveštavanje o jelovniku u vrtiću "Naša Radost" Subotica.

## Funkcionalnosti

- 📅 Prikaz jelovnika za danas i sutra
- 🔄 Preuzimanje najnovijeg jelovnika sa sajta vrtića
- ⏰ Automatsko slanje jelovnika svaki radni dan u 20:00h
- 📱 Rad u Telegram grupama

## Instalacija

### 1. Kloniraj repozitorijum

```bash
git clone <repo-url>
cd klopas
```

### 2. Instaliraj zavisnosti

```bash
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

### Prvo preuzimanje jelovnika

```bash
python main.py
```

Ovo će preuzeti PDF sa sajta i kreirati markdown fajlove.

### Pokretanje bota

```bash
python bot.py
```

Bot će početi da radi i čekaće komande.

## Dostupne komande

- `/start` - Početni meni sa opcijama
- `/danas` - Jelovnik za danas
- `/sutra` - Jelovnik za sutra
- `/jelovnik` - Prikaži meni sa opcijama
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
│   └── daily/             # Markdown fajlovi po danima
├── bot.py                 # Glavna skripta za pokretanje bota
├── main.py                # Skripta za preuzimanje jelovnika
└── requirements.txt       # Python zavisnosti
```

## Automatizacija

Za potpunu automatizaciju, možeš podesiti:

### Linux/Mac - Cron job

```bash
# Edituj crontab
crontab -e

# Dodaj liniju za pokretanje bota pri boot-u
@reboot cd /path/to/klopas && /usr/bin/python3 bot.py

# Dodaj liniju za mesečno preuzimanje jelovnika (1. u mesecu u 08:00)
0 8 1 * * cd /path/to/klopas && /usr/bin/python3 main.py
```

### Systemd service (Linux)

Kreiraj `/etc/systemd/system/klopas-bot.service`:

```ini
[Unit]
Description=Klopas Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/klopas
ExecStart=/usr/bin/python3 /path/to/klopas/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Zatim:
```bash
sudo systemctl enable klopas-bot
sudo systemctl start klopas-bot
```

## Licenca

MIT

## Autor

Kreirao sa ❤️ za roditelje i decu
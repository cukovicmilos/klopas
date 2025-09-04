## Osnovni cilj projekta

Kao korisnik želim da budem obavešten o jelovniku u vrtiću jednom na dan, za idući dan (pon, uto, sred, čet, pet).

Ovu informaciju želim da dobijem kroz Telegram bot. Bot će biti pridodat već postojećoj grupi u Telegramu.

## Realizacija
- Na https://www.nasaradost.edu.rs/jelovnik/ se objavljuje jelovnik za svaki mesec tekuće godine. Jelovnik je u PDF formatu. Naziv link je uglavnom na ovaj način "Jelovnik septembar 2025." Fajl primer: https://www.nasaradost.edu.rs/uploads/daily-menu/3727JELOVNIK%20septembar.pdf
- Potrebno je očitati PDF.
- Uzeti podatke iz PDF-a i snimiti u .md fajl sa mesecom i godinom na primer "mart-2025.md"
  Primer jednog dana iz fajla - za ponedeljak:
PONEDELJAK 01.09.2025.
DORUČAK–MLEKO-1, MLEČNI KAKAO KREM1,2, HLEB-4
UŽINA I –VOĆE
RUČAK – BORANIJA VARIVO SA SVINJSKIM
MESOM-1,4, HLEB-4
UŽINA II – KEKS-1, 2, 4
VARIVO OD BORANIJE SA SVINJSKIM
MESOM
BORANIJA, SVINJSKO MESO, LUK CRNI,
BRAŠNO, ULJE, SO, DODATAK JELIMA, KISELA
PAVLAKA, MIROĐIJA LIST, BELI LUK
- Svakog dana, bez subote, u 20:00 Telegram bot treba da pošalje poruku u grupu šta je na meniju za naredni dan.
- Bot treba da poseduje dugme za proveru da li je izašao jelovnik za naredni mesec "Novi mesec". Sa ovom opcijom se trigeruje preuzimanje PDF-a, parsiranje u .md fajl i pravljenje jelovnika .md fajla za svaki radni dan tog meseca. Kasnije bot šalje sadržaj tog fajla jednom na dan.
# Mesin Lead

Cari bisnes di Google Maps setiap hari dan hantar prospek BARU sahaja ke Telegram anda, siap dengan
nombor telefon, butang WhatsApp dan link Google Maps. Prospek yang pernah dihantar tak akan dihantar lagi.

Ada dua cara guna:

| | Senario 1: Laptop | Senario 2: GitHub Actions (cloud) |
| --- | --- | --- |
| Jalan di | Laptop anda | Komputer GitHub |
| Laptop kena hidup | Ya, pada waktu jadual | Tidak |
| Setup | Claude Desktop di laptop | Browser sahaja, boleh dari telefon |
| Kos | Langganan Claude | Percuma (kuota 2,000 minit sebulan) |

## Senario 2: mula dalam 10 minit, tanpa terminal

1. Tekan **Use this template**, kemudian **Create a new repository**. Pilih **Private**. Wajib private,
   sebab repo anda akan simpan senarai prospek.
2. Buat bot Telegram di **@BotFather** (`/newbot`), salin token, buka bot anda, tekan **Start** dan hantar "hai".
3. Dalam repo anda: **Settings > Secrets and variables > Actions > New repository secret**. Tambah dua:
   - `TELEGRAM_BOT_TOKEN`: token dari BotFather
   - `TELEGRAM_CHAT_ID`: chat ID anda (cara dapatkan ada dalam panduan)
4. Buka fail `mesin-lead.json`, tekan ikon pensel, dan tukar `niche` serta senarai `bandar`. Tekan **Commit changes**.
5. Tab **Actions > Mesin Lead > Run workflow**. Prospek masuk Telegram dalam 1 hingga 2 minit.

Lepas tu, mesin jalan sendiri setiap hari pukul 9 pagi waktu Malaysia. Untuk carian sekali (niche atau
kawasan lain), isi kotak niche, kawasan dan jumlah pada **Run workflow**, termasuk dari app GitHub di telefon.

## Minta leads dengan chat di app Claude

Selepas setup, anda boleh minta leads dengan chat biasa, termasuk dari telefon:

1. Sekali sahaja: sambungkan GitHub ke Claude (claude.ai/code, atau bahagian Code dalam app Claude) dan
   benarkan akses ke repo Mesin Lead anda sahaja.
2. Dalam app Claude, buka **Code**, pilih repo anda, dan taip contohnya: *Cari 5 dental clinic di Seremban*.
3. Claude hantar permintaan ke repo, dan prospek masuk Telegram dalam lebih kurang 1 minit.

Perlukan langganan Claude (Pro atau Max). Laptop tak perlu hidup.

## Senario 1: laptop

Buka folder repo ni dalam Claude Code dan ikut panduan. Semua prompt dan command ada dalam panduan Mesin Lead.

## Tetapan (`mesin-lead.json`)

| Tetapan | Maksud |
| --- | --- |
| `niche` | Jenis bisnes, contoh `pasang aircond`, `dental clinic` |
| `bandar` | Senarai bandar, digilir satu setiap run. Tulis penuh, contoh `Ipoh, Perak, Malaysia` |
| `depth` | 1 = ~20 hasil, 2 = ~40, 5 = ~100 setiap bandar |
| `max_mesej_setiap_run` | Had mesej Telegram setiap run. `0` = hantar semua |
| `tanpa_website_sahaja`, `mesti_ada_telefon`, `rating_minimum`, `semak_pixel_iklan` | Penapis |

## Guna dengan bertanggungjawab

Scraper ni baca Google Maps terus, bukan melalui API rasmi Google, dan ini bercanggah dengan terma
perkhidmatan Google. Nombor telefon dan email ialah data peribadi (PDPA): simpan dengan selamat dan
hubungi prospek secara personal, jangan blast. Tiada jaminan jualan.

## Kredit

Dibina atas [google-maps-scraper-kit](https://github.com/Mahanaicoach/google-maps-scraper-kit) oleh Mahan
(lesen MIT), dikunci pada versi `446f231`. Dokumentasi asal kit ada dalam [README-kit.md](README-kit.md).
Lesen ada dalam [LICENSE](LICENSE).

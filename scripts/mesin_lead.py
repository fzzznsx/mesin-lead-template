#!/usr/bin/env python3
"""Mesin Lead: cari prospek baru di Google Maps dan hantar ke Telegram.

Setiap kali dijalankan, skrip ni:
  1. hidupkan engine scraper (kalau belum hidup)
  2. ambil bandar seterusnya dari mesin-lead.json (bergilir, supaya setiap hari bandar lain)
  3. cari "<niche> in <bandar>" dan buang prospek yang dah pernah dijumpai (leads/master.csv)
  4. simpan prospek baru dalam leads/master.csv
  5. hantar prospek baru ke Telegram, satu mesej satu prospek, dengan link Google Maps

Tetapan ada dalam mesin-lead.json (niche, bandar, penapis). Token bot dan chat ID ada dalam .env:
  TELEGRAM_BOT_TOKEN=...
  TELEGRAM_CHAT_ID=...

Cara guna:
  python3 scripts/mesin_lead.py                  # jalan biasa (untuk jadual harian)
  python3 scripts/mesin_lead.py --dry-run        # cari dan simpan, tapi tak hantar ke Telegram
  python3 scripts/mesin_lead.py --cari-chat-id   # cari chat ID anda (hantar "hai" ke bot dulu)
  python3 scripts/mesin_lead.py --test-telegram  # hantar satu mesej ujian ke Telegram
  python3 scripts/mesin_lead.py --niche "dental clinic" --bandar "Seremban, Negeri Sembilan, Malaysia" --had 20
                                                 # carian sekali: niche dan bandar lain, tanpa ubah tetapan

Skrip ni hanya cetak jumlah, bukan data prospek, supaya AI agent yang menjalankannya tak membaca
teks dari internet. Data prospek hanya pergi ke fail CSV dan Telegram anda.
Standard library sahaja, tiada pip install.
"""
import argparse, csv, datetime, html, json, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(KIT, "mesin-lead.json")
ENV = os.path.join(KIT, ".env")
LEADS = os.path.join(KIT, "leads")
MASTER = os.path.join(LEADS, "master.csv")
STATE = os.path.join(LEADS, "state.json")

FIELDS = ["title", "phone", "emails", "website", "category", "address", "review_rating", "review_count",
          "link", "place_id"]
DEFAULTS = {"niche": "", "bandar": [], "bandar_setiap_run": 1, "depth": 2, "kod_negara": "60",
            "max_mesej_setiap_run": 30, "tanpa_website_sahaja": False, "mesti_ada_telefon": True,
            "rating_minimum": None, "semak_pixel_iklan": False}


def die(msg):
    sys.exit(f"✗ {msg}")


def load_env():
    env = {}
    if os.path.isfile(ENV):
        with open(ENV, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k.startswith("TELEGRAM_")})
    return env


def load_config():
    if not os.path.isfile(CONFIG):
        die(f"Tiada fail tetapan {os.path.basename(CONFIG)}. Salin mesin-lead.example.json kepada mesin-lead.json "
            "dan isi niche serta bandar.")
    with open(CONFIG, encoding="utf-8") as f:
        cfg = {**DEFAULTS, **json.load(f)}
    if not str(cfg["niche"]).strip():
        die('Isi "niche" dalam mesin-lead.json, contoh "kereta sewa".')
    if not cfg["bandar"]:
        die('Isi "bandar" dalam mesin-lead.json, contoh ["Shah Alam, Selangor, Malaysia"].')
    return cfg


# ---------- Telegram ----------

def tg(token, method, payload=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = {}
            try:
                body = json.load(e)
            except Exception:
                pass
            wait = (body.get("parameters") or {}).get("retry_after")
            if e.code == 429 and wait and attempt < 2:  # Telegram minta perlahan sikit
                time.sleep(int(wait) + 1)
                continue
            if e.code == 401:
                die("Token bot Telegram tak sah. Semak TELEGRAM_BOT_TOKEN dalam .env.")
            if e.code in (400, 403) and "chat" in str(body.get("description", "")).lower():
                die("Chat ID salah, atau anda belum tekan Start pada bot. Semak TELEGRAM_CHAT_ID dalam .env.")
            die(f"Telegram jawab HTTP {e.code}: {body.get('description', '')[:200]}")
        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(3)
                continue
            die(f"Tak dapat sambung ke Telegram: {e.reason}")


def need_token(env):
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{30,}", token):
        die("TELEGRAM_BOT_TOKEN kosong atau formatnya salah (contoh 123456789:AAH...). Laptop: semak fail .env. "
            "GitHub Actions: semak Settings > Secrets and variables > Actions.")
    return token


def need_chat(env):
    chat = env.get("TELEGRAM_CHAT_ID", "")
    if not re.fullmatch(r"-?\d{3,}", chat):
        die("TELEGRAM_CHAT_ID kosong. Laptop: hantar 'hai' ke bot, kemudian jalankan "
            "python3 scripts/mesin_lead.py --cari-chat-id. GitHub Actions: tambah secret TELEGRAM_CHAT_ID.")
    return chat


def find_chat_id(env):
    token = need_token(env)
    res = tg(token, "getUpdates")
    chats = {}
    for u in res.get("result", []):
        msg = u.get("message") or u.get("channel_post") or {}
        c = msg.get("chat") or {}
        if "id" in c:
            chats[c["id"]] = c.get("type", "")
    if not chats:
        die("Bot belum terima mesej. Buka bot anda dalam Telegram, tekan Start dan hantar 'hai', "
            "kemudian cuba lagi.")
    for cid, kind in chats.items():
        print(f"✓ Chat ID: {cid}  ({kind})")
    print("  Laptop: letak dalam .env sebagai TELEGRAM_CHAT_ID=<nombor di atas>")
    print("  GitHub Actions: tambah secret TELEGRAM_CHAT_ID dengan nombor di atas")


def send(token, chat, text):
    tg(token, "sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML",
                              "disable_web_page_preview": True})
    time.sleep(1.1)  # Telegram hadkan ~1 mesej sesaat untuk satu chat


# ---------- Format mesej ----------

def esc(v):
    return html.escape(str(v or "").lstrip("'").strip(), quote=True)


def safe_url(u):
    u = str(u or "").lstrip("'").strip()
    if not u:
        return ""
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    return u if re.match(r"^https?://[^\s\"<>]+$", u, re.I) else ""


def whatsapp(phone, cc):
    d = re.sub(r"\D", "", str(phone or ""))
    if d.startswith("0"):
        d = cc + d[1:]
    if cc == "60" and not d.startswith("601"):  # Malaysia: WhatsApp untuk nombor mobile sahaja
        return ""
    return f"https://wa.me/{d}" if len(d) >= 9 else ""


def lead_message(i, n, r, cc):
    lines = [f"<b>{i}/{n} · {esc(r.get('title'))}</b>"]
    if r.get("category"):
        lines.append(f"🏷️ {esc(r.get('category'))}")
    if r.get("phone"):
        wa = whatsapp(r.get("phone"), cc)
        lines.append(f"📞 {esc(r.get('phone'))}" + (f" · <a href=\"{esc(wa)}\">WhatsApp</a>" if wa else ""))
    if r.get("review_rating"):
        lines.append(f"⭐ {esc(r.get('review_rating'))} ({esc(r.get('review_count') or 0)} review)")
    site = safe_url(r.get("website"))
    lines.append(f"🌐 <a href=\"{esc(site)}\">{esc(r.get('website'))[:60]}</a>" if site else "🌐 Tiada website")
    if r.get("emails"):
        lines.append(f"✉️ {esc(r.get('emails'))[:120]}")
    pixels = [name for col, name in (("fb_pixel", "Meta Pixel"), ("google_ads_tag", "Google Ads"),
                                      ("tiktok_pixel", "TikTok Pixel")) if str(r.get(col, "")).lower() in ("true", "1", "yes")]
    if pixels:
        lines.append(f"📣 Dah pasang: {', '.join(pixels)}")
    if r.get("address"):
        lines.append(f"📍 {esc(r.get('address'))[:160]}")
    maps = safe_url(r.get("link"))
    if maps:
        lines.append(f"🗺️ <a href=\"{esc(maps)}\">Buka di Google Maps</a>")
    return "\n".join(lines)


# ---------- Scrape ----------

def read_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def append_master(rows, city, niche):
    os.makedirs(LEADS, exist_ok=True)
    old = read_csv(MASTER)
    stamp = datetime.date.today().isoformat()
    for r in rows:
        r["tarikh_jumpa"], r["bandar_carian"], r["niche"] = stamp, city, niche
    cols = list(dict.fromkeys([c for r in old + rows for c in r.keys()]))
    with open(MASTER, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(old + rows)


def engine_running():
    r = subprocess.run([sys.executable, os.path.join(KIT, "scripts", "engine.py"), "status"],
                       capture_output=True, text=True, cwd=KIT)
    return r.returncode == 0 and "Running" in r.stdout


def engine(cmd):
    r = subprocess.run([sys.executable, os.path.join(KIT, "scripts", "engine.py"), cmd],
                       capture_output=True, text=True, cwd=KIT)
    if cmd == "start" and r.returncode != 0:
        die("Engine scraper tak dapat dihidupkan:\n" + (r.stdout + r.stderr)[-600:])


def scrape(cfg, city, out):
    keyword = f"{cfg['niche']} in {city.split(',')[0].strip()}"
    cmd = [sys.executable, os.path.join(KIT, "scripts", "scrape.py"), keyword, "--city", city,
           "--depth", str(int(cfg["depth"])), "--out", out, "--no-socials"]
    fields = list(FIELDS)
    if cfg["semak_pixel_iklan"]:
        cmd.append("--tech")
    cmd += ["--fields", ",".join(fields)]
    if cfg["tanpa_website_sahaja"]:
        cmd.append("--no-website")
    if cfg["mesti_ada_telefon"]:
        cmd.append("--has-phone")
    if cfg["rating_minimum"]:
        cmd += ["--min-rating", str(cfg["rating_minimum"])]
    if cfg.get("had"):
        cmd += ["--limit", str(int(cfg["had"]))]
    if os.path.isfile(MASTER):
        cmd += ["--exclude", MASTER]
    print(f"▶ Cari: {keyword}  (depth {cfg['depth']})")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=KIT)
    # Cetak baris status skrip scraper sahaja (jumlah dan amaran), bukan data prospek.
    for line in (r.stdout + r.stderr).splitlines():
        line = line.strip()
        if line.startswith(("✓", "⚠", "✗")) or "filters and --exclude" in line:
            print("  " + line[:200])
    if r.returncode not in (0, 1) and not os.path.isfile(out):
        print(f"  ✗ Carian untuk {city} gagal (kod {r.returncode}). Akan cuba lagi pada run seterusnya.")
        return None
    return read_csv(out)


def main():
    ap = argparse.ArgumentParser(description="Mesin Lead: prospek Google Maps terus ke Telegram.")
    ap.add_argument("--dry-run", action="store_true", help="cari dan simpan, tapi jangan hantar ke Telegram")
    ap.add_argument("--cari-chat-id", action="store_true", help="tunjuk chat ID (hantar 'hai' ke bot dulu)")
    ap.add_argument("--test-telegram", action="store_true", help="hantar satu mesej ujian")
    ap.add_argument("--bandar", help="jalankan untuk bandar ini sahaja (abaikan giliran)")
    ap.add_argument("--niche", help="cari niche ini untuk run ini sahaja (tanpa ubah mesin-lead.json)")
    ap.add_argument("--had", type=int, metavar="N", help="ambil N prospek pertama sahaja")
    ap.add_argument("--permintaan", metavar="FAIL",
                    help="baca niche, bandar dan had dari fail JSON (contoh permintaan.json dari Claude)")
    a = ap.parse_args()
    if a.permintaan:
        try:
            with open(a.permintaan, encoding="utf-8") as f:
                req = json.load(f)
        except (OSError, ValueError) as e:
            die(f"Fail permintaan tak boleh dibaca: {e}")
        niche = str(req.get("niche") or "").strip()[:80]
        bandar = str(req.get("bandar") or "").strip()[:120]
        a.niche = a.niche or niche or None
        a.bandar = a.bandar or bandar or None
        if not a.had and str(req.get("had") or "").strip().isdigit():
            a.had = int(str(req["had"]).strip())
        print(f"▶ Permintaan: niche={a.niche or '(harian)'} · kawasan={a.bandar or '(giliran)'} · had={a.had or 'semua'}")
    env = load_env()

    if a.cari_chat_id:
        return find_chat_id(env)
    if a.test_telegram:
        token, chat = need_token(env), need_chat(env)
        send(token, chat, "✅ <b>Mesin Lead bersambung!</b>\nProspek baru akan masuk ke sini.")
        print("✓ Mesej ujian dihantar. Semak Telegram anda.")
        return

    cfg = load_config()
    if a.niche:
        cfg["niche"] = a.niche.strip()
    if a.had:
        cfg["had"] = a.had
    token = chat = None
    if not a.dry_run:
        token, chat = need_token(env), need_chat(env)

    os.makedirs(LEADS, exist_ok=True)
    state = {"seterusnya": 0}
    if os.path.isfile(STATE):
        with open(STATE, encoding="utf-8") as f:
            state.update(json.load(f))
    cities = list(cfg["bandar"])
    if a.bandar:
        picks = [a.bandar]
    else:
        start = int(state.get("seterusnya", 0)) % len(cities)
        n = max(1, min(int(cfg["bandar_setiap_run"]), len(cities)))
        picks = [cities[(start + k) % len(cities)] for k in range(n)]

    started = not engine_running()
    if started:
        print("▶ Hidupkan engine scraper…")
        engine("start")

    total_new, sent = 0, 0
    try:
        for city in picks:
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
            slug = re.sub(r"[^a-z0-9]+", "-", city.split(",")[0].lower()).strip("-")
            out = os.path.join(LEADS, f"run-{stamp}-{slug}.csv")
            rows = scrape(cfg, city, out)
            if rows is None:
                continue
            rows = [r for r in rows if (r.get("title") or "").strip()]
            print(f"  → {len(rows)} prospek BARU di {city.split(',')[0]}")
            if rows:
                append_master(rows, city, cfg["niche"])
            total_new += len(rows)
            if not a.dry_run:
                cap = int(cfg["max_mesej_setiap_run"] or 0) or len(rows)  # 0 = hantar semua
                head = (f"🔔 <b>{len(rows)} prospek baru</b> · {esc(cfg['niche'])} · {esc(city.split(',')[0])}"
                        if rows else f"😴 Tiada prospek baru untuk {esc(cfg['niche'])} di {esc(city.split(',')[0])} hari ni.")
                if len(rows) > cap:
                    head += f"\n(Hantar {cap} teratas di sini. Semua {len(rows)} ada dalam leads/master.csv)"
                send(token, chat, head)
                for i, r in enumerate(rows[:cap], 1):
                    send(token, chat, lead_message(i, min(len(rows), cap), r, str(cfg["kod_negara"])))
                    sent += 1
            if not a.bandar:
                state["seterusnya"] = (cities.index(city) + 1) % len(cities)
                state["run_terakhir"] = datetime.datetime.now().isoformat(timespec="minutes")
                with open(STATE, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
    finally:
        if started:
            engine("stop")

    sent_note = f"{sent} dihantar ke Telegram" if not a.dry_run else "tidak dihantar (dry run)"
    print(f"✓ Siap: {total_new} prospek baru, {sent_note}. Semua disimpan dalam leads/master.csv")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("✗ Dihentikan.")

<!-- Mesin Lead: tambah bahagian di bawah ke dalam CLAUDE.md kit, sebelum bahagian
     "## When the user asks for businesses". Claude boleh buat untuk anda. -->

## Mesin Lead: every lead goes to Telegram
This folder has `scripts/mesin_lead.py`, which scrapes, skips places already in `leads/master.csv`, saves
the new ones there and sends each one to the user's Telegram bot (token and chat ID in `.env`). The user
wants EVERY lead request to reach Telegram, so for any request to find businesses or leads, run Mesin
Lead instead of `scripts/scrape.py`:

- One-off search, any niche and place: `python3 scripts/mesin_lead.py --niche "<niche>" --bandar "<Town, State, Malaysia>" --had <N>`
  (`--had` only when the user names a number; several places = one run per place).
- The daily run (niche and towns from `mesin-lead.json`): `python3 scripts/mesin_lead.py`
- "Tukar niche" for the daily run = change `niche` in `mesin-lead.json` (and reset `leads/state.json`
  `seterusnya` to 0 when the user wants to restart from the first town). Confirm the new value back to the user.
- `max_mesej_setiap_run` is 0 = send every new lead. Telegram takes about one message a second, so 100 leads
  take about 2 minutes: run it in the background and report the script's final `✓ Siap` line.
- `--dry-run` only when the user asks not to send. The script prints counts only; the skill's rules on rate
  limits and keeping scraped values out of your context still apply.

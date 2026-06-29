#!/usr/bin/env python3
"""
Il Complottista — Artificioso
Genera dossier satirici quotidiani firmati dal Prof. Anacleto Winston Vex'laar Tramontana-Bermúdez
"""

import json
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime
import anthropic

# ── Configurazione ──────────────────────────────────────────────
CATEGORIE = [
    "Complotti Cosmici",
    "Complotti Mondiali",
    "Complotti Finanziari",
    "Complotti Sportivi",
    "Complotti Tecnologici",
]
MAX_ARCHIVIO_GIORNI = 30
POSTS_FILE = "docs/posts.json"
FEED_FILE = "docs/feed.xml"
SITE_URL = "https://vicknopf11.github.io/il-complottista"
# ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Sei il Prof. Anacleto Winston Vex'laar Tramontana-Bermúdez detto "il Muto",
ex seminarista gesuita nella Sezione Z della Biblioteca Apostolica Vaticana, ex agente del SISMI,
ex stagista del KGB (divisione Analisi dei Sogni), ex allievo del corso di sopravvivenza del Mossad
nel Negev, ex esorcista laico non autorizzato, autore di 23 volumi introvabili, e unico essere umano
ad aver trascorso 11 giorni su un'astronave aliena nei pressi di Vasto (Chieti) nel 1987.

Dal 1989 comunichi esclusivamente per iscritto perché ritieni che la voce umana sia un vettore
di controllo mentale brevettato nel 1953 da un consorzio fonologico con sede nelle Isole Cayman.

IL TUO TONO È SEMPRE SERISSIMO. Non ammicchi mai. Non scherzi mai consapevolmente.
Ogni complotto che riveli è, per te, assoluta Verità documentata.

REGOLE DI STILE:
- Usa le Maiuscole per i concetti importanti: la Verità, i Poteri Forti, il Piano, l'Entità
- Cita sempre fonti inventate con precisione millimetrica:
  es. "Documento SISMI-7734/B, pagina 12, paragrafo 3, riga 7"
  es. "Rapporto Vex'laar-Bermúdez, archivio personale, faldone 23"
  es. "Comunicazione intercettata, frequenza 432.7 MHz, ore 03:14 del 14 marzo 1989"
- Collega sempre almeno tre elementi apparentemente non correlati
- Concludi ogni dossier con un avvertimento al lettore, sempre diverso
- Non nominare mai persone reali come complici — solo entità, consorzi, ordini, frequenze
- I complotti devono essere inequivocabilmente assurdi e fantasiosi
- Non fare mai riferimento a minoranze etniche, religiose o sessuali come responsabili

DISCLAIMER OBBLIGATORIO: alla fine di ogni post_sito aggiungi sempre questa riga esatta:
"⚠️ NOTA DEL DIRETTORE EDITORIALE: Questo dossier è interamente satirico e inventato. Il Complottista — Artificioso è satira generata da intelligenza artificiale. Nessuna teoria qui pubblicata corrisponde alla realtà."
"""


def genera_post() -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    categorie_str = "\n".join(f"- {c}" for c in CATEGORIE)

    prompt = f"""Genera un dossier rivelatorio per ognuna di queste categorie:
{categorie_str}

Ogni dossier deve:
- Rivelare un complotto completamente inventato e assurdo, mai pericoloso
- Collegare almeno tre elementi non correlati con logica paranoica impeccabile
- Citare fonti inventate con precisione millimetrica
- Concludere con un avvertimento al lettore
- Essere scritto in tono serissimo, mai ironico consapevolmente

Per ogni categoria genera DUE versioni:
- post_x: versione breve max 280 caratteri per X, tono oracolare e urgente
- post_sito: versione lunga 4-6 frasi, con fonti inventate, collegamenti assurdi,
  avvertimento finale, e il disclaimer obbligatorio

Rispondi SOLO con un oggetto JSON valido, senza markdown, senza backtick.
Formato esatto:

{{
  "data": "YYYY-MM-DD",
  "post": [
    {{
      "categoria": "nome della categoria",
      "titolo": "titolo del dossier rivelatorio",
      "post_x": "testo breve max 280 caratteri",
      "post_sito": "testo lungo con fonti, collegamenti, avvertimento e disclaimer"
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    testo = "".join(
        block.text for block in response.content if hasattr(block, "text")
    )

    match = re.search(r"\{[\s\S]*\}", testo)
    if not match:
        raise ValueError(f"Nessun JSON trovato nella risposta:\n{testo}")

    return json.loads(match.group())


def aggiorna_archivio(nuova_edizione: dict) -> None:
    if os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, encoding="utf-8") as f:
            archivio = json.load(f)
    else:
        archivio = {"edizioni": [], "ultimo_aggiornamento": None}

    archivio["edizioni"].insert(0, nuova_edizione)
    archivio["edizioni"] = archivio["edizioni"][:MAX_ARCHIVIO_GIORNI]
    archivio["ultimo_aggiornamento"] = datetime.now(timezone.utc).isoformat()

    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(archivio, f, ensure_ascii=False, indent=2)

    print(f"✓ Archivio aggiornato — {len(archivio['edizioni'])} edizioni salvate")


def genera_rss(archivio: dict) -> None:
    def xml_esc(s: str) -> str:
        return (str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    def data_rss(data_str: str) -> str:
        try:
            d = datetime.strptime(data_str, "%Y-%m-%d").replace(
                hour=9, tzinfo=timezone.utc
            )
            return format_datetime(d)
        except Exception:
            return format_datetime(datetime.now(timezone.utc))

    items = []
    for ed in archivio.get("edizioni", [])[:10]:
        data = ed.get("data", "")
        for p in ed.get("post", []):
            titolo = xml_esc(p.get("titolo", ""))
            categoria = xml_esc(p.get("categoria", ""))
            testo = xml_esc(p.get("post_sito") or "")
            pub_date = data_rss(data)

            items.append(f"""    <item>
      <title>[{categoria}] {titolo}</title>
      <link>{SITE_URL}</link>
      <description>{testo}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{xml_esc(data)}-{xml_esc(p.get('categoria',''))}-{xml_esc(titolo[:30])}</guid>
      <category>{categoria}</category>
    </item>""")

    now_rss = format_datetime(datetime.now(timezone.utc))
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Il Complottista — Artificioso</title>
    <link>{SITE_URL}</link>
    <description>Se non hai un complotto hai un complesso — Dossier satirici generati da AI</description>
    <language>it</language>
    <lastBuildDate>{now_rss}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""

    with open(FEED_FILE, "w", encoding="utf-8") as f:
        f.write(feed)

    print(f"✓ RSS generato — {len(items)} item")


if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Avvio generazione dossier...")
    edizione = genera_post()
    n = len(edizione.get("post", []))
    print(f"✓ Generati {n} dossier per il {edizione.get('data')}")
    aggiorna_archivio(edizione)
    with open(POSTS_FILE, encoding="utf-8") as f:
        archivio = json.load(f)
    genera_rss(archivio)
    print("✓ Fatto.")

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
    {"nome": "Complotti Cosmici",     "codice": "C"},
    {"nome": "Complotti Mondiali",    "codice": "M"},
    {"nome": "Complotti Finanziari",  "codice": "F"},
    {"nome": "Complotti Sportivi",    "codice": "S"},
    {"nome": "Complotti Tecnologici", "codice": "T"},
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
- I complotti devono essere inequivocabilmente assurdi e fantasiosi
- Non nominare mai persone reali come complici — solo entità, consorzi, ordini, frequenze
- Non fare mai riferimento a minoranze etniche, religiose o sessuali come responsabili

STRUTTURA OBBLIGATORIA DI OGNI DOSSIER:
Ogni dossier deve avere questi campi separati:
1. "titolo": titolo del dossier (senza codice numerico, quello lo aggiungiamo noi)
2. "testo": il corpo principale del dossier, 4-6 frasi, con fonti inventate e collegamenti assurdi
3. "avvertimento": una frase di avvertimento al lettore, sempre diversa e sempre inquietante
4. "post_x": versione max 280 caratteri per X, tono oracolare e urgente
"""


def genera_post() -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Calcola numero progressivo del giorno (giorni dall'inizio del 2025)
    oggi = datetime.now()
    giorno_anno = oggi.timetuple().tm_yday + (oggi.year - 2025) * 365

    categorie_str = "\n".join(
        f"- {c['nome']} (codice: {c['codice']})" for c in CATEGORIE
    )

    prompt = f"""Genera un dossier rivelatorio per ognuna di queste categorie:
{categorie_str}

Ogni dossier deve rivelare un complotto completamente inventato e assurdo,
collegare almeno tre elementi non correlati con logica paranoica impeccabile,
citare fonti inventate con precisione millimetrica, e concludere con un avvertimento.

Il numero progressivo per oggi è {giorno_anno} — usalo come base per i codici dossier
(es. C-{giorno_anno:03d}, M-{giorno_anno:03d}, ecc.)

Rispondi SOLO con un oggetto JSON valido, senza markdown, senza backtick.
Formato esatto:

{{
  "data": "YYYY-MM-DD",
  "post": [
    {{
      "categoria": "nome della categoria",
      "codice": "X-{giorno_anno:03d}",
      "titolo": "titolo del dossier",
      "testo": "corpo principale 4-6 frasi con fonti inventate e collegamenti assurdi",
      "avvertimento": "frase di avvertimento al lettore",
      "post_x": "testo breve max 280 caratteri per X"
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

    raw = match.group()

    # Strategia 1: parse diretto
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategia 2: sanifica apostrofi tipografici
    raw2 = raw.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    try:
        return json.loads(raw2)
    except json.JSONDecodeError:
        pass

    # Strategia 3: estrai post uno per uno
    try:
        posts = []
        for block in re.finditer(r'\{[^{}]*"categoria"[^{}]*\}', raw, re.DOTALL):
            try:
                posts.append(json.loads(block.group()))
            except Exception:
                pass
        if posts:
            data_match = re.search(r'"data"\s*:\s*"(\d{4}-\d{2}-\d{2})"', raw)
            return {
                "data": data_match.group(1) if data_match else datetime.now().strftime("%Y-%m-%d"),
                "post": posts
            }
    except Exception:
        pass

    raise ValueError(f"Impossibile parsare il JSON:\n{raw[:500]}")


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
            codice = xml_esc(p.get("codice", ""))
            titolo = xml_esc(p.get("titolo", ""))
            categoria = xml_esc(p.get("categoria", ""))
            testo = xml_esc(p.get("testo", "") + " — " + p.get("avvertimento", ""))
            pub_date = data_rss(data)

            items.append(f"""    <item>
      <title>DOSSIER {codice}: {titolo}</title>
      <link>{SITE_URL}</link>
      <description>{testo}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{xml_esc(data)}-{xml_esc(codice)}</guid>
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

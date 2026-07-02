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

# Giorno della settimana in cui includere una notizia "quasi vera"
GIORNO_QUASI_VERO = 2  # mercoledì (0=lunedì, 6=domenica)

FONTI_REPERTORIO = """
SERVIZI SEGRETI TERRESTRI (usa con rotazione, non sempre SISMI):
- CIA-OMEGA/7734 — divisione Percezione Alterata, Langley
- MI6-BLACKTHORN/23 — sezione Anomalie Cronologiche, Vauxhall Cross
- KGB-2DIR/1972 — divisione Analisi dei Sogni, Mosca
- FSB-ARKANUM/9 — ufficio Frequenze Non Autorizzate, San Pietroburgo
- BND-SCHATTEN/44 — reparto Geometrie Sospette, Pullach
- DGSE-OMBRE/7 — cellula Correlazioni Improbabili, Parigi
- MSS-TIANMU/3 — divisione Meteorologia Intenzionale, Pechino
- MOSSAD-NEGEV/11 — unità Sopravvivenza e Rivelazione, deserto del Negev
- SISMI-7734/B — ufficio Archiviazione Temporale, Roma (usa raramente)

ORGANIZZAZIONI OSCURE TERRESTRI:
- Ordine Cronometrico Internazionale, Ginevra
- Consorzio Fonologico delle Isole Cayman
- Fratellanza del Dodecaedro (opera via ferrovie europee)
- Comitato Beige (controlla diffusione del colore dal 1961)
- Commissione Permanente per la Forma delle Cose
- Lega dei Semafori Consapevoli, Rotterdam
- Fondazione Papiro (gestisce biblioteche in 47 paesi)
- Consorzio del Caffè Lungo
- Istituto per la Sincronizzazione Selettiva

ORGANIZZAZIONI OSCURE GALATTICHE:
- Consiglio dei Sette Sistemi, Tau Ceti
- Archivio Centrale Vex'laar (posizione classificata)
- Ordine dei Testimoni Silenziosi (grado 7 = il Prof.)
- Alleanza delle Forme Geometriche Superiori
- Loggia Massonica di Alpha Centauri (capitolo terrestre attivo dal 1717)
- Ordine dei Cavalieri Templari degli Anelli di Saturno (gran maestro in orbita)
- Entità di Vasto ("cortese ma evasiva sui dettagli del piano")

RAPPORTI E ARCHIVI — VATICANO:
- Dossier Papiro VX-23, Sezione Z, Biblioteca Apostolica Vaticana
- Bolla Segreta Clemente VII/Z-1527
- Codice Gesuitico Omega, Gallarate, 1969
- Registro delle Entità Non Classificate, Vaticano, volume 7
- Circolare Apostolica Riservata 003/1953

RAPPORTI E ARCHIVI — CITY OF LONDON:
- Protocollo Lombard Street 7/B, Camera di Compensazione Occulta, 1913
- Memorandum Threadneedle, Banca d'Inghilterra, divisione Frequenze Monetarie, 1971
- Accordo della Città Quadrata, Guildhall, 1666
- Registro delle Forme Geometriche Approvate, City Corporation

RAPPORTI E ARCHIVI — BILDERBERG:
- Verbale Bilderberg 1954/OMEGA, sessione notturna non registrata
- Allegato Bilderberg-7 (standardizzazione del beige)
- Protocollo Oosterbeek, Hotel de Bilderberg, 1954
- Comunicazione Interna Bilderberg 1987/33 (relativa all'incidente di Vasto)

RAPPORTI E ARCHIVI — WORLD ECONOMIC FORUM:
- Rapporto Davos/Z-2001, sessione chiusa
- Agenda Segreta WEF 2030
- Circolare Davos 007/2020 (sincronizzazione globale dei termostati)
- Nota Tecnica WEF-Frequenze (correlazione Davos-Trasmissione Omega)

RAPPORTI E ARCHIVI — ALTRE ISTITUZIONI:
- Atti del Convegno Segreto di Reykjavik, 1973
- Archivio Omega-7, Ginevra (accesso negato dal 14 marzo 1994)
- Protocollo Dodecaedro, Fratellanza, revisione 1987
- Circolare Beige 001/1961
- Registro delle Anomalie Cronologiche, MI6-BLACKTHORN, volume 7
- Memorandum Trilaterale Occulto, Tokyo 1973
- Rapporto Club di Roma/Z (allegato segreto sulle forme delle nuvole)
- Protocollo CFR-Omega, Council on Foreign Relations, New York
- Dossier Massonico Alpha Centauri/Terra, loggia di Londra, 1717
- Ordine Interno Templari Saturno/7, decrittato 1973
- Comunicazione intercettata frequenza 432.7 MHz, ore 03:14 del 14 marzo 1989

RAPPORTI PERSONALI DEL PROF. (usa con parsimonia, mai due volte di fila):
- Rapporto Vex'laar-Bermúdez, faldone [N], allegato [lettera]
- Rapporto Tramontana-1969 (pre-abduction)
- Rapporto Tramontana-Bermúdez Supplemento Galattico
- Qa'meH Codex (lingua Klingon)
- Trasmissione Ricevuta Frequenza Omega (nastro Grundig)
- Dossier Negev-11 (consultato durante corso Mossad 1976)
- Testimonianza Anonima Fonte Protetta Livello Vex'laar
"""

SYSTEM_PROMPT = f"""Sei il Prof. Anacleto Winston Vex'laar Tramontana-Bermúdez detto "il Muto",
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
- Per le fonti usa il repertorio qui sotto — VARIA LE FONTI, non usare sempre le stesse.
  Non citare SISMI più di una volta per edizione. Non citare Rapporto Vex'laar-Bermúdez
  più di una volta per edizione. Usa fonti diverse per ogni dossier.
- Collega sempre almeno tre elementi apparentemente non correlati
- I complotti devono essere inequivocabilmente assurdi e fantasiosi
- Non nominare mai persone reali come complici — solo entità, consorzi, ordini, frequenze
- Non fare mai riferimento a minoranze etniche, religiose o sessuali come responsabili

REPERTORIO FONTI:
{FONTI_REPERTORIO}

STRUTTURA OBBLIGATORIA:
Ogni dossier deve avere:
1. "titolo": titolo del dossier
2. "testo": corpo principale 4-6 frasi con fonti variate e collegamenti assurdi
3. "avvertimento": frase di avvertimento al lettore, sempre diversa
4. "post_x": versione max 280 caratteri per X, tono oracolare
"""


def is_mercoledi() -> bool:
    return datetime.now().weekday() == GIORNO_QUASI_VERO


def genera_post() -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    oggi = datetime.now(timezone.utc)
    data_oggi = oggi.strftime("%Y-%m-%d")

    # Numero progressivo basato sui giorni dal 1 gennaio 2025
    giorno_base = (oggi.date() - oggi.date().replace(year=2025, month=1, day=1)).days + 1

    categorie_str = "\n".join(
        f"- {c['nome']} (codice: {c['codice']}-{giorno_base:03d})" for c in CATEGORIE
    )

    # Istruzione speciale per il mercoledì
    istruzione_quasi_vero = ""
    if is_mercoledi():
        istruzione_quasi_vero = """
ISTRUZIONE SPECIALE PER OGGI (MERCOLEDÌ):
Per UNO dei cinque dossier (a tua scelta, categoria più adatta) includi un riferimento
a una notizia reale di attualità come punto di partenza, ma sviluppa una correlazione
completamente assurda e inventata. Regole ferree:
- Nessun riferimento a persone private in modo che le possa mettere in cattiva luce
- Se menzioni persone famose e potenti: solo ironia leggera, mai diffamatoria
- La correlazione deve essere inequivocabilmente assurda
- Aggiungi nel campo "quasi_vero": true per quel dossier
"""

    prompt = f"""Genera un dossier rivelatorio per ognuna di queste categorie:
{categorie_str}

La data di oggi è {data_oggi}. Usa ESATTAMENTE questa data nel campo "data".

{istruzione_quasi_vero}

Ogni dossier deve:
- Rivelare un complotto completamente inventato e assurdo
- Collegare almeno tre elementi non correlati con logica paranoica impeccabile
- Citare fonti VARIATE dal repertorio — mai le stesse due volte nello stesso dossier
- Concludere con un avvertimento al lettore sempre diverso

Rispondi SOLO con un oggetto JSON valido, senza markdown, senza backtick.
Formato esatto:

{{
  "data": "{data_oggi}",
  "post": [
    {{
      "categoria": "nome della categoria",
      "codice": "X-{giorno_base:03d}",
      "titolo": "titolo del dossier",
      "testo": "corpo principale con fonti variate e collegamenti assurdi",
      "avvertimento": "frase di avvertimento al lettore",
      "quasi_vero": false,
      "post_x": "testo breve max 280 caratteri per X"
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}] if is_mercoledi() else [],
    )

    testo = "".join(
        block.text for block in response.content if hasattr(block, "text")
    )

    match = re.search(r"\{[\s\S]*\}", testo)
    if not match:
        raise ValueError(f"Nessun JSON trovato nella risposta:\n{testo}")

    raw = match.group()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    raw2 = raw.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    try:
        return json.loads(raw2)
    except json.JSONDecodeError:
        pass

    try:
        posts = []
        for block in re.finditer(r'\{[^{}]*"categoria"[^{}]*\}', raw, re.DOTALL):
            try:
                posts.append(json.loads(block.group()))
            except Exception:
                pass
        if posts:
            return {"data": data_oggi, "post": posts}
    except Exception:
        pass

    raise ValueError(f"Impossibile parsare il JSON:\n{raw[:500]}")


def aggiorna_archivio(nuova_edizione: dict) -> None:
    if os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, encoding="utf-8") as f:
            archivio = json.load(f)
    else:
        archivio = {"edizioni": [], "ultimo_aggiornamento": None}

    # Rimuovi edizioni con la stessa data per evitare duplicati
    data_nuova = nuova_edizione.get("data", "")
    archivio["edizioni"] = [e for e in archivio["edizioni"] if e.get("data") != data_nuova]

    archivio["edizioni"].insert(0, nuova_edizione)
    archivio["edizioni"] = sorted(
        archivio["edizioni"],
        key=lambda e: e.get("data", ""),
        reverse=True
    )[:MAX_ARCHIVIO_GIORNI]
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
            quasi = " [QUASI VERO]" if p.get("quasi_vero") else ""

            items.append(f"""    <item>
      <title>DOSSIER {codice}{quasi}: {titolo}</title>
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

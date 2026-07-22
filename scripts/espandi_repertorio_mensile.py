#!/usr/bin/env python3
"""
Espande automaticamente il repertorio fonti del Complottista una volta al mese:
- aggiunge UNA fonte nuova a ciascuna categoria esistente
- crea UNA categoria interamente nuova con alcune fonti
- rigenera il blocco corrispondente in docs/prompt.html
- registra ogni aggiunta in un log JSONL per trasparenza/controllo

Pensato per girare da GitHub Actions una volta al mese, senza intervento manuale.

Uso:
    python3 espandi_repertorio_mensile.py [percorso_script.py] [percorso_prompt.html]
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

DEFAULT_SCRIPT_PY = "genera.py"          # <-- correggi col vero nome del file
DEFAULT_PROMPT_HTML = "docs/prompt.html"
LOG_FILE = "logs/repertorio-fonti-log.jsonl"

MARKER_START = "<!-- FONTI:START -->"
MARKER_END = "<!-- FONTI:END -->"

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT_ESPANSIONE = """Aiuti a espandere il "repertorio fonti" del Prof. Anacleto Winston \
Vex'laar Tramontana-Bermúdez, personaggio satirico complottista dal tono serissimo e paranoico. \
Il repertorio è una lista di fonti INTERAMENTE INVENTATE (servizi segreti fittizi, ordini oscuri, \
archivi immaginari) usate come citazioni fasulle nei suoi dossier satirici.

REGOLE FERREE per ogni fonte che inventi:
- Deve essere chiaramente e inequivocabilmente FITTIZIA — nessuna organizzazione reale, nessuna
  persona reale, nessun ente realmente esistente o realmente accusabile di alcunché.
- Stile coerente con gli esempi forniti: nomi altisonanti, sigle pseudo-burocratiche, dettagli
  iperspecifici e assurdi (numeri di protocollo, anni, sedi improbabili), tono da cospirazionista
  serissimo e mai ironico esplicitamente.
- Nessun riferimento a minoranze etniche, religiose o sessuali.
- Nessuna persona reale vivente o deceduta usata come presunto complice.
- Non riutilizzare nomi di organizzazioni reali esistenti (es. no CIA vera, no Bilderberg vero come
  se fossero reali — va bene richiamarli in chiave scherzosa/fittizia come già fa il repertorio
  esistente, ma le fonti NUOVE che inventi devono restare nel registro assurdo, non aggiungere
  ulteriore materiale su entità reali).

Rispondi SOLO con un oggetto JSON valido, senza markdown, senza backtick, nel formato:
{
  "categoria_nuova": {
    "titolo": "NOME CATEGORIA (eventuale nota tra parentesi)",
    "fonti": ["Nome fonte — descrizione", "Nome fonte — descrizione", "Nome fonte — descrizione"]
  },
  "fonti_aggiuntive": {
    "TITOLO CATEGORIA ESISTENTE 1": "Nome fonte — descrizione",
    "TITOLO CATEGORIA ESISTENTE 2": "Nome fonte — descrizione"
  }
}

Nel campo "fonti_aggiuntive" usa ESATTAMENTE i titoli di categoria che ti vengono forniti,
uno per ciascuno, con una fonte nuova e diversa da tutte quelle già esistenti."""


# ── Parsing del repertorio esistente ────────────────────────────

def estrai_repertorio(testo_py: str) -> str:
    match = re.search(r'FONTI_REPERTORIO\s*=\s*"""(.*?)"""', testo_py, re.DOTALL)
    if not match:
        raise ValueError("Non trovo FONTI_REPERTORIO nel file Python.")
    return match.group(1)

def normalizza_titolo(t: str) -> str:
    """Toglie eventuali note tra parentesi finali dal titolo, così una
    categoria con o senza quell'annotazione viene comunque riconosciuta
    come la stessa (es. Claude a volte restituisce il titolo senza la
    parentesi, interpretandola come istruzione di stile e non come nome)."""
    senza_parentesi = re.sub(r'\s*\([^)]*\)\s*$', '', t)
    return senza_parentesi.strip().upper()

def parse_categorie(repertorio: str) -> list[tuple[str, list[str]]]:
    categorie = []
    titolo_corrente = None
    voci_correnti: list[str] = []

    for riga in repertorio.split("\n"):
        riga = riga.strip()
        if not riga:
            continue
        if riga.endswith(":"):
            if titolo_corrente is not None:
                categorie.append((titolo_corrente, voci_correnti))
            titolo_corrente = riga[:-1].strip()
            voci_correnti = []
        elif riga.startswith("- "):
            voci_correnti.append(riga[2:].strip())
        else:
            if voci_correnti:
                voci_correnti[-1] += " " + riga

    if titolo_corrente is not None:
        categorie.append((titolo_corrente, voci_correnti))

    return categorie


# ── Chiamata a Claude per generare fonti nuove ──────────────────

def genera_fonti_nuove(categorie: list[tuple[str, list[str]]]) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Diamo a Claude i titoli delle categorie e qualche esempio di fonte per stile,
    # non l'intero repertorio (per contenere i token).
    esempi = []
    for titolo, voci in categorie:
        esempio_voce = voci[0] if voci else ""
        esempi.append(f"- {titolo}: es. \"{esempio_voce}\"")

    prompt = f"""Ecco le categorie esistenti nel repertorio, con un esempio di fonte per ciascuna:

{chr(10).join(esempi)}

Genera:
1. Una fonte nuova, mai vista, per OGNUNA di queste categorie (stesso stile dell'esempio)
2. Una categoria interamente nuova, coerente col resto del repertorio, con 3 fonti fittizie

Rispondi solo con il JSON richiesto."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT_ESPANSIONE,
        messages=[{"role": "user", "content": prompt}],
    )

    testo = "".join(b.text for b in response.content if hasattr(b, "text"))
    match = re.search(r"\{[\s\S]*\}", testo)
    if not match:
        raise ValueError(f"Nessun JSON nella risposta:\n{testo}")

    return json.loads(match.group())


# ── Fusione nel repertorio esistente ────────────────────────────

def fondi_repertorio(
    categorie: list[tuple[str, list[str]]], espansione: dict
) -> tuple[list[tuple[str, list[str]]], dict]:
    """Ritorna (categorie_aggiornate, log_delle_aggiunte)"""
    log = {"fonti_aggiunte": {}, "categoria_nuova": None, "saltate": []}

    fonti_aggiuntive = espansione.get("fonti_aggiuntive", {})
    nuove_categorie = []
    for titolo, voci in categorie:
        voce_nuova = None
        titolo_norm = normalizza_titolo(titolo)
        for titolo_richiesta, fonte in fonti_aggiuntive.items():
            if normalizza_titolo(titolo_richiesta) == titolo_norm:
                voce_nuova = fonte.strip()
                break

        voci_aggiornate = list(voci)
        if voce_nuova:
            duplicato = any(
                voce_nuova.strip().lower() == v.strip().lower() for v in voci
            )
            if duplicato:
                log["saltate"].append(f"{titolo}: fonte duplicata scartata")
            else:
                voci_aggiornate.append(voce_nuova)
                log["fonti_aggiunte"][titolo] = voce_nuova
        nuove_categorie.append((titolo, voci_aggiornate))

    categoria_nuova = espansione.get("categoria_nuova")
    if categoria_nuova and categoria_nuova.get("titolo") and categoria_nuova.get("fonti"):
        titolo_nuovo = categoria_nuova["titolo"].strip()
        fonti_nuove = [f.strip() for f in categoria_nuova["fonti"] if f.strip()]
        titoli_esistenti = {t.strip().upper() for t, _ in categorie}
        if titolo_nuovo.upper() not in titoli_esistenti and fonti_nuove:
            nuove_categorie.append((titolo_nuovo, fonti_nuove))
            log["categoria_nuova"] = {"titolo": titolo_nuovo, "fonti": fonti_nuove}
        else:
            log["saltate"].append(f"Categoria '{titolo_nuovo}' scartata (duplicata o vuota)")

    return nuove_categorie, log


def ricostruisci_repertorio_testo(categorie: list[tuple[str, list[str]]]) -> str:
    blocchi = []
    for titolo, voci in categorie:
        righe = "\n".join(f"- {v}" for v in voci)
        blocchi.append(f"{titolo}:\n{righe}")
    return "\n\n" + "\n\n".join(blocchi) + "\n"


def scrivi_repertorio_nel_py(testo_py: str, nuovo_repertorio: str) -> str:
    pattern = re.compile(r'(FONTI_REPERTORIO\s*=\s*""")(.*?)(""")', re.DOTALL)
    if not pattern.search(testo_py):
        raise ValueError("Non trovo FONTI_REPERTORIO da sostituire nel file Python.")
    return pattern.sub(lambda m: m.group(1) + nuovo_repertorio + m.group(3), testo_py)


# ── Rigenerazione dell'HTML (stessa logica di aggiorna_fonti_prompt.py) ─

def xml_esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def genera_html(categorie: list[tuple[str, list[str]]]) -> str:
    blocchi = []
    for titolo, voci in categorie:
        righe_voci = "\n".join(f"        <li>{xml_esc(v)}</li>" for v in voci)
        blocchi.append(f"\n      <h4>{xml_esc(titolo)}</h4>\n      <ul>\n{righe_voci}\n      </ul>\n")
    return "\n".join(blocchi) + "\n"


def aggiorna_html(html_originale: str, html_fonti: str) -> str:
    if MARKER_START not in html_originale or MARKER_END not in html_originale:
        raise ValueError(f"Marcatori {MARKER_START}/{MARKER_END} non trovati in prompt.html.")
    pattern = re.compile(re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END), re.DOTALL)
    sostituzione = f"{MARKER_START}\n{html_fonti}{MARKER_END}"
    return pattern.sub(sostituzione, html_originale)


# ── Log delle modifiche ─────────────────────────────────────────

def scrivi_log(log: dict) -> None:
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    riga = {
        "data": datetime.now(timezone.utc).isoformat(),
        **log,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(riga, ensure_ascii=False) + "\n")


# ── Main ─────────────────────────────────────────────────────────

def main():
    percorso_py = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SCRIPT_PY)
    percorso_html = Path(sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PROMPT_HTML)

    if not percorso_py.exists():
        print(f"✗ File Python non trovato: {percorso_py}")
        sys.exit(1)
    if not percorso_html.exists():
        print(f"✗ File prompt.html non trovato: {percorso_html}")
        sys.exit(1)

    testo_py = percorso_py.read_text(encoding="utf-8")
    testo_html = percorso_html.read_text(encoding="utf-8")

    repertorio_attuale = estrai_repertorio(testo_py)
    categorie = parse_categorie(repertorio_attuale)

    print(f"→ Repertorio attuale: {len(categorie)} categorie")
    print("→ Chiamo Claude per generare fonti nuove...")
    espansione = genera_fonti_nuove(categorie)

    categorie_aggiornate, log = fondi_repertorio(categorie, espansione)

    if not log["fonti_aggiunte"] and not log["categoria_nuova"]:
        print("✗ Nessuna aggiunta valida generata — file non modificati.")
        scrivi_log(log)
        sys.exit(0)

    nuovo_repertorio = ricostruisci_repertorio_testo(categorie_aggiornate)
    nuovo_testo_py = scrivi_repertorio_nel_py(testo_py, nuovo_repertorio)
    percorso_py.write_text(nuovo_testo_py, encoding="utf-8")

    html_fonti = genera_html(categorie_aggiornate)
    nuovo_testo_html = aggiorna_html(testo_html, html_fonti)
    percorso_html.write_text(nuovo_testo_html, encoding="utf-8")

    scrivi_log(log)

    print(f"✓ Aggiunte {len(log['fonti_aggiunte'])} fonti a categorie esistenti")
    if log["categoria_nuova"]:
        print(f"✓ Nuova categoria: {log['categoria_nuova']['titolo']} "
              f"({len(log['categoria_nuova']['fonti'])} fonti)")
    if log["saltate"]:
        print(f"⚠ Scartate: {log['saltate']}")
    print(f"✓ {percorso_py} e {percorso_html} aggiornati. Log in {LOG_FILE}")


if __name__ == "__main__":
    main()

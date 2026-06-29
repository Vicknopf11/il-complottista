# Il Complottista — Artificioso

> «Se non hai un complotto hai un complesso.»

Sito satirico di teorie del complotto interamente inventate, generato ogni mattina
dal Prof. Anacleto Winston Vex'laar Tramontana-Bermúdez detto "il Muto" —
con l'ausilio dell'intelligenza artificiale.

⚠️ **Tutti i complotti sono falsi. È satira.**

## Setup

### 1. Crea il repository su GitHub
- Nome: `il-complottista`
- Visibilità: **Public**
- Niente README, niente .gitignore

### 2. Carica i file
```bash
git init
git add .
git commit -m "primo dossier"
git branch -M main
git remote add origin https://github.com/TUO_USERNAME/il-complottista.git
git push -u origin main
```

### 3. Aggiungi la chiave API
Settings → Secrets and variables → Actions → New repository secret
- Nome: `ANTHROPIC_API_KEY`
- Valore: la tua chiave `sk-ant-...`

### 4. Attiva GitHub Pages
Settings → Pages → Branch: `main` → Cartella: `/docs` → Save

### 5. Prima esecuzione
Actions → "Genera Dossier" → Run workflow

Il sito sarà live su: `https://TUO_USERNAME.github.io/il-complottista/`

## Struttura
```
il-complottista/
├── .github/workflows/genera-dossier.yml
├── docs/
│   ├── index.html
│   ├── chi-siamo.html
│   ├── posts.json
│   └── feed.xml (generato automaticamente)
├── genera.py
└── README.md
```

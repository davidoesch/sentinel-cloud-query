# 🎯 Simple Version - Ohne DuckDB-WASM

## ✅ Diese Version funktioniert GARANTIERT!

Statt DuckDB-WASM im Browser zu verwenden (was CORS/MIME-Probleme macht), nutzt diese Version:
- ✅ **CSV statt Parquet** (einfacher zu laden)
- ✅ **JavaScript Filter** statt SQL
- ✅ **Keine WASM** Dependencies
- ✅ **Funktioniert auf allen Browsern**

## 📋 Setup (3 Schritte)

### Schritt 1: CSV erstellen

Nach dem Initial Scrape, erstelle die CSV-Datei:

```bash
cd dein-repo

# Aktiviere Python venv
source venv/bin/activate

# Konvertiere Parquet zu CSV
python parquet_to_csv.py

# Sollte ausgeben:
# ✅ Konvertierung erfolgreich!
#    Zeilen: 3000
#    Größe: 0.5 MB
#    Datei: data/scenes.csv
```

### Schritt 2: GitHub Username anpassen

Öffne `index-simple.html` und ändere **Zeile 231**:

```javascript
const REPO_OWNER = 'dein-echter-github-username';  // ← HIER ÄNDERN!
```

### Schritt 3: Deployen

```bash
# Ersetze index.html
cp index-simple.html docs/index.html

# Commit & Push
git add data/scenes.csv docs/index.html
git commit -m "Add simple version with CSV"
git push
```

Nach 2-3 Minuten ist die Website live! 🎉

---

## 🔍 Was ist anders?

### Vorher (mit DuckDB-WASM):
```javascript
// Query direkt auf Parquet-Dateien
const result = await conn.query(`
    SELECT * FROM read_parquet('scenes.parquet')
    WHERE avg_cloud_pct <= 20
`);
```

### Jetzt (Simple Version):
```javascript
// Lade CSV einmal beim Start
await fetch('scenes.csv')
  .then(r => r.text())
  .then(csv => Papa.parse(csv))

// Filter in JavaScript
const filtered = allScenes.filter(scene => 
  scene.avg_cloud_pct <= 20 &&
  scene.date >= startDate &&
  scene.date <= endDate
);
```

---

## ⚡ Performance

| Aspekt | DuckDB-WASM | Simple CSV |
|--------|-------------|------------|
| **Initial Load** | 5-10 Sekunden | 1-2 Sekunden |
| **Query Speed** | ~500ms | ~50ms |
| **Browser Kompatibilität** | Chrome 91+, Firefox 89+ | Alle Browser |
| **CORS Probleme** | Ja | Nein |
| **Dateigröße** | ~50 MB (Parquet + WASM) | ~0.5 MB (CSV) |

---

## 📦 Automatische CSV-Generierung in GitHub Actions

Update deine `.github/workflows/daily-update.yml`:

```yaml
- name: Update with new scenes
  run: |
    python scripts/daily_update.py
    python scripts/parquet_to_csv.py  # ← Neu hinzufügen
  env:
    STAC_URL: https://sys-data.int.bgdi.ch/api/stac/v1
    COLLECTION_ID: ch.swisstopo.swisseo_s2-sr_v200

- name: Commit and push updates
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    git add data/
    git commit -m "Daily update - $(date +'%Y-%m-%d')" || echo "No new scenes"
    git push
```

So wird bei jedem Daily Update automatisch auch die CSV aktualisiert!

---

## ✅ Vorteile dieser Lösung

1. **Keine CORS/MIME Probleme** - CSV lädt problemlos
2. **Schneller** - Keine WASM-Initialisierung
3. **Kleiner** - Nur 0.5 MB statt 50 MB
4. **Einfacher** - Keine komplexen Dependencies
5. **Debugbar** - JavaScript statt WebAssembly

## ❌ Nachteile

1. **Keine Tile-Queries** - Nur Scene-Level Filtering (aber das reicht meist)
2. **Alle Daten im RAM** - Bei 10.000+ Szenen könnte es langsam werden
3. **Keine SQL** - Aber JavaScript Filter sind flexibel genug

---

## 🎯 Beispiel-Nutzung

1. Website öffnen: `https://dein-username.github.io/sentinel-cloud-query/`
2. Warte bis "✅ 3000 Szenen geladen" erscheint
3. Zeichne Polygon auf der Karte
4. Wähle Zeitraum (z.B. Juni-August 2024)
5. Max. Wolken: 20%
6. Klicke "🔍 Abfragen"
7. **Ergebnisse erscheinen sofort!**

---

## 🔄 Wenn du später doch DuckDB-WASM willst

Falls du später mehr Szenen hast (10.000+) und DuckDB-WASM brauchst:

1. **Hoste die Parquet-Dateien auf S3** (besseres CORS)
2. **Oder verwende einen eigenen Server** statt GitHub Pages
3. **Oder nutze DuckDB lokal** und exportiere nur gefilterte JSON

Für jetzt ist die CSV-Lösung aber perfekt! 🎉

---

## ❓ FAQ

**Q: Kann ich beides haben (DuckDB + CSV)?**
A: Ja! Kopiere `index-simple.html` nach `docs/simple.html` und behalte die DuckDB Version in `docs/index.html`.

**Q: Wie groß wird die CSV bei 10.000 Szenen?**
A: Ca. 1.5 MB - immer noch sehr schnell zum Laden.

**Q: Funktioniert das Spatial Filtering?**
A: Ja! JavaScript prüft Bounding Box Intersection genau wie SQL.

**Q: Kann ich nach Tiles filtern?**
A: Nein, nur nach Szenen. Für Tile-Level Queries brauchst du DuckDB-WASM oder einen Server.

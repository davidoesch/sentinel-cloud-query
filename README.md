# Sentinel-2 Cloud Cover Query 🛰️

Serverless Abfrage von Wolkenbedeckung für Schweizer Sentinel-2 Szenen.

## Features

- 🛰️ **Tägliche Updates** via GitHub Actions
- 📊 **DuckDB-WASM** im Browser - kein Backend nötig
- 🇨🇭 **Swiss STAC Catalog** Integration
- ⚡ **Schnelle Queries** über Parquet-Dateien
- 🎯 **1km×1km Auflösung** für präzise Wolkenstatistiken

## Live Demo

👉 **https://YOUR-GITHUB-USERNAME.github.io/sentinel-cloud-query/**

_(Nach dem Setup verfügbar)_

## Schnellstart

### 1. Repository Setup

```bash
# Fork oder Clone dieses Repo
git clone https://github.com/YOUR-USERNAME/sentinel-cloud-query.git
cd sentinel-cloud-query

# Python Environment erstellen (empfohlen)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Dependencies installieren
pip install -r scripts/requirements.txt
```

### 2. Initial Scrape

**Option A: Lokal ausführen** (empfohlen für ersten Test)

```bash
python scripts/initial_scrape.py
```

Dies erstellt:
- `data/scenes.parquet` - Metadaten aller Szenen
- `data/tiles/` - 1km×1km Wolken-Tiles

**Option B: Via GitHub Actions** (für volle Automation)

1. Push zu GitHub
2. Gehe zu: Actions → "Initial STAC Scrape" → "Run workflow"

⚠️ **Wichtig**: Der Initial Scrape kann 1-3 Stunden dauern (je nach Anzahl Szenen).

### 3. GitHub Pages aktivieren

1. Repository Settings → Pages
2. Source: `main` branch, `/docs` folder
3. Save

Website verfügbar unter: `https://YOUR-USERNAME.github.io/sentinel-cloud-query/`

### 4. HTML anpassen

In `docs/index.html` **Zeile 259-260** anpassen:

```javascript
const REPO_OWNER = 'YOUR-GITHUB-USERNAME';  // ← Hier deinen Username eintragen!
const REPO_NAME = 'sentinel-cloud-query';
```

### 5. Commit & Push

```bash
git add .
git commit -m "Initial setup complete"
git push
```

## Nutzung

### Website

1. Öffne deine GitHub Pages URL
2. Warte bis "✅ Bereit" angezeigt wird
3. Wähle Zeitraum und maximale Wolkenbedeckung
4. Klicke "🔍 Abfragen"

### Lokale Entwicklung

```bash
# Teste Verarbeitung einzelner Szene
python -c "
from scripts.process_cloudmask import process_cloudmask_cog
tiles, summary = process_cloudmask_cog(
    'https://sys-data.int.bgdi.ch/ch.swisstopo.swisseo_s2-sr_v200/2025-01-18t103351/swisseo_s2-sr_v200_mosaic_2025-01-18t103351_cloudmask_10m.tif',
    'test_scene',
    '2025-01-18'
)
print(f'Processed {len(tiles)} tiles')
print(f'Avg cloud: {summary[\"avg_cloud_pct\"]}%')
"
```

## Automatische Updates

Die GitHub Action läuft **täglich um 3 Uhr UTC** automatisch und:
1. Holt neue Szenen der letzten 2 Tage aus dem STAC Catalog
2. Verarbeitet Cloud Masks zu 1km×1km Tiles
3. Updated die Parquet-Dateien
4. Committed die Änderungen

### Manuelles Update auslösen

Actions → "Daily Cloud Mask Update" → "Run workflow"

## Datenstruktur

```
data/
├── scenes.parquet              # Scene-Metadaten
│   ├── scene_id               # z.B. "swisseo_s2-sr_v200_mosaic_2025-01-18t103351"
│   ├── date                   # Aufnahmedatum
│   ├── cog_url                # URL zur Cloud Mask
│   ├── avg_cloud_pct          # Durchschn. Wolkenbedeckung
│   ├── total_tiles            # Anzahl 1km-Kacheln
│   └── bounds_*               # Bounding Box
│
└── tiles/                      # Partitioniert nach scene_id
    └── scene_id=XXX/
        └── data.parquet       # 1km×1km Wolken-Tiles
            ├── tile_row       # Kachel-Position
            ├── tile_col
            ├── cloud_pct      # Wolkenbedeckung dieser Kachel
            └── min_x, max_x, min_y, max_y  # Koordinaten
```

## Technologie Stack

- **Python 3.11+** für Processing
- **DuckDB** für Analytics & Parquet-Export
- **Rasterio** für COG-Verarbeitung
- **pystac-client** für STAC Catalog Zugriff
- **DuckDB-WASM** für Browser-Queries
- **GitHub Actions** für Automation
- **GitHub Pages** für Hosting

## Konfiguration

### Umgebungsvariablen

```bash
# STAC Endpoint (optional, hat Defaults)
export STAC_URL="https://sys-data.int.bgdi.ch/api/stac/v1"
export COLLECTION_ID="ch.swisstopo.swisseo_s2-sr_v200"
```

### Anpassen der Prozessierung

In `scripts/initial_scrape.py`:

```python
MAX_SCENES = 3000  # Limit für initiales Scraping
```

In `scripts/process_cloudmask.py`:

```python
tile_size_pixels = 100  # 1km bei 10m Auflösung
                        # Ändern für andere Auflösungen
```

## Troubleshooting

### "No scenes found" beim Initial Scrape

- Überprüfe STAC URL und Collection ID
- Teste manuell: https://sys-data.int.bgdi.ch/api/stac/v1/collections/ch.swisstopo.swisseo_s2-sr_v200

### GitHub Actions schlägt fehl

- Überprüfe Logs unter: Actions → Failed workflow → View logs
- Häufigste Ursache: Dependencies fehlen → Check requirements.txt

### Website zeigt "Fehler" beim Laden

- Überprüfe dass GitHub Pages aktiviert ist
- Check Browser Console für Fehler (F12)
- Stelle sicher dass `REPO_OWNER` in index.html korrekt ist
- CORS: Parquet-Dateien müssen öffentlich lesbar sein

### DuckDB Memory Error

- GitHub Actions haben 7GB RAM Limit
- Bei zu vielen Szenen: Batch Size reduzieren in initial_scrape.py:
  ```python
  if len(batch_scenes) >= 25:  # Statt 50
  ```

## Performance

- Initial Scrape: ~1-3 Stunden für 3000 Szenen
- Daily Update: ~5-15 Minuten
- Website Query: <2 Sekunden für typische Abfragen
- Datengröße: ~50-100 MB Parquet für 3000 Szenen

## Lizenz

MIT License

## Contributing

Pull Requests willkommen! Bitte:
1. Fork das Repo
2. Erstelle Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit deine Änderungen (`git commit -m 'Add AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne Pull Request

## Support

- 🐛 Bugs: [GitHub Issues](https://github.com/YOUR-USERNAME/sentinel-cloud-query/issues)
- 💬 Fragen: [GitHub Discussions](https://github.com/YOUR-USERNAME/sentinel-cloud-query/discussions)

## Datenquelle

Daten von [swisstopo SwissEO](https://www.swisstopo.admin.ch/de/satellite-images-swisseo):
- **Collection**: ch.swisstopo.swisseo_s2-sr_v200
- **STAC Catalog**: https://sys-data.int.bgdi.ch/
- **License**: Free for use with attribution

---

Made with ❤️ for Swiss Earth Observation

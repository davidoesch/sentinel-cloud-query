"""
Tägliches Update: Holt neue Szenen und fügt sie zur DuckDB hinzu
"""
import os
import duckdb
import pandas as pd
from datetime import datetime, timedelta
from pystac_client import Client
from process_cloudmask import process_cloudmask_cog
from pathlib import Path

STAC_URL = os.getenv('STAC_URL', 'https://sys-data.int.bgdi.ch/api/stac/v1')
COLLECTION_ID = os.getenv('COLLECTION_ID', 'ch.swisstopo.swisseo_s2-sr_v200')
DATA_DIR = Path('data')

def fetch_new_scenes(days_back=2):
    """
    Holt Szenen der letzten N Tage
    (days_back=2 um sicherzugehen dass nichts verpasst wird)
    """
    catalog = Client.open(STAC_URL)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"Searching for scenes from {start_date.date()} to {end_date.date()}")
    
    search = catalog.search(
        collections=[COLLECTION_ID],
        datetime=f"{start_date.isoformat()}Z/{end_date.isoformat()}Z"
    )
    
    items = []
    for item in search.items():
        # Cloud Mask Asset finden (enthält "cloudmask" im Namen oder Title)
        cloudmask_asset = None
        for asset_key, asset in item.assets.items():
            if 'cloudmask' in asset_key.lower() or \
               (asset.title and 'cloud mask' in asset.title.lower()):
                cloudmask_asset = asset
                break
        
        if cloudmask_asset:
            items.append({
                'scene_id': item.id,
                'date': datetime.fromisoformat(item.properties['datetime'].replace('Z', '')).date(),
                'cog_url': cloudmask_asset.href
            })
    
    print(f"Found {len(items)} new scenes")
    return items

def update_database(new_scenes):
    """Fügt neue Szenen zur bestehenden Datenbank hinzu"""
    if not new_scenes:
        print("No new scenes to add")
        return
    
    # Lade bestehende Datenbank
    conn = duckdb.connect(':memory:')
    
    # Lade bestehende Parquet-Dateien
    scenes_file = DATA_DIR / 'scenes.parquet'
    
    if scenes_file.exists():
        # Importiere bestehende Daten
        conn.execute(f"""
            CREATE TABLE scenes AS 
            SELECT * FROM read_parquet('{scenes_file}')
        """)
        
        conn.execute(f"""
            CREATE TABLE cloud_tiles AS 
            SELECT * FROM read_parquet('{DATA_DIR}/tiles/*/*.parquet')
        """)
        
        # Hole bereits vorhandene scene_ids
        existing_ids = set(row[0] for row in conn.execute("SELECT scene_id FROM scenes").fetchall())
    else:
        # Erste Daten - erstelle neue Tabellen
        conn.execute("""
            CREATE TABLE scenes (
                scene_id VARCHAR PRIMARY KEY,
                date DATE,
                cog_url VARCHAR,
                total_tiles INTEGER,
                avg_cloud_pct FLOAT,
                min_cloud_pct FLOAT,
                max_cloud_pct FLOAT,
                bounds_min_x DOUBLE,
                bounds_min_y DOUBLE,
                bounds_max_x DOUBLE,
                bounds_max_y DOUBLE,
                crs VARCHAR
            )
        """)
        
        conn.execute("""
            CREATE TABLE cloud_tiles (
                scene_id VARCHAR,
                date DATE,
                tile_row INTEGER,
                tile_col INTEGER,
                center_x DOUBLE,
                center_y DOUBLE,
                min_x DOUBLE,
                min_y DOUBLE,
                max_x DOUBLE,
                max_y DOUBLE,
                cloud_pct FLOAT,
                valid_pixel_pct FLOAT
            )
        """)
        
        existing_ids = set()
    
    # Filter neue Szenen
    new_scenes = [s for s in new_scenes if s['scene_id'] not in existing_ids]
    
    if not new_scenes:
        print("All scenes already in database")
        return
    
    print(f"Adding {len(new_scenes)} new scenes...")
    
    # Verarbeite neue Szenen
    new_scene_summaries = []
    new_tiles = []
    
    for idx, scene in enumerate(new_scenes, 1):
        print(f"Processing {idx}/{len(new_scenes)}: {scene['scene_id']}")
        
        tiles, summary = process_cloudmask_cog(
            scene['cog_url'],
            scene['scene_id'],
            str(scene['date'])
        )
        
        if summary:
            new_scene_summaries.append(summary)
            new_tiles.extend(tiles)
    
    # Insert neue Daten
    if new_scene_summaries:
        scenes_df = pd.DataFrame(new_scene_summaries)
        conn.execute("INSERT INTO scenes SELECT * FROM scenes_df")
        
        tiles_df = pd.DataFrame(new_tiles)
        conn.execute("INSERT INTO cloud_tiles SELECT * FROM tiles_df")
        
        print(f"✓ Added {len(new_scene_summaries)} scenes, {len(new_tiles)} tiles")
    
    # Re-export zu Parquet
    print("Exporting updated database...")
    
    conn.execute(f"""
        COPY (SELECT * FROM scenes ORDER BY date DESC)
        TO '{DATA_DIR}/scenes.parquet'
        (FORMAT PARQUET, COMPRESSION 'ZSTD', ROW_GROUP_SIZE 10000)
    """)
    
    tiles_dir = DATA_DIR / 'tiles'
    tiles_dir.mkdir(exist_ok=True)
    
    conn.execute(f"""
        COPY (SELECT * FROM cloud_tiles ORDER BY scene_id, tile_row, tile_col)
        TO '{tiles_dir}'
        (FORMAT PARQUET, PARTITION_BY (scene_id), COMPRESSION 'ZSTD', ROW_GROUP_SIZE 5000)
    """)
    
    # Statistik
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total_scenes,
            MAX(date) as latest_date
        FROM scenes
    """).fetchone()
    
    print(f"\n✅ Database updated: {stats[0]:,} total scenes (latest: {stats[1]})")
    
    conn.close()

if __name__ == '__main__':
    print("Starting daily update...")
    new_scenes = fetch_new_scenes(days_back=2)
    update_database(new_scenes)
    print("\n✅ Daily update complete!")

"""
Initiales Scraping aller Cloud Masks vom STAC Endpoint
"""
import os
import duckdb
import pandas as pd
from datetime import datetime
from pystac_client import Client
from process_cloudmask import process_cloudmask_cog
from pathlib import Path

STAC_URL = os.getenv('STAC_URL', 'https://sys-data.int.bgdi.ch/api/stac/v1')
COLLECTION_ID = os.getenv('COLLECTION_ID', 'ch.swisstopo.swisseo_s2-sr_v200')
DATA_DIR = Path('data')
MAX_SCENES = 3000  # Limit für initiales Scraping

def fetch_all_scenes():
    """Holt alle Szenen vom STAC Endpoint"""
    print(f"Connecting to STAC: {STAC_URL}")
    catalog = Client.open(STAC_URL)
    
    print(f"Searching collection: {COLLECTION_ID}")
    search = catalog.search(
        collections=[COLLECTION_ID],
        max_items=MAX_SCENES
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
    
    print(f"Found {len(items)} scenes")
    return items

def build_initial_database(scenes):
    """Baut die initiale DuckDB Datenbank"""
    DATA_DIR.mkdir(exist_ok=True)
    
    # Temporäre In-Memory DuckDB
    conn = duckdb.connect(':memory:')
    
    # Tabellen erstellen
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
    
    # Verarbeite Szenen in Batches
    batch_scenes = []
    batch_tiles = []
    
    for idx, scene in enumerate(scenes, 1):
        print(f"Processing {idx}/{len(scenes)}: {scene['scene_id']}")
        
        tiles, summary = process_cloudmask_cog(
            scene['cog_url'],
            scene['scene_id'],
            str(scene['date'])
        )
        
        if summary:
            batch_scenes.append(summary)
            batch_tiles.extend(tiles)
        
        # Insert alle 50 Szenen
        if len(batch_scenes) >= 50 or idx == len(scenes):
            if batch_scenes:
                scenes_df = pd.DataFrame(batch_scenes)
                conn.execute("INSERT INTO scenes SELECT * FROM scenes_df")
                
                tiles_df = pd.DataFrame(batch_tiles)
                conn.execute("INSERT INTO cloud_tiles SELECT * FROM tiles_df")
                
                print(f"  ✓ Inserted {len(batch_scenes)} scenes, {len(batch_tiles)} tiles")
                
                batch_scenes = []
                batch_tiles = []
    
    # Exportiere zu Parquet
    print("\nExporting to Parquet...")
    
    # Scenes
    conn.execute(f"""
        COPY (SELECT * FROM scenes ORDER BY date DESC)
        TO '{DATA_DIR}/scenes.parquet'
        (FORMAT PARQUET, COMPRESSION 'ZSTD', ROW_GROUP_SIZE 10000)
    """)
    
    # Tiles partitioniert nach scene_id
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
            MIN(date) as earliest,
            MAX(date) as latest,
            AVG(avg_cloud_pct) as avg_cloud,
            SUM(total_tiles) as total_tiles
        FROM scenes
    """).fetchone()
    
    print(f"\n{'='*70}")
    print(f"Initial Database Created:")
    print(f"  Scenes: {stats[0]:,}")
    print(f"  Date Range: {stats[1]} to {stats[2]}")
    print(f"  Avg Cloud: {stats[3]:.1f}%")
    print(f"  Total Tiles: {stats[4]:,}")
    print(f"{'='*70}")
    
    conn.close()

if __name__ == '__main__':
    print("Starting initial STAC scrape...")
    scenes = fetch_all_scenes()
    
    if scenes:
        build_initial_database(scenes)
        print("\n✅ Initial scrape complete!")
    else:
        print("\n❌ No scenes found!")
        exit(1)

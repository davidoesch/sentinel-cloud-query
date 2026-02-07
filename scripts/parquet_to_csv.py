#!/usr/bin/env python3
"""
Konvertiert scenes.parquet zu scenes.csv für die simple HTML Version
"""
import duckdb
from pathlib import Path

def parquet_to_csv():
    """Konvertiert scenes.parquet zu scenes.csv"""
    
    data_dir = Path('data')
    parquet_file = data_dir / 'scenes.parquet'
    csv_file = data_dir / 'scenes.csv'
    
    if not parquet_file.exists():
        print(f"❌ {parquet_file} nicht gefunden!")
        print("Führe erst initial_scrape.py aus.")
        return
    
    print(f"Konvertiere {parquet_file} zu {csv_file}...")
    
    conn = duckdb.connect(':memory:')
    
    # Lese Parquet und schreibe CSV
    conn.execute(f"""
        COPY (
            SELECT 
                scene_id,
                date,
                cog_url,
                avg_cloud_pct,
                total_tiles,
                bounds_min_x,
                bounds_min_y,
                bounds_max_x,
                bounds_max_y
            FROM read_parquet('{parquet_file}')
            ORDER BY date DESC
        )
        TO '{csv_file}'
        (HEADER, DELIMITER ',')
    """)
    
    # Statistik
    row_count = conn.execute(f"SELECT COUNT(*) FROM read_csv('{csv_file}')").fetchone()[0]
    file_size = csv_file.stat().st_size / 1024 / 1024
    
    print(f"✅ Konvertierung erfolgreich!")
    print(f"   Zeilen: {row_count:,}")
    print(f"   Größe: {file_size:.2f} MB")
    print(f"   Datei: {csv_file}")
    
    conn.close()

if __name__ == '__main__':
    parquet_to_csv()

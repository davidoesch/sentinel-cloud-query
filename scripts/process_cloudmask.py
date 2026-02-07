"""
Helper functions für Cloud Mask Verarbeitung
"""
import rasterio
import numpy as np
from typing import Dict, List, Tuple

def process_cloudmask_cog(cog_url: str, scene_id: str, acquisition_date: str) -> Tuple[List[Dict], Dict]:
    """
    Verarbeitet ein Cloud Mask COG und erstellt 1km×1km Tiles

    Args:
        cog_url: URL zum Cloud Mask COG
        scene_id: Szenen-ID
        acquisition_date: Aufnahmedatum (YYYY-MM-DD)

    Returns:
        tiles: Liste von Tile-Dicts
        scene_summary: Summary-Dict für die Szene
    """
    tiles = []
    scene_summary = {
        'scene_id': scene_id,
        'date': acquisition_date,
        'cog_url': cog_url,
        'total_tiles': 0,
        'avg_cloud_pct': 0,
        'min_cloud_pct': 100,
        'max_cloud_pct': 0
    }

    try:
        with rasterio.open(cog_url) as src:
            # 1km bei 10m Auflösung = 100 Pixel
            tile_size_pixels = 100

            data = src.read(1)
            transform = src.transform
            crs = src.crs.to_string()

            height, width = data.shape
            cloud_percentages = []

            # Iteriere über 1km Tiles
            for row in range(0, height, tile_size_pixels):
                for col in range(0, width, tile_size_pixels):
                    window_height = min(tile_size_pixels, height - row)
                    window_width = min(tile_size_pixels, width - col)

                    tile_data = data[row:row+window_height, col:col+window_width]

                    # Wolkenpixel zählen (Werte 1 und 2 sind Wolken)
                    total_pixels = tile_data.size
                    cloud_pixels = np.isin(tile_data, [1, 2]).sum()
                    valid_pixels = (tile_data > 0).sum()  # Keine NoData

                    if valid_pixels == 0:
                        continue  # Skip leere Kacheln

                    cloud_pct = (cloud_pixels / valid_pixels) * 100
                    cloud_percentages.append(cloud_pct)

                    # Bounding Box der Kachel
                    min_x, max_y = transform * (col, row)
                    max_x, min_y = transform * (col + window_width, row + window_height)

                    tiles.append({
                        'scene_id': scene_id,
                        'date': acquisition_date,
                        'tile_row': row // tile_size_pixels,
                        'tile_col': col // tile_size_pixels,
                        'center_x': (min_x + max_x) / 2,
                        'center_y': (min_y + max_y) / 2,
                        'min_x': min_x,
                        'min_y': min_y,
                        'max_x': max_x,
                        'max_y': max_y,
                        'cloud_pct': round(cloud_pct, 2),
                        'valid_pixel_pct': round((valid_pixels / total_pixels) * 100, 2)
                    })

            # Scene Summary berechnen
            if cloud_percentages:
                scene_summary['total_tiles'] = len(cloud_percentages)
                scene_summary['avg_cloud_pct'] = round(np.mean(cloud_percentages), 2)
                scene_summary['min_cloud_pct'] = round(np.min(cloud_percentages), 2)
                scene_summary['max_cloud_pct'] = round(np.max(cloud_percentages), 2)
                scene_summary['bounds_min_x'] = min(t['min_x'] for t in tiles)
                scene_summary['bounds_min_y'] = min(t['min_y'] for t in tiles)
                scene_summary['bounds_max_x'] = max(t['max_x'] for t in tiles)
                scene_summary['bounds_max_y'] = max(t['max_y'] for t in tiles)
                scene_summary['crs'] = crs

        return tiles, scene_summary

    except Exception as e:
        print(f"Error processing {scene_id}: {e}")
        return [], {}

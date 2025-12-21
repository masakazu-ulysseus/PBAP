"""
検出領域の統計分析スクリプト
誤検出（パンターG型_005）と正常検出（パンターG型_001）の領域特性を比較する
"""

import json
import numpy as np
from pathlib import Path

def analyze_results(filename):
    json_path = Path(f'poc/output/{filename}/detection_result.json')
    if not json_path.exists():
        print(f"File not found: {json_path}")
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stats = []
    print(f"\n=== Analysis for {filename} ({len(data['regions'])} regions) ===")
    print(f"{'ID':<4} {'Width':<6} {'Height':<6} {'Area':<8} {'Aspect':<6}")
    print("-" * 40)
    
    for r in data['regions']:
        x, y, w, h = r['bbox']
        area = w * h
        aspect = w / h if h > 0 else 0
        
        print(f"{r['id']:<4} {w:<6} {h:<6} {area:<8} {aspect:.2f}")
        
        stats.append({
            'id': r['id'],
            'w': w,
            'h': h,
            'area': area,
            'aspect': aspect
        })
    return stats

def main():
    # 正常系（正解に近い）
    stats_001 = analyze_results('パンターG型_001')
    
    # 異常系（誤検出多い）
    stats_005 = analyze_results('パンターG型_005')
    
    # 比較
    print("\n=== Comparison ===")
    
    # 面積の統計
    areas_001 = [s['area'] for s in stats_001]
    areas_005 = [s['area'] for s in stats_005]
    
    print(f"Area (001): Min={min(areas_001)}, Max={max(areas_001)}, Avg={int(np.mean(areas_001))}")
    print(f"Area (005): Min={min(areas_005)}, Max={max(areas_005)}, Avg={int(np.mean(areas_005))}")

    # アスペクト比の統計
    aspects_001 = [s['aspect'] for s in stats_001]
    aspects_005 = [s['aspect'] for s in stats_005]
    
    print(f"Aspect (001): Min={min(aspects_001):.2f}, Max={max(aspects_001):.2f}")
    print(f"Aspect (005): Min={min(aspects_005):.2f}, Max={max(aspects_005):.2f}")

if __name__ == '__main__':
    main()

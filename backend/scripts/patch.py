# import sqlite3

# conn = sqlite3.connect("./data/movies_chroma/chroma.sqlite3")
# cursor = conn.cursor()

# # Remove the custom sentence-transformer embedding and CUDA config
# cursor.execute("UPDATE collections SET config_json_str = NULL WHERE name = 'movie_screenplays';")
# conn.commit()
# conn.close()
# print("Chroma collection metadata patched successfully.")
# print("Collection metadata reset to CPU.")

import sqlite3
from pathlib import Path

db_path = Path("./data/movies_chroma/chroma.sqlite3")
if db_path.exists():
    resolved_path = db_path.resolve()
    print(f"\nFound Chroma DB at: {resolved_path}")
    
    conn = sqlite3.connect(resolved_path)
    cursor = conn.cursor()
    
    # 1. Inspect existing collections & configs
    cursor.execute("SELECT id, name, config_json_str FROM collections;")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} collection(s):")
    for cid, name, cfg in rows:
        print(f"  - [{name}] (ID: {cid}) => Config: {cfg}")
        
    # 2. Update all instances of 'cuda' to 'cpu' directly in the JSON config
    cursor.execute("""
        UPDATE collections 
        SET config_json_str = REPLACE(config_json_str, '"device": "cuda"', '"device": "cpu"')
        WHERE config_json_str LIKE '%cuda%';
    """)
    print(f"Patched {cursor.rowcount} collection(s) in {db_path.name}.")
    
    # Also check collection_metadata table if present
    try:
        cursor.execute("""
            UPDATE collection_metadata 
            SET str_value = 'cpu' 
            WHERE key = 'device' AND str_value = 'cuda';
        """)
        if cursor.rowcount > 0:
            print(f"Patched {cursor.rowcount} entry in collection_metadata.")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    
    # 3. Verify final state
    cursor.execute("SELECT name, config_json_str FROM collections;")
    print("Updated state:")
    for name, cfg in cursor.fetchall():
        print(f"  - [{name}] => Config: {cfg}")
        
    conn.close()
else:
    print(f"Path not found: {db_path.resolve()}")
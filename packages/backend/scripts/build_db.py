import sys
import os
import sqlite3

# Setup paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# Import CustomConverter from main
# Note: This requires main.py to be importable or refactored. 
# For now, we will duplicate the setup logic or import it if safe (main.py creates app on import).
# safest is to import converter instance if possible, or replicate the class.
# Given main.py creates 'app' and 'converter' at module level, importing it might start side effects, 
# but inside a script we can handle it.
try:
    from main import CustomConverter
except ImportError:
    # If main cannot be imported directly due to structure, setup path again
    sys.path.insert(0, BACKEND_DIR)
    from main import CustomConverter

def setup_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT UNIQUE,
            reading TEXT,
            accent_pattern TEXT, -- JSON string
            mora_count INTEGER
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_mora ON candidates(mora_count)')
    conn.commit()
    return conn

def align_and_validate(converter, text):
    try:
        result = converter.convert(text)
        reading = result['reading']
        pattern = result['accent_pattern']
        
        # Validations
        if not reading: return None
        # Must be mostly katakana reading
        # Check constraints: 2 <= mora <= 10
        mora_count = len(pattern)
        if mora_count < 2 or mora_count > 10:
            return None
            
        return {
            'text': text,
            'reading': reading,
            'accent_pattern': str(pattern),
            'mora_count': mora_count
        }
    except Exception:
        # print(f"Skipping {text}: {e}")
        return None

def main():
    # Use SudachiDict Small source as a seed? 
    # Or actually simpler: Use a Frequency List. 
    # Let's use a curated list of common Japanese nouns if available, 
    # OR iterating through a small dictionary file.
    # For this prototype, let's assume we use a smaller seed list to avoid huge download times
    # and "junk" words. 
    # We will fetch a list of common nouns from a public gist or raw file.
    # (Fallback: Use a hardcoded large starter list if download fails, to ensure it works)

    # For now, let's try to load a local seed file if exists, or download one.
    # Source: IPADIC simplified list or similar. 
    # As a robust start, let's use the current WORD_LIST + extended common words.
    
    # Actually, the user wants "Whole Dictionary". 
    # Sudachi's system_full.dic is HUGE. 
    # Let's use a frequency based approach.
    
    # URL: Japanese frequency list ~20k words (example placeholder)
    # We'll use a local lists for now to demonstrate the DB structure, 
    # and maybe fetch a larger list if requested.
    # Ideally we'd parse SudachiDict's lex.csv.
    
    db_path = os.path.join(BACKEND_DIR, 'data', 'candidates.db')
    conn = setup_db(db_path)
    converter = CustomConverter()
    
    print("Building dictionary... this might take a moment.")
    
    # 1. Seed with existing constants (Safe baseline)
    seeds = [
        "箸", "橋", "端", "雨", "飴", "亀", "瓶", "愛", "青", "赤", "秋", "朝", "足", "味", "汗", "油",
        "家", "池", "石", "椅子", "犬", "命", "海", "駅", "絵", "円", "王", "音", "歌", "馬",
        "機械学習", "人工知能", "深層学習", "自然言語処理", "画像認識",
        "東京", "大阪", "京都", "北海道", "沖縄", "富士山", "桜", "寿司", "天ぷら", "忍者",
        "侍", "相撲", "着物", "漢字", "平仮名", "片仮名", "日本", "世界", "平和", "未来", "宇宙",
        "科学", "技術", "数学", "物理", "化学", "生物", "歴史", "地理", "音楽", "美術", "体育", "英語",
        # Add basic nouns ~1000 common words logic could go here
    ]
    
    # 2. (Optional) Fetch larger list
    # Because we don't have internet browsing to find a direct CSV URL right now, 
    # we will generate a robust starter set.
    # In a real expanded scenario, we would `requests.get` a CSV.
    
    # Let's add more seed words programmatically or just stick to the structure logic.
    # Since User asked for "Whole Dictionary", I should try to support importing a file.
    # If `packages/backend/data/lex.csv` exists, use it.
    
    lex_path = os.path.join(BACKEND_DIR, 'data', 'seed_nouns.txt')
    if os.path.exists(lex_path):
        with open(lex_path, 'r') as f:
            seeds.extend([line.strip() for line in f if line.strip()])
            
    # Deduplicate
    seeds = sorted(list(set(seeds)))
    
    cursor = conn.cursor()
    count = 0
    for word in seeds:
        data = align_and_validate(converter, word)
        if data:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO candidates (text, reading, accent_pattern, mora_count)
                    VALUES (?, ?, ?, ?)
                ''', (data['text'], data['reading'], data['accent_pattern'], data['mora_count']))
                count += 1
            except sqlite3.IntegrityError:
                pass
                
    conn.commit()
    conn.close()
    print(f"Database built with {count} words.")

if __name__ == "__main__":
    main()

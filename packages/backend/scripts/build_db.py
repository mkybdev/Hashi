import sys
import os
import sqlite3
import argparse

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
    c.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT UNIQUE,
            reading TEXT,
            accent_pattern TEXT, -- JSON string
            mora_count INTEGER
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_mora ON candidates(mora_count)")
    conn.commit()
    return conn


def align_and_validate(converter, text):
    try:
        result = converter.convert(text)
        reading = result["reading"]
        pattern = result["accent_pattern"]

        # Validations
        if not reading:
            return None
        # Must be mostly katakana reading
        # Check constraints: 2 <= mora <= 10
        mora_count = len(pattern)
        if mora_count < 2 or mora_count > 10:
            return None

        return {
            "text": text,
            "reading": reading,
            "accent_pattern": str(pattern),
            "mora_count": mora_count,
        }
    except Exception:
        # print(f"Skipping {text}: {e}")
        return None


def is_noun_via_sudachi(text, converter):
    """Check if a word is a noun using Sudachi tokenization"""
    try:
        from sudachipy import tokenizer, dictionary

        dic = dictionary.Dictionary(dict="small")
        tok = dic.create()
        tokens = tok.tokenize(text, tokenizer.Tokenizer.SplitMode.C)

        # Check if single token and is a noun
        if len(tokens) != 1:
            return False

        pos = tokens[0].part_of_speech()
        # POS format: [品詞大分類, 品詞中分類, ...]
        # 名詞 is the main noun category
        return pos[0] == "名詞" if pos else False
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Build candidates database from a Japanese word frequency corpus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default Leeds Corpus
  python build_db.py
  
  # Use custom corpus file
  python build_db.py --corpus /path/to/your/wordlist.txt
  
  # Specify custom output database path
  python build_db.py --corpus custom.txt --output custom_candidates.db
        """,
    )
    parser.add_argument(
        "--corpus",
        type=str,
        default=os.path.join(BACKEND_DIR, "data", "leeds_frequency.txt"),
        help="Path to corpus file (one word per line, frequency-ordered). Default: data/leeds_frequency.txt",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(BACKEND_DIR, "data", "candidates.db"),
        help="Output database path. Default: data/candidates.db",
    )

    args = parser.parse_args()

    corpus_path = args.corpus
    db_path = args.output

    conn = setup_db(db_path)
    converter = CustomConverter()

    print(f"Building dictionary from corpus: {corpus_path}")

    # Load corpus file
    if not os.path.exists(corpus_path):
        print(f"Error: Corpus file not found at {corpus_path}")
        print("Please provide a valid corpus file path.")
        return

    print(f"Loading corpus from {corpus_path}...")
    with open(corpus_path, "r", encoding="utf-8") as f:
        candidates = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(candidates)} words from corpus")

    print(f"Processing {len(candidates)} unique candidates...")

    cursor = conn.cursor()
    count_total = 0
    count_nouns = 0
    count_valid = 0

    for idx, word in enumerate(candidates):
        if idx % 1000 == 0 and idx > 0:
            print(
                f"  Processed {idx}/{len(candidates)} words... ({count_valid} valid nouns added)"
            )

        count_total += 1

        # Filter 1: Must be a noun (via Sudachi POS tagging)
        if not is_noun_via_sudachi(word, converter):
            continue

        count_nouns += 1

        # Filter 2: Validate accent analysis (mora count constraints, etc.)
        data = align_and_validate(converter, word)
        if not data:
            continue

        # Insert into DB
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO candidates (text, reading, accent_pattern, mora_count)
                VALUES (?, ?, ?, ?)
            """,
                (
                    data["text"],
                    data["reading"],
                    data["accent_pattern"],
                    data["mora_count"],
                ),
            )
            count_valid += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("Database build complete!")
    print(f"  Total candidates processed: {count_total}")
    print(f"  Nouns identified: {count_nouns}")
    print(f"  Valid entries added to DB: {count_valid}")
    print("=" * 60)


if __name__ == "__main__":
    main()

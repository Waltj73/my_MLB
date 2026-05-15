import pandas as pd
import requests
import io
import sys

def reveal_sheet_structure():
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    print("🔄 Connecting to sheet stream...")
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla"}, timeout=10)
        df = pd.read_csv(io.StringIO(response.text), header=None)
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
        
    print("\n=== RAW SHEET SHAPE ===")
    print(f"Total Rows Found: {len(df)}")
    print(f"Total Columns Found: {len(df.columns)}")
    
    print("\n=== FIRST 5 ROWS & 5 COLUMNS OF DATA ===")
    # Slices the exact top-left corner of whatever data is being returned
    preview = df.iloc[:5, :5]
    print(preview.to_string())
    print("========================================")

if __name__ == "__main__":
    reveal_sheet_structure()

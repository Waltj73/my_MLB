import io
import pandas as pd

def quick_diagnostic_test():
    print("🔄 Running manual data diagnostic...")
    
    # --- STEP 1: PASTE A SAMPLE OF YOUR MATCHUPS TAB HERE ---
    # Highlight your headers and 2-3 rows in Google Sheets, copy them, 
    # and paste them exactly between the triple quotes below.
    pasted_data = """Away	Home	Away Proj	Home Proj	Vegas Away	Vegas Home
Team A	Team B	5.5	4.2	-130	+110
Team C	Team D	3.8	6.1	+140	-160
"""

    try:
        # Read the data, detecting tabs or commas automatically
        df = pd.read_csv(io.StringIO(pasted_data.strip()), sep='\t')
        if len(df.columns) == 1:
            df = pd.read_csv(io.StringIO(pasted_data.strip()))
            
        print("\n✅ SUCCESS: Data loaded perfectly into the engine.")
        print("Here is what the app sees:")
        print("-" * 50)
        print(df)
        print("-" * 50)
        print("\nIf you see your teams above, the calculation code is ready to drop in.")
        
    except Exception as e:
        print(f"\n❌ FAILED: Could not read the pasted format. Error: {e}")

if __name__ == "__main__":
    quick_diagnostic_test()

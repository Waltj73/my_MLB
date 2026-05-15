import io
import pandas as pd

def quick_diagnostic_test():
    print("🔄 Running manual data diagnostic...")
    
    # --- STEP 1: PASTE A SAMPLE OF YOUR MATCHUPS TAB HERE ---
    # Highlight your headers and 2-3 rows in Google Sheets, copy them, 
    # and paste them exactly between the triple quotes below.
    pasted_data = """Game1		6:40 PM ET		Money	OU	Record	Profit	O-U-P	RF	RA	EST Score	EST Line		6:40 PM ET	Calc Win%
Away	Philadelphia	Phillies	0	+114		21-23	$-966	22-20-2	4	4.7	3.8	8	PHI	0	43.55%
Home	Pittsburgh	Pirates	0	-137	8	24-20	$-89	24-19-1	5	4.3	4.2	-122	PIT	0	56.45%
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

@st.cache_data(ttl=300)
def fetch_vsin_data():
    scraper = cloudscraper.create_scraper()
    splits_url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    
    try:
        response = scraper.get(splits_url)
        # We specify flavor='bs4' to use BeautifulSoup logic which is more stable
        tables = pd.read_html(response.text, flavor='bs4')
        
        if not tables:
            st.error("No tables found on the page.")
            return pd.DataFrame()

        # VSiN usually has the betting splits in the first table
        df = tables[0]
        
        # CLEANING: VSiN uses Multi-Index headers (Two rows of headers)
        # This flattens them so you can use columns easily
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() for col in df.columns.values]
            
        return df

    except Exception as e:
        # This will now show you if it's a '403 Forbidden' (blocked) 
        # or a 'Missing Library' error
        st.error(f"Technical Detail: {e}")
        return pd.DataFrame()

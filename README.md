# Data Grabber 📊🤛
A Python(3.12)-based utility suite for efficient data aggregation. Most API's that handle large datasets have limits on the volume and quantity of API calls. DataGrabber scripts DO NOT circumvent these limits, but rather aims to minimize the volume/quantity of necessary API calls, maximizing the usage of the allocated calls. 

The **⚪️ Yahoo Finance Data Grabber ⚪️** script can be used for downloading, validating, and maintaining historical stock data from Yahoo Finance. It ensures local CSV caches stay up-to-date, properly formatted, and consistent with Yahoo’s latest data (including dividend and split adjustments). 

### Features ⛮  

+ **Validation** ◻️  
  + Compares cached data against fresh API pulls for consistency.  
  + Detects the impact of **splits** and **dividends** on price history.  
  + Marks CSVs as **reusable** or **outdated** based on `Adj Close` deltas.  
  + Outdated CSVs are backed up (`/data/name_OLD.csv`) before replacement.  

+ **Safe Updates** ◻️  
  + Reuses existing CSVs in `/data` instead of overwriting.  
  + Fetches and stitches only the **missing ranges** of data.  
  + Prepends or appends new data without disrupting valid rows.  
  + Skips unnecessary updates when CSV dates fully match request.  

+ **Dynamic Date Handling** ◻️  
  + Supports **flexible user input** (YTD, explicit start date, etc.).  
  + Ensures proper **trading-day alignment** using `get_next_trading_day` and `get_last_trading_day`.  
  + Prevents invalid ranges (start > end) through CLI safeguards.  

+ **Command-Line Interface (CLI)** ◻️
  + `python DataGrabber.py` → User is prompted for ticker, to update if outdated,then base date
  + `python YF.py <ticker>` → YTD data if missing, append-only if file exists.  
  + `python YF.py <ticker> <YYYY-MM-DD>` → fetches from custom start date if it doesn’t overlap CSV.  
  + Clear separation of **interactive mode** (via DataGrabber.py) vs. **direct calls** (for devs).  

+ **Caching & Backup** ◻️  
  + All datasets saved locally in `/data/`.  
  + Automatic **backup of old data** before replacement.  
  + Cached data validated before being reused.  

+ **Extensible Design** ◻️  
  + Built for modular growth — future scripts for WRDS, AlphaVantage, Eikon, etc.  
  + Consistent interface so both non-devs (via DataGrabber) and devs (via one CL call) can work efficiently.  
  + Follows the principle of **minimizing API calls** without circumventing provider limits.  
  
           
### Dependencies
Conda 🐍
```bash
conda install -c conda-forge 
conda install -c pandas 
conda install -c numpy 
conda install -c plotly 
conda install -c kaleido 
conda install -c pycountry
conda install -c pandas-market-calendars 
conda install -c streamlit 
conda install -c yfinance 
```
```bash
pip install eikon # not available on conda
```

Bash 🐧
```bash
pip install --upgrade pip
pip install yfinance --upgrade --no-cache-dir
pip install pandas
pip install numpy
pip install yfinance
pip install pandas_market_calendars
pip install eikon
pip install streamlit
```
PowerShell 📎
```powershell
python -m pip install --upgrade pip
python -m pip install pandas
python -m pip install numpy
python -m pip install yfinance
python -m pip install pandas_market_calendars
python -m pip install eikon
python -m pip install streamlit
```


### How to Run
  ```bash
  python DataGrabber.py
  ```
  ```bash
  python YF.py <ticker>
  ```
  ```bash
  python YF.py <ticker> <YYYY-MM-DD>
  ```
examples:
  ```bash
  python YF.py AAPL
  ```
  ```bash
  python YF.py MSFT 2024-01-01
  ```

### Future Developments
- **Functionality**: Expand cached data usage. Currently if cached data is deemed 'invalid' due to Adj Close prices the cached data is ignored, instead of ignoring perhaps the new valid Adj Close can simply be calculated using the old data and new Adj data, without making a large API call to fill an empty dataframe.

### Contributions
Gus made DataGrabber suite, integrating APIs, writing scripts, and refining algorithms for efficient data aggregation.




# Data Grabber 📊🤛
A Python(3.12)-based library of scripts for efficient data aggregation. Most API's that handle large datasets have limits on the volume and quantity of API calls. DataGrabber scripts DO NOT circumvent these limits, but rather aims to minimize the volume/quantity of necessary API calls, maximizing the usage of the allocated calls. 

The **⚪️ Yahoo Finance Data Grabber ⚪️** script can be used for downloading, validating, and maintaining historical stock data from Yahoo Finance. It ensures local CSV caches stay up-to-date, properly formatted, and consistent with Yahoo’s latest data (including dividend and split adjustments). 

### Features ⛮
+ **Data Efficiency** ◻️
  + Existing CSVs in /data are reused and only missing ranges of data are fetched.
  + New data getes prepended and/or appended to existing data from the CSV file.
+ **Validation** ◻️
  + Compares cached data against fresh data from on-the-spot API queries.
  + Accounts for splits' and dividends' ability to affect prices
  + If CSV data is **validated** as being "reusable" for current/relevant data(Adj Close price Δ of stocks), then depending on the user's desired time frame, dataframes of fresh data can be prepended and/or appended to data originating from the validated CSV file.
  + If CSV data is **invalidated** as being "outdated" for current/relevant data(Adj Close price Δ of stocks).
  + "Outdated" data is backed up as /data/name_OLD.csv before being replaced with /data/name.csv with new validated data.
+ **Trade Day Awareness** ◻️
  + User-entered dates (even weekends/holidays) are adjusted to valid trading days.
+ **Flexible Input** ◻️
  + Inputs like '24 1 1' → 2024-01-01 & '99 12 31' → 1999-12-31 can be used for specifying dates.
+ **Safe Updates** ◻️
  + If the CSV is valid and entered dates match the dates of the file → no update.
  + If the CSV is valid and entered dates offer a wider range → only missing data is stitched.
  + If the CSV is invalid or missing → a fresh download made it.
    
  
           
### Dependencies
Bash 🐧
```bash
pip install --upgrade pip
pip install yfinance --upgrade --no-cache-dir
pip install pandas
pip install numpy
pip install yfinance
pip install pandas_market_calendars
```
PowerShell 📎
```powershell
python -m pip install --upgrade pip
python -m pip install pandas
python -m pip install numpy
python -m pip install yfinance
python -m pip install pandas_market_calendars
```


### How to Run
  ```bash
  python DataGrabber.py
  ```

### Future Developments
- **Functionality*: Allow for a single command line argument for getting and updating data

### Contributions
Gunnar Balch: Designed and developed the DataGrabber lib, integrating APIs, writing scripts, and refining algorithms for efficient data aggregation.




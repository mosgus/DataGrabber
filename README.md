# Data Grabber 📊🤛
A Python-based(3.12) library of scripts for efficient data aggregation. Most API's that handle large datasets have limits on the volume and quantity of API calls. DataGrabber scripts DO NOT circumvent these limits, but rather aims to minimize the volume/quantity of necessary API calls, maximizing the usage of the allocated calls. 

🟣 A Yahoo Finance Data Grabber script can be used for downloading, validating, and maintaining historical stock data from Yahoo Finance. It ensures local CSV caches stay up-to-date, properly formatted, and consistent with Yahoo’s latest data (including dividend and split adjustments).

### Features ⛮
+ **Data Efficiency**
  + Existing CSVs in /data are reused and only missing ranges are fetched 🟣
  + Data is backed up to /data/<symbol>_OLD.csv before being replaced 🟣
- **Validation**:
        
           
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
Powershell 📎
```powershell
python -m pip install --upgrade pip
python -m pip install pandas
python -m pip install numpy
python -m pip install yfinance
python -m pip install pandas_market_calendars
```


### How to Run
Either simply run 
- Example:
  ```bash
  python YF.py
  ```

### Future Developments
- **Performance**: 

### Contributions
Gunnar Balch: Designed and developed the DataGrabber lib, integrating APIs, writing scripts, and refining algorithms for efficient data aggregation.




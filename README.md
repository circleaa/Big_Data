# MLB Historical Data Scraper (MLB 歷史大數據自動採集系統)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![Data Engineering](https://img.shields.io/badge/Domain-Data_Engineering-FF8C00?style=flat-square)

## Introduction
本系統為大數據工程 (Big Data Engineering) 之實務應用。系統針對 MLB 官方統計網站開發自動化動態爬蟲，完整涵蓋 2003 年至 2023 年（共 21 個賽季）的歷史數據。

目標在擷取並整合多維度指標，建立包含球員打擊、球員投球、球隊打擊與球隊投球之四大核心數據庫，為後續的運動數據分析與機器學習預測模型奠定資料基石。

[完整題目](./HW2.pdf)

## Core Features

1. **動態渲染處理與自動排程 (Dynamic Scraping & Pagination)：**
   * 採用 `Selenium` 進行瀏覽器自動化，解決官方網站高度動態載入的限制。
   * 實作自動偵測與點擊「Next Page」邏輯，遍歷每年度的球員清單。
2. **多維度資料合併 (Multi-dimensional Data Merging)：**
   * MLB 數據分散於 "Standard" 與 "Expanded" 兩種表格。系統於後台自動比對球員/球隊識別碼，實作高效的 Join 邏輯，確保所有維度的指標完美整合至同一筆紀錄中。
3. **反爬蟲突破與例外處理 (Exception Handling & Anti-Scraping)：**
   * 面對伺服器嚴格的防護，系統實作了隨機 `time.sleep` 延遲與客製化 `User-Agent` 替換機制，克服 403 Forbidden 連線拒絕錯誤。
   * 內建網路延遲處理與錯誤重試 (Retry) 機制，確保中斷時能記錄斷點，大幅提升巨量資料採集之穩定度。
4. **資料清洗與正規化 (Data Cleaning)：**
   * 運用 Regex (正規表達式) 處理雜亂字串與欄位格式，確保最終輸出的 CSV 檔案具備正確且一致的欄位命名規範。

## Final Deliverables
系統執行完畢後，會自動產出涵蓋所有年份與指標的 4 份 Master CSV 檔案：
* `mlb_player_hitting_2003_2023.csv`
* `mlb_player_pitching_2003_2023.csv`
* `mlb_team_hitting_2003_2023.csv`
* `mlb_team_pitching_2003_2023.csv`

## Usage
```bash
# 1. 安裝所需套件
pip install selenium pandas

# 2. 執行主程式
python mlb_scraper.py
```

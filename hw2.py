import time
import os
import io
import sys
import re
import pandas as pd
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import unicodedata

def normalize_name(w):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', w)
        if not unicodedata.combining(c)
    )

# 修正 Windows 終端機顯示與編碼問題
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

class MLBScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 正式執行建議開啟
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        
        print(">>> 正在啟動瀏覽器引擎...", flush=True)
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def clean_header(self, df, mode):
        # 先清欄位名稱
        new_cols = []
        for col in df.columns:
            if col in ['Page_Order', 'Row_Order']:
                new_cols.append(col)
                continue

            c = str(col).replace('caret-up', '').replace('caret-down', '').replace('caret', '')
            c = re.sub(r'[\u200b-\u200f\ufeff\xa0]', '', c) 

            # 修正重複名稱
            c = c.replace('TEAMTEAM', 'TEAM').replace('PLAYERPLAYER', 'PLAYER').replace('LEAGUELEAGUE', 'LEAGUE')

            # 使用 re.search 並且「只抓取」開頭的大寫字母與符號
            # 我們移除掉原本的 [a-zA-Z]+，改用只允許大寫、數字與特殊符號的組合
            match = re.search(r'^([A-Z0-9/%\+\.\-]+)', c.strip())
            
            if match:
                cleaned_name = match.group(1)
            else:
                # 如果完全沒匹配到大寫（例如某些全小寫的輔助欄位），才取第一個單字
                cleaned_name = c.split()[0] if c.split() else c
            
            new_cols.append(cleaned_name)
        df.columns = new_cols

        # 再清內容
        if mode == "player": # player的只處理PLAYER欄位
            target_cols = [c for c in ['PLAYER'] if c in df.columns]
        elif mode == "team": # team的只處理TEAM欄位
            target_cols = [c for c in ['TEAM'] if c in df.columns]
        else:
            target_cols = []

        for col in target_cols:
            def fix_content(val):
                s = str(val)

                # 1. 移除隱藏字元
                s = re.sub(r'[\u200b-\u200f\ufeff\xa0]', '', s)

                # 2. 抓排名
                match_num = re.match(r'^(\d+)', s.strip())
                prefix_num = match_num.group(1) if match_num else ''

                # 3. 去頭尾數字
                s = re.sub(r'^\d+', '', s).strip()
                s = re.sub(r'\d+$', '', s).strip()

                # 4. 補空格（基本）
                s = re.sub(r'([a-z\.])([A-Z])', r'\1 \2', s)
                # 砍掉 Jr. 後面的所有東西
                s = re.sub(r'\bJr\..*$', '', s)

                # 5. 拆黏在一起的字（IIHarris / d'Arnaud）
                s = re.sub(r'([a-zA-Z])([A-Z][a-z])', r'\1 \2', s)

                # 6. 刪 position
                s = re.sub(r'\s*(1B|2B|3B|SS|LF|CF|RF|DH|C|P|TWP)$', '', s)

                # 7. 刪 suffix + 後面全部
                s = re.sub(r'\b(Jr\.|Sr\.|II|III|-)\b.*$', '', s)

                # 8. 刪中間縮寫（保留 J.D.）
                s = re.sub(r"\b[A-Z]\b(?![\.'])", '', s)

                # 9. 清孤立點
                s = re.sub(r'\b\.\b', '', s)

                # 10. 清空格
                s = re.sub(r'\s+', ' ', s).strip()

                # 11. 刪重複姓（支援撇號）
                s = re.sub(r"\b([\w']+)\s+\1\b", r"\1", s)

                # 12. 處理多字重複（De La Cruz 類）
                words = s.split()
                n = len(words)

                for i in range(1, n // 2 + 1):
                    left = words[-2*i:-i]
                    right = words[-i:]

                    if [normalize_name(w) for w in left] == [normalize_name(w) for w in right]:
                        words = words[:-i]
                        break

                s = " ".join(words)
                # 修回 deGrom
                s = re.sub(r'\b(de|la|van|von)\s+([A-Z])', lambda m: m.group(1) + m.group(2), s)

                # 13. 補回排名
                if prefix_num:
                    return f"{prefix_num} {s}".strip()
                return s
            df[col] = df[col].apply(fix_content)

        return df
    
    def scrape_table_to_df(self, label="頁面"):
        all_data = []
        page_num = 1
        while True:
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr")))
                time.sleep(random.uniform(1, 3)) 
                html_content = self.driver.page_source
                tables = pd.read_html(io.StringIO(html_content))

                if tables:
                    df_page = tables[0]
                    if not df_page.empty:
                        df_page['Page_Order'] = page_num
                        df_page['Row_Order'] = range(len(df_page))
                        all_data.append(df_page)
                        print(f"      > {label}: 第 {page_num} 頁抓取成功", flush=True)

                first_row_text = self.driver.find_element(By.CSS_SELECTOR, "tbody tr").text
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 5))
                
                next_btns = self.driver.find_elements(By.XPATH, "//button[.//span or contains(., 'Next')]")
                next_btn = None
                for btn in next_btns:
                    if "next" in btn.text.lower() or "next" in (btn.get_attribute("aria-label") or "").lower():
                        next_btn = btn
                        break

                if not next_btn or next_btn.get_attribute("disabled"):
                    break

                self.driver.execute_script("arguments[0].click();", next_btn)
                self.wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "tbody tr").text != first_row_text)
                page_num += 1
                time.sleep(random.uniform(1, 3))
            except:
                break
        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    def get_data_flow(self, year, category, stat_type):
        url = f"https://www.mlb.com/stats/{category}/{stat_type}?season={year}"
        self.driver.get(url)
        time.sleep(random.uniform(2, 4))

        print(f"  [{year}] 讀取 Standard...", flush=True)
        df_std = self.scrape_table_to_df("Standard")

        print(f"  [{year}] 切換 Expanded...", flush=True)
        # 重新載入頁面
        self.driver.get(url)
        time.sleep(random.uniform(2, 4))
        try:
            exp_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Expanded')]"))
            )
            self.driver.execute_script("arguments[0].click();", exp_btn)

            time.sleep(random.uniform(2, 4))

            df_exp = self.scrape_table_to_df("Expanded")
        except:
            df_exp = pd.DataFrame()

        if not df_exp.empty and not df_std.empty:
            df_std = self.clean_header(df_std, category)
            df_exp = self.clean_header(df_exp, category)
            
            keys = ['PLAYER', 'TEAM', 'Page_Order', 'Row_Order']
            keys = [k for k in keys if k in df_std.columns and k in df_exp.columns]
            
            # 確保 Expanded 的新欄位能合併進來
            other_cols = [c for c in df_exp.columns if c not in df_std.columns or c in keys]
            df_final = pd.merge(df_std, df_exp[other_cols], on=keys, how="outer", sort=False)
            return df_final
            
        return self.clean_header(df_std, category) if not df_std.empty else df_std

    def run(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        years = range(2003, 2024) 
        tasks = [
            ("player", "hitting", "mlb_player_hitting_2003_2023.csv"),
            ("player", "pitching", "mlb_player_pitching_2003_2023.csv"),
            ("team", "hitting", "mlb_team_hitting_2003_2023.csv"),
            ("team", "pitching", "mlb_team_pitching_2003_2023.csv")
        ]

        for cat, stat, filename in tasks:
            path = os.path.join(current_dir, filename)
            if os.path.exists(path):
                try: os.remove(path)
                except: return

            print(f"\n>>> 啟動任務: {filename}", flush=True)
            for y in years:
                res = self.get_data_flow(y, cat, stat)
                if not res.empty:
                    res = res.sort_values(by=['Page_Order', 'Row_Order'], ascending=True)
                    res = res.drop(columns=['Page_Order', 'Row_Order'], errors='ignore')
                    res['Season'] = y
                    write_header = not os.path.exists(path)
                    res.to_csv(path, mode='a', index=False, header=write_header, encoding='utf-8-sig')
                    print(f"    [成功] {y} 年完成 (共 {len(res)} 筆)", flush=True)
                time.sleep(random.uniform(5, 10))

    def quit(self):
        self.driver.quit()

if __name__ == "__main__":
    bot = MLBScraper()
    try: bot.run()
    finally:
        bot.quit()
        print("\n>>> 全部完成！ <<<", flush=True)
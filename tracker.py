import os
import json
import gspread
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

print("=== STARTING MULTI-MIRROR RUN ===")

# 1. Authenticate with Google Sheets
try:
    creds_json = json.loads(os.environ.get("GOOGLE_CREDS"))
    sheet_id = os.environ.get("SPREADSHEET_ID")
    
    gc = gspread.service_account_from_dict(creds_json)
    sh = gc.open_by_key(sheet_id)
    
    worksheet = None
    target_name = "incomingposts"
    for ws in sh.worksheets():
        if ws.title.lower().replace(" ", "") == target_name:
            worksheet = ws
            break
    if worksheet is None:
        print("❌ Sheet tab 'IncomingPosts' missing.")
        exit(1)
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

# 2. List of alternative free, unlimited mirrors to bypass the 403 block
MIRRORS = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
    "https://rsshub.moeyy.xyz",
    "https://moelove.info/rsshub"
]

CLIENTS = ["zuck", "mosseri"] 

for username in CLIENTS:
    print(f"\n--- Processing: {username} ---")
    post_found = False
    
    # Try each mirror until one works
    for mirror in MIRRORS:
        try:
            rss_url = f"{mirror}/instagram/user/{username}"
            print(f"Trying mirror: {mirror}")
            
            response = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                latest_item = root.find('./channel/item')
                
                if latest_item is not None:
                    pub_date_str = latest_item.find('pubDate').text
                    post_link = latest_item.find('link').text
                    
                    try:
                        pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                    except ValueError:
                        pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                    
                    time_diff = datetime.utcnow() - pub_date.replace(tzinfo=None)
                    
                    # Set to 100 days for your current live data test
                    if time_diff < timedelta(days=100):
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        worksheet.append_row([timestamp, username, post_link, "PENDING"])
                        print(f"🚀 SUCCESS: Wrote row for {username} using {mirror}")
                    else:
                        print("⏳ Post is older than test window.")
                    
                    post_found = True
                    break # Success! Break the mirror loop and move to next client
            else:
                print(f"⚠️ Mirror responded with code {response.status_code}, trying next one...")
        except Exception as e:
            print(f"❌ Mirror connection failed: {e}")
            
    if not post_found:
        print(f"❌ Critical: All free mirrors failed or were blocked for {username} this run.")

print("\n=== RUN COMPLETE ===")

import os
import json
import gspread
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

print("=== STARTING DIAGNOSTIC RUN ===")

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
        print("❌ ERROR: Could not find the Google Sheet tab named 'IncomingPosts'.")
        exit(1)
    else:
        print("✅ SUCCESS: Successfully connected to your Google Sheet tab!")
        
except Exception as e:
    print(f"❌ CRITICAL AUTH ERROR: {e}")
    exit(1)

# 2. Check the Instagram profiles
CLIENTS = ["zuck", "mosseri"] 
print(f"Tracking profiles: {CLIENTS}")

for username in CLIENTS:
    print(f"\n--- Checking Profile: {username} ---")
    try:
        rss_url = f"https://rsshub.app/instagram/user/{username}"
        print(f"Sending web request to: {rss_url}")
        
        response = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15)
        print(f"Server responded with Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"⚠️ SKIPPED: The public tracker feed is temporarily rate-limited or blocking requests (Status {response.status_code}).")
            continue
            
        root = ET.fromstring(response.content)
        latest_item = root.find('./channel/item')
        
        if latest_item is None:
            print("⚠️ SKIPPED: No post items found inside the feed structure.")
            continue
            
        pub_date_str = latest_item.find('pubDate').text
        post_link = latest_item.find('link').text
        print(f"Found latest post link: {post_link}")
        print(f"Raw post date from feed: {pub_date_str}")
        
        # Parse dates flexibly
        try:
            pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
        except ValueError:
            pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
            
        time_diff = datetime.utcnow() - pub_date.replace(tzinfo=None)
        print(f"Post age calculated: {time_diff.days} days ago.")
        
        # Test window set wide open to 100 days to force data insertion
        if time_diff < timedelta(days=100):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            worksheet.append_row([timestamp, username, post_link, "PENDING"])
            print(f"🚀 SUCCESS: Wrote row for {username} to Google Sheet!")
        else:
            print("⏳ SKIPPED: Post is older than 100 days.")
            
    except Exception as e:
        print(f"❌ ERROR while processing {username}: {e}")

print("\n=== DIAGNOSTIC RUN COMPLETE ===")

import os
import json
import gspread
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# 1. Authenticate with Google Sheets
try:
    creds_json = json.loads(os.environ.get("GOOGLE_CREDS"))
    sheet_id = os.environ.get("SPREADSHEET_ID")
    
    gc = gspread.service_account_from_dict(creds_json)
    sh = gc.open_by_key(sheet_id)
    
    # SMART MATCHING: Loop through all tabs, clean their names, and look for a match
    worksheet = None
    target_name = "incomingposts"
    
    for ws in sh.worksheets():
        # Clean the tab name by making it lowercase and removing all spaces
        cleaned_tab_title = ws.title.lower().replace(" ", "")
        if cleaned_tab_title == target_name:
            worksheet = ws
            break
            
    if worksheet is None:
        # If it still fails, print out exactly what tabs it DID find so we can spot the error
        all_tabs = [w.title for w in sh.worksheets()]
        print(f"Error: Could not find 'IncomingPosts'. Your current sheet tabs are: {all_tabs}")
        exit(1)
        
except Exception as e:
    print(f"Google Authentication Error: {e}")
    exit(1)

# 2. List the usernames of the clients you want to track
CLIENTS = ["zuck", "mosseri"] 

for username in CLIENTS:
    try:
        # Fetch RSS feed
        rss_url = f"https://rsshub.app/instagram/user/{username}"
        response = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            latest_item = root.find('./channel/item')
            
            if latest_item is not None:
                pub_date_str = latest_item.find('pubDate').text
                post_link = latest_item.find('link').text
                
                pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                
                # Check if post was made in the last 15 minutes
                if datetime.utcnow() - pub_date < timedelta(days=100):
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Append directly to Google Sheet row
                    worksheet.append_row([timestamp, username, post_link, "PENDING"])
                    print(f"SUCCESS: Added new post for {username} to Google Sheet.")
                else:
                    print(f"No new posts discovered for {username}.")
    except Exception as e:
        print(f"Error checking profile {username}: {e}")

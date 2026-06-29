import os
import sqlite3
import time
import requests

# --- PHASE 1: DATABASE LOGIC ---
def init_db(db_name="nasa_pipeline.db"):
    """Initializes the local SQLite database and creates the metadata table."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS space_metadata (
            date TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            explanation TEXT,
            url TEXT NOT NULL,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("🗄️ SQLite Database initialized and verified.")

def log_to_database(data, db_name="nasa_pipeline.db"):
    """Logs metadata to SQLite. Prevents duplicates using the PRIMARY KEY (date)."""
    if not data:
        return
        
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        # 'INSERT OR IGNORE' is where the automatic duplicate check happens!
        cursor.execute("""
            INSERT OR IGNORE INTO space_metadata (date, title, explanation, url)
            VALUES (?, ?, ?, ?)
        """, (
            data.get("date"),
            data.get("title"),
            data.get("explanation"),
            data.get("url")
        ))
        conn.commit()
        
        # Check if a row was actually inserted or if it was ignored as a duplicate
        if cursor.rowcount > 0:
            print(f"💾 Successfully logged '{data.get('title')}' into SQLite!")
        else:
            print(f"ℹ️ Date {data.get('date')} already exists in database. Skipping duplicate log.")
            
    except sqlite3.Error as e:
        print(f"❌ Database write error: {e}")
    finally:
        conn.close()


# --- PHASE 2: CORE PIPELINE WITH RETRIES ---
def download_space_photo(api_key="5ZEZKqw8XxfcFQL1884TUagrdZVR2HRwwRZTEXhZ", output_folder="nasa_images"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"📁 Created local folder: {output_folder}")
        
    url = "https://api.nasa.gov/planetary/apod"
    params = {"api_key": api_key}
    
    data = None
    max_retries = 3
    attempt = 0
    
    # --- RETRY LOOP FOR STEP 1 ---
    print("📡 Step 1: Fetching metadata from NASA...")
    while attempt < max_retries:
        attempt += 1
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            print("✅ Metadata Retrieved Successfully!")
            break # Success! Break out of the retry loop.
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                # Exponential backoff: wait 2s, then 4s, then 8s...
                wait_time = 2 ** attempt
                print(f"⏳ Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print("❌ Step 1 Critical Failure: Max retries reached. NASA gateway is unreachable.")
                return None

    # Extract metadata details
    title = data.get("title", "space_photo")
    date = data.get("date", "unknown_date")
    img_url = data.get("hdurl") or data.get("url")
    
    if not img_url:
        print("⚠️ No image URL found in today's payload.")
        return data

    # --- STEP 2: IMAGE DOWNLOAD ---
    print(f"📥 Step 2: Attempting image download from: {img_url}")
    try:
        img_response = requests.get(img_url, stream=True, timeout=15)
        img_response.raise_for_status()
        
        clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
        filename = f"{date}_{clean_title.replace(' ', '_')}.jpg"
        file_path = os.path.join(output_folder, filename)
        
        with open(file_path, "wb") as f:
            for chunk in img_response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"📸 File successfully saved to {file_path}")
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Step 2 Failed: Could not download physical image asset, but we have the text metadata. Error: {e}")

    # --- STEP 3: DATABASE INSERTION ---
    log_to_database(data)
    return data

if __name__ == "__main__":
    init_db()               # 1. Ensure database table exists
    download_space_photo()  # 2. Run the pipeline
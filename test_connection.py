import os
import requests

def download_space_photo(api_key="5ZEZKqw8XxfcFQL1884TUagrdZVR2HRwwRZTEXhZ", output_folder="nasa_images"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"📁 Created local folder: {output_folder}")
        
    url = "https://api.nasa.gov/planetary/apod"
    params = {"api_key": api_key}
    
    try:
        print("📡 Step 1: Fetching metadata from NASA...")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        title = data.get("title", "space_photo")
        date = data.get("date", "unknown_date")
        img_url = data.get("hdurl") or data.get("url")
        
        print(f"🌌 Metadata Retrieved Successfully! Title: '{title}'")
        
        if not img_url:
            print("⚠️ No image URL found in today's payload.")
            return data

        # Step 2: Attempt the image download wrapped in its own try/except block
        print(f"📥 Step 2: Attempting image download from: {img_url}")
        try:
            img_response = requests.get(img_url, stream=True, timeout=10)
            img_response.raise_for_status()
            
            clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
            filename = f"{date}_{clean_title.replace(' ', '_')}.jpg"
            file_path = os.path.join(output_folder, filename)
            
            with open(file_path, "wb") as f:
                for chunk in img_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ Success! Image saved to {file_path}")
            
        except requests.exceptions.HTTPError as http_err:
            if img_response.status_code == 503:
                print("⚠️ Step 2 Skipped: NASA's image hosting asset server (apod.nasa.gov) is currently experiencing a 503 Service Unavailable outtage. We have the text data, but the file cannot be reached right now.")
            else:
                print(f"⚠️ Step 2 Failed: HTTP Error during download: {http_err}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Step 2 Failed: Network issue downloading image: {e}")

        # Return the data anyway so we can still log the text to our database!
        return data

    except requests.exceptions.RequestException as e:
        print(f"❌ Step 1 Critical Failure: Could not connect to the primary API gateway: {e}")
        return None

if __name__ == "__main__":
    download_space_photo()
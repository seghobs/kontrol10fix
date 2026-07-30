import urllib.request
import os

os.makedirs("scratch/old_repo", exist_ok=True)

urls = {
    "session_state.py": "https://raw.githubusercontent.com/seghobs/kontrolyeni-v4/main/app_core/session_state.py",
}

for name, url in urls.items():
    path = f"scratch/old_repo/{name}"
    print(f"Downloading {url} to {path}...")
    try:
        urllib.request.urlretrieve(url, path)
        print("Success!")
    except Exception as e:
        print(f"Failed: {e}")

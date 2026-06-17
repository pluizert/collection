import time
import requests

def test_429():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    for i in range(10):
        resp = session.get("https://brickset.com/sets/75354-1")
        print(f"Request {i+1}: {resp.status_code}")
        if resp.status_code == 429:
            print("Got 429, waiting 10 seconds...")
            time.sleep(10)
        else:
            time.sleep(2)

test_429()

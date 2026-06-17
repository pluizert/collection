import requests
url = "https://www.bricklink.com/ajax/clone/catalog/config.ajax?itemid=75386-1"
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
print(resp.status_code)
print(resp.text[:200])

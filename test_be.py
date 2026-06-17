import urllib.request
try:
    req = urllib.request.Request('https://www.brickeconomy.com/set/75386-1', headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    print("Success, length:", len(html))
except Exception as e:
    print("Failed:", e)

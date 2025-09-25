import requests

url = "http://127.0.0.1:9000/ask"  # make sure matches uvicorn port
payload = {"q": "What is PPE?", "k": 3, "mode": "hybrid"}
resp = requests.post(url, json=payload)

print("Status code:", resp.status_code)
print("Raw response:", resp.text)   # 👈 check what server actually sent

try:
    print("As JSON:", resp.json())
except Exception as e:
    print("JSON decode failed:", e)



import json

import requests

url = "https://raw.githubusercontent.com/Baskerville42/outage-data-ua/main/data/kyiv-region.json"

response = requests.get(url)
data = response.json()

# Сохраняем локально
with open("kyiv-region.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Данные скачаны и сохранены.")

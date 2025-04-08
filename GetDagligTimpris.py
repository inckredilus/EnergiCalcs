#
# This script fetches hourly electricity prices for a given date from the Elpriset Just Nu API.
# It prints the prices in SEK per kWh for each hour of the specified date.
#
import requests
import json

def fetch_and_print_prices(date, price_area="SE3"):
    year, month, day = date.split("-")
    url = f"https://www.elprisetjustnu.se/api/v1/prices/{year}/{month}-{day}_{price_area}.json"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        print(f"Timpris i SEK för {date} ({price_area}):")
        for entry in data:
            start_time = entry["time_start"][11:16]  # HH:MM
            price_sek = entry["SEK_per_kWh"]
 #           print(f"{start_time}: {price_sek:.5f} SEK/kWh") # Print full item
            print(f"{price_sek:.5f}")                       # Print only price
    else:
        print("Misslyckades att hämta elpriser.")

# Testa med ett datum
fetch_and_print_prices("2025-03-01")

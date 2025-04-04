#
# This script reads a JSON file containing hourly electricity prices for a specific date and prints the prices in a formatted manner.
#
import json
def print_hourly_prices(filename):
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    print("Timpris i SEK för 2025-03-25:")
    for entry in data:
        start_time = entry["time_start"][11:16]  # Extrahera HH:MM från time_start
        price_sek = entry["SEK_per_kWh"]
        print(f"{start_time}: {price_sek:.5f} SEK/kWh")

# Filnamnet kan senare ersättas med en dynamisk hämtning
filename = "pris250325.json"
print_hourly_prices(filename)


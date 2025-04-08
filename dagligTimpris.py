#
# This script reads a JSON file containing hourly electricity prices for a specific date and prints the prices in a formatted manner.
#
import json
"""def print_hourly_prices(filename):
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    print("Timpris i SEK för 2025-03-25:")
    for entry in data:
        start_time = entry["time_start"][11:16]  # Extrahera HH:MM från time_start
        price_sek = entry["SEK_per_kWh"]
        print(f"{start_time}: {price_sek:.5f} SEK/kWh")
"""
# Filnamnet kan senare ersättas med en dynamisk hämtning

#filename = "pris250325.json"
#print_hourly_prices(filename)


import pandas as pd

def print_hourly_prices(filename):
    """
    Läser elpriser från en JSON-fil och skriver ut dem.
    
    :param filename: Sökvägen till JSON-filen som innehåller elpriser per timme.
    """
    try:
        with open(filename, "r") as file:
            price_data = json.load(file)
        
        # Konvertera till DataFrame
        df_prices = pd.DataFrame(price_data)
        
        # Försäkra att 'Datetime' är en datetime-kolumn
        df_prices["Datetime"] = pd.to_datetime(df_prices["Datetime"], errors="coerce")
        
        # Skriva ut elpriserna
        print(df_prices)
        
        return df_prices

    except Exception as e:
        print(f"Fel vid inläsning av JSON-fil: {e}")

filename = "pris250325.json"
print_hourly_prices(filename)

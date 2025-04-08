#
# Hämtar elpriser från API och läser in energiförbrukning från CSV-fil
#
import pandas as pd
import requests

def load_energy_data(filename):
    """Läser in CSV-fil med energiförbrukning timme för timme och returnerar en DataFrame."""
    df = pd.read_csv(filename, sep=";", skiprows=2, names=["Datetime", "Energy_kWh"], decimal=",")
    
    # Konvertera Datetime-kolumnen till datetime-format
    df["Datetime"] = pd.to_datetime(df["Datetime"], format="%Y-%m-%d %H:%M")
    
    # Extrahera datum (utan tid) för gruppering
    df["Date"] = df["Datetime"].dt.date  
    
    return df

def fetch_prices_for_dates(dates, price_area="SE3"):
    """Hämtar elpriser för en lista av datum och returnerar en DataFrame."""
    price_data = []
    
    for date in dates:
        year, month, day = str(date).split("-")
        url = f"https://www.elprisetjustnu.se/api/v1/prices/{year}/{month}-{day}_{price_area}.json"
        
        response = requests.get(url)
#       print(f"Hämtar elpris från: {url}")  # Debug
        if response.status_code == 200:
            data = response.json()
#           print(f"API-svar ({date}): {data}")  # Debug - ser vi något?
            for entry in data:
                price_data.append({
                    "Datetime": entry["time_start"],
                    "Price_SEK_per_kWh": entry["SEK_per_kWh"]
                })
        else:
            print(f"Misslyckades att hämta prisdata för {date}. HTTP-status: {response.status_code}")
    
    df_prices = pd.DataFrame(price_data) if price_data else None
    if df_prices is not None:
#        df_prices["Datetime"] = pd.to_datetime(df_prices["Datetime"])
        df_prices["Datetime"] = pd.to_datetime(df_prices["Datetime"], utc=True)
    return df_prices

def merge_energy_prices(df_energy, df_prices):
    """Mergar energidata med elpriser baserat på tidpunkt."""
    
    # Konvertera df_prices till tidszonsfri datetime

 #   df_prices["Datetime"] = pd.to_datetime(df_prices["Datetime"], utc=True)  # Säkerställ UTC-tid
    df_prices["Datetime"] = pd.to_datetime(df_prices["Datetime"], utc=True, errors="coerce") # Säkerställ UTC-tid
 #   print("Efter pd.to_datetime:", df_prices["Datetime"].iloc[0])  # Förväntat: 2025-02-28 23:00:00+00:00

    df_prices["Datetime"] = df_prices["Datetime"].dt.tz_convert("Europe/Stockholm")  # Konvertera till svensk tid
#    print("Efter tz_convert:", df_prices["Datetime"].iloc[0])  # Förväntat: 2025-03-01 00:00:00+01:00

    df_prices["Datetime"] = df_prices["Datetime"].dt.tz_localize(None)  # Ta bort tidszon
#    print("Efter tz_localize:", df_prices["Datetime"].iloc[0])  # Förväntat: 2025-03-01 00:00:00

    df_merged = df_energy.merge(df_prices, on="Datetime", how="inner")
    df_merged["Cost_SEK"] = df_merged["Energy_kWh"] * df_merged["Price_SEK_per_kWh"]

    return df_merged

#
## Huvudprogrammet körs här
#
if __name__ == "__main__":
    df_energy = load_energy_data("elforbrukning.csv")  # Laddar energiförbrukning från CSV
    df_prices = fetch_prices_for_dates(df_energy["Date"].unique())  # Hämtar elpriser från API

    df_merged = merge_energy_prices(df_energy, df_prices)  # Mergar energidata med priser

   # Testa att startdatum är korrekt
    print("Första raden i df_prices:", df_prices.iloc[0]["Datetime"])
    print("Första raden i df_energy:", df_energy.iloc[0]["Datetime"])
 
    df_daily = df_merged.groupby("Date")[["Energy_kWh", "Cost_SEK"]].sum().reset_index()  # Summerar per dag

    print(df_daily)  # Skriver ut totalkostnaden per dag
#    df_daily.to_excel("elkostnad_per_dag.xlsx", index=False)  # Sparar till Excel


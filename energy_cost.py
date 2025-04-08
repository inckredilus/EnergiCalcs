# Slutversion av energikostnadsberäkning
# Hämtar elpriser från API och läser in energiförbrukning från CSV-fil
#
import pandas as pd
import requests
import os 

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

        if response.status_code == 200:
            data = response.json()

            for entry in data:
                price_data.append({
                    "Datetime": entry["time_start"],
                    "Price_SEK_per_kWh": entry["SEK_per_kWh"]
                })
        else:
            print(f"Misslyckades att hämta prisdata för {date}. HTTP-status: {response.status_code}")
    
    df_prices = pd.DataFrame(price_data)

# Konvertera och justera tidpunkterna: 
# 1. Konvertering till UTC: Vi tolkar alla datum som UTC (och hanterar eventuella fel med errors="coerce").
# 2. Konvertering till svensk tid: Vi justerar tiden från UTC till "Europe/Stockholm".
# 3. Borttagning av tidszonsinformation: Vi tar bort tidszonen så att datumen blir jämförbara med de i df_energy.

    df_prices["Datetime"] = pd.to_datetime(df_prices["Datetime"], utc=True, errors="coerce")
    df_prices["Datetime"] = df_prices["Datetime"].dt.tz_convert("Europe/Stockholm")
    df_prices["Datetime"] = df_prices["Datetime"].dt.tz_localize(None)

    return df_prices

def merge_energy_prices(df_energy, df_prices):
    """Mergar energiförbrukning och elpriser baserat på 'Datetime' och beräknar elkostnad per timme."""
    df_merged = df_energy.merge(df_prices, on="Datetime", how="inner")
    df_merged["Cost_SEK"] = df_merged["Energy_kWh"] * df_merged["Price_SEK_per_kWh"]
    return df_merged

def calculate_daily_cost(df_merged):
    """Grupperar per dag och summerar energiförbrukning och elkostnad."""

    df_daily = df_merged.groupby("Date")[["Energy_kWh", "Cost_SEK"]].sum().reset_index()
    return df_daily

def export_to_excel(df, excel_file, sheet_name):
    """Exporterar DataFrame till Excel, ersätter flik om den finns, annars skapar ny."""
    
    # Kontrollera om filen finns
    if os.path.exists(excel_file):
        try:
            # Läs in befintliga flikar
            with pd.ExcelFile(excel_file, engine="openpyxl") as xls:
                existing_sheets = xls.sheet_names
        except Exception as e:
            print(f"Kunde inte läsa in Excel-filen: {e}")
            return
        
        mode = "a"  # Append-läge om filen finns
        if sheet_name in existing_sheets:
            if_sheet_exists = "replace"  # Ersätt fliken om den finns
        else:
            if_sheet_exists = None  # Skapa ny flik
    else:
        mode = "w"  # Skriv-läge om filen inte finns
        if_sheet_exists = None  # Skapa ny flik

    # Skriv till Excel
    try:
        with pd.ExcelWriter(excel_file, mode=mode, if_sheet_exists=if_sheet_exists, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"Data exporterat till {excel_file}, flik: {sheet_name}")
    except PermissionError:
        print("Excel-filen är öppen. Stäng den och försök igen.")
    except Exception as e:
        print(f"Ett fel uppstod vid skrivning till Excel: {e}")

#
## Huvudprogrammet körs här
#
if __name__ == "__main__":
    # Ändringsbara variabler
    csv_file = "konsumtion2501.csv"          # CSV-fil med timdata
    excel_file = "elkostnad_resultat.xlsx"  # Excel-fil där resultatet ska skrivas
    output_sheet = "Elkostnad"              # Namn på fliken där resultatet ska skrivas
    price_area = "SE3"                      # Prisområde, standard är SE3

    # Steg 1: Läs in energiförbrukning
    df_energy = load_energy_data(csv_file)
    
    # Steg 2: Hämta elpriser för unika datum
    unique_dates = df_energy["Date"].astype(str).unique()
    df_prices = fetch_prices_for_dates(unique_dates, price_area=price_area)
    
    # Steg 3: Merg:a energiförbrukning och priser samt beräkna elkostnad per timme
    df_merged = merge_energy_prices(df_energy, df_prices)
    
    # Steg 4: Summera elkostnad per dag
    df_daily = calculate_daily_cost(df_merged)
    
    # Visa resultatet i terminalen
    print("Elkostnad per dag:")
    print(df_daily)
    
    # Steg 5: Exportera resultatet till Excel på vald flik
    export_to_excel(df_daily, excel_file, output_sheet)
import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Set

# Read charging session data from an Excel file
def load_charging_sessions(file_path: str, sheet_name: str = "InputData") -> tuple[pd.DataFrame, int, int]:
    """
    Reads charging session data from an Excel file and checks that all sessions belong to the same month.

    :param file_path: Path to the Excel file.
    :param sheet_name: Name of the worksheet to read from (default is "InputData").
    :return: Tuple of (DataFrame with charging sessions, year, month)
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df["Start"] = pd.to_datetime(df["Start"])
    df["End"] = pd.to_datetime(df["End"])
    df["Consumption"] = df["Consumption"].astype(float)

    # Kombinera start och slutdatum till en lista av alla involverade datum
    all_dates = pd.concat([df["Start"], df["End"]]).dt.to_period("M")
    unique_months = all_dates.unique()

    if len(unique_months) != 1:
        print("⚠️  Flera månader hittades i indatafilen. Programmet stöder endast en månad åt gången.")
        print(f"Hittade månader: {list(unique_months)}")
        sys.exit(1)

    year = unique_months[0].year
    month = unique_months[0].month

    if _TEST:
        print(f"✅ Alla sessioner ligger inom månaden: {year}-{month:02d}")

    return df, year, month
#
# Load hourly prices from JSON file
#
def load_hourly_prices(json_file: str) -> dict:
    """
    Loads hourly electricity prices from a JSON file.

    :param json_file: Path to the JSON file containing electricity prices.
    :return: Dictionary with datetime keys and price values (SEK/kWh).
    """
    with open(json_file, "r", encoding="utf-8") as f:
        price_data = json.load(f)

 #   print(price_data)  # Lägg till denna för att debugga

    hourly_prices = {}
    for price_entry in price_data:
        # Hämta starttiden och SEK-priset från varje objekt
        start_time = price_entry["time_start"]
        price_sek = price_entry["SEK_per_kWh"]
        
        # Lägg till i dictionaryn
        hourly_prices[start_time] = price_sek

    return hourly_prices
#
# Calculate the cost of charging based on hourly prices
#
def fetch_monthly_prices_from_api(year: int, month: int) -> pd.DataFrame:
    """
    Fetches hourly electricity prices from 'Elpriset Just Nu'-API for a specific month.

    :param year: The year to fetch data for (e.g. 2025)
    :param month: The month to fetch data for (e.g. 3 for March)
    :return: DataFrame with columns: "DateTime" and "SE3"
    """
    all_data = []

    # Början av månaden
    current_day = datetime(year, month, 1)

    # Slutet av månaden (nästa månad minus en dag)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    while current_day < next_month:
        date_str = current_day.strftime("%Y-%m-%d")
        url = f"https://www.elprisetjustnu.se/api/v1/prices/{year}/{month:02d}-{current_day.day:02d}_SE3.json"

        if _TEST:
            print(f"Hämtar data för {date_str} från API...")

        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"API-fel för {date_str}: {response.status_code}")

        daily_data = response.json()
        all_data.extend(daily_data)
        current_day += timedelta(days=1)

    # Konvertera till DataFrame
    df = pd.DataFrame(all_data)
    df["DateTime"] = pd.to_datetime(df["time_start"])
    df["SE3"] = df["SEK_per_kWh"]

    return df[["DateTime", "SE3"]]

def calculate_charging_cost(start: datetime, end: datetime, energy_kwh: float, price_data: dict) -> float:
    """
    Calculates the cost of charging an electric vehicle based on hourly prices.

    :param start: Start time of charging (datetime).
    :param end: End time of charging (datetime).
    :param energy_kwh: Total energy to charge (float, in kWh).
    :param price_data: Dictionary with datetime keys and price values (SEK/kWh).
    :return: Total cost of the charging session in SEK.
    """
    total_cost = 0.0
    total_energy_check = 0.0
    total_seconds = (end - start).total_seconds()

    current = start.replace(minute=0, second=0, microsecond=0)
    while current < end:
        next_hour = current + timedelta(hours=1)
        period_start = max(start, current)
        period_end = min(end, next_hour)
        duration_seconds = (period_end - period_start).total_seconds()

        fraction = duration_seconds / total_seconds
        energy_fraction = energy_kwh * fraction
        total_energy_check += energy_fraction

        key = current.isoformat() + "+01:00"  # Tidzon-fixad nyckel
        price = price_data.get(key, 0)

        cost = energy_fraction * price
        total_cost += cost

        if _TEST:
            print(f"Timme: {current} -> {next_hour}")
            print(f"  Period: {period_start.time()} - {period_end.time()} ({int(duration_seconds)} s)")
            print(f"  Energiandel: {energy_fraction:.5f} kWh")
            print(f"  Använt pris (SEK/kWh): {price}")
            print(f"  Kostnad denna timme: {cost:.5f} SEK\n")

        current = next_hour

    if _TEST:
        print(f"Totalt summerad energi: {total_energy_check:.5f} kWh (förväntat: {energy_kwh} kWh)")
        print(f"Total kostnad: {total_cost:.2f} SEK")

    return total_cost

#
# Extract unique months from the DataFrame
#
def extract_unique_months(df: pd.DataFrame) -> List[datetime.date]:
    """
    Extracts a sorted list of unique (year, month) combinations from the start and end dates.

    :param df: DataFrame with columns 'Start' and 'End' as datetime.
    :return: Sorted list of unique datetime.date objects representing each month (day always = 1).
    """
    start_months = df["Start"].dt.to_period("M").dt.to_timestamp().dt.date
    end_months = df["End"].dt.to_period("M").dt.to_timestamp().dt.date
    all_months: Set[datetime.date] = set(start_months).union(set(end_months))
    sorted_months = sorted(all_months)
    return sorted_months

# #
# MAIN FUNCTION
# This is the main function that runs when the script is executed directly.
# #

if __name__ == "__main__":

    _TEST = False   # Sätt till True för att aktivera debugutskrift

    # Test av läsning av laddsessioner
    excel_file = "laddsessioner.xlsx"
    sheet = "InputData"

    try:
        df_sessions = load_charging_sessions(excel_file, sheet)
        print(df_sessions)
    except Exception as e:
        print(f"Fel vid inläsning av laddsessioner: {e}")
        sys.exit(1)

    if _TEST:

        # Testdata
        start_time = datetime(2025, 3, 24, 1, 30)  # exempel på starttid
        end_time = datetime(2025, 3, 24, 3, 15)  # exempel på sluttid
        energy = 10.0  # exempel på energi i kWh

        # Använd den tidigare definierade load_hourly_prices
        price_data = load_hourly_prices("pris250324.json")

        # Beräkna laddkostnaden
        cost = calculate_charging_cost(start_time, end_time, energy, price_data)
        print(f"Laddkostnad: {cost:.2f} SEK")

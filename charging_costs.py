import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Set, Tuple

# Read charging session data from an Excel file
def load_charging_sessions(file_path: str, sheet_name: str = "InputData") -> Tuple[pd.DataFrame, int, int]:
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
def fetch_monthly_prices_from_api(year: int, month: int, elområde: str = "SE3") -> pd.DataFrame:
    """
    Fetches hourly electricity prices for an entire month from the 'elprisetjustnu' API.

    :param year: Year of interest (e.g., 2025).
    :param month: Month of interest (1–12).
    :param elområde: Electricity price area (e.g., "SE3", "SE1", "SE2", "SE4").
    :return: A DataFrame with columns "DateTime" and the selected elområde column (e.g., "SE3").
    """
    # Lista för att samla dagspriser
    all_data = []

    # Hämta antal dagar i månaden
    days_in_month = pd.Period(f"{year}-{month}").days_in_month

    for day in range(1, days_in_month + 1):
        date_str = f"{month:02d}-{day:02d}"
        url = f"https://www.elprisetjustnu.se/api/v1/prices/{year}/{date_str}_{elområde}.json"

        try:
            response = requests.get(url)
            response.raise_for_status()
            json_data = response.json()
        except Exception as e:
            print(f"Fel vid hämtning av data för {date_str}: {e}")
            continue  # hoppa över till nästa dag

        # Konvertera till DataFrame
        df = pd.DataFrame(json_data)
        df["DateTime"] = pd.to_datetime(df["time_start"], utc=True).dt.tz_convert("Europe/Stockholm")
        df[elområde] = df["SEK_per_kWh"]
        all_data.append(df[["DateTime", elområde]])

    if not all_data:
        raise ValueError("Ingen data kunde hämtas från API:et.")

    # Slå ihop allt till en enda DataFrame
    full_df = pd.concat(all_data).sort_values("DateTime").reset_index(drop=True)
    return full_df
#
# Calculate the cost of charging based on hourly prices
#
def calculate_charging_cost(start_time, end_time, energy_kwh, price_data):
    """
    Calculates the cost of charging an electric vehicle over a specified time interval.

    Parameters:
        start_time (datetime): Local start time of the charging session.
        end_time (datetime): Local end time of the charging session.
        energy_kwh (float): Total energy to be charged during the session (in kWh).
        price_data (dict): Dictionary of hourly electricity prices with keys as UTC ISO8601 strings 
                           (e.g., '2025-03-01T01:00:00+00:00') and values as prices in SEK/kWh.

    Returns:
        float: Total cost for the charging session (rounded to 4 decimal places).
    """
    if start_time >= end_time:
        return 0.0

    total_seconds = (end_time - start_time).total_seconds()
    total_cost = 0.0
    total_energy_check = 0.0

    current = start_time.replace(minute=0, second=0, microsecond=0)

    while current < end_time:
        next_hour = current + timedelta(hours=1)
        period_start = max(current, start_time)
        period_end = min(next_hour, end_time)

        duration_seconds = (period_end - period_start).total_seconds()
        energy_fraction = energy_kwh * (duration_seconds / total_seconds)

        # Match UTC time to price_data keys
        current_utc = current.replace(tzinfo=timezone.utc)
 #      key = current_utc.isoformat()
        key = current_utc
        price = price_data.get(key, 0.0)
        cost = energy_fraction * price

        total_cost += cost
        total_energy_check += energy_fraction

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

    return round(total_cost, 4)

#
# Calculate the cost of charging for all sessions
#
def calculate_all_charging_costs(   
    df_sessions: pd.DataFrame,
    price_df: pd.DataFrame,
    price_column: str = "SE3"
) -> pd.DataFrame:
    """
    Calculates the charging cost for all sessions in the DataFrame using hourly electricity prices.

    :param df_sessions: DataFrame with columns 'Start', 'End', and 'Consumption'
    :param price_df: DataFrame with hourly prices. Must contain 'DateTime' and a column for the selected price zone (e.g., 'SE3')
    :param price_column: Column name for the electricity price zone to use (default is 'SE3')
    :return: A new DataFrame identical to df_sessions but with an extra column 'ChargingCost'
    """
    # Skapa en dictionary med priser för snabbare uppslag i beräkningarna
    price_data = dict(
        zip(
            price_df["DateTime"],
            price_df[price_column]
        )
    )

    # Lista för att samla alla kostnader
    costs = []

    for index, row in df_sessions.iterrows():
        start_time = row["Start"]
        end_time = row["End"]
        energy = row["Consumption"]

        try:
            cost = calculate_charging_cost(start_time, end_time, energy, price_data)
        except Exception as e:
            print(f"Fel vid beräkning av session på rad {index}: {e}")
            cost = None  # eller 0.0 om du föredrar det

        costs.append(cost)

    # Lägg till kolumnen i den ursprungliga DataFramen
    df_sessions["ChargingCost"] = costs
    return df_sessions

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

    _TEST = True   # Sätt till True för att aktivera debugutskrift

    # Test av läsning av laddsessioner
    excel_file = "laddsessioner.xlsx"
    sheet = "InputData"

    try:
        df_sessions, year, month = load_charging_sessions(excel_file, sheet)
        df_price = fetch_monthly_prices_from_api(year, month, elområde="SE3")
        if _TEST:
        # Extrahera start_time, end_time och energy från första raden i df_sessions
            first_session = df_sessions.iloc[0]  # Hämta första raden
            start_time = first_session["Start"]
            end_time = first_session["End"]
            energy = first_session["Consumption"]

        # Testa beräkningen för första laddsessionen
        charging_cost = calculate_charging_cost(start_time, end_time, energy, df_price)
        
        # Skriv ut resultatet
        print(f"Laddkostnad för första sessionen: {charging_cost:.2f} SEK")

 #          print(df_price.head())
 #          print(df_price.iloc[740:745][["DateTime", "SE3"]]) # Debuggning av priser

   #     df_result = calculate_all_charging_costs(df_sessions, df_price, price_column="SE3")
   #     print(df_result[["Start", "End", "Consumption", "ChargingCost"]].head())
    except Exception as e:
        print(f"Fel vid inläsning av laddsessioner: {e}")
        sys.exit(1)

def old():

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

import energy_cost as ec
import pandas as pd
import os

# Ange testparametrar
test_date = pd.to_datetime("2025-03-01")
csv_file = "elforbrukning.csv"

# Hämta energidata och prisdata
df_energy = ec.load_energy_data(csv_file)
df_prices = ec.fetch_prices_for_dates(df_energy)

# Slå ihop energidata med prisdata
df_merged = ec.merge_energy_prices(df_energy, df_prices)

# Kör testfunktionen för att skriva ut detaljerad info för en dag
ec.print_day_details(df_merged, df_prices, test_date)

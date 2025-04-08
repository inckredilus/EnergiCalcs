"""Detta skript hämtar elkonsumtion per dygnstimme i kWh från en CSV-fil och sparar dem i en DataFrame. 
Functionen har lagts in i modulen energy_cost.py och skall användas därifrån istället.
Denna version uppdateras inte efter 2025-04-02.18:30"""

import pandas as pd

def load_energy_data(filename):
    df = pd.read_csv(filename, sep=";", skiprows=2, names=["Datetime", "Energy_kWh"], decimal=",")
    
    # Konvertera Datetime-kolumnen till datetime-format
    df["Datetime"] = pd.to_datetime(df["Datetime"], format="%Y-%m-%d %H:%M")
    
    # Extrahera datum (utan tid) för gruppering
    df["Date"] = df["Datetime"].dt.date  
    
    return df

# Testa att läsa in din fil
filename = "elforbrukning.csv"
df_energy = load_energy_data(filename)
# print(df_energy.head(24))             # Print 24 timmaar (1 dygn) av energiförbrukning
[print(value) for value in df_energy["Energy_kWh"].head(24)] # Samma som ovan men bara kWh

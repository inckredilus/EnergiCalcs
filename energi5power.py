import pandas as pd
import numpy as np
from datetime import datetime

def calculate_energy_and_power(input_file, input_sheet, output_sheet):
    try:
        # Läs in Excel-filen
        df = pd.read_excel(input_file, sheet_name=input_sheet)
    except PermissionError:
        print("Excel-filen är öppen. Stäng den och försök igen.")
        return
    
    # Omvandla Start och End till datetime-format
    df['Start'] = pd.to_datetime(df['Start'])
    df['End'] = pd.to_datetime(df['End'])
    
    # Beräkna varaktighet i sekunder och konvertera till timmar
    df['Duration'] = (df['End'] - df['Start']).dt.total_seconds() / 3600  # Konverterad till decimal timmar
    
    # Beräkna effekten
    df['Power'] = df['Consumption'] / df['Duration']
    
    # Identifiera närmaste hela klockslag för Start och End
    df['Start Hour'] = df['Start'].dt.floor('h')
    df['End Hour'] = df['End'].dt.ceil('h')
    
    # Beräkna minuter före och efter hela klockslag
    df['Before Minutes'] = ((df['Start Hour'] + pd.Timedelta(hours=1)) - df['Start']).dt.total_seconds() / 60
    df['After Minutes'] = (df['End'] - (df['End Hour'] - pd.Timedelta(hours=1))).dt.total_seconds() / 60
    
    # Differens mellan End Hour och Start Hour
    hour_diff = (df['End Hour'] - df['Start Hour']).dt.total_seconds() / 3600
    
    # Full Hour Power logik
    df['Full Hour Power'] = np.where(
        hour_diff > 2,  # Fall 1: Minst två klockslag passeras
        df['Power'],
        np.where(
            hour_diff == 2,  # Fall 2: Exakt ett klockslag passeras
            0,  
            df['Power'] * df['Duration']  # Fall 3: Hela Duration inom samma timme
        )
    )
    
    # Before Power och After Power logik
    df['Before Power'] = np.where(hour_diff > 1, df['Power'] * df['Before Minutes'] / 60, 0)
    df['After Power'] = np.where(hour_diff > 1, df['Power'] * df['After Minutes'] / 60, 0)
    
    # Spara till ny eller befintlig flik i Excel
    with pd.ExcelWriter(input_file, mode='a', if_sheet_exists='replace') as writer:
        df.to_excel(writer, sheet_name=output_sheet, index=False)
    
    print(f"Beräkning klar! Data sparad i fliken '{output_sheet}' i {input_file}.")

# Exempel på körning
input_sheet = "InputData"
output_sheet = "ProcessedData"
file_path = "energidata.xlsx"

calculate_energy_and_power(file_path, input_sheet, output_sheet)
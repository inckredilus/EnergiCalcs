import pandas as pd
import numpy as np
from datetime import datetime

def calculate_energy_and_power(file_path, input_sheet, output_sheet):
    try:
        # Försök att läsa in filen, fånga fel om den är öppen
        xl = pd.ExcelFile(file_path)
    except PermissionError:
        print(f"Fel: Kan inte öppna {file_path}. Stäng Excel-filen och försök igen.")
        return
    
    df = xl.parse(input_sheet)
    
    # Se till att datatyperna är korrekta
    df['Start'] = pd.to_datetime(df['Start'])
    df['End'] = pd.to_datetime(df['End'])
    
    df['Duration'] = (df['End'] - df['Start']).dt.total_seconds() / 60
    df['Power'] = df['Consumption'] / (df['Duration'] / 60)
    
    before_power = []
    full_hour_power = []
    after_power = []
    
    for _, row in df.iterrows():
        start, end, power = row['Start'], row['End'], row['Power']
        start_hour = start.ceil("h").replace(minute=0, second=0)  # Bytt "H" till "h"
        end_hour = end.floor("h").replace(minute=0, second=0)
        
        if start < start_hour:
            before_minutes = (start_hour - start).total_seconds() / 60
        else:
            before_minutes = 0
        
        if end > end_hour:
            after_minutes = (end - end_hour).total_seconds() / 60
        else:
            after_minutes = 0
        
        full_hour_minutes = row['Duration'] - before_minutes - after_minutes
        
        if full_hour_minutes >= 60:
            full_hour_power.append(power)
            before_power.append((before_minutes / 60) * power if before_minutes > 0 else 0)
            after_power.append((after_minutes / 60) * power if after_minutes > 0 else 0)
        elif full_hour_minutes > 0:
            full_hour_power.append((full_hour_minutes / 60) * power)
            before_power.append(0)
            after_power.append(0)
        else:
            full_hour_power.append(0)
            before_power.append((before_minutes / 60) * power)
            after_power.append((after_minutes / 60) * power)
    
    df['Before Power'] = before_power
    df['Full Hour Power'] = full_hour_power
    df['After Power'] = after_power
    
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df.to_excel(writer, sheet_name=output_sheet, index=False)
    
    print(f"Beräkningar klara och sparade i fliken '{output_sheet}' i {file_path}.")


# Exempel på körning
input_sheet = "InputData"
output_sheet = "ProcessedData"
file_path = "energidata.xlsx"

calculate_energy_and_power(file_path, input_sheet, output_sheet)
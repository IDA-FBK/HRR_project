import pandas as pd
import numpy as np
from collections import deque

# Compute the number of acute hospitalizations in the past 365 days for each patient episode, based on episode type and discharge department. This is a key feature for our readmission prediction model, as recent acute events are strong predictors of readmission risk.
LOOKBACK_DAYS = 365 
EPISODE_TYPE_RO = "RO"  # Ordinary Hospitalization
ACUTE_DEPARTMENTS = {
    "Medicina Generale", "Cardiologia", "Chirurgia Vascolare - Angiologia",
    "Cardiochirurgia", "Unità Coronarica", "Neurologia", "Nefrologia",
    "Terapia Intensiva", "Terapia Semi Intensiva"
}

def compute_acute_counts(df):
    # Sort by patient and time
    df = df.copy()
    df['episode_start'] = pd.to_datetime(df['episode_start'])
    df = df.sort_values(['crypted_patient_id', 'episode_start'])
    
    # Initialize the target column
    df['num_acute_inpatient'] = 0
    
    # Group by Patient
    grouped = df.groupby('crypted_patient_id', sort=False)
    
    # List to store updated indices/values
    results = []

    for _, patient_df in grouped:
        # Queue stores (timestamp of acute event)
        acute_events = deque()
        
        for idx, row in patient_df.iterrows():
            current_start = row['episode_start']
            cutoff = current_start - pd.Timedelta(days=LOOKBACK_DAYS)
            
            # Remove expired events (older than 365 days)
            while acute_events and acute_events[0] < cutoff:
                acute_events.popleft()
            
            # Record prior 12 months 
            df.at[idx, 'num_acute_inpatient'] = len(acute_events)
            
            # Record current event in history if it qualifies as Acute
            is_ro = row.get('episode_type') == EPISODE_TYPE_RO
            is_acute = row.get('discharge_department') in ACUTE_DEPARTMENTS
            
            if is_ro and is_acute:
                acute_events.append(current_start)
                
    return df

df = pd.read_csv("../../../data/processed/modeling/inpatient_episodes.csv")
df_with_acute = compute_acute_counts(df)
df_with_acute.to_csv("../../../data/processed/modeling/inpatient_episodes_with_acute.csv", index=False)
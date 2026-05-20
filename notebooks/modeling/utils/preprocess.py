import pandas as pd
AGE_GROUP_UNDER_50 = {
    '0', '1-4', '5-9', '10-14', '15-19',
    '20-24', '25-29', '30-34', '35-39', '40-44', '45-49'
}

AGE_ORDER = [
    '<50',    
    '50-54',
    '55-59',
    '60-64',
    '65-69',
    '70-74',
    '75-79',
    '80-84',
    '85-89',
    '90+',
]
# Create a mapping from age group to ordinal integer based on the defined order
AGE_ORDINAL = {age: i for i, age in enumerate(AGE_ORDER)}
def preprocess_features(df, cols_to_drop=None, target_col='is_readmitted'):
    df = df.copy()

    # Clinical Department Grouping
    DEPARTMENT_GROUPS = {
        "General Medicine": ["Medicina Generale"],
        "Cardiovascular": ["Cardiologia", "Chirurgia Vascolare - Angiologia", "Cardiochirurgia", "Unità Coronarica"],
        "Neurovascular": ["Neurologia"],
        "Renal/Metabolic": ["Nefrologia", "Nefrologia (Abilitato Al Trapianto Rene)"],
        "High Acuity": ["Terapia Semi Intensiva", "Terapia Intensiva"],
        "Rehab/Frailty": ["Medicina Fisica E Riabilitazione", "Lungodegenti", "Geriatria"],
        "Other": ["Pneumologia", "Chirurgia Toracica", "Oncologia"]
    }

    # Reverse the dictionary for easy mapping
    inv_map = {dept: grp for grp, depts in DEPARTMENT_GROUPS.items() for dept in depts}
    df['num_comorbidities'] = df['num_comorbidities'].clip(upper=3)
    # OHE the grouped departments, drop the original column
    if 'discharge_department' in df.columns:
        # Map existing depts to groups, fill unmapped with "Other"
        df['dept_group'] = df['discharge_department'].map(inv_map).fillna("Other")
        # Now OHE the groups instead of the raw departments
        df = pd.get_dummies(df, columns=['dept_group'], prefix='grp', drop_first=True)
        # Drop the original raw column
        df = df.drop(columns=['discharge_department'])
    
    df['ATC_12m_before'] = df['P_ATC_12m_before'] + df['S_ATC_12m_before'] + df['D_ATC_12m_before']
    df.drop(columns=['S_ATC_12m_before', 'D_ATC_12m_before', 'P_ATC_12m_before'], inplace=True)
    if cols_to_drop is not None:
        existing_cols_to_drop = [c for c in cols_to_drop if c in df.columns]
        df = df.drop(columns=existing_cols_to_drop)
    if 'age_group' in df.columns:
        df['age'] = encode_age_group(df['age_group'])
        df = df.drop(columns=['age_group'])
    # Split X and y
    if target_col in df.columns:
        y = df[target_col]
        X = df.drop(columns=[target_col])
        return X, y
    
    return df

# Encode age groups into ordinal integers, mapping all under-50 groups to a single category
def encode_age_group(series: pd.Series) -> pd.Series:
    def _map(val):
        v = str(val).strip()
        if v in AGE_GROUP_UNDER_50:
            return AGE_ORDINAL['<50']
        if v in AGE_ORDINAL:
            return AGE_ORDINAL[v]
        raise ValueError(f"Unknown age_group value: '{val}'. Update AGE_GROUP_UNDER_50 or AGE_ORDER.")

    return series.map(_map).astype(float)

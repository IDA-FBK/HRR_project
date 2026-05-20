import pandas as pd
from sklearn.model_selection import train_test_split

def get_train_test_split(patients_path, episodes_path, test_size=0.30, random_state=42):
    patients = pd.read_csv(patients_path)
    episodes = pd.read_csv(episodes_path)

    # PATIENT-LEVEL STRATIFIED SPLIT
    # We split the patients, not the episodes, to ensure a patient is never 
    # in both training and testing sets.
    train_pat, test_pat = train_test_split(
        patients,
        test_size=test_size,
        random_state=random_state, 
        stratify=patients["readmission_flag"]
    )

    train_ids = set(train_pat["crypted_patient_id"])
    test_ids  = set(test_pat["crypted_patient_id"])
    print(f"Unique patients - Train: {len(train_ids)} | Test: {len(test_ids)}")
    # Map back to episodes
    train_df = episodes[episodes["crypted_patient_id"].isin(train_ids)].copy()
    test_df  = episodes[episodes["crypted_patient_id"].isin(test_ids)].copy()
    
    # Save the ddatasets
    train_df.to_csv("../../data/splits/train_episodes.csv", index=False)
    test_df.to_csv("../../data/splits/test_episodes.csv", index=False)
    groups_train = train_df['crypted_patient_id'].values
    return train_df, test_df, groups_train
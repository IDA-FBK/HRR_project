import os
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance
from sksurv.ensemble import RandomSurvivalForest
import matplotlib.pyplot as plt
import seaborn as sns

# =====================================================================
# FASE 0: CONFIGURAZIONE SEED DI RIPRODUCIBILITÀ GLOBALE
# =====================================================================
SEED_PROGETTO = 42
np.random.seed(SEED_PROGETTO)
os.environ['PYTHONHASHSEED'] = str(SEED_PROGETTO)

DATA_FOLDER = "../../data/new_dataset/"
OUTPUT_FOLDER = "outputs/"


# =====================================================================
# FASE 1: CARICAMENTO FILE CSV
# =====================================================================
print("=====================================================================")
print("1. Caricamento dei file CSV reali...")
print("=====================================================================")


def carica_csv_sicuro(nome_file):
    if os.path.exists(nome_file):
        return pd.read_csv(nome_file, sep=';', low_memory=False)
    else:
        raise FileNotFoundError(f"Errore: Il file '{nome_file}' non è stato trovato.")


df_anagrafica = carica_csv_sicuro(f"{DATA_FOLDER}anagrafica.csv")
df_laboratorio = carica_csv_sicuro(f"{DATA_FOLDER}laboratorio.csv")
df_farmaceutica = carica_csv_sicuro(f"{DATA_FOLDER}farmaceutica.csv")
df_ospedalizzazioni = carica_csv_sicuro(f"{DATA_FOLDER}ospedalizzazioni.csv")
df_specialistica = carica_csv_sicuro(f"{DATA_FOLDER}specialistica.csv")

print("-> Tutti i file sono stati caricati correttamente.")

# =====================================================================
# FASE 2: PREPROCESSING & CONVERSIONE DATE
# =====================================================================
df_anagrafica['data_ini'] = pd.to_datetime(df_anagrafica['data_ini'])
df_anagrafica['data_fine'] = pd.to_datetime(df_anagrafica['data_fine'])
df_laboratorio['data_esec'] = pd.to_datetime(df_laboratorio['data_esec'])
df_farmaceutica['data_presc'] = pd.to_datetime(df_farmaceutica['data_presc'])
df_ospedalizzazioni['data_ric'] = pd.to_datetime(df_ospedalizzazioni['data_ric'])
df_specialistica['data_esec'] = pd.to_datetime(df_specialistica['data_esec'])

# =====================================================================
# FASE 2.5: MAPPATURA MULTI-COLONNA TARGET & REGEX ANTI-DATA-LEAKAGE
# =====================================================================
print("\n[INFO] Identificazione dell'evento (ICD9: 410x) su tutte le colonne SDO...")

colonne_target = [
    'dia_pri', 'dia1', 'dia2', 'dia3', 'dia4', 'dia5',
    'int_pri', 'int1', 'int2', 'int3', 'int4', 'int5'
]

maschera_infarto = np.zeros(len(df_ospedalizzazioni), dtype=bool)

for col in colonne_target:
    if col in df_ospedalizzazioni.columns:
        sdo_pulito = df_ospedalizzazioni[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        sdo_pulito = sdo_pulito.str.replace('.', '', regex=False)
        maschera_infarto |= sdo_pulito.str.startswith('410', na=False)

df_infarti = df_ospedalizzazioni[maschera_infarto]
df_ultimo_infarto = df_infarti.groupby('id_paz')['data_ric'].max().reset_index(name='data_evento')

df_anagrafica = df_anagrafica.merge(df_ultimo_infarto, on='id_paz', how='left')
df_anagrafica['classe'] = df_anagrafica['data_evento'].notna().astype(int)

df_anagrafica['Tempo_In_Giorni'] = np.where(
    df_anagrafica['classe'] == 1,
    (df_anagrafica['data_evento'] - df_anagrafica['data_ini']).dt.days,
    (df_anagrafica['data_fine'] - df_anagrafica['data_ini']).dt.days
)
df_anagrafica['Tempo_In_Giorni'] = df_anagrafica['Tempo_In_Giorni'].clip(lower=1)

# --- CREAZIONE DEL MURO TEMPORALE PER ESCLUDERE IL LEAKAGE FUTURE ---
mappa_date_limite = pd.Series(
    np.where(df_anagrafica['classe'] == 1, df_anagrafica['data_evento'], pd.to_datetime('2099-12-31')),
    index=df_anagrafica['id_paz']
).to_dict()

df_laboratorio = df_laboratorio[df_laboratorio['data_esec'] <= df_laboratorio['id_paz'].map(mappa_date_limite)]
df_farmaceutica = df_farmaceutica[df_farmaceutica['data_presc'] <= df_farmaceutica['id_paz'].map(mappa_date_limite)]
df_specialistica = df_specialistica[df_specialistica['data_esec'] <= df_specialistica['id_paz'].map(mappa_date_limite)]
df_ospedalizzazioni_filtrate = df_ospedalizzazioni[
    df_ospedalizzazioni['data_ric'] < df_ospedalizzazioni['id_paz'].map(mappa_date_limite)]

print("-> Troncamento multi-colonna completato con successo. Dati post-evento eliminati.")

# =====================================================================
# FASE 3: FEATURE ENGINEERING (Sui dati correttamente troncati)
# =====================================================================
print("\n[INFO] Generazione della matrice delle caratteristiche (Feature Engineering)...")

df_matrice_base = df_anagrafica[['id_paz', 'sesso', 'anno_nasc']].copy()
df_matrice_base['eta_paziente'] = df_anagrafica['data_ini'].dt.year - df_matrice_base['anno_nasc']
df_matrice_base['sesso_M'] = df_matrice_base['sesso'].astype(str).str.upper().map({'M': 1, 'F': 0})
df_matrice_base.drop(columns=['sesso', 'anno_nasc'], inplace=True)

# 3.1 Laboratorio (Parsing alfanumerico robusto)
if not df_laboratorio.empty:
    df_laboratorio['cod_esame'] = df_laboratorio['cod_esame'].astype(str).str.strip()
    df_laboratorio['ris_pulito'] = df_laboratorio['ris_esame'].astype(str).str.replace('<', '').str.replace('>', '')
    df_laboratorio['ris_num'] = pd.to_numeric(df_laboratorio['ris_pulito'], errors='coerce')

    lab_agg = df_laboratorio.groupby(['id_paz', 'cod_esame'])['ris_num'].agg(['mean', 'max', 'min']).unstack()
    lab_agg.columns = [f"{stat}_{esame}" for stat, esame in lab_agg.columns]
    lab_agg = lab_agg.reset_index()
    df_matrice_base = df_matrice_base.merge(lab_agg, on='id_paz', how='left')

# 3.2 Specialistica Ambulatoriale
spe_agg = df_specialistica.groupby('id_paz').size().reset_index(name='numero_visite_specialistiche')
df_matrice_base = df_matrice_base.merge(spe_agg, on='id_paz', how='left')

# 3.3 Farmaceutica Multi-Classe con Dizionario di Mappatura Clinica
df_farmaceutica['atc'] = df_farmaceutica['atc'].astype(str).str.strip()

# Configurazione delle classi ATC target da estrarre
classi_farmaci_target = {
    'statine_pure': 'C10AA',
    'antiaggreganti': 'B01AC'
}

# Dizionario d'appoggio in cui accumuleremo i valori di fillna per la fase 3.4
valori_riempimento_base = {
    'numero_visite_specialistiche': 0,
    'sesso_M': 0
}

# Ciclo di estrazione e aggregazione per ciascun filone terapeutico identificato
for nome_clinico, prefisso_atc in classi_farmaci_target.items():
    farm_target = df_farmaceutica[df_farmaceutica['atc'].str.startswith(prefisso_atc, na=False)]

    if not farm_target.empty:
        # Aggregazione per singolo paziente ed estrazione delle metriche longitudinali
        farm_esposizione = farm_target.groupby('id_paz').agg(
            prima_prescr=('data_presc', 'min'),
            ultima_prescr=('data_presc', 'max'),
            unita_totali=('unita', 'sum'),
            spesa_totale=('spesa', 'sum')
        ).reset_index()

        # Calcolo dell'intervallo temporale continuo di persistenza terapeutica
        farm_esposizione[f'tempo_esposizione_{nome_clinico}_giorni'] = (
                farm_esposizione['ultima_prescr'] - farm_esposizione['prima_prescr']
        ).dt.days

        # Ridenominazione univoca delle colonne per evitare collisioni nella matrice delle caratteristiche
        farm_esposizione = farm_esposizione.rename(columns={
            'unita_totali': f'unita_totali_{nome_clinico}',
            'spesa_totale': f'spesa_totale_{nome_clinico}'
        })

        # Unione dei dati sulla matrice anagrafica di base
        df_matrice_base = df_matrice_base.merge(
            farm_esposizione[['id_paz', f'unita_totali_{nome_clinico}', f'tempo_esposizione_{nome_clinico}_giorni',
                              f'spesa_totale_{nome_clinico}']],
            on='id_paz', how='left'
        )
    else:
        # Gestione preventiva qualora la classe non producesse record nel database d'esempio
        df_matrice_base[f'unita_totali_{nome_clinico}'] = 0
        df_matrice_base[f'tempo_esposizione_{nome_clinico}_giorni'] = 0
        df_matrice_base[f'spesa_totale_{nome_clinico}'] = 0.0

    # Popolamento dinamico delle regole di imputazione per i pazienti non esposti
    valori_riempimento_base[f'unita_totali_{nome_clinico}'] = 0
    valori_riempimento_base[f'tempo_esposizione_{nome_clinico}_giorni'] = 0
    valori_riempimento_base[f'spesa_totale_{nome_clinico}'] = 0.0

# =====================================================================
# FASE 3.4: IMPUTAZIONE VALORI MANCANTI (COERENTE)
# =====================================================================
df_matrice_base = df_matrice_base.fillna(value=valori_riempimento_base)

colonne_lab = [col for col in df_matrice_base.columns if col.startswith(('mean_', 'max_', 'min_'))]
if colonne_lab:
    medie_laboratorio = df_matrice_base[colonne_lab].mean().fillna(0.0).to_dict()
    df_matrice_base[colonne_lab] = df_matrice_base[colonne_lab].fillna(value=medie_laboratorio)

df_matrice_base = df_matrice_base.merge(df_anagrafica[['id_paz', 'classe', 'Tempo_In_Giorni']], on='id_paz', how='left')

casi_reali = df_matrice_base['classe'].sum()
print(
    f"-> Casi totali di Infarto estratti (Diagnosi Pri/Sec + Interventi): {casi_reali} | Sani: {len(df_matrice_base) - casi_reali}")

# =====================================================================
# FASE 5: MACHINE LEARNING (Random Survival Forest)
# =====================================================================
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

if casi_reali < 2:
    print("\n[ATTENZIONE] Eventi insufficienti nei dati. Verifica la presenza dei codici 410 nei file di input.")
else:
    X = df_matrice_base.drop(columns=['id_paz', 'classe', 'Tempo_In_Giorni'])
    y = np.array(list(zip(df_matrice_base['classe'].astype(bool), df_matrice_base['Tempo_In_Giorni'])),
                 dtype=[('Status', '?'), ('Survival_in_days', '<f8')])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=SEED_PROGETTO, stratify=df_matrice_base['classe']
    )

    model = RandomSurvivalForest(n_estimators=100, min_samples_split=10, min_samples_leaf=5, n_jobs=-1,
                                 random_state=SEED_PROGETTO)
    model.fit(X_train, y_train)

    c_index = model.score(X_test, y_test)
    print(f"\n[ACCURATEZZA] Concordance Index (C-Index): {c_index:.3f}")

    risk_scores = model.predict(X_test)
    punteggi_unici = risk_scores + np.random.uniform(-1e-7, 1e-7, size=len(risk_scores))

    classi_rischio = pd.qcut(punteggi_unici, q=4,
                             labels=['Basso Rischio', 'Moderato Rischio', 'Alto Rischio', 'Molto Alto Rischio'])

    df_output_prognosi = pd.DataFrame({
        'Classe_Rischio_Assegnata': classi_rischio,
        'Giorni_A_Rischio': [t[1] for t in y_test]
    })

    # =====================================================================
    # FASE 6: GENERAZIONE DEI PLOTS FINALI
    # =====================================================================
    sns.set_theme(style="whitegrid")

    # Grafico 1: Permutation Importance
    risultato_importanza = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=SEED_PROGETTO)
    df_importanza = pd.DataFrame({'Fattore': X.columns, 'Impatto': risultato_importanza.importances_mean}).sort_values(
        by='Impatto', ascending=False)

    plt.figure(figsize=(10, 8))
    # 15 fattori di importanza
    sns.barplot(x='Impatto', y='Fattore', data=df_importanza.head(15), palette='Reds_r', hue='Fattore', legend=False)
    plt.title('Fattori Correlabili all\'Insorgenza dell\'Infarto (Multi-colonna SDO)', weight='bold', pad=15)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_FOLDER}importanza_fattori_infarto.png", dpi=300)
    plt.close()

    # Grafico 2: Semaforo Prognostico
    df_plot_prognosi = df_output_prognosi.groupby('Classe_Rischio_Assegnata', observed=False)[
        'Giorni_A_Rischio'].mean().reset_index()
    color_dict = {'Basso Rischio': '#2ecc71', 'Moderato Rischio': '#f1c40f', 'Alto Rischio': '#e67e22',
                  'Molto Alto Rischio': '#e74c3c'}

    plt.figure(figsize=(9, 5))
    sns.barplot(x='Classe_Rischio_Assegnata', y='Giorni_A_Rischio', data=df_plot_prognosi,
                palette=[color_dict[cat] for cat in df_plot_prognosi['Classe_Rischio_Assegnata']],
                hue='Classe_Rischio_Assegnata', legend=False)
    plt.title('Stratificazione Prognostica: Giorni Medi Liberi da Infarto', weight='bold', pad=15)

    for index, row in df_plot_prognosi.iterrows():
        if not pd.isna(row['Giorni_A_Rischio']):
            plt.text(index, row['Giorni_A_Rischio'] + (row['Giorni_A_Rischio'] * 0.05),
                     f"{int(row['Giorni_A_Rischio'])} gg", color='black', ha="center", weight='semibold')

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_FOLDER}stratificazione_infarto.png", dpi=300)
    plt.close()

    print(f"\n[PROCESSO COMPLETATO] Pipeline eseguita con successo. Grafici salvati in '{OUTPUT_FOLDER}'.")
import pandas as pd
import numpy as np
import mysql.connector

cnx = mysql.connector.connect(user='root', password='Fbk!23SQLpw', port=3333,
                            host='127.0.0.1',
                            database='patient_events_selected_conditions')


def get_data():
    cur = cnx.cursor()
    cur.execute('''select * from inpatient_episodes_labeled''')
    df = pd.DataFrame(cur.fetchall())
    df.columns = [item[0] for item in cur.description]
    # Save feature dataset
    df.to_csv("data/raw/feature_dataset.csv")
    return df


if __name__ == '__main__':
    get_data()
    
select
    DISTINCT he.crypted_patient_id
from
    healthcare_event he
    join inpatient_event ie on he.event_id = ie.event_id
    join diagnosis_code dc on ie.primary_diagnosis_code = dc.code
    join secondary_diagnosis sd on sd.event_id = ie.event_id
WHERE
    REGEXP_LIKE(dc.code, '^428')
    OR dc.code IN (
        '402.01',
        '402.11',
        '402.91',
        '404.01',
        '404.03',
        '404.11',
        '404.13',
        '404.91',
        '404.93'
    )
    OR sd.diagnosis_code REGEXP '^428'
    OR sd.diagnosis_code in (
        '402.01',
        '402.11',
        '402.91',
        '404.01',
        '404.03',
        '404.11',
        '404.13',
        '404.91',
        '404.93'
    );
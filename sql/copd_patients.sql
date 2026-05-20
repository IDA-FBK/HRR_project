select
    DISTINCT he.crypted_patient_id
from
    healthcare_event he
    join inpatient_event ie on he.event_id = ie.event_id
    join diagnosis_code dc on ie.primary_diagnosis_code = dc.code
    join secondary_diagnosis sd on sd.event_id = ie.event_id
WHERE
    dc.code REGEXP '^49[0-2]'
    or dc.code REGEXP '^494'
    or dc.code REGEXP '^496'
    OR sd.diagnosis_code REGEXP '^49[0-2]'
    or sd.diagnosis_code REGEXP '^494'
    or sd.diagnosis_code REGEXP '^496'
UNION
SELECT
    he.crypted_patient_id
FROM
    healthcare_event he
    JOIN medication_event me ON he.event_id = me.event_id
    JOIN medication_code mc ON me.medication_code = mc.code
WHERE
    mc.ATC REGEXP '^R0' 
GROUP BY
    he.crypted_patient_id
HAVING(
    SUM(me.quantity) > 5 
    AND DATEDIFF(MAX(me.event_date), MIN(me.event_date)) >= 90
);
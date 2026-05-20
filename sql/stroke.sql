SELECT DISTINCT he.crypted_patient_id
FROM healthcare_event he
JOIN inpatient_event ie 
    ON he.event_id = ie.event_id
JOIN diagnosis_code dc 
    ON ie.primary_diagnosis_code = dc.code
JOIN secondary_diagnosis sd 
    ON sd.event_id = ie.event_id
WHERE 
    -- Hemorrhagic stroke
    dc.code REGEXP '^43[0-1]'
    OR sd.diagnosis_code REGEXP '^43[0-1]'
    -- Ischemic stroke: ICD 433.x1  
    OR dc.code REGEXP '^433\\.[0-9]*1$'
    OR sd.diagnosis_code REGEXP '^433\\.[0-9]*1$'
    -- Ischemic stroke: ICD 434.x1 
    OR dc.code REGEXP '^434\\.[0-9]*1$'
    OR sd.diagnosis_code REGEXP '^434\\.[0-9]*1$';

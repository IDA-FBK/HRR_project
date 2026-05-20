-- Pneumonia
SELECT DISTINCT he.crypted_patient_id
FROM healthcare_event he
JOIN inpatient_event ie 
    ON he.event_id = ie.event_id
JOIN diagnosis_code dc 
    ON ie.primary_diagnosis_code = dc.code
JOIN secondary_diagnosis sd 
    ON sd.event_id = ie.event_id
WHERE 
    dc.code REGEXP '^48[0-6]' 
    OR sd.diagnosis_code REGEXP '^48[0-6]'
    -- Pneumonia due to solids and liquids (507)
    OR dc.code REGEXP '^507'
    OR sd.diagnosis_code REGEXP '^507'
    -- Pulmonary tularemia
    OR dc.code = '021.2'
    OR sd.diagnosis_code = '021.2'
    -- Pulmonary actinomycosis 
    OR dc.code = '039.1'
    OR sd.diagnosis_code = '039.1'
    -- Varicella pneumonia
    OR dc.code = '052.1'
    OR sd.diagnosis_code = '052.1'
    -- Postmeasles pneumonia
    OR dc.code = '055.1'
    OR sd.diagnosis_code = '055.1'
    -- Ornithosis pneumonia 
    OR dc.code = '073.0'
    OR sd.diagnosis_code = '073.0'
    -- Candidiasis of lung
    OR dc.code = '112.4'
    OR sd.diagnosis_code = '112.4'
    -- Primary coccidioidomycosis
    OR dc.code REGEXP '^114'
    OR sd.diagnosis_code REGEXP '^114'
    -- Toxoplasmosis with pneumonia
    OR dc.code = '130.4'
    OR sd.diagnosis_code = '130.4'
    -- Pneumocystis carinii pneumonia
    OR dc.code = '136.3'
    OR sd.diagnosis_code = '136.3'
    -- Influenza with pneumonia
    OR dc.code = '487.0'
    OR sd.diagnosis_code = '487.0'
    -- Salmonella pneumonia
    OR dc.code = '003.22'
    OR sd.diagnosis_code = '003.22'
    -- Histoplasmosis with pneumonia
    OR dc.code IN ('115.05','115.15','115.95')
    OR sd.diagnosis_code IN ('115.05','115.15','115.95');

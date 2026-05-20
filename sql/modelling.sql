CREATE TABLE IF NOT EXISTS patients_readmission_flag AS 
SELECT 
    iel.crypted_patient_id,
    CASE 
        WHEN MAX(iel.is_readmitted) = 1 THEN 1
        ELSE 0
    END AS readmission_flag
FROM inpatient_episodes_labeled AS iel
GROUP BY iel.crypted_patient_id;

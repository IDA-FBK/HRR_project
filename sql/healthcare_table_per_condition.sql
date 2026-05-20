-- Table 2

SELECT p.condition, COUNT(*) AS patient_count
FROM patients p 
GROUP BY p.condition;

-- Number of hospitalizations per condition
SELECT p.condition, COUNT(*) AS patient_hospitalizations_count
FROM patients p 
NATURAL JOIN inpatient_episodes ie
GROUP BY p.condition;

-- Number of hospital readmissions (<= 30days, >1) per condition
SELECT 
    p.condition, 
    COUNT(*) AS readmissions_30d_gt1day
FROM inpatient_episodes cur
JOIN patients p 
    ON p.crypted_patient_id = cur.crypted_patient_id
WHERE DATEDIFF(cur.episode_end, cur.episode_start) > 1
  AND EXISTS (
      SELECT 1
      FROM inpatient_episodes prev
      WHERE prev.crypted_patient_id = cur.crypted_patient_id
        AND prev.episode_end < cur.episode_start
        AND DATEDIFF(cur.episode_start, prev.episode_end) <= 30
  )
GROUP BY p.condition;

-- Number of patients who experienced readmission (<=30days, >1) per condition
SELECT 
    p.condition, 
    COUNT(DISTINCT p.crypted_patient_id ) AS patients_30d_gt1day
FROM inpatient_episodes cur
JOIN patients p 
    ON p.crypted_patient_id = cur.crypted_patient_id
WHERE DATEDIFF(cur.episode_end, cur.episode_start) > 1
  -- Use EXISTS to prevent row multiplication
  AND EXISTS (
      SELECT 1
      FROM inpatient_episodes prev
      WHERE prev.crypted_patient_id = cur.crypted_patient_id
        AND prev.episode_end < cur.episode_start
        -- FIX: cur.start minus prev.end yields a positive number
        AND DATEDIFF(cur.episode_start, prev.episode_end) <= 30
  )
GROUP BY p.condition;

-- Number of emergency episodes per condition
SELECT p.condition, COUNT(*) AS patient_emergency_episodes
FROM patients p 
NATURAL JOIN emergency_care_episode ece 
GROUP BY p.condition;

-- Number of medications records per condition
SELECT p.condition, COUNT(*) AS medications_records
FROM patients p 
NATURAL JOIN healthcare_events.healthcare_event he
NATURAL JOIN medication_event me 
GROUP BY p.condition;

-- Number of ambulatory care records per condition
SELECT p.condition, COUNT(*) AS ambulatory_care_records
FROM patients p 
NATURAL JOIN healthcare_events.healthcare_event he
NATURAL JOIN ambulatory_event ae
GROUP BY p.condition;
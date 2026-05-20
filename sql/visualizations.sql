-- Age distribution for each condition
SELECT 
    p.condition,
    he.age_group, 
    COUNT(*) AS patient_count
FROM patients p
JOIN healthcare_events.healthcare_event he 
ON p.crypted_patient_id = he.crypted_patient_id 
GROUP BY p.condition, he.age_group
ORDER BY p.condition, he.age_group;

-- Monthly readmission over time
SELECT 
    DATE_FORMAT(cur.episode_start, '%Y-%m-01') AS month,
    COUNT(*) AS monthly_readmissions
FROM inpatient_episodes cur
JOIN inpatient_episodes prev
    ON cur.crypted_patient_id = prev.crypted_patient_id
    AND prev.episode_end < cur.episode_start
    AND DATEDIFF(prev.episode_end, cur.episode_start) <= 30
JOIN patients p
    ON p.crypted_patient_id = cur.crypted_patient_id
WHERE DATEDIFF(cur.episode_end, cur.episode_start) > 1
GROUP BY DATE_FORMAT(cur.episode_start, '%Y-%m-01')
ORDER BY month;

-- Distribution of readmissions for each department
SELECT 
	readmissions.department_id,
	d.description ,
	readmissions.department_readmissions
FROM healthcare_events.department d
JOIN (SELECT ie.department_id, COUNT(*) as department_readmissions
FROM inpatient_event ie 
JOIN inpatient_episodes cur 
	ON cur.episode_id = ie.associated_episode_id
JOIN inpatient_episodes prev
	ON  cur.crypted_patient_id = prev.crypted_patient_id
  	AND prev.episode_end < cur.episode_start
  	AND DATEDIFF(prev.episode_end, cur.episode_start) <= 30
JOIN patients p	
  ON p.crypted_patient_id = cur.crypted_patient_id
WHERE DATEDIFF(cur.episode_end, cur.episode_start) > 1
GROUP BY ie.department_id) as readmissions
ON d.id = readmissions.department_id;
-- Create indexes
CREATE INDEX idx_inpep_patient_start_end
    ON inpatient_episodes (crypted_patient_id, episode_start, episode_end);
CREATE INDEX idx_patients_crypted_condition
    ON patients (crypted_patient_id, 'condition');

SELECT 
    p.condition,
    he.age_group,
    SUM(CASE -- readmissions
        WHEN EXISTS (
            SELECT 1 FROM inpatient_episodes prev 
            WHERE prev.crypted_patient_id = ie.crypted_patient_id
            AND prev.episode_end < ie.episode_start
            AND DATEDIFF(ie.episode_start, prev.episode_end) BETWEEN 0 AND 30
        ) THEN 1 ELSE 0 
    END) as readmissions,
    SUM(CASE  -- initial admissions
        WHEN NOT EXISTS (
            SELECT 1 FROM inpatient_episodes prev 
            WHERE prev.crypted_patient_id = ie.crypted_patient_id
            AND prev.episode_end < ie.episode_start
            AND DATEDIFF(ie.episode_start, prev.episode_end) BETWEEN 0 AND 30
        ) THEN 1 ELSE 0 
    END) as initial_admissions
FROM patients p
JOIN inpatient_episodes ie ON p.crypted_patient_id = ie.crypted_patient_id
JOIN healthcare_events.healthcare_event he ON he.crypted_patient_id = ie.crypted_patient_id
WHERE YEAR(ie.episode_start) < 2024 AND DATEDIFF(ie.episode_end, ie.episode_start) > 1
GROUP BY p.condition, he.age_group;










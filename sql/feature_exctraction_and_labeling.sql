-- Create indexes for emergency_care_episodes and inpatient_episodes
CREATE INDEX idx_inpatient_patient_date 
ON inpatient_episodes (crypted_patient_id, episode_start);

CREATE INDEX idx_emergency_patient_date 
ON emergency_care_episode (crypted_patient_id, episode_start);

-- Count prior inpatient episodes, emergency episodes and emergency care episodes (12 months)
-- Then get meds used during the episode and 12 months before with age_group of patient
CREATE VIEW vw_patient_episode_features AS
WITH history AS (
    -- Selecting the distinct episode_id and the corresponding age_group
    -- We will use the patient's age group at the start of the episode
    SELECT 
        ie.episode_id,
        MIN(he.age_group) AS age_group, -- Age group from the healthcare event table associated with the episode
        (
            SELECT COUNT(*)
            FROM inpatient_episodes prev
            WHERE prev.crypted_patient_id = ie.crypted_patient_id
              AND prev.episode_start >= DATE_SUB(ie.episode_start, INTERVAL 12 MONTH)
              AND prev.episode_start < ie.episode_start
        ) AS count_prior_inpatient,
        (
            SELECT COUNT(*)
            FROM emergency_care_episode emerg
            WHERE emerg.crypted_patient_id = ie.crypted_patient_id
              AND emerg.episode_start >= DATE_SUB(ie.episode_start, INTERVAL 12 MONTH)
              AND emerg.episode_start < ie.episode_start
        ) AS count_prior_emergency,
	     	(SELECT COUNT(*)
		     FROM emergency_care_episode emerg
		     WHERE emerg.crypted_patient_id = ie.crypted_patient_id
		       AND emerg.episode_start >= DATE_SUB(ie.episode_start, INTERVAL 30 DAY)
		       AND emerg.episode_start < ie.episode_start
	    ) AS count_prior_emergency_30days,
        (
            SELECT COUNT(*)
            FROM healthcare_events.healthcare_event he_amb
            JOIN ambulatory_event ae ON ae.event_id = he_amb.event_id
            WHERE he_amb.crypted_patient_id = ie.crypted_patient_id
              AND ae.event_date >= DATE_SUB(ie.episode_start, INTERVAL 12 MONTH)
              AND ae.event_date < ie.episode_start
        ) AS count_prior_ambulatory
    FROM inpatient_episodes ie
    JOIN inpatient_event iev 
        ON iev.associated_episode_id = ie.episode_id
    JOIN healthcare_events.healthcare_event he 
        ON he.event_id = iev.event_id
    GROUP BY ie.episode_id, count_prior_inpatient, count_prior_emergency, count_prior_ambulatory, count_prior_emergency_30days
)
SELECT
    ie.episode_id,
    ie.crypted_patient_id,
    ie.episode_start,
    ie.episode_end,
    ie.num_inpatient_events,
    ie.num_days,
    ie.episode_type,
    ie.lookback_months,
    ie.lookahead_months,
    -- MAX(he.age_group) as age_group, -- We won't take MAX(he.age_group) here, as it risks picking the wrong value.
    h.age_group, -- Age group at the time of the current episode (accurate for this episode)
    h.count_prior_inpatient,
    h.count_prior_emergency,
    h.count_prior_ambulatory,
    COUNT(DISTINCT CASE 
        WHEN me.medication_type = 'P'
             AND me.event_date >= DATE_SUB(ie.episode_start, INTERVAL 12 MONTH)
             AND me.event_date < ie.episode_start
             AND me.medication_code  NOT LIKE 'A11%'
             AND me.medication_code NOT LIKE 'A12%'
             AND me.medication_code NOT LIKE 'D%'
        THEN me.medication_code END) AS P_ATC_12m_before,
    COUNT(DISTINCT CASE 
        WHEN me.medication_type = 'S'
             AND me.event_date >= DATE_SUB(ie.episode_start, INTERVAL 12 MONTH)
             AND me.event_date < ie.episode_start
             AND me.medication_code NOT LIKE 'A11%'
             AND me.medication_code NOT LIKE 'A12%'
             AND me.medication_code NOT LIKE 'D%'
        THEN me.medication_code END) AS S_ATC_12m_before,
    COUNT(DISTINCT CASE 
        WHEN me.medication_type = 'D'
             AND me.event_date >= DATE_SUB(ie.episode_start, INTERVAL 12 MONTH)
             AND me.event_date < ie.episode_start
             AND me.medication_code NOT LIKE 'A11%'
             AND me.medication_code NOT LIKE 'A12%'
             AND me.medication_code NOT LIKE 'D%'
        THEN me.medication_code END) AS D_ATC_12m_before,
    COUNT(DISTINCT CASE 
        WHEN me.medication_type = 'P'
             AND me.event_date BETWEEN ie.episode_start AND ie.episode_end
             AND me.medication_code NOT LIKE 'A11%'
             AND me.medication_code NOT LIKE 'A12%'
             AND me.medication_code NOT LIKE 'D%'
        THEN me.medication_code END) AS P_ATC_during_episode,
    COUNT(DISTINCT CASE 
        WHEN me.medication_type = 'S'
             AND me.event_date BETWEEN ie.episode_start AND ie.episode_end
             AND me.medication_code NOT LIKE 'A11%'
             AND me.medication_code NOT LIKE 'A12%'
             AND me.medication_code NOT LIKE 'D%'
        THEN me.medication_code END) AS S_ATC_during_episode,
    COUNT(DISTINCT CASE 
        WHEN me.medication_type = 'D'
             AND me.event_date BETWEEN ie.episode_start AND ie.episode_end
             AND me.medication_code NOT LIKE 'A11%'
             AND me.medication_code NOT LIKE 'A12%'
             AND me.medication_code NOT LIKE 'D%'
        THEN me.medication_code END) AS D_ATC_during_episode
FROM inpatient_episodes ie
JOIN history h ON h.episode_id = ie.episode_id
JOIN healthcare_events.healthcare_event he 
  ON he.crypted_patient_id = ie.crypted_patient_id 
LEFT JOIN medication_event me -- here we can lose information if no meds at all during episode or before (!!!!)
  ON me.event_id = he.event_id
GROUP BY
    ie.episode_id,
    ie.crypted_patient_id,
    ie.episode_start,
    ie.episode_end,
    ie.num_inpatient_events,
    ie.num_days,
    ie.episode_type,
    ie.lookback_months,
    ie.lookahead_months,
    h.age_group,
    h.count_prior_inpatient,
    h.count_prior_emergency,
    h.count_prior_ambulatory;
-- check number of rows stays the same (!!!)
-- get (episode_id,primary_diagnosis_code, age_group) for CCI.ipynb
-- added DISTINCT to avoid duplicates (!!!!)
CREATE TABLE inpatient_episode_history AS
WITH episode_age AS (
    SELECT DISTINCT 
        ie.episode_id, 
        he.age_group
    FROM inpatient_episodes ie
    JOIN inpatient_event ie2 
        ON ie2.associated_episode_id = ie.episode_id  
    JOIN healthcare_event he 
        ON he.event_id = ie2.event_id
),
all_relevant_events AS (
    -- Retrieve events from past episodes within 12 months of the current episode start
    SELECT
        ie_current.episode_id AS index_episode_id,  
        past_event.event_id  
    FROM inpatient_episodes ie_current
    JOIN inpatient_episodes ie_past
        ON ie_past.crypted_patient_id = ie_current.crypted_patient_id
       AND ie_past.episode_end < ie_current.episode_start          -- Prior episodes before current episode
       AND ie_past.episode_end >= DATE_SUB(ie_current.episode_start, INTERVAL 12 MONTH)  -- Within past 12 months
    JOIN inpatient_event past_event
        ON past_event.associated_episode_id = ie_past.episode_id
    UNION ALL 
    -- Retrieve events from the current episode    
    SELECT
        ie_current.episode_id AS index_episode_id,  
        curr_event.event_id  
    FROM inpatient_episodes ie_current
    JOIN inpatient_event curr_event
        ON curr_event.associated_episode_id = ie_current.episode_id
)
SELECT DISTINCT
    are.index_episode_id AS episode_id,  
    d.diagnosis_code,
    ae.age_group
FROM all_relevant_events are
JOIN (
    -- Primary diagnoses
    SELECT event_id, primary_diagnosis_code AS diagnosis_code
    FROM inpatient_event
    WHERE primary_diagnosis_code IS NOT NULL
    UNION ALL
    -- Secondary diagnoses
    SELECT event_id, diagnosis_code
    FROM healthcare_events.secondary_diagnosis
) d
    ON d.event_id = are.event_id
JOIN episode_age ae 
    ON ae.episode_id = are.index_episode_id  
ORDER BY episode_id, diagnosis_code;


-- Create table with extracted features
CREATE TABLE IF NOT EXISTS inpatient_episode_extracted AS
SELECT
    vw.episode_id,
    vw.crypted_patient_id,
    vw.age_group,
    vw.episode_start,
    vw.episode_end,
    vw.num_inpatient_events,
    vw.num_days,
    vw.episode_type,
    vw.lookback_months,
    vw.lookahead_months,
    vw.count_prior_inpatient,
    vw.count_prior_emergency,
    vw.count_prior_ambulatory,
    vw.P_ATC_12m_before,
    vw.S_ATC_12m_before,
    vw.D_ATC_12m_before,
    vw.P_ATC_during_episode,
    vw.S_ATC_during_episode,
    vw.D_ATC_during_episode,
    iec.num_comorbidities,
    iec.age_adj_comorbidity_score,
    mad.num_medications_at_discharge,
    -- compute entered_with_emergency directly
    CASE 
        WHEN EXISTS (
            SELECT 1
            FROM emergency_care_episode ece
            WHERE ece.crypted_patient_id = vw.crypted_patient_id
              AND ece.episode_end = vw.episode_start
        ) THEN 1
        ELSE 0
    END AS entered_with_emergency
FROM vw_patient_episode_features AS vw
LEFT JOIN inpatient_episode_comorbidity AS iec
  ON vw.episode_id = iec.id
LEFT JOIN medications_at_discharge mad on mad.episode_id = vw.episode_id;



-- Labeling
CREATE VIEW labelled_inpatient_episodes AS
WITH labelled_episodes AS (
    SELECT 
        ie.*,
        LEAD(episode_start) OVER ( -- get very next episode_start for crypted_patient_id
            PARTITION BY crypted_patient_id 
            ORDER BY episode_start ASC
        ) as next_episode_start
    FROM inpatient_episodes ie
)
SELECT 
	le.episode_id,
    le.crypted_patient_id,
    le.episode_start,
    le.episode_end,
    le.num_inpatient_events,
    le.num_days,
    le.total_cost,
    CASE 
        WHEN next_episode_start IS NOT NULL 
             AND DATEDIFF(next_episode_start, episode_end) <= 30 
        THEN 1 
        ELSE 0 
    END as is_readmitted
FROM labelled_episodes le
WHERE episode_end <= DATE_SUB('2024-03-31', INTERVAL 30 DAY); -- here we lose approx 200 rows 

SELECT COUNT(DISTINCT lie.crypted_patient_id)
FROM labelled_inpatient_episodes AS lie;

SELECT * 
FROM department d
WHERE d.department_relevance = 'keep' OR d.department_relevance = 'uncertain';
CREATE TABLE IF NOT EXISTS inpatient_episodes_labeled AS
SELECT *
FROM inpatient_episode_extracted AS iee
NATURAL JOIN labelled_inpatient_episodes AS lie
NATURAL JOIN selected_inpatient_episodes_labeled siel
NATURAL JOIN selected_inpatient_episodes_with_drg_features siewdf
NATURAL JOIN medications_at_discharge AS mad
WHERE 
    iee.lookback_months >= 12 
    AND iee.episode_type = 'RO' 
    AND iee.lookahead_months >= 1
    AND (siewdf.HF != 0 OR siewdf.IHD != 0 OR siewdf.Stroke != 0 OR siewdf.COPD != 0 OR siewdf.Pneumonia != 0);
ALTER TABLE inpatient_episodes_labeled
DROP COLUMN department_relevance;
ALTER TABLE 
SELECT * FROM
inpatient_episodes_labeled iel ;

DROP TABLE IF EXISTS inpatient_episode_extracted;
CREATE TABLE inpatient_episode_extracted AS
SELECT
    vw.episode_id,
    (
        SELECT COUNT(*)
        FROM emergency_care_episode ece
        WHERE ece.crypted_patient_id = vw.crypted_patient_id
          AND ece.episode_end >= vw.episode_start - INTERVAL 1 YEAR
          AND ece.episode_end < vw.episode_start
    ) AS count_er_12m_before
FROM vw_patient_episode_features AS vw
LEFT JOIN inpatient_episode_comorbidity AS iec
  ON vw.episode_id = iec.id
LEFT JOIN medications_at_discharge mad 
  ON mad.episode_id = vw.episode_id;
SELECT *
FROM inpatient_episodes_labeled iel 
NATURAL JOIN inpatient_episode_extracted iee;
CREATE INDEX idx_emergency_episode_end 
ON emergency_care_episode (episode_end);
ALTER TABLE inpatient_episodes_labeled 
DROP COLUMN is_readmitted;
CREATE TABLE inpatient_labeled AS
WITH EpisodeSequencing AS (
    SELECT 
    	*,
        -- Get the start date of the NEXT admission for this specific patient
        LEAD(episode_start) OVER (
            PARTITION BY crypted_patient_id 
            ORDER BY episode_start
        ) AS next_t_start
    FROM inpatient_episodes_labeled iel 
)
SELECT 
    *,
    CASE 
        WHEN next_t_start IS NOT NULL 
             AND DATEDIFF(next_t_start,episode_end) <= 30 
        THEN 1 
        ELSE 0 
    END AS is_readmitted
FROM EpisodeSequencing;
ALTER TABLE inpatient_labeled
DROP COLUMN next_t_start;


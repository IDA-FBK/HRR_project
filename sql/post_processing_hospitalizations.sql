-- SQL to update lookahead_months in inpatient_episodes table
UPDATE inpatient_episodes iep
JOIN (
    SELECT 
        he.crypted_patient_id,
        MAX(
            COALESCE(
                me.event_date,
                ae.event_date,
                ece.event_date
            )
        ) AS last_event_date
    FROM healthcare_event he
    LEFT JOIN patient_events_selected_conditions.patients p
        ON he.crypted_patient_id = p.crypted_patient_id
    LEFT JOIN ambulatory_event ae 
        ON he.event_id = ae.event_id
    LEFT JOIN medication_event me 
        ON he.event_id = me.event_id
    LEFT JOIN inpatient_event ie2 
        ON he.event_id = ie2.event_id
    LEFT JOIN emergency_care_event ece 
        ON he.event_id = ece.event_id
    LEFT JOIN home_care_event hce 
        ON he.event_id = hce.event_id
    LEFT JOIN residential_assessment_event rae 
        ON he.event_id = rae.event_id
    GROUP BY he.crypted_patient_id
) AS last_event_per_patient
    ON iep.crypted_patient_id = last_event_per_patient.crypted_patient_id
SET iep.lookahead_months = ROUND(
    GREATEST(
        DATEDIFF(last_event_per_patient.last_event_date, iep.episode_end), 0
    ) / 30.4375,
    2
);

-- SQL to create inpatient_episode_extracted table (with lookahead_months and entered_with_emergency)
drop table inpatient_episode_extracted;
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


-- SQL to create inpatient_episodes_labeled table (filtered with lookback and lookahead months)
drop table inpatient_episodes_labeled;
CREATE TABLE IF NOT EXISTS inpatient_episodes_labeled AS
SELECT
    iee.episode_id,
    iee.crypted_patient_id,
    iee.episode_start,
    iee.episode_end,
    iee.num_inpatient_events,
    iee.num_days,
    iee.episode_type,
    iee.lookback_months,
    iee.lookahead_months,
    iee.age_group,
    iee.count_prior_inpatient,
    iee.count_prior_emergency,
    iee.count_prior_ambulatory,
    iee.P_ATC_12m_before,
    iee.S_ATC_12m_before,
    iee.D_ATC_12m_before,
    iee.P_ATC_during_episode,
    iee.S_ATC_during_episode,
    iee.D_ATC_during_episode,
    iee.num_comorbidities,
    iee.age_adj_comorbidity_score,
    iee.entered_with_emergency,
    lie.total_cost,
    lie.is_readmitted,
    mad.num_medications_at_discharge
FROM inpatient_episode_extracted AS iee
NATURAL JOIN labelled_inpatient_episodes AS lie
LEFT JOIN medications_at_discharge AS mad
  ON mad.episode_id = iee.episode_id
WHERE iee.lookback_months >= 12
  AND iee.lookahead_months >= 1


-- SQL to create selected_inpatient_episodes_labeled table (filtered by department relevance)
CREATE TABLE selected_inpatient_episodes_labeled AS
SELECT *
FROM inpatient_episodes_labeled iel
WHERE EXISTS (
    SELECT 1
    FROM inpatient_event ie
    JOIN department d
      ON d.id = ie.department_id
    WHERE ie.associated_episode_id = iel.episode_id
      AND d.department_relevance IN ('keep', 'uncertain')
);

SELECT COUNT(DISTINCT sie2.crypted_patient_id)
FROM selected_inpatient_episodes_v2 as sie2
NATURAL JOIN selected_inpatient_episodes_with_drg_features;

SELECT COUNT(DISTINCT ie.crypted_patient_id)
FROM inpatient_episodes ie;

-- CREATE TABLE selected_inpatient_episodes_labeled AS
SELECT *
FROM selected_inpatient_episodes_with_drug_features siewdf 
WHERE siewdf.discharge_department IN (SELECT d.department_relevance FROM department d WHERE d.department_relevance = 'exclude')


create table medications_at_discharge as
WITH episodes AS (
    SELECT
        iep.episode_id,
        iep.crypted_patient_id,
        iep.episode_start,
        iep.episode_end
    FROM inpatient_episodes iep
), discharge_meds AS (
    SELECT
        he.crypted_patient_id,
        me.event_date,
        mc.ATC
    FROM medication_event me
    JOIN healthcare_event he ON he.event_id = me.event_id
    JOIN medication_code mc ON mc.code = me.medication_code
    WHERE me.medication_type in ('D', 'P')
      AND mc.ATC NOT LIKE 'A11%'
      AND mc.ATC NOT LIKE 'A12%'
      AND mc.ATC NOT LIKE 'D%'
)
, med_counts AS (
    SELECT
        e.episode_id,
        COUNT(DISTINCT d.ATC) AS num_medications_at_discharge
    FROM inpatient_episodes e
    LEFT JOIN discharge_meds d
        ON d.crypted_patient_id = e.crypted_patient_id
       AND d.event_date BETWEEN e.episode_end AND DATE_ADD(e.episode_end, INTERVAL 1 DAY)
    GROUP BY e.episode_id
)
SELECT
    e.*,
    COALESCE(m.num_medications_at_discharge, 0) AS num_medications_at_discharge
FROM inpatient_episodes e
LEFT JOIN med_counts m
    ON e.episode_id = m.episode_id;

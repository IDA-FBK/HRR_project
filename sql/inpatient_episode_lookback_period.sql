ALTER TABLE inpatient_episodes
ADD COLUMN lookback_months DECIMAL(5,2) DEFAULT NULL;


UPDATE inpatient_episodes iep
JOIN (
    SELECT 
        he.crypted_patient_id,
        MIN(
            COALESCE(
                me.event_date,
                ae.event_date,
                ie2.admission_date,
                ece.event_date
            )
        ) AS first_event_date
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
) AS first_event_per_patient
    ON iep.crypted_patient_id = first_event_per_patient.crypted_patient_id
SET iep.lookback_months = ROUND(
    GREATEST(
        DATEDIFF(iep.episode_start, first_event_per_patient.first_event_date), 0
    ) / 30.4375,
    2
);

use patient_events_selected_conditions;
select count(*)
from inpatient_episodes ie 
where ie.lookback_months >= 12;

ALTER TABLE inpatient_episodes
ADD COLUMN episode_type VARCHAR(3);

WITH episode_event_summary AS (
    SELECT
        ie.associated_episode_id AS episode_id,
        CASE
            WHEN SUM(CASE WHEN he.event_type = 'RO' THEN 1 ELSE 0 END) > 0 THEN 'RO'
            WHEN SUM(CASE WHEN he.event_type = 'DHC' THEN 1 ELSE 0 END) > 0 THEN 'DHC'
            ELSE 'DHM'
        END AS episode_type
    FROM inpatient_event ie
    join healthcare_event he on ie.event_id = he.event_id
    GROUP BY ie.associated_episode_id
)
UPDATE inpatient_episodes ep
JOIN episode_event_summary ees
  ON ep.episode_id = ees.episode_id
SET ep.episode_type = ees.episode_type;

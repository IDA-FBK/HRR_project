ALTER TABLE inpatient_episodes
ADD COLUMN lookahead_months DECIMAL(5,2) DEFAULT NULL;

UPDATE inpatient_episodes iep
JOIN (
    SELECT 
        he.crypted_patient_id,
        MAX(
            COALESCE(
                me.event_date,
                ae.event_date,
                ie2.admission_date,
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

select count(*)
from inpatient_episodes ie ;

select count(*)
from inpatient_episodes ie 
where ie.lookahead_months >= 1;

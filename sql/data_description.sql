WITH yearly_stats AS (
    SELECT 
        p.condition,
        YEAR(ie.episode_start) as report_year,
        COUNT(DISTINCT ie.crypted_patient_id) as n_patients,
        COUNT(ie.episode_id) as n_hospitalizations,
        SUM(CASE 
            WHEN EXISTS (
                SELECT 1 FROM inpatient_episodes prev 
                WHERE prev.crypted_patient_id = ie.crypted_patient_id
                AND prev.episode_end < ie.episode_start
                AND DATEDIFF(ie.episode_start, prev.episode_end) <= 30
            ) THEN 1 ELSE 0 
        END) as n_readmissions,
        COUNT(DISTINCT CASE
            WHEN EXISTS (
                SELECT 1 FROM inpatient_episodes prev 
                WHERE prev.crypted_patient_id = ie.crypted_patient_id
                AND prev.episode_end < ie.episode_start
                AND DATEDIFF(ie.episode_start, prev.episode_end) <= 30
            ) THEN ie.crypted_patient_id 
        END) as n_patients_readmitted
    FROM patients p
    JOIN inpatient_episodes ie ON p.crypted_patient_id = ie.crypted_patient_id
    WHERE YEAR(ie.episode_start) BETWEEN 2019 AND 2023
    GROUP BY p.`condition`, YEAR(ie.episode_start)
),
yearly_emergency AS (
    SELECT 
        p.condition,
        YEAR(ece.episode_start) as report_year,
        COUNT(ece.episode_id) as n_emergency
    FROM patients p
    JOIN emergency_care_episode ece ON p.crypted_patient_id = ece.crypted_patient_id
    WHERE YEAR(ece.episode_start) BETWEEN 2019 AND 2023
    GROUP BY p.`condition`, YEAR(ece.episode_start)
),
yearly_meds AS (
    SELECT 
        p.condition,
        YEAR(me.event_date) as report_year,
        COUNT(me.event_id) as n_meds
    FROM patients p
    JOIN healthcare_events.healthcare_event he ON he.crypted_patient_id = p.crypted_patient_id
    JOIN medication_event me ON me.event_id = he.event_id
    WHERE YEAR(me.event_date) BETWEEN 2019 AND 2023
    GROUP BY p.`condition`, YEAR(me.event_date)
),
yearly_ambulatory AS (
    SELECT 
        p.condition,
        YEAR(ae.event_date) as report_year,
        COUNT(ae.event_id) as n_ambulatory
    FROM patients p
    JOIN healthcare_events.healthcare_event he ON he.crypted_patient_id = p.crypted_patient_id
    JOIN ambulatory_event ae ON ae.event_id = he.event_id
    WHERE YEAR(ae.event_date) BETWEEN 2019 AND 2023
    GROUP BY p.`condition`, YEAR(ae.event_date)
)
SELECT 
    ys.`condition`,
    ys.report_year,
    ys.n_patients,
    ys.n_hospitalizations,
    ys.n_readmissions,
    ys.n_patients_readmitted,
    ye.n_emergency as n_emergency,
    ym.n_meds as n_meds,
    ya.n_ambulatory as n_ambulatory
FROM yearly_stats ys
LEFT JOIN yearly_emergency ye 
    ON ys.`condition` = ye.`condition` AND ys.report_year = ye.report_year
LEFT JOIN yearly_meds ym 
    ON ys.`condition` = ym.`condition` AND ys.report_year = ym.report_year
LEFT JOIN yearly_ambulatory ya 
    ON ys.`condition` = ya.`condition` AND ys.report_year = ya.report_year
ORDER BY ys.`condition`, ys.report_year;
-- Cost 
WITH yearly_stats AS (
    SELECT 
        p.`condition`,
        YEAR(ie.episode_start) as report_year,
        COUNT(DISTINCT ie.crypted_patient_id) as n_patients,
        COUNT(ie.episode_id) as n_hospitalizations,
        SUM(CASE 
            WHEN EXISTS (
                SELECT 1 FROM inpatient_episodes prev 
                WHERE prev.crypted_patient_id = ie.crypted_patient_id
                AND prev.episode_end < ie.episode_start
                AND DATEDIFF(ie.episode_start, prev.episode_end) <= 30
            ) THEN 1 ELSE 0 
        END) as n_readmissions,
        COUNT(DISTINCT CASE
            WHEN EXISTS (
                SELECT 1 FROM inpatient_episodes prev 
                WHERE prev.crypted_patient_id = ie.crypted_patient_id
                AND prev.episode_end < ie.episode_start
                AND DATEDIFF(ie.episode_start, prev.episode_end) <= 30
            ) THEN ie.crypted_patient_id 
        END) as n_patients_readmitted,
        SUM(ie.total_cost) as total_inpatient_cost
    FROM patients p
    JOIN inpatient_episodes ie ON p.crypted_patient_id = ie.crypted_patient_id
    WHERE YEAR(ie.episode_start) BETWEEN 2019 AND 2023
    GROUP BY p.`condition`, YEAR(ie.episode_start)
),
yearly_emergency AS (
    SELECT 
        p.condition,
        YEAR(ece.episode_start) as report_year,
        COUNT(ece.episode_id) as n_emergency,
        SUM(ece.total_cost) as total_emergency_cost
    FROM patients p
    JOIN emergency_care_episode ece ON p.crypted_patient_id = ece.crypted_patient_id
    WHERE YEAR(ece.episode_start) BETWEEN 2019 AND 2023
    GROUP BY p.`condition`, YEAR(ece.episode_start)
),
yearly_meds AS (
    SELECT 
        p.condition,
        YEAR(me.event_date) as report_year,
        COUNT(me.event_id) as n_meds,
        SUM(me.cost) as total_medication_cost
    FROM patients p
    JOIN healthcare_events.healthcare_event he ON he.crypted_patient_id = p.crypted_patient_id
    JOIN medication_event me ON me.event_id = he.event_id
    WHERE YEAR(me.event_date) BETWEEN 2019 AND 2023
    GROUP BY p.`condition`, YEAR(me.event_date)
),
yearly_ambulatory AS (
    SELECT 
        p.condition,
        YEAR(ae.event_date) as report_year,
        COUNT(ae.event_id) as n_ambulatory
    FROM patients p
    JOIN healthcare_events.healthcare_event he ON he.crypted_patient_id = p.crypted_patient_id
    JOIN ambulatory_event ae ON ae.event_id = he.event_id
    WHERE YEAR(ae.event_date) BETWEEN 2019 AND 2023
    GROUP BY p.`condition`, YEAR(ae.event_date)
)
SELECT 
    ys.`condition`,
    ys.report_year,
    -- Per-episode costs
    ys.total_inpatient_cost / ys.n_hospitalizations as avg_cost_per_hospitalization,
    ye.total_emergency_cost / ye.n_emergency as avg_cost_per_emergency_visit,
    ym.total_medication_cost / ys.n_patients as avg_medication_cost_per_patient
FROM yearly_stats ys
LEFT JOIN yearly_emergency ye 
    ON ys.`condition` = ye.`condition` AND ys.report_year = ye.report_year
LEFT JOIN yearly_meds ym 
    ON ys.`condition` = ym.`condition` AND ys.report_year = ym.report_year
LEFT JOIN yearly_ambulatory ya 
    ON ys.`condition` = ya.`condition` AND ys.report_year = ya.report_year
ORDER BY ys.`condition`, ys.report_year;


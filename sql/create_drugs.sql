CREATE TABLE selected_inpatient_episodes_with_drug_features AS (
SELECT
    siel.*,
    /* Antidiabetics: A10 */
    MAX(
        CASE
            WHEN mc.ATC LIKE 'A10%' THEN 1
            ELSE 0
        END
    ) AS any_antidiabetic,
    /* Antihypertensives: C02, C07, C08, C09 */
    MAX(
        CASE
            WHEN mc.ATC LIKE 'C02%'
              OR mc.ATC LIKE 'C07%'
              OR mc.ATC LIKE 'C08%'
              OR mc.ATC LIKE 'C09%'
            THEN 1
            ELSE 0
        END
    ) AS any_antihypertensive,
    /* Diuretics: C03 */
    MAX(
        CASE
            WHEN mc.ATC LIKE 'C03%' THEN 1
            ELSE 0
        END
    ) AS any_diuretic,
    /* NSAIDs: M01A */
    MAX(
        CASE
            WHEN mc.ATC LIKE 'M01A%' THEN 1
            ELSE 0
        END
    ) AS any_nsaid,
    /* Inhaled bronchodilators: beta2-agonists (R03AC) + anticholinergics (R03BB) */
    MAX(
        CASE
            WHEN mc.ATC LIKE 'R03AC%'
              OR mc.ATC LIKE 'R03BB%'
            THEN 1
            ELSE 0
        END
    ) AS any_inhaled_bronchodilator
FROM selected_inpatient_episodes_v2 siel
LEFT JOIN healthcare_event he
    ON siel.crypted_patient_id = he.crypted_patient_id
LEFT JOIN medication_event me
    ON me.event_id = he.event_id
   AND me.event_date >= DATE_SUB(siel.episode_start, INTERVAL 12 MONTH)
   AND me.event_date < siel.episode_start
LEFT JOIN healthcare_events.medication_code mc
    ON me.medication_code = mc.code
GROUP BY
    episode_id,
    crypted_patient_id,
    episode_start,
    episode_end,
    num_inpatient_events,
    num_days,
    episode_type,
    lookback_months,
    lookahead_months,
    age_group,
    count_prior_inpatient,
    count_prior_emergency,
    count_prior_ambulatory,
    P_ATC_12m_before,
    S_ATC_12m_before,
    D_ATC_12m_before,
    P_ATC_during_episode,
    S_ATC_during_episode,
    D_ATC_during_episode,
    num_comorbidities,
    age_adj_comorbidity_score,
    entered_with_emergency,
    total_cost,
    is_readmitted,
    num_medications_at_discharge,
    HF,
    COPD,
    IHD,
    Pneumonia,
    Stroke,
    any_antidiabetic,
    any_antihypertensive,
    any_diuretic,
    any_nsaid,
    discharge_department
);

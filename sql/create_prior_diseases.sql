CREATE TABLE selected_inpatient_episodes_with_drg_features AS
SELECT
    siel.*,
    -- Prior renal disease
	MAX(
	  CASE WHEN ie.drg_code LIKE '302%' OR ie.drg_code LIKE '303%' OR ie.drg_code LIKE '304%' OR ie.drg_code LIKE '305%'
	        OR ie.drg_code LIKE '316%' OR ie.drg_code LIKE '317%' OR ie.drg_code LIKE '318%' OR ie.drg_code LIKE '319%'
	        OR ie.drg_code LIKE '320%' OR ie.drg_code LIKE '321%' OR ie.drg_code LIKE '322%' OR ie.drg_code LIKE '323%'
	        OR ie.drg_code LIKE '324%' OR ie.drg_code LIKE '325%' OR ie.drg_code LIKE '326%' OR ie.drg_code LIKE '327%'
	        OR ie.drg_code LIKE '328%' OR ie.drg_code LIKE '329%' OR ie.drg_code LIKE '331%' OR ie.drg_code LIKE '332%'
	        OR ie.drg_code LIKE '333%'
	  THEN 1 ELSE 0 END
	) AS prior_renal_admission,
    -- Prior respiratory disease
	MAX(
	  CASE WHEN ie.drg_code LIKE '068%' OR ie.drg_code LIKE '069%' OR ie.drg_code LIKE '070%' OR ie.drg_code LIKE '071%'
	        OR ie.drg_code LIKE '072%' OR ie.drg_code LIKE '078%' OR ie.drg_code LIKE '079%' OR ie.drg_code LIKE '080%'
	        OR ie.drg_code LIKE '081%' OR ie.drg_code LIKE '087%' OR ie.drg_code LIKE '088%' OR ie.drg_code LIKE '089%'
	        OR ie.drg_code LIKE '090%' OR ie.drg_code LIKE '091%' OR ie.drg_code LIKE '092%' OR ie.drg_code LIKE '097%'
	        OR ie.drg_code LIKE '098%' OR ie.drg_code LIKE '099%' OR ie.drg_code LIKE '100%' OR ie.drg_code LIKE '101%'
	        OR ie.drg_code LIKE '102%' OR ie.drg_code LIKE '565%' OR ie.drg_code LIKE '566%'
	  THEN 1 ELSE 0 END
	) AS prior_respiratory_admission,
    -- Prior cerebrovascular disease / stroke
	MAX(
	  CASE WHEN ie.drg_code LIKE '014%' OR ie.drg_code LIKE '015%' OR ie.drg_code LIKE '016%' OR ie.drg_code LIKE '017%'
	        OR ie.drg_code LIKE '524%' OR ie.drg_code LIKE '559%'
	  THEN 1 ELSE 0 END
	) AS prior_stroke_admission,
		MAX(
	  CASE WHEN ie.drg_code LIKE '103%' OR ie.drg_code LIKE '105%' OR ie.drg_code LIKE '108%' OR ie.drg_code LIKE '110%'
	        OR ie.drg_code LIKE '111%' OR ie.drg_code LIKE '121%' OR ie.drg_code LIKE '122%' OR ie.drg_code LIKE '123%'
	        OR ie.drg_code LIKE '124%' OR ie.drg_code LIKE '125%' OR ie.drg_code LIKE '126%' OR ie.drg_code LIKE '127%'
	        OR ie.drg_code LIKE '140%' OR ie.drg_code LIKE '547%' OR ie.drg_code LIKE '548%' OR ie.drg_code LIKE '549%'
	        OR ie.drg_code LIKE '550%' OR ie.drg_code LIKE '551%' OR ie.drg_code LIKE '553%' OR ie.drg_code LIKE '554%'
	        OR ie.drg_code LIKE '555%' OR ie.drg_code LIKE '556%' OR ie.drg_code LIKE '557%' OR ie.drg_code LIKE '558%'
	  THEN 1 ELSE 0 END
	) AS prior_CHD_admission
FROM selected_inpatient_episodes_with_drug_features siel
LEFT JOIN healthcare_event he
    ON siel.crypted_patient_id = he.crypted_patient_id
LEFT JOIN inpatient_event ie
    ON he.event_id = ie.event_id
   AND ie.admission_date < siel.episode_start
   AND ie.admission_date >= DATE_SUB(siel.episode_start, INTERVAL 12 MONTH)
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
    discharge_department, any_antidiabetic, any_antihypertensive, any_diuretic, any_nsaid, any_inhaled_bronchodilator;

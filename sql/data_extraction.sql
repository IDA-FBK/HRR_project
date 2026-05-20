CREATE DATABASE IF NOT EXISTS HF_IHD_PatientEventDatabase;
-- Patients who have at least one record that satisfies Gini Conditions (inpatients or medication) for Heart failure --
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_patients AS
SELECT DISTINCT he.crypted_patient_id
FROM healthcare_event AS he
JOIN inpatient_event AS ie
     ON he.event_id = ie.event_id
JOIN diagnosis_code AS dc
     ON ie.primary_diagnosis_code = dc.code
JOIN secondary_diagnosis AS sd
     ON sd.event_id = ie.event_id
WHERE REGEXP_LIKE(dc.code, '^428') OR
    dc.code IN (
         '402.01', '402.11', '402.91',
         '404.01', '404.03', '404.11',
         '404.13', '404.91', '404.93'
    )
    OR sd.diagnosis_code REGEXP '^428' OR sd.diagnosis_code in (
         '402.01', '402.11', '402.91',
         '404.01', '404.03', '404.11',
         '404.13', '404.91', '404.93'
	);

-- Patients who have at least one record that satisfies Gini Conditions (inpatient or medication) for Ischaemic heart disease --
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_patients AS
SELECT DISTINCT he.crypted_patient_id
FROM healthcare_event AS he
JOIN inpatient_event AS ie
     ON he.event_id = ie.event_id
JOIN diagnosis_code AS dc
     ON ie.primary_diagnosis_code = dc.code
JOIN secondary_diagnosis AS sd
     ON sd.event_id = ie.event_id
WHERE 
    dc.code REGEXP '^410|^411|^412|^413|^414'
    OR sd.diagnosis_code REGEXP '^410|^411|^412|^413|^414'
UNION
SELECT DISTINCT crypted_patient_id
FROM (
    SELECT he.crypted_patient_id
    FROM healthcare_event AS he
    JOIN medication_event AS me
        ON me.event_id = he.event_id 
    JOIN medication_code AS mc
        ON mc.code = me.medication_code 
    WHERE mc.ATC LIKE 'C01DA%'
    GROUP BY he.crypted_patient_id, EXTRACT(YEAR FROM me.event_date)
    HAVING COUNT(DISTINCT me.event_date) >= 2
) as cryp;

-- Healthcare events for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_healthcare_event AS
SELECT
    he.event_id,
    he.crypted_patient_id,
    he.age_group,
    he.facility_id,
    he.event_type
FROM healthcare_event he
WHERE he.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.HF_patients
);
-- Healthcare events for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_healthcare_event AS
SELECT
    he.event_id,
    he.crypted_patient_id,
    he.age_group,
    he.facility_id,
    he.event_type
FROM healthcare_event he
WHERE he.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.IHD_patients
);
-- Inpatient events for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_inpatient_event AS
SELECT
    ie.event_id,
    ie.drg_code,
    ie.admission_date,
    ie.discharge_date,
    ie.department_id,
    ie.primary_diagnosis_code,
    ie.primary_intervention_code,
    ie.associated_episode_id
FROM healthcare_event he
NATURAL JOIN inpatient_event ie
WHERE he.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.HF_patients
);
-- Inpatient events for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_inpatient_event AS
SELECT
    ie.event_id,
    ie.drg_code,
    ie.admission_date,
    ie.discharge_date,
    ie.department_id,
    ie.primary_diagnosis_code,
    ie.primary_intervention_code,
    ie.associated_episode_id
FROM healthcare_event he
NATURAL JOIN inpatient_event ie
WHERE he.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.IHD_patients
);
-- Inpatient episodes for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_inpatient_episode AS
SELECT *
FROM inpatient_episode iee  
WHERE iee.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.HF_patients
);
-- Inpatient episodes for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_inpatient_episode AS
SELECT *
FROM inpatient_episode iee  
WHERE iee.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.IHD_patients
);
-- Ambulatory events for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_ambulatory_event AS
SELECT
	ae.event_id, 
	ae.event_date ,
	ae.cost 
FROM ambulatory_event ae 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.HF_patients
);
-- Ambulatory events for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_ambulatory_event AS
SELECT
	ae.event_id, 
	ae.event_date ,
	ae.cost 
FROM ambulatory_event ae 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.IHD_patients
);
-- Emergency events for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_emergency_event AS
SELECT
	ece.event_id ,
	ece.event_date ,
	ece.associated_episode_id 
FROM emergency_care_event ece  
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.HF_patients
);
-- Emergency events for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_emergency_event AS
SELECT
	ece.event_id ,
	ece.event_date ,
	ece.associated_episode_id 
FROM emergency_care_event ece  
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.IHD_patients
);
-- Emergency episodes for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_emergency_care_episode AS
SELECT 
	ece2.episode_id,
	ece2.crypted_patient_id ,
	ece2.episode_start ,
	ece2.episode_end ,
	ece2.num_days ,
	ece2.total_cost 
FROM emergency_care_episode ece2  
WHERE ece2.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.HF_patients
);
-- Emergency episodes for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_emergency_care_episode AS
SELECT 
	ece2.episode_id,
	ece2.crypted_patient_id ,
	ece2.episode_start ,
	ece2.episode_end ,
	ece2.num_days ,
	ece2.total_cost 
FROM emergency_care_episode ece2  
WHERE ece2.crypted_patient_id IN (
    SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.IHD_patients
);

-- Outpatient care events for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_outpatient_care AS 
SELECT 
	oc.event_id,
	oc.outpatient_code,
	oc.department_id ,
	oc.cost ,
	oc.quantity 
FROM outpatient_care oc 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN (
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.HF_patients
);
-- Outpatient care events for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_outpatient_care AS
SELECT 
	oc.event_id,
	oc.outpatient_code,
	oc.department_id ,
	oc.cost ,
	oc.quantity 
FROM outpatient_care oc 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN (
	SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.IHD_patients
);
-- Home care events for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_home_care_event AS 
SELECT 
	hce.event_id,
	hce.event_date 
FROM home_care_event hce 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN (
	SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.HF_patients
);
-- Home care events for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_home_care_event AS 
SELECT 
	hce.event_id,
	hce.event_date 
FROM home_care_event hce 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN (
	SELECT crypted_patient_id
    FROM HR_IHD_PatientEventDatabase.IHD_patients
);
-- Residential assessment for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_residential_assesment_event AS 
SELECT 
	rae.event_id,
	rae.event_date ,
	rae.primary_diagnosis_code 
FROM residential_assessment_event rae 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.HF_patients
);
-- Residential assessment for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_residential_assesment_event AS 
SELECT 
	rae.event_id,
	rae.event_date ,
	rae.primary_diagnosis_code 
FROM residential_assessment_event rae 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.IHD_patients
);
-- Hospice event for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_hospice_event AS 
SELECT 
	he.event_id,
	he.admission_date ,
	he.discharge_date ,
	he.cost 
FROM hospice_event he 
NATURAL JOIN healthcare_event he2 
WHERE he2.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.HF_patients
);
-- Hospice event for IHD patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_hospice_event AS 
SELECT 
	he.event_id,
	he.admission_date ,
	he.discharge_date ,
	he.cost 
FROM hospice_event he 
NATURAL JOIN healthcare_event he2 
WHERE he2.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.IHD_patients
);
-- Secondary diagnosis for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_secondary_diagnosis
SELECT
	sd.event_id ,
	sd.diagnosis_code 
FROM secondary_diagnosis sd 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.HF_patients
);
-- Secondary diagnosis for HF patient group
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_secondary_diagnosis
SELECT
	sd.event_id ,
	sd.diagnosis_code 
FROM secondary_diagnosis sd 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.IHD_patients
);
-- Secondary intervention for HF patient group 
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_secondary_intervention
SELECT
	si.event_id ,
	si.intervention_code  
FROM secondary_intervention si 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.HF_patients
);
-- Secondary intervention for IHD patient group 
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_secondary_intervention
SELECT
	si.event_id ,
	si.intervention_code  
FROM secondary_intervention si 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.IHD_patients
);
-- Outpatient codes used in HF_outpatient_care
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_outpatient_code AS 
SELECT 
	oc.code ,
	oc.description 
FROM outpatient_code oc 
WHERE oc.code IN (
	SELECT hoc.outpatient_code 
	FROM HF_IHD_PatientEventDatabase.HF_outpatient_care hoc 
);
-- Outpatient codes used in IHD_outpatient_care
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_outpatient_code AS 
SELECT 
	oc.code ,
	oc.description 
FROM outpatient_code oc 
WHERE oc.code IN (
	SELECT hoc.outpatient_code 
	FROM HF_IHD_PatientEventDatabase.IHD_outpatient_care hoc 
);
-- Codes used as a primary (inpatient) or secondary diagnoses for patients HF
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_diagnosis_code AS 
SELECT 
	dc.code,
	dc.description 
FROM diagnosis_code dc 
WHERE dc.code IN (
	SELECT hie.primary_diagnosis_code 
	FROM HF_IHD_PatientEventDatabase.HF_inpatient_event hie 
	UNION
	SELECT hsd.diagnosis_code 
	FROM HF_IHD_PatientEventDatabase.HF_secondary_diagnosis hsd
); 
-- Codes used as a primary (inpatient) or secondary diagnoses for patients IHD
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_diagnosis_code AS 
SELECT 
	dc.code,
	dc.description 
FROM diagnosis_code dc 
WHERE dc.code IN (
	SELECT hie.primary_diagnosis_code 
	FROM HF_IHD_PatientEventDatabase.IHD_inpatient_event hie 
	UNION
	SELECT hsd.diagnosis_code 
	FROM HF_IHD_PatientEventDatabase.IHD_secondary_diagnosis hsd
); 
-- Codes for interventions on patients HF
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_intervention_code AS 
SELECT 
	ic.code,
	ic.description 
FROM intervention_code ic 
WHERE ic.code IN (
	SELECT hsi.intervention_code 
	FROM HF_IHD_PatientEventDatabase.HF_secondary_intervention hsi 
);
-- Codes for interventions on patients IHD
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_intervention_code AS 
SELECT 
	ic.code,
	ic.description 
FROM intervention_code ic 
WHERE ic.code IN (
	SELECT hsi.intervention_code 
	FROM HF_IHD_PatientEventDatabase.IHD_secondary_intervention hsi 
);
-- Medication events for patients HF
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.HF_medication_code AS 
SELECT 
	me.event_id ,
	me.event_date ,
	me.medication_code ,
	me.medication_type ,
	me.department_id ,
	me.quantity ,
	me.cost 
FROM medication_event me 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.HF_patients
);
-- Medication events for patients IHD
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.IHD_medication_code AS 
SELECT 
	me.event_id ,
	me.event_date ,
	me.medication_code ,
	me.medication_type ,
	me.department_id ,
	me.quantity ,
	me.cost 
FROM medication_event me 
NATURAL JOIN healthcare_event he 
WHERE he.crypted_patient_id IN(
	SELECT crypted_patient_id
    FROM HF_IHD_PatientEventDatabase.IHD_patients
);
-- Cleaned facility
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.facility AS 
SELECT
	f.id ,
	f.description ,
	f.unified_id 
FROM facility f;
-- Department
CREATE TABLE IF NOT EXISTS HF_IHD_PatientEventDatabase.department AS 
SELECT *
FROM department d;
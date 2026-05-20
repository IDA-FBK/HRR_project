SHOW INDEX FROM healthcare_events.medication_event;

SHOW INDEX FROM healthcare_events.healthcare_event;

SHOW INDEX FROM healthcare_events.ambulatory_event;

DROP INDEX idx_med_event_lookup ON medication_event;

-- CREATE INDEXES
CREATE UNIQUE INDEX idx_med_event_event_id
ON medication_event (event_id);

CREATE INDEX idx_patients_crypted_pid 
ON patient_events_selected_conditions.patients (crypted_patient_id);

-- QUERIES
SELECT p.condition, COUNT(*) AS medications_records
FROM patient_events_selected_conditions.patients p 
NATURAL JOIN healthcare_events.healthcare_event he
NATURAL JOIN medication_event me 
GROUP BY p.condition;


SELECT p.condition, COUNT(*) AS medications_records
FROM patient_events_selected_conditions.patients p 
JOIN healthcare_events.healthcare_event he on he.crypted_patient_id = p.crypted_patient_id 
JOIN medication_event me on he.event_id = me.event_id 
GROUP BY p.condition;


SELECT p.condition, COUNT(*) AS ambulatory_care_records
FROM patient_events_selected_conditions.patients p 
NATURAL JOIN healthcare_events.healthcare_event he
NATURAL JOIN ambulatory_event ae
GROUP BY p.condition;

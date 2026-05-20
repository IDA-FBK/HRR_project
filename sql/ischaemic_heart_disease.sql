SELECT
    DISTINCT crypted_patient_id
FROM
    (
        SELECT
            DISTINCT he.crypted_patient_id
        FROM
            healthcare_event he
            JOIN inpatient_event ie ON he.event_id = ie.event_id
            JOIN diagnosis_code dc ON ie.primary_diagnosis_code = dc.code
            JOIN secondary_diagnosis sd ON sd.event_id = ie.event_id
        WHERE
            dc.code REGEXP '^41[0-4]'
            OR sd.diagnosis_code REGEXP '^41[0-4]'
        UNION
        SELECT
            me_group.crypted_patient_id
        FROM
            (
                SELECT
                    he.crypted_patient_id,
                    YEAR(me.event_date) AS disp_year,
                    COUNT(DISTINCT me.event_date) AS distinct_disp_days
                FROM
                    healthcare_event he
                    JOIN medication_event me ON he.event_id = me.event_id
                    JOIN medication_code mc ON me.medication_code = mc.code
                WHERE
                    mc.ATC REGEXP '^C01DA'
                GROUP BY
                    he.crypted_patient_id,
                    YEAR(me.event_date)
                HAVING
                    COUNT(DISTINCT me.event_date) >= 2
            ) AS me_group
    ) AS combined;
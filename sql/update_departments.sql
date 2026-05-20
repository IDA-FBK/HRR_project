UPDATE department 
SET department_relevance = CASE
    -- Keep relevant departments
    WHEN description IN (
        'Cardiologia',
        'Unità Coronarica',
        'Cardiochirurgia',
        'Chirurgia Vascolare - Angiologia',
        'Pneumologia',
        'Medicina Generale',
        'Terapia Intensiva',
        'Terapia Semi Intensiva',
        'Neurologia',
        'Medicina Fisica E Riabilitazione',
        'Geriatria'
    ) THEN 'keep'
    -- Uncertain / possibly relevant departments (optional)
    WHEN description IN (
        'Cardiochirurgia Infantile',
        'Chirurgia Toracica',
        'Nefrologia',
        'Nefrologia (Abilitato Al Trapianto Rene)',
        'Oncologia',
        'Lungodegenti'
    ) THEN 'uncertain'
    -- All others generally not relevant
    ELSE 'exclude'
END;

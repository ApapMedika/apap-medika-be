from django.db import models

class TimestampedModel(models.Model):
    """
    Abstract base class with common timestamp fields
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True

class UserActionModel(TimestampedModel):
    """
    Abstract base class with user tracking fields
    """
    created_by = models.CharField(max_length=150, null=True, blank=True)
    updated_by = models.CharField(max_length=150, null=True, blank=True)
    
    class Meta:
        abstract = True

# Treatment data that will be inserted manually
TREATMENT_DATA = [
    (1, 'X-ray', 150000),
    (2, 'CT Scan', 1000000),
    (3, 'MRI', 2500000),
    (4, 'Ultrasound', 300000),
    (5, 'Blood Clotting Test', 50000),
    (6, 'Blood Glucose Test', 30000),
    (7, 'Liver Function Test', 75000),
    (8, 'Complete Blood Count', 50000),
    (9, 'Urinalysis', 40000),
    (10, 'COVID-19 testing', 150000),
    (11, 'Cholesterol Test', 60000),
    (12, 'Inpatient care', 1000000),
    (13, 'Surgery', 7000000),
    (14, 'ICU', 2000000),
    (15, 'ER', 500000),
    (16, 'Flu shot', 100000),
    (17, 'Hepatitis vaccine', 200000),
    (18, 'COVID-19 Vaccine', 200000),
    (19, 'MMR Vaccine', 350000),
    (20, 'HPV Vaccine', 800000),
    (21, 'Pneumococcal Vaccine', 900000),
    (22, 'Herpes Zoster Vaccine', 1500000),
    (23, 'Physical exam', 250000),
    (24, 'Mammogram', 500000),
    (25, 'Colonoscopy', 3000000),
    (26, 'Dental X-ray', 200000),
    (27, 'Fillings', 400000),
    (28, 'Dental scaling', 500000),
    (29, 'Physical therapy', 250000),
    (30, 'Occupational therapy', 300000),
    (31, 'Speech therapy', 300000),
    (32, 'Psychiatric evaluation', 600000),
    (33, 'Natural delivery', 3500000),
    (34, 'C-section', 12000000),
]

# Coverage data that will be inserted manually
COVERAGE_DATA = [
    (1, 'X-ray', 150000),
    (2, 'CT Scan', 1000000),
    (3, 'MRI', 2500000),
    (4, 'Ultrasound', 300000),
    (5, 'Blood Clotting Test', 50000),
    (6, 'Blood Glucose Test', 30000),
    (7, 'Liver Function Test', 75000),
    (8, 'Complete Blood Count', 50000),
    (9, 'Urinalysis', 40000),
    (10, 'COVID-19 testing', 150000),
    (11, 'Cholesterol Test', 60000),
    (12, 'Inpatient care', 1000000),
    (13, 'Surgery', 7000000),
    (14, 'ICU', 2000000),
    (15, 'ER', 500000),
    (16, 'Flu shot', 100000),
    (17, 'Hepatitis vaccine', 200000),
    (18, 'COVID-19 Vaccine', 200000),
    (19, 'MMR Vaccine', 350000),
    (20, 'HPV Vaccine', 800000),
    (21, 'Pneumococcal Vaccine', 900000),
    (22, 'Herpes Zoster Vaccine', 1500000),
    (23, 'Physical exam', 250000),
    (24, 'Mammogram', 500000),
    (25, 'Colonoscopy', 3000000),
    (26, 'Dental X-ray', 200000),
    (27, 'Fillings', 400000),
    (28, 'Dental scaling', 500000),
    (29, 'Physical therapy', 250000),
    (30, 'Occupational therapy', 300000),
    (31, 'Speech therapy', 300000),
    (32, 'Psychiatric evaluation', 600000),
    (33, 'Natural delivery', 3500000),
    (34, 'C-section', 12000000),
]

# Doctor specialization mapping
DOCTOR_SPECIALIZATIONS = {
    0: "UMM",  # General Practitioner
    1: "GGI",  # Dentist
    2: "ANK",  # Pediatrician
    3: "BDH",  # Surgery
    4: "PRE",  # Plastic, Reconstructive, and Aesthetic Surgery
    5: "JPD",  # Heart and Blood Vessels
    6: "KKL",  # Skin and Venereal Diseases
    7: "MTA",  # Eyes
    8: "OBG",  # Obstetrics and Gynecology
    9: "PDL",  # Internal Medicine
    10: "PRU", # Lungs
    11: "ENT", # Ear, Nose, Throat, Head and Neck Surgery
    12: "RAD", # Radiology
    13: "KSJ", # Mental Health
    14: "ANS", # Anesthesia
    15: "NRO", # Neurology
    16: "URO", # Urology
}
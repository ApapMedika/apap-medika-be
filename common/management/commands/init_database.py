from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.hashers import make_password
from faker import Faker
import random

from profiles.models import EndUser, Admin, Nurse, Patient, Doctor, Pharmacist
from appointment.models import Treatment
from insurance.models import Coverage
from pharmacy.models import Medicine
from hospitalization.models import Facility

fake = Faker()

class Command(BaseCommand):
    help = 'Initialize database with static data and sample users'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-data',
            action='store_true',
            help='Create sample data including users',
        )
    
    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Initializing database...')
            
            # Create static data
            self.create_treatments()
            self.create_coverages()
            self.create_sample_medicines()
            self.create_sample_facilities()
            
            if options['sample_data']:
                self.create_sample_users()
                self.create_sample_doctors()
                self.create_sample_pharmacists()
            
            self.stdout.write(
                self.style.SUCCESS('Database initialized successfully!')
            )
    
    def create_treatments(self):
        """Create treatment data"""
        self.stdout.write('Creating treatments...')
        
        treatment_data = [
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
        
        for treatment_id, name, price in treatment_data:
            Treatment.objects.get_or_create(
                id=treatment_id,
                defaults={'name': name, 'price': price}
            )
        
        self.stdout.write(f'Created {len(treatment_data)} treatments')
    
    def create_coverages(self):
        """Create coverage data (same as treatments)"""
        self.stdout.write('Creating coverages...')
        
        coverage_data = [
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
        
        for coverage_id, name, amount in coverage_data:
            Coverage.objects.get_or_create(
                id=coverage_id,
                defaults={'name': name, 'coverage_amount': amount}
            )
        
        self.stdout.write(f'Created {len(coverage_data)} coverages')
    
    def create_sample_medicines(self):
        """Create sample medicines"""
        self.stdout.write('Creating sample medicines...')
        
        medicine_names = [
            'Paracetamol 500mg', 'Ibuprofen 400mg', 'Amoxicillin 500mg',
            'Aspirin 81mg', 'Metformin 500mg', 'Lisinopril 10mg',
            'Atorvastatin 20mg', 'Omeprazole 20mg', 'Amlodipine 5mg',
            'Simvastatin 40mg', 'Levothyroxine 50mcg', 'Albuterol Inhaler',
            'Furosemide 40mg', 'Prednisone 20mg', 'Gabapentin 300mg',
            'Tramadol 50mg', 'Hydrochlorothiazide 25mg', 'Warfarin 5mg',
            'Insulin Glargine', 'Vitamin D3 1000IU', 'Folic Acid 5mg',
            'Iron Sulfate 325mg', 'Calcium Carbonate 500mg', 'Multivitamin',
            'Cold Pack', 'Ketoprofen Gel 30g', 'Naproxen 250mg', 'Elastic Bandage'
        ]
        
        for i, name in enumerate(medicine_names):
            medicine_id = f"MED{str(i+1).zfill(4)}"
            price = random.randint(5000, 50000)  # Random price between 5k-50k
            stock = random.randint(50, 500)
            
            Medicine.objects.get_or_create(
                id=medicine_id,
                defaults={
                    'name': name,
                    'price': price,
                    'stock': stock,
                    'description': f'Medicine for {name.lower()}',
                    'created_by': 'system',
                    'updated_by': 'system'
                }
            )
        
        self.stdout.write(f'Created {len(medicine_names)} medicines')
    
    def create_sample_facilities(self):
        """Create sample facilities"""
        self.stdout.write('Creating sample facilities...')
        
        facility_data = [
            ('WiFi Access', 50000),
            ('Television', 25000),
            ('Air Conditioning', 100000),
            ('Private Bathroom', 75000),
            ('Mini Refrigerator', 40000),
            ('Telephone', 20000),
            ('Extra Bed', 150000),
            ('Meal Service', 80000),
            ('Laundry Service', 30000),
            ('Nursing Care', 200000),
            ('Physical Therapy', 300000),
            ('Wheelchair Rental', 50000),
            ('Oxygen Support', 250000),
            ('IV Stand', 75000),
            ('Medical Equipment', 500000),
        ]
        
        for name, fee in facility_data:
            Facility.objects.get_or_create(
                name=name,
                defaults={
                    'fee': fee,
                    'created_by': 'system',
                    'updated_by': 'system'
                }
            )
        
        self.stdout.write(f'Created {len(facility_data)} facilities')
    
    def create_sample_users(self):
        """Create sample users for each role"""
        self.stdout.write('Creating sample users...')
        
        # Create admin user
        admin_user, _ = EndUser.objects.get_or_create(
            email='admin@apapmedika.com',
            defaults={
                'username': 'admin',
                'name': 'System Administrator',
                'gender': False,
                'role': 'ADMIN',
                'password': make_password('admin123')
            }
        )
        # Use get_or_create for Admin as well
        Admin.objects.get_or_create(user=admin_user)
        
        # Create nurses
        for i in range(3):
            nurse_user, _ = EndUser.objects.get_or_create(
                email=f'nurse{i+1}@apapmedika.com',
                defaults={
                    'username': f'nurse{i+1}',
                    'name': fake.name(),
                    'gender': random.choice([True, False]),
                    'role': 'NURSE',
                    'password': make_password('nurse123')
                }
            )
            # Use get_or_create for Nurse
            Nurse.objects.get_or_create(user=nurse_user)
        
        # Create patients
        for i in range(10):
            patient_user, _ = EndUser.objects.get_or_create(
                email=f'patient{i+1}@example.com',
                defaults={
                    'username': f'patient{i+1}',
                    'name': fake.name(),
                    'gender': random.choice([True, False]),
                    'role': 'PATIENT',
                    'password': make_password('patient123')
                }
            )
            # Use get_or_create for Patient
            Patient.objects.get_or_create(
                user=patient_user,
                defaults={
                    'nik': fake.numerify('################'),
                    'birth_place': fake.city(),
                    'birth_date': fake.date_of_birth(minimum_age=18, maximum_age=80),
                    'p_class': random.choice([1, 2, 3])
                }
            )
        
        self.stdout.write('Created sample users')
    
    def create_sample_doctors(self):
        """Create sample doctors"""
        self.stdout.write('Creating sample doctors...')
        
        specializations = list(range(17))  # 0-16
        
        for i in range(8):
            doctor_user, _ = EndUser.objects.get_or_create(
                email=f'doctor{i+1}@apapmedika.com',
                defaults={
                    'username': f'doctor{i+1}',
                    'name': fake.name(),
                    'gender': random.choice([True, False]),
                    'role': 'DOCTOR',
                    'password': make_password('doctor123')
                }
            )
            
            # Generate doctor ID
            specialty_codes = {
                0: "UMM", 1: "GGI", 2: "ANK", 3: "BDH", 4: "PRE", 5: "JPD",
                6: "KKL", 7: "MTA", 8: "OBG", 9: "PDL", 10: "PRU", 11: "ENT",
                12: "RAD", 13: "KSJ", 14: "ANS", 15: "NRO", 16: "URO"
            }
            specialization = random.choice(specializations)
            specialty_code = specialty_codes.get(specialization, "UMM")
            doctor_id = f"{specialty_code}{str(i+1).zfill(3)}"
            
            # Use get_or_create for Doctor
            Doctor.objects.get_or_create(
                id=doctor_id,
                defaults={
                    'user': doctor_user,
                    'specialization': specialization,
                    'years_of_experience': random.randint(2, 25),
                    'fee': random.randint(200000, 1000000),
                    'schedules': random.sample(range(7), k=random.randint(3, 5))
                }
            )
        
        self.stdout.write('Created sample doctors')
    
    def create_sample_pharmacists(self):
        """Create sample pharmacists"""
        self.stdout.write('Creating sample pharmacists...')
        
        for i in range(3):
            # First, get or create the base EndUser
            pharmacist_user, _ = EndUser.objects.get_or_create(
                email=f'pharmacist{i+1}@apapmedika.com',
                defaults={
                    'username': f'pharmacist{i+1}',
                    'name': fake.name(),
                    'gender': random.choice([True, False]),
                    'role': 'PHARMACIST',
                    'password': make_password('pharmacist123')
                }
            )
            
            # Now, use get_or_create for the Pharmacist profile to make it idempotent
            Pharmacist.objects.get_or_create(user=pharmacist_user)
        
        self.stdout.write('Created sample pharmacists')
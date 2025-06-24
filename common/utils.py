import jwt
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from common.models import DOCTOR_SPECIALIZATIONS
import string
import random

def generate_jwt_token(user):
    """
    Generate JWT token for user authentication
    """
    now = timezone.now()
    exp = now + timedelta(seconds=settings.JWT_EXPIRATION_DELTA)
    
    payload = {
        'id': str(user.id),
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'exp': int(exp.timestamp()),
        'iat': int(now.timestamp()),
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token

def decode_jwt_token(token):
    """
    Decode JWT token and return payload
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')

def get_user_from_token(token):
    """
    Get user instance from JWT token
    """
    from profiles.models import EndUser  # Import here to avoid circular imports
    
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get('id')
        if user_id:
            return EndUser.objects.get(id=user_id, deleted_at__isnull=True)
        return None
    except (EndUser.DoesNotExist, Exception):
        return None

def get_appointment_code(doctor_specialization, appointment_date, sequence):
    """
    Generate appointment code: specialty(3) + date(4) + sequence(3)
    """
    specialty_code = DOCTOR_SPECIALIZATIONS.get(doctor_specialization, "UMM")
    date_str = appointment_date.strftime("%d%m")
    sequence_str = str(sequence).zfill(3)
    return f"{specialty_code}{date_str}{sequence_str}"

def get_doctor_code(specialization, sequence):
    """
    Generate doctor code: specialty(3) + sequence(3)
    """
    specialty_code = DOCTOR_SPECIALIZATIONS.get(specialization, "UMM")
    sequence_str = str(sequence).zfill(3)
    return f"{specialty_code}{sequence_str}"

def get_medicine_code(sequence):
    """
    Generate medicine code: MED + sequence(4)
    """
    sequence_str = str(sequence).zfill(4)
    return f"MED{sequence_str}"

def get_room_code(sequence):
    """
    Generate room code: RM + sequence(4)
    """
    sequence_str = str(sequence).zfill(4)
    return f"RM{sequence_str}"

def get_prescription_code(medicine_count, day_of_week, time_str):
    """
    Generate prescription code: RES + medicine_count(2) + day(3) + time(8)
    """
    medicine_count_str = str(medicine_count)[-2:].zfill(2)
    days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    day_code = days[day_of_week]
    
    return f"RES{medicine_count_str}{day_code}{time_str}"

def get_reservation_code(date_diff, day_of_week, nik_last_4, total_reservations):
    """
    Generate reservation code: RES + date_diff(2) + day(3) + nik_last_4(4) + sequence(4)
    """
    date_diff_str = str(date_diff)[-2:].zfill(2)
    days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    day_code = days[day_of_week]
    sequence_str = str(total_reservations + 1).zfill(4)
    
    return f"RES{date_diff_str}{day_code}{nik_last_4}{sequence_str}"

def get_policy_code(patient_name, company_name, total_policies):
    """
    Generate policy code: POL + patient_initials(2) + company_initials(3) + sequence(4)
    """
    # Get patient initials
    name_parts = patient_name.strip().split()
    if len(name_parts) >= 2:
        patient_initials = (name_parts[0][:1] + name_parts[1][:1]).upper()
    else:
        patient_initials = name_parts[0][:2].upper()
    
    # Get company initials
    company_initials = company_name[:3].upper()
    
    # Get sequence
    sequence_str = str(total_policies + 1).zfill(4)
    
    return f"POL{patient_initials}{company_initials}{sequence_str}"

def soft_delete_object(obj, user):
    """
    Soft delete an object by setting deleted_at timestamp
    """
    obj.deleted_at = timezone.now()
    obj.updated_by = user.username if user else None
    obj.save()

def update_user_fields(obj, user):
    """
    Update created_by and updated_by fields
    """
    if not obj.pk:  # New object
        obj.created_by = user.username if user else None
    obj.updated_by = user.username if user else None

def generate_random_string(length=10):
    """
    Generate random string
    """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def calculate_age(birth_date):
    """
    Calculate age from birth date
    """
    today = timezone.now().date()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def get_days_between_dates(start_date, end_date):
    """
    Calculate days between two dates
    """
    return (end_date - start_date).days + 1

def format_currency(amount):
    """
    Format currency to Indonesian Rupiah
    """
    return f"Rp {amount:,.2f}".replace('.00', '')

def get_available_limit(patient, policies):
    """
    Calculate available insurance limit for patient
    """
    insurance_limits = {
        1: 100000000,  # Class 1 - Rp 100,000,000
        2: 50000000,   # Class 2 - Rp 50,000,000
        3: 25000000,   # Class 3 - Rp 25,000,000
    }
    
    total_limit = insurance_limits.get(patient.p_class, 0)
    total_coverage_used = sum(policy.total_coverage for policy in policies if policy.status != 4)  # Exclude cancelled
    
    return total_limit - total_coverage_used

def validate_nik(nik):
    """
    Validate Indonesian NIK (16 digits)
    """
    if not nik or len(nik) != 16 or not nik.isdigit():
        return False
    return True

def get_prescription_status_display(status):
    """
    Get human readable prescription status
    """
    status_map = {
        0: 'Created',
        1: 'Waiting for Stock',
        2: 'Done',
        3: 'Cancelled',
    }
    return status_map.get(status, 'Unknown')

def get_status_color(status, entity_type='prescription'):
    """
    Get CSS color class for status badges
    """
    if entity_type == 'prescription':
        color_map = {
            0: 'bg-blue-100 text-blue-800',    # Created
            1: 'bg-yellow-100 text-yellow-800', # Waiting for Stock
            2: 'bg-green-100 text-green-800',   # Done
            3: 'bg-red-100 text-red-800',       # Cancelled
        }
    else:
        # Default color mapping
        color_map = {
            0: 'bg-blue-100 text-blue-800',
            1: 'bg-yellow-100 text-yellow-800',
            2: 'bg-green-100 text-green-800',
            3: 'bg-red-100 text-red-800',
        }
    
    return color_map.get(status, 'bg-gray-100 text-gray-800')
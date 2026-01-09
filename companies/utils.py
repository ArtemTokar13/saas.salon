import uuid
import random
import string
from django.utils.text import slugify


def company_img_upload(instance, filename):
    ext = filename.split('.')[-1].lower()

    company = getattr(instance, 'company', None)
    company_slug = slugify(company.name) if company else 'company'
    company_id = company.pk if company and company.pk else 'temp'

    unique_id = uuid.uuid4().hex[:8]

    # Різні папки для різних моделей (дуже корисно)
    model_name = instance.__class__.__name__.lower()

    return f"uploads/company/{company_id}/{model_name}/{company_slug}_{unique_id}.{ext}"



def make_random_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password
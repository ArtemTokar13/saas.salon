import uuid
import random
import string
from django.utils.text import slugify


def company_img_upload(instance, filename):
    ext = filename.split('.')[-1].lower()
    company_slug = slugify(instance.name)
    unique_id = uuid.uuid4().hex[:8]
    company_id = instance.pk or "temp"

    return f"uploads/company/{company_id}/{company_slug}_{unique_id}.{ext}"


def make_random_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password
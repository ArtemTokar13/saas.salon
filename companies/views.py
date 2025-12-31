from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import Company, Staff, Service, WorkingHours, CompanyImage
from .forms import CompanyRegistrationForm, CompanyProfileForm, CompanyStaffForm, ServiceForm
from billing.models import Subscription
from users.models import UserProfile
from companies.models import DAYS_OF_WEEK
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings


def register_company(request):
    """Company registration with user creation and subscription"""
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # create user as inactive until email confirmation
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1']
            )
            user.is_active = False
            user.save()

            company = Company.objects.create(
                administrator=user,
                name=form.cleaned_data['company_name'],
                description=form.cleaned_data.get('company_description', ''),
                address=form.cleaned_data['company_address'],
                city=form.cleaned_data['company_city'],
                phone=form.cleaned_data.get('company_phone', ''),
                email=form.cleaned_data.get('company_email', ''),
                logo=form.cleaned_data.get('company_logo')
            )

            UserProfile.objects.create(
                user=user,
                company=company,
                is_admin=True
            )

            # build activation link (uid + token)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activate_path = reverse('activate_company', args=[uid, token])
            activate_link = request.build_absolute_uri(activate_path)

            # send activation email
            subject = 'Activate your account'
            message = f"Please confirm your registration by clicking the following link:\n{activate_link}\n\nIf you didn't request this, ignore this email."
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            recipient_list = [user.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            except Exception:
                # If email sending fails, remove created objects to avoid orphaned entries
                user.delete()
                company.delete()
                messages.error(request, 'Failed to send activation email. Please try again later.')
                return redirect('register_company')

            messages.success(request, 'Registration successful. Check your email for the activation link.')
            return redirect('register_company')
    else:
        form = CompanyRegistrationForm()
    
    return render(request, 'companies/register.html', {'form': form})


def activate_company(request, uidb64, token):
    """Activate a company user after email confirmation"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        # login the user
        login(request, user)
        messages.success(request, 'Your account has been activated.')
        return redirect('company_dashboard')
    else:
        messages.error(request, 'Activation link is invalid or has expired.')
        return redirect('register_company')


@login_required
def company_dashboard(request):
    """Dashboard for company administrators"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            redirect('/')
        
        company = profile.company
        staff_count = Staff.objects.filter(company=company).count()
        service_count = Service.objects.filter(company=company).count()
        
        # Get active subscription
        subscription = Subscription.objects.filter(
            company=company, 
            is_active=True
        ).first()
        
        context = {
            'company': company,
            'staff_count': staff_count,
            'service_count': service_count,
            'subscription': subscription,
        }
        
        return render(request, 'companies/dashboard.html', context)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
def edit_company_profile(request):
    """Edit company profile"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        company = profile.company
        company_images = CompanyImage.objects.filter(company=company)
        
        if request.method == 'POST':
            form = CompanyProfileForm(request.POST, request.FILES, instance=company)
            if form.is_valid():
                # Process social media key-value pairs
                social_media_keys = request.POST.getlist('social_media_key[]')
                social_media_values = request.POST.getlist('social_media_value[]')
                
                social_media = {}
                for key, value in zip(social_media_keys, social_media_values):
                    if key.strip() and value.strip():  # Only add non-empty pairs
                        social_media[key.strip().lower()] = value.strip()
                
                company_instance = form.save(commit=False)
                company_instance.social_media = social_media
                company_instance.save()

                images = request.FILES.getlist('images')
                current_image_count = CompanyImage.objects.filter(company=company).count()
                max_images = 3
                
                if images:
                    remaining_slots = max_images - current_image_count
                    if remaining_slots <= 0:
                        messages.warning(request, f'Maximum {max_images} images allowed. Please delete existing images first.')
                    else:
                        images_to_add = images[:remaining_slots]
                        for img in images_to_add:
                            CompanyImage.objects.create(company=company, image=img)
                        if len(images) > remaining_slots:
                            messages.warning(request, f'Only {remaining_slots} image(s) added. Maximum {max_images} images allowed.')
                
                messages.success(request, 'Company profile updated successfully!')
                return redirect('company_dashboard')
        else:
            form = CompanyProfileForm(instance=company)
        
        return render(request, 'companies/edit_profile.html', {'form': form, 'company': company, 'company_images': company_images})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


def company_public_page(request, company_id):
    """Public-facing company page for customers"""
    company = get_object_or_404(Company, id=company_id)
    staff = Staff.objects.filter(company=company, is_active=True)
    services = Service.objects.filter(company=company, is_active=True)
    working_hours = WorkingHours.objects.filter(company=company).order_by('day_of_week')
    images = CompanyImage.objects.filter(company=company)
    
    context = {
        'company': company,
        'staff': staff,
        'services': services,
        'working_hours': working_hours,
        'images': images,
    }
    
    return render(request, 'companies/public_page.html', context)


@login_required
def delete_company_image(request, image_id):
    """Delete a company image via AJAX"""
    
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        image = get_object_or_404(CompanyImage, id=image_id)
        
        # Verify the image belongs to the user's company
        if image.company != profile.company:
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        image.delete()
        return JsonResponse({'success': True})
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found'}, status=403)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def staff_list(request):
    """List staff members for the company"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        company = profile.company
        staff_members = Staff.objects.filter(company=company)
        
        return render(request, 'companies/staff_list.html', {'staff_members': staff_members, 'company': company})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
def add_staff(request):
    """Add a new staff member"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        if request.method == 'POST':
            form = CompanyStaffForm(request.POST, company=profile.company)
            if form.is_valid():
                staff_member = Staff.objects.create(
                    company=profile.company,
                    name=form.cleaned_data['name'],
                    specialization=form.cleaned_data.get('specialization', ''),
                    avatar=form.cleaned_data.get('avatar')
                )
                staff_member.services.set(form.cleaned_data.get('services', []))

                user = User.objects.create_user(
                    username=form.cleaned_data['email'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password1']
                )

                UserProfile.objects.create(
                    user=user,
                    company=profile.company,
                    country_code=form.cleaned_data.get('country_code', ''),
                    phone_number=form.cleaned_data.get('phone', ''),
                    staff=staff_member
                )

                messages.success(request, 'Staff member added successfully!')
                return redirect('staff_list')
        else:
            form = CompanyStaffForm(company=profile.company)
        
        return render(request, 'companies/add_staff.html', {'form': form})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
def edit_staff(request, staff_id):
    """Edit an existing staff member"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        staff_member = get_object_or_404(Staff, id=staff_id, company=profile.company)
        if request.method == 'POST':
            form = CompanyStaffForm(request.POST, request.FILES, company=profile.company, require_password=False)
            if form.is_valid():
                staff_member.name = form.cleaned_data['name']
                staff_member.specialization = form.cleaned_data.get('specialization', '')
                # Staff model doesn't store phone/country; these are on UserProfile
                country_code_val = form.cleaned_data.get('country_code', '')
                phone_val = form.cleaned_data.get('phone', '')
                staff_member.is_active = form.cleaned_data.get('is_active', True)
                if form.cleaned_data.get('avatar'):
                    staff_member.avatar = form.cleaned_data.get('avatar')
                staff_member.save()
                
                # Update services relationship
                staff_member.services.set(form.cleaned_data.get('services', []))
                # Update associated UserProfile (phone_number, country_code)
                try:
                    user_profile = UserProfile.objects.filter(staff=staff_member).first()
                    if user_profile:
                        user_profile.country_code = country_code_val
                        user_profile.phone_number = phone_val
                        user_profile.save()
                except Exception:
                    # Don't block the update if profile update fails
                    pass

                messages.success(request, 'Staff member updated successfully!')
                return redirect('staff_list')
        else:
            initial_data = {
                'name': staff_member.name,
                'specialization': staff_member.specialization,
                'avatar': staff_member.avatar,
                'is_active': staff_member.is_active,
                'services': staff_member.services.all(),
            }
            # populate phone and country_code from related UserProfile if available
            user_profile = UserProfile.objects.filter(staff=staff_member).first()
            if user_profile:
                initial_data['country_code'] = user_profile.country_code
                initial_data['phone'] = user_profile.phone_number

            form = CompanyStaffForm(initial=initial_data, company=profile.company, require_password=False)
        return render(request, 'companies/edit_staff.html', {'form': form, 'staff_member': staff_member})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
def delete_staff(request, staff_id):
    """Delete a staff member"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        staff_member = get_object_or_404(Staff, id=staff_id, company=profile.company)
        staff_member.delete()
        messages.success(request, 'Staff member deleted successfully!')
        return redirect('staff_list')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')
    

@login_required
def service_list(request):
    """List services for the company"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        company = profile.company
        services = Service.objects.filter(company=company)
        
        return render(request, 'companies/services_list.html', {'services': services, 'company': company})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')
    

@login_required
def add_service(request):
    """Add a new service"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        if request.method == 'POST':
            form = ServiceForm(request.POST)
            if form.is_valid():
                Service.objects.create(
                    company=profile.company,
                    name=form.cleaned_data['name'],
                    duration=form.cleaned_data['duration'],
                    price=form.cleaned_data['price'],
                    is_active=form.cleaned_data['is_active']
                )
                messages.success(request, 'Service added successfully!')
                return redirect('service_list')
        else:
            form = ServiceForm()
        
        return render(request, 'companies/add_service.html', {'form': form})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
def edit_service(request, service_id):
    """Edit an existing service"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        service = get_object_or_404(Service, id=service_id, company=profile.company)
        if request.method == 'POST':
            form = ServiceForm(request.POST, company=profile.company)
            if form.is_valid():
                service.name = form.cleaned_data['name']
                service.duration = form.cleaned_data['duration']
                service.price = form.cleaned_data['price']
                service.is_active = form.cleaned_data['is_active']
                service.save()
                messages.success(request, 'Service updated successfully!')
                return redirect('service_list')
        else:
            initial_data = {
                'name': service.name,
                'duration': service.duration,
                'price': service.price,
                'is_active': service.is_active,
            }
            form = ServiceForm(initial=initial_data, company=profile.company)
        
        return render(request, 'companies/edit_service.html', {'form': form, 'service': service})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')
    

@login_required
def delete_service(request, service_id):
    """Delete a service"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        service = get_object_or_404(Service, id=service_id, company=profile.company)
        service.delete()
        messages.success(request, 'Service deleted successfully!')
        return redirect('service_list')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
def working_hours(request):
    """View and manage working hours for the company"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        company = profile.company
        
        if request.method == 'POST':
            for day_num, day_name in DAYS_OF_WEEK:
                is_working = request.POST.get(f'is_working_{day_num}') == 'on'
                start_time = request.POST.get(f'start_time_{day_num}', '').strip()
                end_time = request.POST.get(f'end_time_{day_num}', '').strip()
                
                working_hour, created = WorkingHours.objects.get_or_create(
                    company=company,
                    day_of_week=day_num,
                    defaults={
                        'start_time': start_time if start_time else '09:00',
                        'end_time': end_time if end_time else '17:00',
                        'is_day_off': not is_working
                    }
                )
                
                if not created:
                    working_hour.is_day_off = not is_working
                    # Only update times if working day and times are provided
                    if is_working:
                        if start_time:
                            working_hour.start_time = start_time
                        if end_time:
                            working_hour.end_time = end_time
                    working_hour.save()
            
            messages.success(request, 'Working hours updated successfully.')
            return redirect('working_hours')
        working_hours = WorkingHours.objects.filter(company=company).order_by('day_of_week')
        working_hours_dict = {wh.day_of_week: wh for wh in working_hours}
        
        days_data = []
        for day_num, day_name in DAYS_OF_WEEK:
            if day_num in working_hours_dict:
                wh = working_hours_dict[day_num]
                days_data.append({
                    'number': day_num,
                    'name': day_name,
                    'is_working': not wh.is_day_off,
                    'start_time': wh.start_time.strftime('%H:%M'),
                    'end_time': wh.end_time.strftime('%H:%M'),
                })
            else:
                days_data.append({
                    'number': day_num,
                    'name': day_name,
                    'is_working': True,
                    'start_time': '09:00',
                    'end_time': '17:00',
                })
        
        return render(request, 'companies/working_hours.html', {
            'days_data': days_data,
            'company': company
        })
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')
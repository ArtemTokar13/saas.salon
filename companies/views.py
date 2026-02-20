from datetime import timedelta
import logging
import traceback
import json
import qrcode
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.db import models
from .models import Company, Staff, Service, WorkingHours, CompanyImage, EmailLog
from .forms import CompanyRegistrationForm, CompanyProfileForm, CompanyStaffForm, CompanyStaffActivateForm, ServiceForm
from .utils import make_random_password
from billing.models import Subscription
from users.models import UserProfile
from companies.models import DAYS_OF_WEEK
from bookings.models import Customer, Booking
from app.decorators import subscription_required


logger = logging.getLogger(__name__)


def register_company(request):
    """Company registration with user creation and subscription"""
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # create user as inactive until email confirmation
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
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
            html_message = render_to_string('email/account_activation.html', {
                'activate_link': activate_link,
                'current_year': timezone.now().year,
                'site_name': 'Salon Booking System',
            })
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            recipient_list = [user.email]
            
            # Create email log entry
            email_log = EmailLog.objects.create(
                recipient_email=user.email,
                subject=subject,
                email_type='registration',
                status='pending'
            )
            
            try:
                msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send()
                # Mark as successful
                email_log.status = 'success'
                email_log.sent_at = timezone.now()
                email_log.save()
            except Exception as e:
                # Log the error details
                error_msg = str(e)
                error_trace = traceback.format_exc()
                
                email_log.status = 'failed'
                email_log.error_message = error_msg
                email_log.error_traceback = error_trace
                email_log.save()
                
                # Also log to Django's logger for production monitoring
                logger.error(
                    f"Email sending failed for registration. User: {user.email}, Error: {error_msg}",
                    exc_info=True
                )
                
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
@subscription_required
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
@subscription_required
def edit_company_profile(request):
    """Edit company profile"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        company = profile.company
        company_images = CompanyImage.objects.filter(company=company).order_by('order')
        
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
                max_images = 15
                
                if images:
                    remaining_slots = max_images - current_image_count
                    if remaining_slots <= 0:
                        messages.warning(request, f'Maximum {max_images} images allowed. Please delete existing images first.')
                    else:
                        images_to_add = images[:remaining_slots]
                        # Get the highest order value
                        max_order = CompanyImage.objects.filter(company=company).aggregate(models.Max('order'))['order__max'] or 0
                        for idx, img in enumerate(images_to_add, start=1):
                            CompanyImage.objects.create(company=company, image=img, order=max_order + idx)
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
    images = CompanyImage.objects.filter(company=company).order_by('order')
    
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
def delete_company_logo(request):
    """Delete company logo via AJAX"""
    
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        company = profile.company
        
        if company.logo:
            company.logo.delete(save=True)
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'No logo to delete'}, status=404)
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found'}, status=403)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@subscription_required
@csrf_exempt
def delete_staff_avatar(request, staff_id):
    """Delete staff avatar via AJAX"""
    
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        staff_member = get_object_or_404(Staff, id=staff_id, company=profile.company)
        
        if staff_member.avatar:
            staff_member.avatar.delete(save=True)
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'No avatar to delete'}, status=404)
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found'}, status=403)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def reorder_company_images(request):
    """Reorder company images via AJAX"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST requests are allowed'}, status=405)
    
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        company = profile.company
        data = json.loads(request.body)
        image_order = data.get('imageOrder', [])
        
        # Update the order for each image
        for idx, image_id in enumerate(image_order):
            CompanyImage.objects.filter(
                id=image_id,
                company=company
            ).update(order=idx)
        
        return JsonResponse({'success': True})
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found'}, status=403)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
@subscription_required
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
@subscription_required
def add_staff(request):
    """Add a new staff member"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        if request.method == 'POST':
            form = CompanyStaffForm(request.POST, request.FILES, company=profile.company)
            if form.is_valid():
                # Convert working_days from strings to integers
                working_days = [int(day) for day in form.cleaned_data.get('working_days', [])]
                
                staff_member = Staff.objects.create(
                    company=profile.company,
                    name=form.cleaned_data['name'],
                    specialization=form.cleaned_data.get('specialization', ''),
                    avatar=form.cleaned_data.get('avatar'),
                    working_days=working_days,
                    break_start=form.cleaned_data.get('break_start'),
                    break_end=form.cleaned_data.get('break_end'),
                    out_of_office_start=form.cleaned_data.get('out_of_office_start'),
                    out_of_office_end=form.cleaned_data.get('out_of_office_end'),
                    is_active=False
                )
                staff_member.services.set(form.cleaned_data.get('services', []))

                simple_password = make_random_password()
                user = User.objects.create_user(
                    username=form.cleaned_data['email'],
                    email=form.cleaned_data['email'],
                    password=simple_password
                )

                UserProfile.objects.create(
                    user=user,
                    company=profile.company,
                    country_code=form.cleaned_data.get('country_code', ''),
                    phone_number=form.cleaned_data.get('phone', ''),
                    staff=staff_member
                )

                # build activation link (uid + token)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                activate_path = reverse('activate_staff_account', args=[uid, token])
                activate_link = request.build_absolute_uri(activate_path)

                # send activation email
                subject = 'Activate your staff account'
                html_message = render_to_string('email/staff_activation.html', {
                    'activate_link': activate_link,
                    'company_name': profile.company.name,
                    'current_year': timezone.now().year,
                    'site_name': 'Salon Booking System',
                })
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                recipient_list = [user.email]

                # Create email log entry
                email_log = EmailLog.objects.create(
                    recipient_email=user.email,
                    subject=subject,
                    email_type='staff_registration',
                    status='pending'
                )

                try:
                    msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                    msg.attach_alternative(html_message, "text/html")
                    # Send copy to company admin
                    if profile.company.administrator.email:
                        msg.bcc = [profile.company.administrator.email]
                    msg.send()
                    email_log.status = 'success'
                    email_log.sent_at = timezone.now()
                    email_log.save()
                except Exception as e:
                    error_msg = str(e)
                    error_trace = traceback.format_exc()

                    email_log.status = 'failed'
                    email_log.error_message = error_msg
                    email_log.error_traceback = error_trace
                    email_log.save()

                    logger.error(
                        f"Email sending failed for staff registration. User: {user.email}, Error: {error_msg}",
                        exc_info=True
                    )

                messages.success(request, 'Staff member added successfully!')
                return redirect('staff_list')
        else:
            form = CompanyStaffForm(company=profile.company)
        
        return render(request, 'companies/add_staff.html', {'form': form})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')
    
def activate_staff_account(request, uidb64, token):
    """Activate staff account via email link"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        staff = Staff.objects.filter(userprofile__user=user).first()
    except Exception:
        user = None

    if request.method == 'POST':
        form = CompanyStaffActivateForm(request.POST)
        if form.is_valid():
            password1 = form.cleaned_data.get('password1')
            password2 = form.cleaned_data.get('password2')
            if user is not None and default_token_generator.check_token(user, token):
                if password1 == password2:
                    user.set_password(password1)
                    user.is_active = True
                    user.save()

                    staff.is_active = True
                    staff.save()

                    # send confirmation email
                    subject = 'Your staff account has been activated'
                    html_message = render_to_string('email/account_activated.html', {
                        'user_name': user.first_name or user.username,
                        'current_year': timezone.now().year,
                        'site_name': 'Salon Booking System',
                    })
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                    recipient_list = [user.email]

                    try:
                        msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                        msg.attach_alternative(html_message, "text/html")
                        # Send copy to company admin
                        try:
                            company = staff.company
                            if company and company.administrator.email:
                                msg.bcc = [company.administrator.email]
                        except Exception:
                            pass
                        msg.send()
                    except Exception as e:
                        logger.error(f"Failed to send confirmation email: {e}")

                    login(request, user)
                    messages.success(request, 'Account activated successfully!')
                    return redirect('login')  # Redirect to staff calendar or login
                else:
                    messages.error(request, 'Passwords do not match.')
            else:
                messages.error(request, 'Activation link is invalid or has expired. Please contact your administrator.')
    else:
        form = CompanyStaffActivateForm()
    return render(request, 'companies/activate_staff_account.html', {'form': form})


def forgot_password(request):
    """Handle forgot password requests for staff"""
    email = request.GET.get('email')
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # build reset link (uid + token)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_path = reverse('reset_password', args=[uid, token])
            reset_link = request.build_absolute_uri(reset_path)

            # send reset email
            subject = 'Reset your password'
            html_message = render_to_string('email/password_reset.html', {
                'reset_link': reset_link,
                'current_year': timezone.now().year,
                'site_name': 'Salon Booking System',
            })
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            recipient_list = [user.email]

            try:
                msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send()
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e}")

            messages.success(request, 'Password reset link sent to your email.')
        except User.DoesNotExist:
            messages.error(request, 'No user found with that email address.')
        return redirect('login')

    return render(request, 'companies/forgot_password.html', {"email": email})


def reset_password(request, uidb64, token):
    """Reset password for staff account via email link (not implemented)"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if request.method == 'POST':
        form = CompanyStaffActivateForm(request.POST)
        if form.is_valid():
            password1 = form.cleaned_data.get('password1')
            password2 = form.cleaned_data.get('password2')
            if user is not None and default_token_generator.check_token(user, token):
                if password1 == password2:
                    user.set_password(password1)
                    user.save()

                    # send confirmation email
                    subject = 'Your password has been reset'
                    html_message = render_to_string('email/password_reset_success.html', {
                        'user_name': user.first_name or user.username,
                        'current_year': timezone.now().year,
                        'site_name': 'Salon Booking System',
                    })
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                    recipient_list = [user.email]

                    try:
                        msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                        msg.attach_alternative(html_message, "text/html")
                        # Send copy to company admin for security purposes
                        try:
                            user_profile = UserProfile.objects.filter(user=user).first()
                            if user_profile and user_profile.company and user_profile.company.administrator.email:
                                msg.bcc = [user_profile.company.administrator.email]
                        except Exception:
                            pass
                        msg.send()
                    except Exception as e:
                        logger.error(f"Failed to send confirmation email: {e}")

                    messages.success(request, 'Password reset successfully!')
                    return redirect('login')  # Redirect to login
                else:
                    messages.error(request, 'Passwords do not match.')
            else:
                messages.error(request, 'Reset link is invalid or has expired. Please contact your administrator.')
    else:
        form = CompanyStaffActivateForm()
    return render(request, 'companies/reset_password.html', {'form': form})


@login_required
@subscription_required
def edit_staff(request, staff_id):
    """Edit an existing staff member"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        staff_member = get_object_or_404(Staff, id=staff_id, company=profile.company)
        user_profile = UserProfile.objects.filter(staff=staff_member).first()
        staff_email = user_profile.user.email if user_profile else None
        if request.method == 'POST':
            form = CompanyStaffForm(request.POST, request.FILES, company=profile.company)
            if form.is_valid():
                staff_member.name = form.cleaned_data['name']
                staff_member.specialization = form.cleaned_data.get('specialization', '')
                # Convert working_days from strings to integers
                working_days = [int(day) for day in form.cleaned_data.get('working_days', [])]
                staff_member.working_days = working_days
                staff_member.break_start = form.cleaned_data.get('break_start')
                staff_member.break_end = form.cleaned_data.get('break_end')
                staff_member.out_of_office_start = form.cleaned_data.get('out_of_office_start')
                staff_member.out_of_office_end = form.cleaned_data.get('out_of_office_end')
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
                'working_days': [str(day) for day in staff_member.working_days],
                'break_start': staff_member.break_start,
                'break_end': staff_member.break_end,
                'out_of_office_start': staff_member.out_of_office_start,
                'out_of_office_end': staff_member.out_of_office_end,
                'is_active': staff_member.is_active,
                'services': staff_member.services.all(),
            }
            # populate phone and country_code from related UserProfile if available
            user_profile = UserProfile.objects.filter(staff=staff_member).first()
            if user_profile:
                initial_data['country_code'] = user_profile.country_code
                initial_data['phone'] = user_profile.phone_number

            form = CompanyStaffForm(initial=initial_data, company=profile.company)
        return render(request, 'companies/edit_staff.html', {'form': form, 'staff_member': staff_member, 'staff_email': staff_email})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
@subscription_required
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
@subscription_required
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
@subscription_required
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
                # Get available dates from POST
                available_dates = []
                date_values = request.POST.getlist('available_date[]')
                for date_str in date_values:
                    if date_str.strip():  # Only add non-empty dates
                        available_dates.append(date_str.strip())
                
                # Limit to 10 dates
                available_dates = available_dates[:10]
                
                Service.objects.create(
                    company=profile.company,
                    name=form.cleaned_data['name'],
                    duration=form.cleaned_data['duration'],
                    time_for_servicing=form.cleaned_data['time_for_servicing'],
                    price=form.cleaned_data['price'],
                    need_staff_confirmation=form.cleaned_data['need_staff_confirmation'],
                    is_active=form.cleaned_data['is_active'],
                    restrict_to_available_dates=form.cleaned_data['restrict_to_available_dates'],
                    available_dates=available_dates
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
@subscription_required
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
                # Get available dates from POST
                available_dates = []
                date_values = request.POST.getlist('available_date[]')
                for date_str in date_values:
                    if date_str.strip():  # Only add non-empty dates
                        available_dates.append(date_str.strip())
                
                # Limit to 10 dates
                available_dates = available_dates[:10]
                
                service.name = form.cleaned_data['name']
                service.duration = form.cleaned_data['duration']
                service.time_for_servicing = form.cleaned_data['time_for_servicing']
                service.price = form.cleaned_data['price']
                service.need_staff_confirmation = form.cleaned_data['need_staff_confirmation']
                service.is_active = form.cleaned_data['is_active']
                service.restrict_to_available_dates = form.cleaned_data['restrict_to_available_dates']
                service.available_dates = available_dates
                service.save()
                messages.success(request, 'Service updated successfully!')
                return redirect('service_list')
        else:
            initial_data = {
                'name': service.name,
                'duration': service.duration,
                'time_for_servicing': service.time_for_servicing,
                'price': service.price,
                'need_staff_confirmation': service.need_staff_confirmation,
                'is_active': service.is_active,
                'restrict_to_available_dates': service.restrict_to_available_dates,
            }
            form = ServiceForm(initial=initial_data, company=profile.company)
        
        return render(request, 'companies/edit_service.html', {'form': form, 'service': service})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')
    

@login_required
@subscription_required
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
@subscription_required
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
            return redirect('company_dashboard')
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
    

@login_required
@subscription_required
def customers_list(request):
    """List of customers for staff/admin"""
    try:
        profile = request.user.userprofile
        customers = Customer.objects.filter(booking__company=profile.company).distinct()
        
        # Search functionality
        search_query = request.GET.get('search', '').strip()
        if search_query:
            customers = customers.filter(
                Q(name__icontains=search_query) | 
                Q(phone__icontains=search_query)
            )
        
        customers = customers.order_by('name')
        
        # Pagination
        paginator = Paginator(customers, 25)  # Show 25 customers per page
        page = request.GET.get('page')
        try:
            customers_page = paginator.page(page)
        except PageNotAnInteger:
            customers_page = paginator.page(1)
        except EmptyPage:
            customers_page = paginator.page(paginator.num_pages)
        
        context = {
            'customers': customers_page,
            'company': profile.company,
            'search_query': search_query,
        }
        return render(request, 'companies/customers_list.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
@subscription_required
def search_customers_ajax(request):
    """AJAX endpoint for searching customers"""
    try:
        profile = request.user.userprofile
        search_query = request.GET.get('search', '').strip()
        page = request.GET.get('page', 1)
        
        customers = Customer.objects.filter(booking__company=profile.company).distinct()
        
        if search_query:
            customers = customers.filter(
                Q(name__icontains=search_query) | 
                Q(phone__icontains=search_query)
            )
        
        customers = customers.order_by('name')
        
        # Pagination
        paginator = Paginator(customers, 25)
        try:
            customers_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            customers_page = paginator.page(1)
        
        # Build customer data
        customers_data = []
        for customer in customers_page:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
            })
        
        return JsonResponse({
            'success': True,
            'customers': customers_data,
            'has_previous': customers_page.has_previous(),
            'has_next': customers_page.has_next(),
            'current_page': customers_page.number,
            'total_pages': customers_page.paginator.num_pages,
            'total_count': customers_page.paginator.count,
            'previous_page': customers_page.previous_page_number() if customers_page.has_previous() else None,
            'next_page': customers_page.next_page_number() if customers_page.has_next() else None,
        })
    
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)


@login_required
@subscription_required
def customer_detail(request, customer_id):
    """View details of a specific customer"""
    try:
        profile = request.user.userprofile
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Ensure the customer is associated with the company/staff
        if not customer.booking_set.filter(company=profile.company).exists():
            messages.error(request, 'Access denied.')
            return redirect('customers_list')
        
        # Get bookings with pagination
        customer_bookings_list = customer.booking_set.filter(company=profile.company).order_by('-date', '-start_time')
        paginator = Paginator(customer_bookings_list, 25)  # Show 25 bookings per page
        page = request.GET.get('page')
        try:
            customer_bookings = paginator.page(page)
        except PageNotAnInteger:
            customer_bookings = paginator.page(1)
        except EmptyPage:
            customer_bookings = paginator.page(paginator.num_pages)
        
        # Get services and their counts (only confirmed bookings)
        customer_services = Service.objects.filter(booking__customer=customer, booking__company=profile.company, booking__status=1).distinct()
        service_counter_dict = {}
        for service in customer_services:
            count = customer.booking_set.filter(service=service, company=profile.company, status=1).count()
            service_counter_dict[service.id] = count
        
        context = {
            'customer': customer,
            'company': profile.company,
            'customer_bookings': customer_bookings,
            'customer_services': customer_services,
            'service_counter_dict': service_counter_dict,
        }
        return render(request, 'companies/customer_detail.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
def generate_qr_code(request):
    """Generate and return QR code image for company public page"""
    url = request.GET.get('url')
    company_id = request.GET.get('company_id')
    
    if not url or not company_id:
        return HttpResponse('Missing parameters', status=400)
    
    # Verify the user owns this company
    try:
        company = Company.objects.get(id=company_id, administrator=request.user)
    except Company.DoesNotExist:
        return HttpResponse('Unauthorized', status=403)
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Return as HTTP response
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    # Create a safe filename from company name
    safe_name = "".join(c for c in company.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_name = safe_name.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{safe_name}_qr_code.png"'
    return response


@login_required
@subscription_required
def service_analytics(request):
    """Analytics page showing service usage and booking statistics"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('/')
        
        company = profile.company
        
        # Get date range filters (default to last 30 days)
        from datetime import datetime, date
        from django.db.models import Count, Sum, Avg, F, ExpressionWrapper, DurationField
        
        # Get filter parameters
        date_range = request.GET.get('range', '30')  # 7, 30, 90, 365, or 'all'
        
        # Calculate date filter
        end_date = date.today()
        if date_range == 'all':
            start_date = None
        else:
            try:
                days = int(date_range)
                start_date = end_date - timedelta(days=days)
            except (ValueError, TypeError):
                days = 30
                start_date = end_date - timedelta(days=30)
        
        # Get all services for this company
        services = Service.objects.filter(company=company)
        
        # Filter bookings by date if applicable
        bookings = Booking.objects.filter(company=company)
        if start_date:
            bookings = bookings.filter(date__gte=start_date)
        
        # Get confirmed bookings only (status=1)
        confirmed_bookings = bookings.filter(status=1)
        
        # Service analytics
        service_stats = []
        total_bookings = confirmed_bookings.count()
        total_revenue = confirmed_bookings.aggregate(
            total=Sum('price')
        )['total'] or 0
        
        for service in services:
            service_bookings = confirmed_bookings.filter(service=service)
            booking_count = service_bookings.count()
            revenue = service_bookings.aggregate(total=Sum('price'))['total'] or 0
            
            # Calculate percentage
            percentage = (booking_count / total_bookings * 100) if total_bookings > 0 else 0
            revenue_percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            
            # Get unique customers for this service
            unique_customers = service_bookings.values('customer').distinct().count()
            
            service_stats.append({
                'service': service,
                'booking_count': booking_count,
                'revenue': revenue,
                'percentage': round(percentage, 1),
                'revenue_percentage': round(revenue_percentage, 1),
                'unique_customers': unique_customers,
                'avg_price': round(revenue / booking_count, 2) if booking_count > 0 else 0,
            })
        
        # Sort by booking count (most popular first)
        service_stats.sort(key=lambda x: x['booking_count'], reverse=True)
        
        # Identify services with no bookings
        services_no_bookings = [s for s in service_stats if s['booking_count'] == 0]
        
        # Status breakdown
        status_breakdown = bookings.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        status_dict = {
            0: 'Pending',
            1: 'Confirmed',
            2: 'Cancelled',
            3: 'PreBooked'
        }
        
        status_stats = [
            {
                'status': status_dict.get(int(item['status']), 'Unknown'),
                'count': item['count']
            }
            for item in status_breakdown
        ]
        
        # Monthly trends (last 12 months or within date range)
        if date_range == 'all' or int(date_range) >= 90:
            from django.db.models.functions import TruncMonth
            monthly_data = confirmed_bookings.annotate(
                month=TruncMonth('date')
            ).values('month').annotate(
                count=Count('id'),
                revenue=Sum('price')
            ).order_by('month')
        else:
            monthly_data = []
        
        # Top customers
        top_customers = confirmed_bookings.values(
            'customer__name', 'customer__id'
        ).annotate(
            total_bookings=Count('id'),
            total_spent=Sum('price')
        ).order_by('-total_bookings')[:10]
        
        # Calculate average booking value
        avg_booking_value = round(total_revenue / total_bookings, 2) if total_bookings > 0 else 0
        
        context = {
            'company': company,
            'service_stats': service_stats,
            'services_no_bookings': services_no_bookings,
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
            'avg_booking_value': avg_booking_value,
            'status_stats': status_stats,
            'monthly_data': monthly_data,
            'top_customers': top_customers,
            'date_range': date_range,
            'start_date': start_date,
            'end_date': end_date,
        }
        
        return render(request, 'companies/analytics.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')
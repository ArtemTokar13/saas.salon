from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from billing.models import Plan
from bookings.models import Booking, Customer
from companies.models import Company, Service, Staff
from decimal import Decimal
import json
from datetime import datetime


def get_plan_price(request):
    """API endpoint to get plan price based on selected period"""
    plan_id = request.GET.get('plan_id')
    period = request.GET.get('period')

    try:
        plan = Plan.objects.get(id=plan_id)
        price = plan.get_price_for_period(period)
        price_formatted = f"${price:.2f}"
        return JsonResponse({'price': str(price), 'price_formatted': price_formatted})
    except Plan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)


# ============ AUTH ENDPOINTS ============

@csrf_exempt
@require_http_methods(["POST"])
def auth_login(request):
    """API endpoint for user login"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return JsonResponse({'error': 'Email and password required'}, status=400)

        # Authenticate user by email (assuming username is email)
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            return JsonResponse({
                'token': request.session.session_key or 'session_token',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.get_full_name() or user.username,
                    'phone': getattr(user.userprofile, 'phone_number', None) if hasattr(user, 'userprofile') else None,
                    'is_admin': getattr(user.userprofile, 'is_admin', False) if hasattr(user, 'userprofile') else False,
                    'company_id': user.userprofile.company.id if hasattr(user, 'userprofile') and user.userprofile.company else None,
                    'company_name': user.userprofile.company.name if hasattr(user, 'userprofile') and user.userprofile.company else None,
                    'staff_id': user.userprofile.staff.id if hasattr(user, 'userprofile') and user.userprofile.staff else None,
                    'staff_name': user.userprofile.staff.get_full_name() if hasattr(user, 'userprofile') and user.userprofile.staff else None,
                }
            })
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def auth_register(request):
    """API endpoint for user registration"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        phone = data.get('phone', '')

        if not email or not password:
            return JsonResponse({'error': 'Email and password required'}, status=400)

        # Check if user exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'User with this email already exists'}, status=400)

        # Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Auto login after registration
        login(request, user)
        
        return JsonResponse({
            'token': request.session.session_key or 'session_token',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name() or user.username,
                'phone': phone,
            }
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def auth_logout(request):
    """API endpoint for user logout"""
    logout(request)
    return JsonResponse({'message': 'Logged out successfully'}, status=200)


@require_http_methods(["GET"])
def get_user(request):
    """API endpoint to get current user info"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    return JsonResponse({
        'id': request.user.id,
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'full_name': request.user.get_full_name() or request.user.username,
        'phone': request.user.profile.phone if hasattr(request.user, 'profile') else None,
    })


# ============ BOOKING ENDPOINTS ============

@csrf_exempt
def bookings_list(request):
    """API endpoint to list or create bookings"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method == 'GET':
        # Get user's bookings
        bookings = Booking.objects.filter(customer__email=request.user.email).select_related(
            'company', 'service', 'staff', 'customer'
        ).order_by('-created_at')
        
        bookings_data = [{
            'id': booking.id,
            'customer_id': booking.customer.id,
            'customer_name': booking.customer.name,
            'customer_phone': booking.customer.phone,
            'company_id': booking.company.id,
            'company_name': booking.company.name,
            'service_id': booking.service.id,
            'service_name': booking.service.name,
            'staff_id': booking.staff.id if booking.staff else None,
            'staff_name': booking.staff.name if booking.staff else None,
            'booking_date': booking.date.isoformat(),
            'start_time': booking.start_time.strftime('%H:%M'),
            'end_time': booking.end_time.strftime('%H:%M') if booking.end_time else None,
            'status': ['pending', 'confirmed', 'cancelled', 'prebooked'][booking.status],
            'price': str(booking.price) if booking.price else '0.00',
            'notes': '',
            'created_at': booking.created_at.isoformat(),
        } for booking in bookings]
        
        return JsonResponse(bookings_data, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get or create customer
            customer, _ = Customer.objects.get_or_create(
                email=request.user.email,
                defaults={
                    'name': request.user.get_full_name() or request.user.username,
                    'phone': data.get('customer_phone', ''),
                }
            )
            
            # Create booking
            booking = Booking.objects.create(
                customer=customer,
                company_id=data['company_id'],
                service_id=data['service_id'],
                staff_id=data.get('staff_id'),
                date=datetime.fromisoformat(data['booking_date']).date(),
                start_time=data['start_time'],
                end_time=data.get('end_time'),
                price=data.get('price', 0),
                status=0,  # Pending
            )
            
            return JsonResponse({
                'id': booking.id,
                'customer_id': booking.customer.id,
                'customer_name': booking.customer.name,
                'customer_phone': booking.customer.phone,
                'company_id': booking.company.id,
                'company_name': booking.company.name,
                'service_id': booking.service.id,
                'service_name': booking.service.name,
                'staff_id': booking.staff.id if booking.staff else None,
                'staff_name': booking.staff.name if booking.staff else None,
                'booking_date': booking.date.isoformat(),
                'start_time': booking.start_time.strftime('%H:%M'),
                'end_time': booking.end_time.strftime('%H:%M') if booking.end_time else None,
                'status': 'pending',
                'price': str(booking.price),
                'notes': '',
                'created_at': booking.created_at.isoformat(),
            }, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
def booking_detail(request, id):
    """API endpoint for booking detail"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        booking = Booking.objects.select_related('company', 'service', 'staff', 'customer').get(
            id=id,
            customer__email=request.user.email
        )
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse({
            'id': booking.id,
            'customer_id': booking.customer.id,
            'customer_name': booking.customer.name,
            'customer_phone': booking.customer.phone,
            'company_id': booking.company.id,
            'company_name': booking.company.name,
            'service_id': booking.service.id,
            'service_name': booking.service.name,
            'staff_id': booking.staff.id if booking.staff else None,
            'staff_name': booking.staff.name if booking.staff else None,
            'booking_date': booking.date.isoformat(),
            'start_time': booking.start_time.strftime('%H:%M'),
            'end_time': booking.end_time.strftime('%H:%M') if booking.end_time else None,
            'status': ['pending', 'confirmed', 'cancelled', 'prebooked'][booking.status],
            'price': str(booking.price) if booking.price else '0.00',
            'notes': '',
            'created_at': booking.created_at.isoformat(),
        })
    
    elif request.method == 'DELETE':
        booking.status = 2  # Cancelled
        booking.save()
        return JsonResponse({'message': 'Booking cancelled'}, status=200)


# ============ COMPANY ENDPOINTS ============

@require_http_methods(["GET"])
def companies_list(request):
    """API endpoint to list all companies"""
    companies = Company.objects.all()
    
    companies_data = [{
        'id': company.id,
        'name': company.name,
        'description': company.description or '',
        'address': company.address or '',
        'phone': company.phone or '',
        'email': company.email or '',
        'logo': company.logo.url if company.logo else None,
    } for company in companies]
    
    return JsonResponse(companies_data, safe=False)


@require_http_methods(["GET"])
def company_detail(request, id):
    """API endpoint for company detail"""
    try:
        company = Company.objects.get(id=id)
        return JsonResponse({
            'id': company.id,
            'name': company.name,
            'description': company.description or '',
            'address': company.address or '',
            'phone': company.phone or '',
            'email': company.email or '',
            'logo': company.logo.url if company.logo else None,
        })
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)


@require_http_methods(["GET"])
def company_services(request, id):
    """API endpoint to list company services"""
    try:
        company = Company.objects.get(id=id)
        services = Service.objects.filter(company=company)
        
        services_data = [{
            'id': service.id,
            'name': service.name,
            'description': service.description or '',
            'duration': service.duration,
            'price': str(service.price),
            'company_id': service.company.id,
        } for service in services]
        
        return JsonResponse(services_data, safe=False)
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)


@csrf_exempt
@require_http_methods(["GET"])
def company_staff(request, id):
    """API endpoint to list company staff"""
    try:
        company = Company.objects.get(id=id)
        staff_members = Staff.objects.filter(company=company, is_active=True)
        
        staff_data = [{
            'id': staff.id,
            'name': staff.name,
            'first_name': staff.name.split()[0] if staff.name else '',
            'last_name': ' '.join(staff.name.split()[1:]) if len(staff.name.split()) > 1 else '',
            'email': '',  # Staff model doesn't have email field
            'phone': '',  # Staff model doesn't have phone field
            'avatar': staff.avatar.url if staff.avatar else None,
            'specialization': staff.specialization or None,
            'is_active': staff.is_active,
            'company_id': staff.company.id,
        } for staff in staff_members]
        
        return JsonResponse(staff_data, safe=False)
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)


@csrf_exempt
@require_http_methods(["GET"])
def company_bookings(request, id):
    """API endpoint to list all bookings for a company (for salon owners/staff)"""
    # TODO: Fix authentication - currently disabled for testing
    # if not request.user.is_authenticated:
    #     return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        company = Company.objects.get(id=id)
        
        # TODO: Re-enable permission check after fixing authentication
        # Check permissions: user must be admin or staff of this company
        # user_profile = getattr(request.user, 'userprofile', None)
        # if not user_profile or user_profile.company != company:
        #     return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get all bookings for this company
        bookings = Booking.objects.filter(company=company).select_related(
            'company', 'service', 'staff', 'customer'
        ).order_by('-date', '-start_time')
        
        bookings_data = [{
            'id': booking.id,
            'customer_id': booking.customer.id,
            'customer_name': booking.customer.name,
            'customer_phone': booking.customer.phone,
            'company_id': booking.company.id,
            'company_name': booking.company.name,
            'service_id': booking.service.id,
            'service_name': booking.service.name,
            'staff_id': booking.staff.id if booking.staff else None,
            'staff_name': booking.staff.name if booking.staff else None,
            'booking_date': booking.date.isoformat(),
            'start_time': booking.start_time.strftime('%H:%M'),
            'end_time': booking.end_time.strftime('%H:%M') if booking.end_time else None,
            'status': ['pending', 'confirmed', 'cancelled', 'prebooked'][int(booking.status)],
            'price': str(booking.price) if booking.price else '0.00',
            'notes': '',
            'created_at': booking.created_at.isoformat(),
        } for booking in bookings]
        
        return JsonResponse(bookings_data, safe=False)
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============ SERVICE ENDPOINTS ============

@require_http_methods(["GET"])
def services_list(request):
    """API endpoint to list all services"""
    services = Service.objects.all().select_related('company')
    
    services_data = [{
        'id': service.id,
        'name': service.name,
        'description': service.description or '',
        'duration': service.duration,
        'price': str(service.price),
        'company_id': service.company.id,
        'company_name': service.company.name,
    } for service in services]
    
    return JsonResponse(services_data, safe=False)
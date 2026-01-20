from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import timedelta
import uuid
import stripe
import json
from .models import Plan, Subscription, Transaction
from .forms import ChangePlanForm
from .stripe_utils import (
    create_stripe_checkout_session, 
    cancel_stripe_subscription,
    reactivate_stripe_subscription,
    create_customer_portal_session,
    sync_subscription_from_stripe
)
from users.models import UserProfile, Company

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def subscription_details(request):
    """View current subscription and billing history"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')

        company = profile.company
        current_subscription = Subscription.objects.filter(company=company, is_active=True).first()
        subscription_history = Subscription.objects.filter(company=company).order_by('-start_date')
        transactions = Transaction.objects.filter(subscription__company=company).order_by('-transaction_date')
        total_spent = sum(t.amount for t in transactions)

        context = {
            'company': company,
            'current_subscription': current_subscription,
            'subscription_history': subscription_history,
            'transactions': transactions,
            'total_spent': total_spent,
        }
        return render(request, 'billing/subscription_details.html', context)

    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def view_plans(request):
    """View all available plans"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')

        company = profile.company
        current_subscription = Subscription.objects.filter(company=company, end_date__gte=timezone.now(), is_active=True).first()
        plans = Plan.objects.all()

        context = {
            'company': company,
            'current_subscription': current_subscription,
            'plans': plans,
        }
        return render(request, 'billing/view_plans.html', context)

    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def change_plan(request, plan_id):
    """Change subscription plan with worker selection and Stripe payment"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, "Access denied.")
            return redirect("home")

        company = profile.company
        new_plan = get_object_or_404(Plan, id=plan_id)

        if request.method == "POST":
            billing_period = request.POST.get("billing_period", "monthly")
            num_workers = int(request.POST.get("num_workers", new_plan.base_workers))

            if num_workers < 1:
                messages.error(request, "Number of workers must be at least 1.")
                return redirect("change_plan", plan_id=plan_id)

            # Створюємо Stripe Checkout сесію
            success_url = request.build_absolute_uri("/billing/payment-success/")
            cancel_url = request.build_absolute_uri(f"/billing/change-plan/{plan_id}/")
            
            try:
                checkout_session = create_stripe_checkout_session(
                    company=company,
                    plan=new_plan,
                    billing_period=billing_period,
                    success_url=success_url,
                    cancel_url=cancel_url,
                    num_workers=num_workers
                )
                # Перенаправляємо на Stripe для введення картки
                return redirect(checkout_session.url)
            except Exception as e:
                messages.error(request, f"Stripe error: {str(e)}")
                return redirect("change_plan", plan_id=plan_id)

        context = {
            "plan": new_plan,
            "company": company,
            "billing_periods": Subscription.BILLING_PERIOD_CHOICES,
        }
        return render(request, "billing/change_plan.html", context)

    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect("home")


@login_required
def cancel_subscription(request):
    """Cancel active subscription"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, "Access denied.")
            return redirect("home")

        company = profile.company

        if request.method == "POST":
            subscription = Subscription.objects.filter(company=company, is_active=True).first()
            if subscription:
                subscription.is_active = False
                subscription.status = Subscription.STATUS_CANCELLED
                subscription.cancelled_at = timezone.now()
                subscription.save()
                messages.success(request, "Subscription cancelled successfully.")
            else:
                messages.warning(request, "No active subscription found.")

            return redirect("subscription_details")

        return render(request, "billing/cancel_subscription.html", {"company": company})

    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect("home")


@login_required
def payment_success(request):
    messages.success(request, "Payment successful! Your subscription has been activated.")
    return redirect("subscription_details")


@login_required
def payment_cancelled(request):
    messages.warning(request, "Payment was cancelled.")
    return redirect("view_plans")


@login_required
def customer_portal(request):
    """View subscription details and transactions locally (replaces Stripe portal)"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, "Access denied.")
            return redirect("home")

        company = profile.company
        subscription = Subscription.objects.filter(company=company, is_active=True).first()
        if not subscription:
            messages.error(request, "No active subscription found.")
            return redirect("subscription_details")

        transactions = Transaction.objects.filter(subscription__company=company).order_by('-transaction_date')

        context = {
            'company': company,
            'subscription': subscription,
            'transactions': transactions,
        }
        return render(request, 'billing/customer_portal.html', context)

    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found.")
        return redirect("home")



@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    from django.conf import settings

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        handle_checkout_session_completed(data)
    elif event_type == "invoice.payment_succeeded":
        handle_invoice_payment_succeeded(data)
    elif event_type == "invoice.payment_failed":
        handle_invoice_payment_failed(data)

    return HttpResponse(status=200)


def handle_checkout_session_completed(session):
    """Handle completed checkout session"""
    try:
        company_id = session["metadata"].get("company_id")
        plan_id = session["metadata"].get("plan_id")
        billing_period = session["metadata"].get("billing_period", "monthly")
        num_workers = int(session["metadata"].get("num_workers", 3))

        company = Company.objects.get(id=company_id)
        plan = Plan.objects.get(id=plan_id)

        # Deactivate old subscriptions
        Subscription.objects.filter(company=company, is_active=True).update(is_active=False)

        start_date = timezone.now().date()
        period_days = {
            "monthly": 30,
            "three_months": 90,
            "six_months": 180,
            "yearly": 365,
        }
        end_date = start_date + timedelta(days=period_days.get(billing_period, 30))

        subscription = Subscription.objects.create(
            company=company,
            plan=plan,
            billing_period=billing_period,
            num_workers=num_workers,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            status=Subscription.STATUS_ACTIVE,
        )

        # Create transaction record
        amount = plan.get_price_for_period(billing_period, num_workers)
        Transaction.objects.create(
            subscription=subscription,
            amount=amount,
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            payment_status=Transaction.PAYMENT_STATUS_SUCCEEDED,
        )
    except Exception as e:
        print(f"Error handling checkout session completed: {str(e)}")


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment"""
    try:
        subscription = Subscription.objects.filter(id=invoice.get("subscription")).first()
        if subscription:
            Transaction.objects.create(
                subscription=subscription,
                amount=invoice["amount_paid"] / 100,
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                payment_status=Transaction.PAYMENT_STATUS_SUCCEEDED,
            )
            subscription.status = Subscription.STATUS_ACTIVE
            subscription.is_active = True
            subscription.save()
    except Exception as e:
        print(f"Error handling invoice payment succeeded: {str(e)}")


def handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment"""
    try:
        subscription = Subscription.objects.filter(id=invoice.get("subscription")).first()
        if subscription:
            subscription.status = Subscription.STATUS_PAST_DUE
            subscription.save()
            Transaction.objects.create(
                subscription=subscription,
                amount=invoice["amount_due"] / 100,
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                payment_status=Transaction.PAYMENT_STATUS_FAILED,
            )
    except Exception as e:
        print(f"Error handling invoice payment failed: {str(e)}")

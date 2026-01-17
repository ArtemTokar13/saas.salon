"""
Management command to sync Django billing plans with Stripe products and prices
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import stripe
from billing.models import Plan
from decimal import Decimal

stripe.api_key = settings.STRIPE_SECRET_KEY


class Command(BaseCommand):
    help = 'Sync billing plans with Stripe - creates products and prices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--plan-id',
            type=int,
            help='Sync only a specific plan by ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )

    def handle(self, *args, **options):
        if not settings.STRIPE_SECRET_KEY:
            raise CommandError('STRIPE_SECRET_KEY is not configured in settings')
        
        self.stdout.write(self.style.WARNING('Starting Stripe sync...'))
        
        # Get plans to sync
        if options['plan_id']:
            plans = Plan.objects.filter(id=options['plan_id'])
            if not plans.exists():
                raise CommandError(f"Plan with ID {options['plan_id']} does not exist")
        else:
            plans = Plan.objects.filter(is_active=True)
        
        if not plans.exists():
            self.stdout.write(self.style.WARNING('No plans found to sync'))
            return
        
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Sync each plan
        for plan in plans:
            self.stdout.write(f'\nProcessing plan: {plan.name}')
            self.sync_plan(plan, dry_run)
        
        self.stdout.write(self.style.SUCCESS('\nSync completed!'))

    def sync_plan(self, plan, dry_run=False):
        """Sync a single plan with Stripe"""
        
        # Create or update Stripe Product
        if plan.stripe_product_id:
            self.stdout.write(f'  Product ID already exists: {plan.stripe_product_id}')
            if not dry_run:
                try:
                    # Update existing product
                    stripe.Product.modify(
                        plan.stripe_product_id,
                        name=plan.name,
                        description=plan.description or '',
                    )
                    self.stdout.write(self.style.SUCCESS('  ✓ Product updated'))
                except stripe.error.StripeError as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error updating product: {str(e)}'))
                    return
        else:
            if dry_run:
                self.stdout.write('  Would create Stripe Product')
            else:
                try:
                    product = stripe.Product.create(
                        name=plan.name,
                        description=plan.description or '',
                        metadata={'plan_id': plan.id}
                    )
                    plan.stripe_product_id = product.id
                    plan.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created product: {product.id}'))
                except stripe.error.StripeError as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error creating product: {str(e)}'))
                    return
        
        # Create prices for each billing period
        periods = {
            'monthly': {'months': 1, 'label': 'Monthly'},
            'three_months': {'months': 3, 'label': '3 Months'},
            'six_months': {'months': 6, 'label': '6 Months'},
            'yearly': {'months': 12, 'label': 'Yearly'},
        }
        
        for period_key, period_info in periods.items():
            price_field = f'stripe_price_id_{period_key}'
            existing_price_id = getattr(plan, price_field)
            
            # Calculate price for this period
            price_amount = plan.get_price_for_period(period_key)
            price_cents = int(price_amount * 100)
            
            if existing_price_id:
                self.stdout.write(f'  {period_info["label"]}: Price ID already exists: {existing_price_id}')
            else:
                if dry_run:
                    self.stdout.write(f'  Would create {period_info["label"]} price: ${price_amount}')
                else:
                    try:
                        stripe_price = stripe.Price.create(
                            product=plan.stripe_product_id,
                            unit_amount=price_cents,
                            currency='usd',
                            recurring={
                                'interval': 'month',
                                'interval_count': period_info['months'],
                            },
                            nickname=f'{plan.name} - {period_info["label"]}',
                            metadata={
                                'plan_id': plan.id,
                                'billing_period': period_key,
                            }
                        )
                        setattr(plan, price_field, stripe_price.id)
                        plan.save()
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ Created {period_info["label"]} price: {stripe_price.id} (${price_amount})'
                        ))
                    except stripe.error.StripeError as e:
                        self.stdout.write(self.style.ERROR(
                            f'  ✗ Error creating {period_info["label"]} price: {str(e)}'
                        ))

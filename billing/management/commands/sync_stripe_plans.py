"""
Management command to view billing plans locally
"""
from django.core.management.base import BaseCommand
from billing.models import Plan

class Command(BaseCommand):
    help = 'View all active billing plans and their pricing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--plan-id',
            type=int,
            help='Show only a specific plan by ID',
        )

    def handle(self, *args, **options):
        if options['plan_id']:
            plans = Plan.objects.filter(id=options['plan_id'])
            if not plans.exists():
                self.stdout.write(self.style.ERROR(f"Plan with ID {options['plan_id']} does not exist"))
                return
        else:
            plans = Plan.objects.filter(is_active=True)

        if not plans.exists():
            self.stdout.write(self.style.WARNING("No active plans found"))
            return

        for plan in plans:
            self.stdout.write(f"\nPlan: {plan.name}")
            self.stdout.write(f"  Base workers: {plan.base_workers}")
            self.stdout.write(f"  Base monthly price: ${plan.base_monthly_price}")
            self.stdout.write(f"  Additional worker price: ${plan.additional_worker_price}")
            self.stdout.write("  Prices by period:")
            for period in plan.PERIOD_MULTIPLIERS.keys():
                price = plan.get_price_for_period(period)
                self.stdout.write(f"    {period}: ${price}")

"""
Management command to setup Google OAuth Social Application
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings
from allauth.socialaccount.models import SocialApp
import os


class Command(BaseCommand):
    help = 'Setup Google OAuth Social Application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            type=str,
            help='Google OAuth Client ID (or set GOOGLE_OAUTH_CLIENT_ID env var or in settings)',
        )
        parser.add_argument(
            '--client-secret',
            type=str,
            help='Google OAuth Client Secret (or set GOOGLE_OAUTH_CLIENT_SECRET env var or in settings)',
        )
        parser.add_argument(
            '--site-domain',
            type=str,
            default='localhost:8000',
            help='Site domain (default: localhost:8000)',
        )

    def handle(self, *args, **options):
        # Get credentials from arguments, environment variables, or Django settings (local_settings.py)
        client_id = (
            options.get('client_id') or 
            os.environ.get('GOOGLE_OAUTH_CLIENT_ID') or
            getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
        )
        client_secret = (
            options.get('client_secret') or 
            os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET') or
            getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', None)
        )
        site_domain = options.get('site_domain')

        if not client_id or not client_secret:
            self.stdout.write(
                self.style.ERROR(
                    'Google OAuth credentials not provided. '
                    'Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables '
                    'or use --client-id and --client-secret arguments.'
                )
            )
            return

        # Get or create the site
        site, created = Site.objects.get_or_create(
            domain=site_domain,
            defaults={'name': site_domain}
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created site: {site_domain}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Site already exists: {site_domain}')
            )

        # Create or update the Google social app
        social_app, created = SocialApp.objects.get_or_create(
            provider='google',
            name='Google OAuth',
            defaults={
                'client_id': client_id,
                'secret': client_secret,
            }
        )

        if not created:
            # Update existing app
            social_app.client_id = client_id
            social_app.secret = client_secret
            social_app.save()
            self.stdout.write(
                self.style.WARNING('Updated existing Google OAuth app')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Created Google OAuth app')
            )

        # Associate the app with the site
        if site not in social_app.sites.all():
            social_app.sites.add(site)
            self.stdout.write(
                self.style.SUCCESS(f'Associated Google OAuth app with site: {site_domain}')
            )

        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ Google OAuth setup complete!\n'
                f'  Client ID: {client_id[:20]}...\n'
                f'  Site: {site_domain}\n\n'
                'You can now use Google OAuth for authentication.'
            )
        )

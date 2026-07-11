from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Plan, Subscription, Transaction, StripeErrorLog, SellerBillingInfo, ClientBillingInfo, ManualInvoice

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_monthly_price', 'base_workers', 'additional_worker_price', 'trial_days', 'is_active']
    search_fields = ['name']
    list_filter = ['is_active']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'features', 'is_active', 'whatsapp_included')
        }),
        ('Pricing Configuration', {
            'fields': ('base_workers', 'base_monthly_price', 'additional_worker_price', 'trial_days'),
            'description': 'Set base price for included workers, price per additional worker, and trial period'
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'company', 'plan', 'num_workers', 'billing_period', 'status',
        'trial_status', 'calculated_price', 'start_date', 'end_date', 'is_active'
    ]
    list_filter = ['plan', 'billing_period', 'status', 'is_active', 'start_date', 'end_date']
    search_fields = ['company__name']
    fieldsets = (
        ('Subscription Details', {
            'fields': ('company', 'plan', 'num_workers', 'billing_period', 'start_date', 'end_date', 'trial_end', 'is_active', 'status')
        }),
    )

    def trial_status(self, obj):
        """Display trial status"""
        if obj.is_trial:
            return format_html('<span style="color: blue;">🎁 Trial until {}</span>', obj.trial_end)
        return '-'
    trial_status.short_description = 'Trial'

    def calculated_price(self, obj):
        """Display the calculated price for this subscription"""
        breakdown = obj.pricing_breakdown
        price_display = f'${obj.price}'
        if obj.is_trial:
            price_display = f'<del>${obj.price}</del> <strong style="color: green;">FREE (Trial)</strong>'
        return format_html(
            '{} <small>(${}/mo × {} workers)</small>',
            price_display,
            breakdown['total_monthly'],
            obj.num_workers
        )
    calculated_price.short_description = 'Total Price'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'subscription', 'amount', 'payment_status', 'transaction_date']
    list_filter = ['payment_status', 'transaction_date']
    search_fields = ['transaction_id']
    fieldsets = (
        ('Transaction Details', {
            'fields': ('subscription', 'amount', 'transaction_id', 'payment_status', 'transaction_date')
        }),
    )


@admin.register(StripeErrorLog)
class StripeErrorLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'function_name', 'error_type', 'company', 'subscription', 'resolved', 'short_error_message']
    list_filter = ['resolved', 'error_type', 'function_name', 'created_at']
    search_fields = ['error_message', 'function_name', 'company__name']
    readonly_fields = ['created_at', 'function_name', 'error_type', 'error_message', 'request_params', 'company', 'subscription']
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Error Information', {
            'fields': ('function_name', 'error_type', 'error_message', 'created_at')
        }),
        ('Context', {
            'fields': ('company', 'subscription', 'request_params')
        }),
        ('Resolution', {
            'fields': ('resolved', 'notes')
        }),
    )
    
    def short_error_message(self, obj):
        """Display truncated error message"""
        msg = obj.error_message[:100]
        if len(obj.error_message) > 100:
            msg += '...'
        return msg
    short_error_message.short_description = 'Error Message'
    
    actions = ['mark_as_resolved', 'mark_as_unresolved']
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(resolved=True)
        self.message_user(request, f'{queryset.count()} errors marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected errors as resolved'
    
    def mark_as_unresolved(self, request, queryset):
        queryset.update(resolved=False)
        self.message_user(request, f'{queryset.count()} errors marked as unresolved.')
    mark_as_unresolved.short_description = 'Mark selected errors as unresolved'


@admin.register(SellerBillingInfo)
class SellerBillingInfoAdmin(admin.ModelAdmin):
    """Singleton: edit-only, no delete or add button shown."""
    fields = ['company_name', 'tax_id', 'address', 'city', 'province', 'postal_code', 'country', 'phone', 'email']

    def has_add_permission(self, request):
        return not SellerBillingInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_object(self, request, object_id, from_field=None):
        # Always load pk=1
        return SellerBillingInfo.objects.filter(pk=1).first()

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # Redirect add view to edit pk=1 if it already exists
        if object_id is None and SellerBillingInfo.objects.filter(pk=1).exists():
            from django.urls import reverse
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(
                reverse('admin:billing_sellerbillinginfo_change', args=[1])
            )
        return super().changeform_view(request, object_id, form_url, extra_context)


@admin.register(ClientBillingInfo)
class ClientBillingInfoAdmin(admin.ModelAdmin):
    list_display = ['billing_name', 'company', 'tax_id', 'city', 'country']
    search_fields = ['billing_name', 'company__name', 'tax_id']
    readonly_fields = ['company']


@admin.register(ManualInvoice)
class ManualInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'invoice_date', 'client_name', 'description', 'total_display', 'download_link']
    list_filter = ['invoice_date']
    search_fields = ['invoice_number', 'client_name', 'description']
    date_hierarchy = 'invoice_date'
    readonly_fields = ['invoice_number', 'created_at', 'download_link']

    fieldsets = (
        ('Invoice', {
            'fields': ('invoice_number', 'invoice_date', 'company', 'notes')
        }),
        ('Seller (FROM)', {
            'fields': (
                'seller_company_name', 'seller_tax_id', 'seller_address',
                'seller_city', 'seller_province', 'seller_postal_code',
                'seller_country', 'seller_phone', 'seller_email',
            ),
            'classes': ('collapse',),
            'description': 'Auto-filled from Seller Billing Info on first save. Edit if needed.',
        }),
        ('Client (TO)', {
            'fields': (
                'client_name', 'client_tax_id', 'client_address',
                'client_city', 'client_province', 'client_postal_code',
                'client_country', 'client_phone', 'client_email',
            ),
            'description': 'Auto-filled from company billing info when company is selected and client name is blank.',
        }),
        ('Line Item', {
            'fields': ('description', 'period_start', 'period_end', 'quantity', 'unit_price'),
        }),
        ('Payment', {
            'fields': ('payment_method',),
        }),
        ('Actions', {
            'fields': ('download_link',),
        }),
    )

    def total_display(self, obj):
        return format_html('€{}', obj.total)
    total_display.short_description = 'Total'

    def download_link(self, obj):
        if obj and obj.pk:
            url = reverse('admin_manual_invoice_pdf', args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" class="button" '
                'style="background:#417690;color:#fff;padding:4px 10px;border-radius:4px;text-decoration:none;">'
                '⬇ Download PDF</a>', url
            )
        return '—'
    download_link.short_description = 'PDF'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:invoice_id>/pdf/', self.admin_site.admin_view(self.invoice_pdf_view),
                 name='admin_manual_invoice_pdf'),
        ]
        return custom + urls

    def invoice_pdf_view(self, request, invoice_id):
        from django.shortcuts import get_object_or_404
        from xhtml2pdf import pisa
        from io import BytesIO
        invoice = get_object_or_404(ManualInvoice, pk=invoice_id)
        html = render_to_string('billing/manual_invoice_print.html', {'invoice': invoice}, request=request)
        result = BytesIO()
        pdf = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=result)
        if pdf.err:
            return HttpResponse('Error generating PDF', status=500)
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="receipt_{invoice.invoice_number}.pdf"'
        return response


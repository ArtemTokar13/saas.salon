from django.db import models
from bookings.models import Customer, Booking
from companies.models import Company


class WhatsAppConversation(models.Model):
    """Track WhatsApp conversations for context"""
    phone_number = models.CharField(max_length=50)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    conversation_state = models.JSONField(default=dict, blank=True)
    # States: 'idle', 'collecting_info', 'showing_slots', 'confirming'
    current_state = models.CharField(max_length=50, default='idle')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['phone_number', '-updated_at']),
        ]
    
    def __str__(self):
        return f"{self.phone_number} - {self.current_state}"


class WhatsAppMessage(models.Model):
    """Log all WhatsApp messages"""
    conversation = models.ForeignKey(WhatsAppConversation, on_delete=models.CASCADE, related_name='messages')
    from_number = models.CharField(max_length=50)
    to_number = models.CharField(max_length=50)
    message_body = models.TextField()
    direction = models.CharField(max_length=10)  # 'inbound' or 'outbound'
    message_sid = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.direction} - {self.from_number[:20]}"


class PendingBooking(models.Model):
    """Temporary storage for bookings in progress"""
    conversation = models.ForeignKey(WhatsAppConversation, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    service_name = models.CharField(max_length=255, null=True, blank=True)
    service = models.ForeignKey('companies.Service', on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey('companies.Staff', on_delete=models.SET_NULL, null=True, blank=True)
    booking_date = models.DateField(null=True, blank=True)
    booking_time = models.TimeField(null=True, blank=True)
    available_slots = models.JSONField(default=list, blank=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    created_booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Pending: {self.service_name} on {self.booking_date}"

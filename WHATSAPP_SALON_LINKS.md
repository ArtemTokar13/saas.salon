# WhatsApp Salon-Specific Links & QR Codes

## 🎯 Overview

Each salon gets **unique entry points** (links & QR codes) that automatically select the salon when clients click them. Clients don't need to type the salon name!

**Benefits:**
- ✅ One WhatsApp number for all salons
- ✅ Each salon has custom link/QR code
- ✅ Automatic salon detection
- ✅ Better user experience
- ✅ Track which salon gets more bookings

---

## 📱 How It Works

### Example Flow:

```
Salon Website/Poster
     ↓
[Click WhatsApp Button/Scan QR]
     ↓
Opens WhatsApp with pre-filled message: "SALON_CENTRO"
     ↓
Bot detects "SALON_CENTRO" → Sets salon automatically
     ↓
Client just says: "I want haircut tomorrow"
     ↓
Bot already knows: Peluquería UJI Centro ✅
```

---

## 🔗 Step 1: Create WhatsApp Links

### Format:
```
https://wa.me/[YOUR_NUMBER]?text=[SALON_CODE]
```

### Your Links:

**Replace `34964123456` with your actual WhatsApp Business number:**

#### Salon Centro:
```
https://wa.me/34964123456?text=SALON_CENTRO
```

#### Salon Norte:
```
https://wa.me/34964123456?text=SALON_NORTE
```

#### Salon Sur:
```
https://wa.me/34964123456?text=SALON_SUR
```

### Prettier Versions (with greeting):

```
https://wa.me/34964123456?text=Hola!%20Quiero%20reservar%20en%20Peluquer%C3%ADa%20UJI%20Centro
```

**URL Encoding:**
- Spaces: `%20`
- Accents: `í` = `%C3%AD`

---

## 🎨 Step 2: Create QR Codes

### Online Generator:
Go to: **https://www.qr-code-generator.com/**

For each salon:

1. Select "URL"
2. Paste the WhatsApp link:
   ```
   https://wa.me/34964123456?text=SALON_CENTRO
   ```
3. Customize:
   - Add logo (salon logo in center)
   - Choose colors (match your brand)
   - Add text below: "Reserva por WhatsApp"
4. Download high-resolution PNG

### Example QR Codes:

**Salon Centro:**
```
┌─────────────────────┐
│  ▄▄▄▄▄▄▄  ▄  ▄▄▄▄▄▄▄│
│  █ ▄▄▄ █ ▀▀  █ ▄▄▄ █│
│  █ ███ █ ▄█▄ █ ███ █│  [Your Salon Logo]
│  █▄▄▄▄▄█ ▄ ▄ █▄▄▄▄▄█│
│  ▄▄  ▄▄▄█▄██▄  ▄▄▄  │
│  ███▄▄ ▄ ▀▄██ ▀█▀▄  │
│  ▄▄▄▄▄▄▄ █▄  ▄ █  ▄ │
│  █ ▄▄▄ █  ▄██▄█▀▄▄▀ │
│  █ ███ █ ▄▀ ▄▀ ▄▄█  │
│  █▄▄▄▄▄█ █ █▀█▄▄ ▄█ │
└─────────────────────┘
  Reserva por WhatsApp
   Peluquería UJI Centro
```

---

## 🌐 Step 3: Add to Your Website

### Website Button Example:

```html
<!-- Salon Centro Page -->
<a href="https://wa.me/34964123456?text=SALON_CENTRO" 
   class="whatsapp-button"
   target="_blank">
   📱 Reservar por WhatsApp
</a>

<!-- Salon Norte Page -->
<a href="https://wa.me/34964123456?text=SALON_NORTE" 
   class="whatsapp-button"
   target="_blank">
   📱 Reservar por WhatsApp
</a>
```

### CSS Styling:

```css
.whatsapp-button {
  background: #25D366; /* WhatsApp green */
  color: white;
  padding: 12px 24px;
  border-radius: 25px;
  text-decoration: none;
  font-weight: bold;
  display: inline-block;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}

.whatsapp-button:hover {
  background: #128C7E;
  transform: translateY(-2px);
}
```

---

## 📄 Step 4: Print Materials

### Business Cards:
```
┌──────────────────────────────┐
│  Peluquería UJI Centro       │
│  Calle Mayor 15, Valencia    │
│                              │
│  [QR CODE]                   │
│                              │
│  Reserva por WhatsApp        │
│  Escanea el código           │
└──────────────────────────────┘
```

### Posters/Flyers:
```
┌─────────────────────────────────────┐
│                                     │
│     RESERVA TU CITA POR WHATSAPP    │
│                                     │
│         [LARGE QR CODE]             │
│                                     │
│   Escanea y reserva en segundos     │
│        ¡Sin llamadas!               │
│                                     │
│      Peluquería UJI Centro          │
│      📍 Calle Mayor 15              │
└─────────────────────────────────────┘
```

### Storefront Window Sticker:
```
┌─────────────────────┐
│                     │
│  Reserva aquí       │
│   por WhatsApp      │
│                     │
│   [QR CODE]         │
│                     │
│  📱 Rápido y fácil  │
│                     │
└─────────────────────┘
```

---

## ⚙️ Step 5: Configure Salon Codes (Technical)

### Current Configuration:

The system detects these codes automatically (already in `views.py`):

```python
salon_codes = {
    'SALON_CENTRO': 'centro',
    'SALON_NORTE': 'norte', 
    'SALON_SUR': 'sur',
    'CENTRO': 'centro',
    'NORTE': 'norte',
    'SUR': 'sur',
}
```

### To Add More Salons:

Edit `/home/ubuntu/reserva-ya/whatsapp_bot/views.py`:

```python
salon_codes = {
    'SALON_CENTRO': 'centro',
    'SALON_NORTE': 'norte',
    'SALON_SUR': 'sur',
    'SALON_ESTE': 'este',      # Add new salon
    'SALON_OESTE': 'oeste',    # Add new salon
}
```

### Matching Logic:

The system tries to match the code to your salon name in database:
- Looks for salon with "centro" in name
- Fuzzy matching: "Peluquería UJI Centro" ✅
- Works even if spelled: "peluqueria centro" ✅

**Make sure your salon names in database contain these keywords!**

---

## 📊 Step 6: Track Usage

### Check Which QR Code/Link Was Used:

In Django Admin:
```
WhatsApp Conversations → View conversation
Look for: salon_auto_selected = True
```

### Analytics:

Add to your admin dashboard:
```python
# Count bookings by entry method
auto_selected = WhatsAppConversation.objects.filter(
    conversation_state__salon_auto_selected=True
).count()

manual_selection = WhatsAppConversation.objects.filter(
    conversation_state__salon_auto_selected__isnull=True
).count()
```

---

## 🧪 Testing

### Test Each Link:

1. **Click Link** (or scan QR with phone)
2. WhatsApp opens with message: "SALON_CENTRO"
3. **Send the message** (or type something else)
4. **Bot should respond:**
   ```
   ✅ ¡Bienvenido a Peluquería UJI Centro!
   
   📍 Calle Mayor 15, Valencia
   📞 964 123 456
   
   ¿Qué servicio necesitas?
   ```

5. **Type:** "corte de pelo mañana"
6. **Bot shows availability** (doesn't ask which salon!)

---

## 🎨 Design Examples

### Social Media Posts:

**Instagram Story:**
```
┌─────────────────┐
│                 │
│  Reserva tu     │
│  próxima cita   │
│                 │
│   [QR CODE]     │
│                 │
│  👆 Escanea     │
│                 │
└─────────────────┘
```

**Facebook Post:**
```
💇‍♀️ ¡Reserva tu cita por WhatsApp!

Ahora es más fácil que nunca:
👉 Click aqui: [Link]
⏱️ Respuesta en segundos
📅 Elige tu horario preferido

#PeluqueriaUJI #ReservaOnline #WhatsApp
```

### Email Signature:
```
---
María García
Peluquería UJI Centro
📱 Reserva por WhatsApp: [Link Button]
📞 964 123 456
📧 info@peluqueriauji.com
```

---

## 💡 Advanced: Custom Messages Per Salon

### Personalized Greetings:

Instead of generic codes, use full messages:

**Salon Centro:**
```
https://wa.me/34964123456?text=Hola!%20Quiero%20reservar%20en%20Peluquer%C3%ADa%20UJI%20Centro
```

**Salon Norte:**
```
https://wa.me/34964123456?text=Hola!%20Quiero%20reservar%20en%20Peluquer%C3%ADa%20UJI%20Norte
```

The bot detects "reservar en [Salon Name]" and extracts the salon automatically!

---

## 📋 Checklist

Before going live with each salon:

- [ ] Create WhatsApp link with correct salon code
- [ ] Generate QR code (high resolution, 300+ DPI)
- [ ] Test link on mobile phone
- [ ] Verify bot recognizes salon automatically
- [ ] Add to salon website
- [ ] Print QR codes for physical locations
- [ ] Update business cards
- [ ] Create social media posts
- [ ] Train staff about new booking method
- [ ] Monitor first week of bookings

---

## 🔧 Troubleshooting

### Bot Doesn't Recognize Salon:

**Check:**
1. Salon name in database matches keyword
2. Salon has `online_appointments_enabled = True`
3. Code is spelled correctly in link
4. Check logs: `tail -f logs/django.log | grep "Auto-selected"`

### Fix:
```python
# In Django shell
from companies.models import Company
salon = Company.objects.get(name="Peluquería UJI Centro")
print(salon.online_appointments_enabled)  # Should be True
```

### Client Says "Link Doesn't Work":

**Check:**
1. Phone number format: `34964123456` (no + or -)
2. URL encoding is correct
3. Link works in browser first
4. WhatsApp is installed on client's phone

---

## 📱 Mobile Deep Links (Advanced)

### iOS/Android Direct Links:

```html
<!-- Opens WhatsApp app directly -->
<a href="whatsapp://send?phone=34964123456&text=SALON_CENTRO">
  Open in WhatsApp App
</a>

<!-- Web version (works on desktop) -->
<a href="https://wa.me/34964123456?text=SALON_CENTRO">
  Open in WhatsApp Web
</a>

<!-- Universal (works everywhere) -->
<a href="https://api.whatsapp.com/send?phone=34964123456&text=SALON_CENTRO">
  Open WhatsApp
</a>
```

---

## 🎯 Summary

**Each salon gets:**
- ✅ Unique WhatsApp link
- ✅ Branded QR code
- ✅ Automatic salon detection
- ✅ Personalized welcome message

**All using ONE WhatsApp Business number!**

**Client experience:**
1. Click/Scan → Opens WhatsApp
2. Send message → Bot knows salon
3. "I want haircut tomorrow" → Done!

**No need to type salon name. Magic! ✨**

---

## Quick Setup Commands

```bash
# Step 1: Make sure code is deployed
cd /home/ubuntu/reserva-ya
git pull  # if using git

# Step 2: Restart server
sudo systemctl restart gunicorn  # or your server

# Step 3: Test
python manage.py shell
>>> from whatsapp_bot.views import detect_salon_code
>>> # Test function works

# Step 4: Create your links (replace with your number)
# No commands needed - just use the URLs above!
```

---

**Ready to create your salon-specific links and QR codes!** 🚀

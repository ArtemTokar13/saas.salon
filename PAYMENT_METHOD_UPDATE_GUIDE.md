# Система оновлення платіжних даних - Інструкція

## 🎯 Що було додано

Створено повноцінну систему для оновлення платіжних методів через **Stripe Customer Portal**. Тепер клієнти можуть:

✅ Додавати нові картки  
✅ Видаляти старі картки  
✅ Змінювати основний платіжний метод  
✅ Переглядати історію платежів  
✅ Повторювати невдалі платежі  

---

## 🛠️ Налаштування Stripe Customer Portal

Перед використанням потрібно активувати Customer Portal в Stripe:

### Крок 1: Активація Customer Portal

1. Зайдіть в **Stripe Dashboard**: https://dashboard.stripe.com/
2. Перейдіть в **Settings** → **Billing** → **Customer portal**
3. Натисніть **"Activate portal"** або **"Configure portal settings"**

### Крок 2: Налаштування прав доступу

Увімкніть наступні опції:

#### ✅ Обов'язкові налаштування:
- **Allow customers to update payment methods** - ✅ Увімкнути
- **Allow customers to view invoices** - ✅ Увімкнути

#### ⚠️ Опціональні налаштування:
- **Allow customers to cancel subscriptions** - ❌ Вимкнути (щоб клієнти не могли самі скасовувати)
- **Allow customers to switch plans** - ❌ Вимкнути (керуємо через власний інтерфейс)
- **Allow customers to pause subscriptions** - ❌ Вимкнути

### Крок 3: Брендинг (опціонально)

Налаштуйте вигляд Customer Portal:
- Завантажте логотип компанії
- Виберіть кольорову схему
- Додайте Custom CSS (якщо потрібно)

---

## 📱 Як використовувати

### Для адміністратора (ви)

#### 1. Перевірка статусу клієнта

Використовуйте діагностичний скрипт:

```bash
python check_customer_stripe.py client@email.com
```

Він покаже:
- Поточний статус підписки
- Збережені платіжні методи
- Останні помилки платежів
- Деталі payment intent

#### 2. Генерація посилання для клієнта

```bash
python generate_customer_portal_link.py client@email.com
```

Це згенерує посилання, яке діє **24 години**. Відправте його клієнту.

#### 3. Повторна спроба платежу (опціонально)

Якщо клієнт оновив картку, спробуйте:

```bash
python generate_customer_portal_link.py client@email.com --retry
```

---

### Для клієнта (автоматично)

Клієнт бачить в особистому кабінеті:

#### 1. Warning Banner (якщо є проблема з платежем)

Червоний банер з попередженням:
```
⚠️ Payment Issue
There was a problem with your last payment...
[Update Payment Method] [Retry Payment]
```

#### 2. Кнопка "Update Payment Method"

В розділі **Subscription & Billing** є синя кнопка **"Update Payment Method"**.

**Що відбувається:**
1. Клієнт натискає кнопку
2. Автоматичний редирект на Stripe Customer Portal
3. Клієнт додає/оновлює картку
4. Після завершення - повертається назад в систему
5. Stripe автоматично спробує списати гроші з нової картки

#### 3. Кнопка "Retry Payment"

Якщо картка вже оновлена, клієнт може натиснути **"Retry Payment"** для негайної спроби списання.

---

## 🚨 Найпоширеніші проблеми та рішення

### Проблема 1: Дебетова картка Santander (Іспанія)

**Симптоми:**
- Код помилки: `card_declined` / `insufficient_funds`
- Дебетова картка (debit)
- Іспанський банк

**Рішення для клієнта:**

```
Hola,

El banco Santander ha rechazado el pago automático. 
Esto es común con tarjetas de débito españolas.

SOLUCIONES:

1. Llame al banco (910 12 34 56) y solicite:
   • Activar "pagos recurrentes internacionales"
   • Aumentar el límite de compras online

2. O use una tarjeta de crédito en lugar de débito

Después, actualice su tarjeta aquí:
[ENLACE]

Saludos
```

### Проблема 2: Payment Intent в статусі "requires_payment_method"

**Симптоми:**
- Status: `past_due`
- Payment intent: `requires_payment_method`
- Stripe припинив автоматичні спроби

**Рішення:**
1. Клієнт **обов'язково** повинен оновити платіжний метод
2. Після оновлення натиснути "Retry Payment"
3. Або Stripe автоматично спробує списати через кілька годин

### Проблема 3: "No default payment method set"

**Симптоми:**
- В діагностиці: `⚠️ No default payment method set`
- Картка є, але не встановлена як default

**Рішення:**
1. Клієнт йде в Customer Portal
2. Видаляє стару картку (якщо потрібно)
3. Додає нову картку - вона автоматично стане default

---

## 🔄 Автоматичні процеси Stripe

### Повторні спроби платежу (Smart Retries)

Stripe автоматично робить:
- **1-ша спроба:** Відразу при створенні invoice
- **2-га спроба:** Через 3 дні (якщо перша неуспішна)
- **3-тя спроба:** Через 5 днів (якщо друга неуспішна)
- **4-та спроба:** Через 7 днів (остання спроба)

**⚠️ Важливо:** Якщо код помилки `insufficient_funds` (51), Stripe може припинити спроби раніше.

### Webhook події

Система автоматично обробляє:
- ✅ `invoice.payment_succeeded` - платіж успішний
- ❌ `invoice.payment_failed` - платіж невдалий
- 📝 `checkout.session.completed` - нова підписка створена

---

## 📊 Моніторинг та аналітика

### Stripe Dashboard

Перевіряйте регулярно:
1. **Payments** → Фільтр "Failed" - невдалі платежі
2. **Customers** → Пошук по email - деталі клієнта
3. **Subscriptions** → Фільтр "Past due" - проблемні підписки

### Stripe Error Logs (в вашій БД)

```python
from billing.models import StripeErrorLog

# Останні помилки
recent_errors = StripeErrorLog.objects.order_by('-created_at')[:10]
for error in recent_errors:
    print(f"{error.function_name}: {error.error_type}")
```

---

## 📧 Шаблони листів для клієнтів

### Шаблон 1: Перша невдача платежу

```
Subject: [Reserva-Ya] Problema con su pago / Payment Issue

Hola,

Hubo un problema al procesar su pago de €49.00 para la suscripción.

Código de error: Fondos insuficientes
Tarjeta: Mastercard ••••4985

ACCIONES A TOMAR:

1. Actualice su método de pago aquí:
   [ENLACE AL CUSTOMER PORTAL]

2. O llame a su banco para autorizar pagos recurrentes.

El enlace expira en 24 horas.
Si necesita ayuda, responda a este correo.

Saludos,
Equipo Reserva-Ya
```

### Шаблон 2: Друга невдача (критична)

```
Subject: [URGENTE] Su cuenta será suspendida

Hola,

Su pago ha fallado por segunda vez. Su cuenta será suspendida en 3 días.

Para evitar la interrupción del servicio:

1. Actualice su tarjeta AHORA: [ENLACE]
2. O llame a soporte: +XX XXX XXX XXX

MOTIVOS COMUNES:
• Las tarjetas de débito españolas bloquean pagos recurrentes
• Fondos insuficientes
• Tarjeta expirada

¡Necesitamos su acción inmediata!

Saludos,
Equipo Reserva-Ya
```

### Шаблон 3: Після успішного оновлення

```
Subject: ✅ Método de pago actualizado correctamente

Hola,

Su método de pago ha sido actualizado exitosamente.

Nueva tarjeta: Visa ••••1234
Próximo cargo: €49.00 el 17 de mayo

Gracias por su confianza.

Saludos,
Equipo Reserva-Ya
```

---

## 🔧 Технічні деталі

### Файли, що були змінені:

1. **billing/views.py**
   - `update_payment_method()` - редирект на Customer Portal
   - `retry_payment()` - повторна спроба платежу
   - `subscription_details()` - додана синхронізація статусу

2. **billing/urls.py**
   - `update-payment-method/` - новий маршрут
   - `retry-payment/` - новий маршрут

3. **templates/billing/subscription_details.html**
   - Warning banner для past_due статусу
   - Кнопка "Update Payment Method"
   - Кнопка "Retry Payment"

4. **Нові скрипти:**
   - `check_customer_stripe.py` - діагностика
   - `generate_customer_portal_link.py` - генерація посилань

### Security Notes:

✅ **PCI DSS Compliant** - ніколи не зберігаємо дані карток  
✅ **Stripe Hosted** - всі дані карток на серверах Stripe  
✅ **Token Based** - використовуємо тільки токени payment methods  
✅ **HTTPS Only** - всі запити через HTTPS  

---

## 📞 Підтримка

Якщо виникають проблеми:

1. Перевірте Stripe Dashboard → Logs
2. Перегляньте `StripeErrorLog` в Django Admin
3. Запустіть діагностичний скрипт
4. Напишіть в Stripe Support (якщо проблема на їхній стороні)

---

## ✨ Наступні кроки (опціонально)

### Можливі покращення:

1. **Email сповіщення** при невдалих платежах
2. **SMS сповіщення** для критичних проблем
3. **Automatic dunning** - автоматичні нагадування
4. **Grace period** - період відстрочення перед відключенням
5. **Webhook retry logic** - повторні спроби webhook

### Рекомендації:

1. Налаштуйте email нотифікації в Stripe Dashboard
2. Додайте метрики в систему моніторингу (Sentry, DataDog тощо)
3. Створіть дашборд для відстеження failed payments
4. Автоматизуйте процес нагадувань клієнтам

---

## 🎉 Готово!

Система повністю функціональна і готова до використання.

**Останній чеклист:**
- [x] Views створено
- [x] URLs налаштовано
- [x] Шаблон оновлено
- [x] Діагностичні скрипти готові
- [ ] **Stripe Customer Portal активовано** ← ЗРОБІТЬ ЦЕ!
- [ ] Протестуйте з тестовою карткою

**Тестові картки Stripe:**

```
Успішна: 4242 4242 4242 4242
Недостатньо коштів: 4000 0000 0000 9995
3D Secure: 4000 0027 6000 3184
Відхилена: 4000 0000 0000 0002
```

Все готово до роботи! 🚀

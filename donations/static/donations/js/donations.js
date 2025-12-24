// JavaScript для системы донатов

// Проверка статуса платежа
function checkPaymentStatus(donationId) {
    fetch(`/donations/api/check-status/${donationId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'succeeded') {
                window.location.reload();
            } else if (data.status === 'canceled') {
                alert('Платеж отменен');
                window.location.href = '/donations/';
            }
        })
        .catch(error => {
            console.error('Ошибка проверки статуса:', error);
        });
}

// Автоматическая проверка статуса каждые 5 секунд
function startStatusPolling(donationId, interval = 5000) {
    const pollInterval = setInterval(() => {
        checkPaymentStatus(donationId);
    }, interval);
    
    // Останавливаем через 5 минут
    setTimeout(() => {
        clearInterval(pollInterval);
    }, 300000);
    
    return pollInterval;
}

// Валидация формы
function validateDonationForm(form) {
    const amount = parseFloat(form.querySelector('[name="amount"]').value);
    const email = form.querySelector('[name="user_email"]').value;
    const paymentMethod = form.querySelector('[name="payment_method"]:checked');
    
    if (!amount || amount <= 0) {
        alert('Введите корректную сумму');
        return false;
    }
    
    if (!email || !isValidEmail(email)) {
        alert('Введите корректный email');
        return false;
    }
    
    if (!paymentMethod) {
        alert('Выберите способ оплаты');
        return false;
    }
    
    return true;
}

// Проверка email
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Форматирование суммы
function formatAmount(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// Уведомления
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
        type === 'warning' ? 'bg-yellow-500' :
        'bg-blue-500'
    } text-white`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.5s ease-out';
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Добавляем обработчики для форм
    const donationForms = document.querySelectorAll('form[id*="donation"]');
    donationForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateDonationForm(this)) {
                e.preventDefault();
            }
        });
    });
    
    // Автоматическая проверка статуса, если мы на странице с QR
    const qrPage = document.querySelector('[data-donation-id]');
    if (qrPage) {
        const donationId = qrPage.getAttribute('data-donation-id');
        startStatusPolling(donationId);
    }
});

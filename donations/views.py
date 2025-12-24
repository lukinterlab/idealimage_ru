from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.db import models
from decimal import Decimal
import json
import logging

from .models import (
    Donation, DonationSettings, PaymentWebhookLog, DonationNotification,
    AuthorRole, BonusFormula, AuthorStats, AuthorBonus,
    AuthorPenaltyReward, WeeklyReport, BonusPaymentRegistry
)
from .forms import DonationForm, QuickDonationForm, AuthorPenaltyRewardForm
from .payment_utils import get_payment_handler, YandexKassaPayment, SberPayPayment, SBPPayment
from .qr_utils import generate_payment_qr, generate_yandex_qr, generate_sber_qr
from .email_utils import send_thank_you_email, send_admin_notification
from .bonus_calculator import get_author_stats_summary
from .weekly_processor import get_current_week_summary, get_week_boundaries

logger = logging.getLogger(__name__)


def donation_page(request):
    """Страница оплаты: поддержка проекта или покупка услуги.
    Поддерживает GET-параметры:
    - purpose: назначение платежа (см. Donation.PAYMENT_PURPOSE_CHOICES)
    - amount: сумма (руб)
    - title, description: заголовок/описание услуги для отображения
    - article_id: если поддержка статьи
    """
    donation_settings = DonationSettings.get_settings()

    # Контекст по умолчанию (донаты)
    selected_title = donation_settings.donation_page_title
    selected_description = donation_settings.donation_page_description
    selected_amount = request.GET.get('amount')
    selected_purpose = request.GET.get('purpose', 'donation')

    # Перекрываем заголовок/описание для услуг
    selected_title = request.GET.get('title', selected_title)
    selected_description = request.GET.get('description', selected_description)

    # Привязка к статье (донат из статьи)
    article_id = request.GET.get('article_id')
    article = None
    if article_id:
        from blog.models import Post
        try:
            article = Post.objects.get(id=article_id)
        except Post.DoesNotExist:
            article = None

    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)

            # Привязываем пользователя
            if request.user.is_authenticated:
                donation.user = request.user

            # Назначение платежа (если пришло с формы hidden)
            form_purpose = request.POST.get('payment_purpose')
            if form_purpose:
                donation.payment_purpose = form_purpose

            # Если заранее задана сумма (сквозной сценарий услуги)
            preset_amount = request.POST.get('preset_amount')
            if preset_amount:
                try:
                    donation.amount = Decimal(preset_amount)
                except Exception:
                    pass

            # Привязка к статье
            if article:
                donation.article = article
                donation.article_author = article.author

            donation.save()

            return redirect('donations:process_payment', donation_id=donation.id)
    else:
        form = DonationForm(initial={
            'amount': selected_amount if selected_amount else None,
        })

    context = {
        'form': form,
        'settings': donation_settings,
        'page_title': selected_title,
        'page_description': selected_description,
        'article': article,
        'selected_purpose': selected_purpose,
        'selected_amount': selected_amount,
    }

    return render(request, 'donations/donation_page.html', context)


def quick_donation(request):
    """Быстрая форма доната с предустановленными суммами"""
    donation_settings = DonationSettings.get_settings()
    
    # Получаем article_id из GET параметров
    article_id = request.GET.get('article_id')
    article = None
    
    if article_id:
        from blog.models import Post
        try:
            article = Post.objects.get(id=article_id)
        except Post.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = QuickDonationForm(request.POST)
        if form.is_valid():
            # Создаем донат
            donation = Donation.objects.create(
                amount=form.cleaned_data['final_amount'],
                payment_method=form.cleaned_data['payment_method'],
                user_email=form.cleaned_data['user_email'],
                user=request.user if request.user.is_authenticated else None,
            )
            
            # Привязываем статью и автора из POST или сессии
            article_id_post = request.POST.get('article_id')
            if article_id_post:
                from blog.models import Post
                try:
                    article = Post.objects.get(id=article_id_post)
                    donation.article = article
                    donation.article_author = article.author
                    donation.save()
                except Post.DoesNotExist:
                    pass
            
            return redirect('donations:process_payment', donation_id=donation.id)
    else:
        # Проверяем, есть ли предустановленная сумма в URL
        initial_data = {}
        amount = request.GET.get('amount')
        if amount and amount.isdigit():
            initial_data['custom_amount'] = amount
        
        form = QuickDonationForm(initial=initial_data)
    
    context = {
        'form': form,
        'settings': donation_settings,
        'preset_amount': amount if amount and amount.isdigit() else None,
        'article': article,
        'article_id': article_id,
    }
    
    return render(request, 'donations/quick_donation.html', context)


def process_payment(request, donation_id):
    """Обработка платежа и перенаправление на платежную систему"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Проверяем, что платеж еще не обработан
    if donation.status != 'pending':
        return redirect('donations:donation_status', donation_id=donation.id)
    
    # Формируем URL для возврата
    return_url = request.build_absolute_uri(
        reverse('donations:payment_return', kwargs={'donation_id': donation.id})
    )
    
    try:
        # Обновляем статус
        donation.status = 'processing'
        donation.save()
        
        # Формируем описание платежа в зависимости от назначения
        if donation.payment_purpose and donation.payment_purpose != 'donation':
            # Для услуг используем более подробное описание
            purpose_descriptions = {
                'premium_monthly': 'Premium подписка (1 месяц) - IdealImage.ru',
                'premium_3months': 'Premium подписка (3 месяца) - IdealImage.ru',
                'premium_yearly': 'Premium подписка (12 месяцев) - IdealImage.ru',
                'ai_coauthor_monthly': 'AI-Соавтор (1 месяц) - IdealImage.ru',
                'ai_once': 'AI-Соавтор (разовая генерация) - IdealImage.ru',
                'ai_pack_5': 'AI-Соавтор (пакет 5 статей) - IdealImage.ru',
                'ai_pack_10': 'AI-Соавтор (пакет 10 статей) - IdealImage.ru',
                'ai_pack_30': 'AI-Соавтор (пакет 30 статей) - IdealImage.ru',
                'marathon_skin': 'Марафон "Идеальная кожа" - IdealImage.ru',
                'marathon_makeup': 'Марафон "Макияж" - IdealImage.ru',
                'marathon_wardrobe': 'Марафон "Гардероб" - IdealImage.ru',
                'ad_main_banner': 'Реклама: Баннер на главной - IdealImage.ru',
                'ad_sidebar': 'Реклама: Боковой блок - IdealImage.ru',
                'ad_in_content': 'Реклама: Внутри статей - IdealImage.ru',
                'ad_article': 'Рекламная статья - IdealImage.ru',
                'ad_ticker': 'Бегущая строка - IdealImage.ru',
                'ad_telegram': 'Пост в Telegram - IdealImage.ru',
                'ad_pack_start': 'Реклама: Пакет Старт - IdealImage.ru',
                'ad_pack_pro': 'Реклама: Пакет Профи - IdealImage.ru',
            }
            description = purpose_descriptions.get(donation.payment_purpose, f'Услуга {donation.payment_purpose} - IdealImage.ru')
        else:
            description = 'Донат на поддержку IdealImage.ru'

        # Обрабатываем в зависимости от способа оплаты
        if donation.payment_method == 'yandex':
            handler = YandexKassaPayment()
            result = handler.create_payment(
                amount=donation.amount,
                description=description,
                return_url=return_url,
                user_email=donation.user_email,
                metadata={
                    'donation_id': str(donation.id),
                    'user_email': donation.user_email,
                    'payment_purpose': donation.payment_purpose,
                }
            )
            
            if 'error' in result:
                logger.error(f"Ошибка ЮКассы: {result['error']}")
                raise Exception(f"Ошибка ЮКассы: {result['error']}")
            
            logger.info(f"ЮКасса создала платеж: {result}")
            donation.payment_id = result.get('id')
            donation.payment_url = result.get('confirmation', {}).get('confirmation_url')
            donation.payment_data = result
            
            # Генерируем QR-код для оплаты
            if donation.payment_url:
                donation.qr_code = generate_yandex_qr(donation.payment_url)
            
            donation.save()
            
            # Перенаправляем на страницу оплаты
            if donation.payment_url:
                return redirect(donation.payment_url)
            else:
                raise Exception("Не удалось получить ссылку для оплаты от ЮКассы")
        
        elif donation.payment_method == 'sberpay':
            handler = SberPayPayment()
            result = handler.create_payment(
                amount=donation.amount,
                order_number=str(donation.id),
                return_url=return_url,
                description=description,
                user_email=donation.user_email,
            )
            
            if 'error' in result:
                raise Exception(result['error'])
            
            donation.payment_id = result.get('orderId')
            donation.payment_url = result.get('formUrl')
            donation.payment_data = result
            
            # Генерируем QR-код
            if donation.payment_url:
                donation.qr_code = generate_sber_qr(donation.payment_url)
            
            donation.save()
            
            if donation.payment_url:
                return redirect(donation.payment_url)
            else:
                raise Exception("Не удалось получить ссылку для оплаты от Сбербанка")
        
        elif donation.payment_method in ['sbp', 'qr']:
            # Для СБП и QR создаем платеж через выбранный шлюз
            handler = SBPPayment()
            result = handler.create_sbp_payment(
                amount=donation.amount,
                description=description,
                return_url=return_url,
                user_email=donation.user_email,
            )
            
            if 'error' in result:
                raise Exception(result['error'])
            
            donation.payment_id = result.get('id') or result.get('orderId')
            donation.payment_url = result.get('confirmation', {}).get('confirmation_url') or result.get('formUrl')
            donation.payment_data = result
            
            # Генерируем QR-код
            if donation.payment_url:
                donation.qr_code = generate_payment_qr(donation.payment_url)
            
            donation.save()
            
            # Для QR показываем страницу с QR-кодом
            if donation.payment_method == 'qr':
                return redirect('donations:show_qr', donation_id=donation.id)
            else:
                if donation.payment_url:
                    return redirect(donation.payment_url)
                else:
                    raise Exception("Не удалось получить ссылку для оплаты")
        
        else:
            raise Exception(f"Неподдерживаемый метод оплаты: {donation.payment_method}")
    
    except Exception as e:
        logger.error(f"Ошибка создания платежа для доната {donation.id}: {str(e)}")
        donation.status = 'canceled'
        donation.save()
        
        # Возвращаем пользователя на страницу оплаты с ошибкой
        messages.error(request, f'Ошибка создания платежа: {str(e)}')
        
        # Если это была услуга, возвращаем на страницу услуги
        if donation.payment_purpose and donation.payment_purpose != 'donation':
            url = reverse('donations:donation_page') + f'?purpose={donation.payment_purpose}&amount={donation.amount}'
            return redirect(url)
        else:
            return redirect('donations:donation_page')


def show_qr(request, donation_id):
    """Показ QR-кода для оплаты"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    context = {
        'donation': donation,
    }
    
    return render(request, 'donations/show_qr.html', context)


def payment_debug(request):
    """Страница отладки платежей"""
    donations = Donation.objects.all().order_by('-created_at')[:20]
    
    context = {
        'donations': donations,
    }
    
    return render(request, 'donations/payment_debug.html', context)


def payment_return(request, donation_id):
    """Страница возврата после оплаты"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Проверяем статус платежа
    if donation.payment_method == 'yandex':
        handler = YandexKassaPayment()
        if donation.payment_id:
            payment_info = handler.get_payment(donation.payment_id)
            
            if payment_info.get('status') == 'succeeded':
                donation.status = 'succeeded'
                donation.completed_at = timezone.now()
                donation.save()
                
                # Отправляем благодарственное письмо
                try:
                    send_thank_you_email(donation)
                except Exception as e:
                    logger.error(f"Ошибка отправки письма: {str(e)}")
    
    elif donation.payment_method == 'sberpay':
        handler = SberPayPayment()
        if donation.payment_id:
            status_info = handler.get_order_status(donation.payment_id)
            
            order_status = status_info.get('orderStatus')
            if order_status == 2:  # 2 = оплачен
                donation.status = 'succeeded'
                donation.completed_at = timezone.now()
                donation.save()
                
                try:
                    send_thank_you_email(donation)
                except Exception as e:
                    logger.error(f"Ошибка отправки письма: {str(e)}")
    
    return redirect('donations:donation_status', donation_id=donation.id)


def donation_status(request, donation_id):
    """Страница статуса доната"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    context = {
        'donation': donation,
    }
    
    return render(request, 'donations/donation_status.html', context)


@csrf_exempt
@require_POST
def yandex_webhook(request):
    """Webhook для получения уведомлений от Яндекс.Кассы"""
    try:
        payload = json.loads(request.body)
        
        # Логируем webhook
        webhook_log = PaymentWebhookLog.objects.create(
            payment_system='yandex',
            webhook_data=payload,
        )
        
        event = payload.get('event')
        payment_object = payload.get('object', {})
        payment_id = payment_object.get('id')
        
        # Находим донат по payment_id
        try:
            donation = Donation.objects.get(payment_id=payment_id)
            webhook_log.donation = donation
            webhook_log.save()
        except Donation.DoesNotExist:
            logger.error(f"Донат с payment_id {payment_id} не найден")
            webhook_log.error = f"Донат не найден: {payment_id}"
            webhook_log.save()
            return HttpResponse(status=200)
        
        # Обрабатываем события
        if event == 'payment.succeeded':
            donation.status = 'succeeded'
            donation.completed_at = timezone.now()
            donation.payment_data = payment_object
            donation.save()
            
            webhook_log.processed = True
            webhook_log.save()
            
            # Автоматическая активация услуг
            try:
                from .service_activator import service_activator
                activation_result = service_activator.activate_service(donation)
                if activation_result:
                    logger.info(f"Услуга активирована для доната {donation.id}")
                else:
                    logger.warning(f"Не удалось активировать услугу для доната {donation.id}")
            except Exception as e:
                logger.error(f"Ошибка активации услуги для доната {donation.id}: {str(e)}")
            
            # Отправляем уведомления
            try:
                send_thank_you_email(donation)
                send_admin_notification(donation)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомлений: {str(e)}")
        
        elif event == 'payment.canceled':
            donation.status = 'canceled'
            donation.payment_data = payment_object
            donation.save()
            
            webhook_log.processed = True
            webhook_log.save()
        
        elif event == 'refund.succeeded':
            donation.status = 'refunded'
            donation.payment_data = payment_object
            donation.save()
            
            webhook_log.processed = True
            webhook_log.save()
        
        return HttpResponse(status=200)
    
    except Exception as e:
        logger.error(f"Ошибка обработки webhook от ЮKassa: {str(e)}")
        return HttpResponse(status=500)


@csrf_exempt
@require_POST
def sber_webhook(request):
    """Webhook для получения уведомлений от Сбербанка"""
    try:
        # Сбербанк отправляет данные в формате form-data
        data = request.POST.dict()
        
        # Логируем webhook
        webhook_log = PaymentWebhookLog.objects.create(
            payment_system='sberbank',
            webhook_data=data,
        )
        
        order_id = data.get('orderId') or data.get('mdOrder')
        
        # Находим донат
        try:
            donation = Donation.objects.get(payment_id=order_id)
            webhook_log.donation = donation
            webhook_log.save()
        except Donation.DoesNotExist:
            logger.error(f"Донат с payment_id {order_id} не найден")
            webhook_log.error = f"Донат не найден: {order_id}"
            webhook_log.save()
            return HttpResponse(status=200)
        
        # Проверяем статус
        order_status = int(data.get('status', 0))
        
        if order_status == 2:  # Оплачен
            donation.status = 'succeeded'
            donation.completed_at = timezone.now()
            donation.payment_data = data
            donation.save()
            
            webhook_log.processed = True
            webhook_log.save()
            
            # Отправляем уведомления
            try:
                send_thank_you_email(donation)
                send_admin_notification(donation)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомлений: {str(e)}")
        
        elif order_status in [3, 4, 6]:  # Отменен/отклонен
            donation.status = 'canceled'
            donation.payment_data = data
            donation.save()
            
            webhook_log.processed = True
            webhook_log.save()
        
        return HttpResponse(status=200)
    
    except Exception as e:
        logger.error(f"Ошибка обработки webhook от Сбербанка: {str(e)}")
        return HttpResponse(status=500)


def services_page(request):
    """Страница с прайс-листом всех услуг"""
    context = {
        'page_title': 'Услуги и подписки IdealImage.ru',
        'page_description': 'Платформа контента о моде и красоте с премиум-сервисами'
    }
    return render(request, 'donations/services.html', context)

def subscribe_premium_page(request):
    """Страница Premium подписки"""
    return render(request, 'donations/subscribe_premium.html')

def subscribe_ai_page(request):
    """Страница AI-Соавтора"""
    return render(request, 'donations/subscribe_ai_coauthor.html')

def marathons_catalog(request):
    """Каталог марафонов"""
    return render(request, 'donations/marathons_catalog.html')

def advertising_marketplace(request):
    """Витрина рекламы с аукционом"""
    return render(request, 'donations/advertising_marketplace.html')


def donation_list(request):
    """Список всех успешных донатов (публичная страница)"""
    donations = Donation.objects.filter(
        status='succeeded',
        is_anonymous=False
    ).order_by('-completed_at')[:50]
    
    # Подсчет статистики
    total_amount = Donation.objects.filter(status='succeeded').aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    total_count = Donation.objects.filter(status='succeeded').count()
    
    context = {
        'donations': donations,
        'total_amount': total_amount,
        'total_count': total_count,
    }
    
    return render(request, 'donations/donation_list.html', context)


@require_GET
def check_payment_status(request, donation_id):
    """API endpoint для проверки статуса платежа (AJAX)"""
    try:
        donation = get_object_or_404(Donation, id=donation_id)
        
        return JsonResponse({
            'status': donation.status,
            'amount': str(donation.amount),
            'payment_method': donation.get_payment_method_display(),
            'created_at': donation.created_at.isoformat(),
            'completed_at': donation.completed_at.isoformat() if donation.completed_at else None,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================
# Страницы системы бонусов
# ============================================

def author_bonuses_page(request):
    """Страница бонусов для авторов - редирект в личный кабинет"""
    if not request.user.is_authenticated:
        return redirect('Visitor:user-login')
    
    # Редирект в личный кабинет, где теперь отображаются все бонусы
    return redirect('Visitor:personal_cabinet')


def admin_bonuses_dashboard(request):
    """Дашборд бонусов для администратора"""
    if not request.user.is_staff:
        return redirect('Visitor:user-login')
    
    # Текущая неделя (живая статистика)
    current_week = get_current_week_summary()
    week_start, week_end = get_week_boundaries()
    
    # Последний зафиксированный отчет
    latest_report = WeeklyReport.objects.filter(
        is_finalized=True
    ).order_by('-week_start').first()
    
    # Все авторы со статистикой за текущую неделю
    authors_stats = AuthorStats.objects.filter(
        period_type='week',
        period_start__gte=week_start
    ).select_related('author', 'current_role').order_by('-calculated_points')
    
    # Все донаты за текущую неделю
    week_donations = Donation.objects.filter(
        status='succeeded',
        completed_at__gte=week_start,
        completed_at__lt=week_end
    ).select_related('article', 'article_author').order_by('-completed_at')
    
    # Все роли с формулами для виджета
    all_roles = AuthorRole.objects.all().select_related('formula').order_by('level')
    
    # Статистика по ролям
    roles_stats = []
    for role in all_roles:
        authors_count = authors_stats.filter(current_role=role).count()
        roles_stats.append({
            'role': role,
            'authors_count': authors_count
        })
    
    # Неоплаченные выплаты
    pending_payments = BonusPaymentRegistry.objects.filter(
        status__in=['pending', 'partial']
    ).select_related('author', 'week_report').order_by('-created_at')[:10]
    
    # Недавние штрафы/премии
    recent_adjustments = AuthorPenaltyReward.objects.filter(
        is_active=True
    ).select_related('author', 'created_by').order_by('-created_at')[:10]
    
    context = {
        'page_title': 'Дашборд бонусов - Админ панель',
        'page_description': 'Управление системой бонусов для авторов IdealImage.ru',
        'current_week': current_week,
        'week_start': week_start,
        'week_end': week_end,
        'latest_report': latest_report,
        'authors_stats': authors_stats,
        'week_donations': week_donations,
        'roles_stats': roles_stats,
        'pending_payments': pending_payments,
        'recent_adjustments': recent_adjustments,
        'all_roles': all_roles,
    }
    
    return render(request, 'donations/admin_bonuses_dashboard.html', context)


def payment_registry_page(request):
    """Страница реестра выплат"""
    if not request.user.is_staff:
        return redirect('Visitor:user-login')
    
    # Получаем week_id из GET параметров
    week_id = request.GET.get('week_id')
    
    # Все недельные отчеты
    all_reports = WeeklyReport.objects.all().order_by('-week_start')
    
    # Выбранный отчет
    selected_report = None
    registry_entries = []
    
    if week_id:
        selected_report = get_object_or_404(WeeklyReport, id=week_id)
        registry_entries = BonusPaymentRegistry.objects.filter(
            week_report=selected_report
        ).select_related('author', 'bonus').order_by('author__username')
    elif all_reports.exists():
        # По умолчанию показываем последний отчет
        selected_report = all_reports.first()
        if selected_report:
            registry_entries = BonusPaymentRegistry.objects.filter(
                week_report=selected_report
            ).select_related('author', 'bonus').order_by('author__username')
    
    # Статистика по выплатам
    if selected_report:
        total_to_pay = registry_entries.aggregate(
            total=models.Sum('amount_to_pay')
        )['total'] or Decimal('0.00')
        
        total_paid = registry_entries.aggregate(
            total=models.Sum('paid_amount')
        )['total'] or Decimal('0.00')
        
        payment_stats = {
            'total_entries': registry_entries.count(),
            'total_to_pay': total_to_pay,
            'total_paid': total_paid,
            'total_remaining': total_to_pay - total_paid,
            'paid_count': registry_entries.filter(status='paid').count(),
            'pending_count': registry_entries.filter(status='pending').count(),
            'partial_count': registry_entries.filter(status='partial').count(),
        }
    else:
        payment_stats = None
    
    context = {
        'page_title': 'Реестр выплат - Админ панель',
        'page_description': 'Реестр выплат бонусов авторам IdealImage.ru',
        'all_reports': all_reports,
        'selected_report': selected_report,
        'registry_entries': registry_entries,
        'payment_stats': payment_stats,
    }
    
    return render(request, 'donations/payment_registry.html', context)


@login_required
def api_author_bonuses(request):
    """API для загрузки бонусов с пагинацией (AJAX)"""
    from django.core.paginator import Paginator
    
    page_number = request.GET.get('page', 1)
    bonuses = AuthorBonus.objects.filter(
        author=request.user
    ).select_related('role_at_calculation').order_by('-created_at')
    
    paginator = Paginator(bonuses, 20)
    page_obj = paginator.get_page(page_number)
    
    data = {
        'bonuses': [{
            'id': b.id,
            'period': f"{b.period_start.strftime('%d.%m')} - {b.period_end.strftime('%d.%m.%Y')}",
            'total_bonus': float(b.total_bonus),
            'created_at': b.created_at.strftime('%d.%m.%Y %H:%M'),
            'status': b.get_status_display(),
        } for b in page_obj],
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
    }
    
    return JsonResponse(data)


@login_required
def api_bonus_details(request, bonus_id):
    """API: Детальная информация о бонусе для модального окна"""
    bonus = get_object_or_404(AuthorBonus, id=bonus_id, author=request.user)
    
    data = {
        'id': bonus.id,
        'week': f"{bonus.period_start.strftime('%d.%m')} - {bonus.period_end.strftime('%d.%m.%Y')}",
        'total_bonus': float(bonus.total_bonus),
        'created_at': bonus.created_at.strftime('%d.%m.%Y %H:%M'),
        'status': bonus.get_status_display(),
        'details': {
            'calculated_bonus': float(bonus.calculated_bonus),  # От донатов
            'tasks_reward': float(bonus.tasks_reward),  # За задания
            'bonus_from_points': float(bonus.bonus_from_points),  # Из баллов
            'points_earned': float(bonus.points_earned),  # Заработанные баллы
        }
    }
    
    return JsonResponse(data)


@login_required
def penalty_reward_create(request):
    """Создание штрафа/премии для автора"""
    if not request.user.is_staff:
        return redirect('Home:home')
    
    if request.method == 'POST':
        form = AuthorPenaltyRewardForm(request.POST)
        if form.is_valid():
            penalty_reward = form.save(commit=False)
            penalty_reward.created_by = request.user
            penalty_reward.save()
            
            type_name = 'Штраф' if penalty_reward.type == 'penalty' else 'Премия'
            messages.success(request, f'{type_name} для {penalty_reward.author.username} создан')
            return redirect('Home:master_admin_dashboard')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = AuthorPenaltyRewardForm()
    
    context = {
        'page_title': 'Создание штрафа/премии - IdealImage.ru',
        'page_description': 'Назначение штрафа или премии автору',
        'form': form,
    }
    
    return render(request, 'donations/penalty_reward_form.html', context)


@login_required
def penalty_reward_edit(request, pr_id):
    """Редактирование штрафа/премии"""
    if not request.user.is_staff:
        return redirect('Home:home')
    
    penalty_reward = get_object_or_404(AuthorPenaltyReward, id=pr_id)
    
    if request.method == 'POST':
        form = AuthorPenaltyRewardForm(request.POST, instance=penalty_reward)
        if form.is_valid():
            penalty_reward = form.save()
            
            type_name = 'Штраф' if penalty_reward.type == 'penalty' else 'Премия'
            messages.success(request, f'{type_name} обновлен')
            return redirect('Home:master_admin_dashboard')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = AuthorPenaltyRewardForm(instance=penalty_reward)
    
    context = {
        'page_title': f'Редактирование - IdealImage.ru',
        'page_description': 'Редактирование штрафа/премии',
        'form': form,
        'penalty_reward': penalty_reward,
    }
    
    return render(request, 'donations/penalty_reward_form.html', context)
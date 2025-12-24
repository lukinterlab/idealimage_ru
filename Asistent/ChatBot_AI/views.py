"""
Views для чат-бота

API endpoints для обработки сообщений пользователей
"""

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings as django_settings
from datetime import timedelta
import json
import time
import logging

from .models import ChatbotSettings, ChatMessage
from .services import FAQSearchService, ArticleSearchService, ResponseFormatter
from .services.semantic_search import SemanticSearchService
from .config import AI_PROVIDER
from .utils import get_client_ip

logger = logging.getLogger(__name__)


@require_POST
def chatbot_message(request):
    """Обработка сообщения от пользователя в чат-боте"""
    
    start_time = time.time()
    
    try:
        # Получаем настройки чат-бота
        settings = ChatbotSettings.objects.first()
        
        # Проверка активности
        if not settings or not settings.is_active:
            return JsonResponse({
                'error': 'Чат-бот временно недоступен. Попробуйте позже.',
                'show_contact_form': True
            }, status=503)
        
        # Получаем или создаем ключ сессии
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        
        # Rate limiting - проверка лимита сообщений
        hour_ago = timezone.now() - timedelta(hours=1)
        recent_count = ChatMessage.objects.filter(
            session_key=session_key,
            created_at__gte=hour_ago
        ).count()
        
        if recent_count >= settings.rate_limit_messages:
            return JsonResponse({
                'error': f'Превышен лимит сообщений ({settings.rate_limit_messages} в час). Попробуйте позже или свяжитесь с администратором.',
                'show_contact_form': True
            }, status=429)
        
        # Получаем сообщение пользователя
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Сообщение не может быть пустым'}, status=400)
        
        if len(message) > 1000:
            return JsonResponse({'error': 'Сообщение слишком длинное (макс. 1000 символов)'}, status=400)
        
        response_text = ""
        source = "error"
        found_articles_data = []
        
        # 🚀 ПРИОРИТЕТ 1: GigaChat ПЕРВЫМ (не экономим токены!)
        if settings.use_ai:
            try:
                logger.info(f"🤖 GigaChat: обрабатываем запрос первым")
                ai_provider = AI_PROVIDER()
                ai_response = ai_provider.get_response(
                    prompt=message,
                    system_prompt=settings.system_prompt
                )
                if ai_response and ai_response.get('success'):
                    response_text = ai_response.get('text', '')
                    source = 'ai'
                    logger.info(f"✅ GigaChat: ответ получен ({len(response_text)} символов)")
                else:
                    logger.warning(f"⚠️ GigaChat: пустой ответ")
            except Exception as e:
                logger.error(f"❌ GigaChat: ошибка - {e}")
        
        # FALLBACK 1: Если GigaChat не справился - ищем в FAQ
        if not response_text:
            logger.info(f"🔍 FAQ: GigaChat не ответил, ищем в FAQ")
            faq_result = SemanticSearchService.hybrid_search_faq(message)
            if faq_result:
                response_text = faq_result['answer']
                source = 'faq'
                if faq_result.get('url'):
                    response_text += f"\n\n🔗 <a href='{faq_result['url']}' target='_blank'>Подробнее здесь</a>"
                
                # Увеличиваем счетчик использования
                faq_result['faq_obj'].increment_usage()
                logger.info(f"✅ FAQ: найден ответ")
        
        # FALLBACK 2: Если FAQ не нашёл - ищем в статьях
        if not response_text and settings.search_articles:
            logger.info(f"📚 Статьи: FAQ не нашёл, ищем в статьях")
            article_service = ArticleSearchService()
            articles = article_service.search(message, settings.max_search_results)
            if articles:
                response_text = ResponseFormatter.format_articles(articles)
                source = 'article_search'
                # Преобразуем в формат для found_articles_data
                for article in articles:
                    if isinstance(article, dict):
                        found_articles_data.append(article)
                    else:
                        found_articles_data.append({
                            'id': article.id,
                            'title': article.title,
                            'url': article.get_absolute_url()
                        })
                logger.info(f"✅ Статьи: найдено {len(articles)} статей")
        
        # FALLBACK 3: Если ничего не помогло - предлагаем связаться с админом
        if not response_text:
            logger.warning(f"⚠️ Ничего не найдено: предлагаем контакт с админом")
            response_text = ResponseFormatter.format_error()
            source = 'error'
        
        # Сохраняем сообщение в историю
        processing_time = time.time() - start_time
        chat_message = ChatMessage.objects.create(
            session_key=session_key,
            user=request.user if request.user.is_authenticated else None,
            message=message,
            response=response_text,
            source=source,
            found_articles=found_articles_data,
            processing_time=processing_time,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        logger.info(f"💬 Чат-бот: {session_key[:8]}... | {source} | {processing_time:.2f}s")
        
        return JsonResponse({
            'success': True,
            'response': response_text,
            'source': source,
            'articles': found_articles_data,
            'show_contact_form': source == 'error' and settings.admin_contact_enabled,
            'processing_time': processing_time
        })
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения чат-бота: {e}")
        return JsonResponse({
            'error': 'Произошла ошибка. Попробуйте позже.',
            'show_contact_form': True
        }, status=500)


@require_POST
def contact_admin_from_chat(request):
    """Отправка сообщения администратору из чат-бота"""
    
    try:
        settings = ChatbotSettings.objects.first()
        
        if not settings or not settings.admin_contact_enabled:
            return JsonResponse({'error': 'Функция отключена'}, status=403)
        
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        
        # Валидация
        if not name or not email or not message:
            return JsonResponse({'error': 'Все поля обязательны'}, status=400)
        
        if len(message) > 2000:
            return JsonResponse({'error': 'Сообщение слишком длинное'}, status=400)
        
        # Формируем письмо
        email_subject = f'Обращение через чат-бот от {name}'
        email_body = f"""
            Новое обращение через чат-бот на сайте IdealImage.ru

            От: {name}
            Email: {email}

            Сообщение:
            {message}

            ---
            Отправлено: {timezone.now().strftime('%d.%m.%Y %H:%M')}
            IP: {request.META.get('REMOTE_ADDR', 'не определен')}
            """
        
        # Отправляем email
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.admin_email],
            fail_silently=False,
        )
        
        logger.info(f"📧 Отправлено сообщение админу от {name} ({email})")
        
        return JsonResponse({
            'success': True,
            'message': 'Спасибо! Ваше сообщение отправлено администратору. Мы свяжемся с вами в ближайшее время.'
        })
        
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения админу: {e}")
        return JsonResponse({
            'error': 'Ошибка отправки сообщения. Попробуйте позже.',
        }, status=500)


def get_chatbot_settings_api(request):
    """API для получения настроек чат-бота (приветствие и т.д.)"""
    
    try:
        settings = ChatbotSettings.objects.first()
        
        if not settings:
            # Создаем настройки по умолчанию
            settings = ChatbotSettings.objects.create()
        
        return JsonResponse({
            'is_active': settings.is_active,
            'welcome_message': settings.welcome_message,
            'admin_contact_enabled': settings.admin_contact_enabled,
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения настроек чат-бота: {e}")
        return JsonResponse({
            'is_active': False,
            'welcome_message': 'Здравствуйте! 👋',
            'admin_contact_enabled': True,
        })


"""
WebSocket consumers для отображения прогресса генерации статей.
Использует Django Channels для real-time обновлений.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class PromptTestProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для отображения прогресса тестирования промпта.
    
    Подключение: ws://localhost:8000/ws/prompt-test/{template_id}/
    """
    
    async def connect(self):
        """Подключение клиента"""
        self.template_id = self.scope['url_route']['kwargs']['template_id']
        self.room_group_name = f'prompt_test_{self.template_id}'
        
        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket подключен: template_id={self.template_id}")
        
        # Отправляем приветственное сообщение
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Подключено к серверу прогресса'
        }))
    
    async def disconnect(self, close_code):
        """Отключение клиента"""
        # Покидаем группу
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket отключен: template_id={self.template_id}, code={close_code}")
    
    async def receive(self, text_data):
        """Получение сообщения от клиента (не используется)"""
        pass
    
    # Обработчики событий от сервера
    
    async def generation_progress(self, event):
        """Отправка прогресса генерации клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'progress',
            'step': event['step'],
            'percentage': event['percentage']
        }))
    
    async def generation_complete(self, event):
        """Уведомление о завершении генерации"""
        await self.send(text_data=json.dumps({
            'type': 'complete',
            'success': event.get('success', True),
            'message': event.get('message', 'Генерация завершена')
        }))
    
    async def generation_error(self, event):
        """Уведомление об ошибке"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': event.get('message', 'Произошла ошибка')
        }))


class ProgressSender:
    """
    Хелпер для отправки прогресса через WebSocket.
    Используется в Orchestrator.
    """
    
    def __init__(self, template_id: int):
        self.template_id = template_id
        self.room_group_name = f'prompt_test_{template_id}'
    
    def send_progress(self, step: str, percentage: int):
        """Отправка прогресса"""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'generation.progress',
                        'step': step,
                        'percentage': percentage
                    }
                )
                logger.debug(f"📡 Прогресс отправлен: {step} ({percentage}%)")
        except Exception as e:
            logger.warning(f"Не удалось отправить прогресс: {e}")
    
    def send_complete(self, success: bool = True, message: str = ''):
        """Отправка уведомления о завершении"""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'generation.complete',
                        'success': success,
                        'message': message or ('Генерация завершена' if success else 'Ошибка генерации')
                    }
                )
                logger.info(f"📡 Завершение отправлено: success={success}")
        except Exception as e:
            logger.warning(f"Не удалось отправить завершение: {e}")
    
    def send_error(self, message: str):
        """Отправка уведомления об ошибке"""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'generation.error',
                        'message': message
                    }
                )
                logger.error(f"📡 Ошибка отправлена: {message[:50]}")
        except Exception as e:
            logger.warning(f"Не удалось отправить ошибку: {e}")


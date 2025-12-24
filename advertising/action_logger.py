"""
Модуль для логирования действий с рекламой
"""
from .models import AdActionLog


class AdActionLogger:
    """Класс для удобного логирования действий с рекламой"""
    
    @staticmethod
    def log_action(action_type, target_type, target_id, target_name='', 
                   description='', performed_by=None, performed_by_ai=False,
                   old_data=None, new_data=None, can_revert=True):
        """
        Создать запись в журнале действий
        
        Args:
            action_type: тип действия ('create', 'update', 'delete', и т.д.)
            target_type: тип объекта ('banner', 'context_ad', и т.д.)
            target_id: ID объекта
            target_name: название объекта (для удобства)
            description: описание действия
            performed_by: пользователь (User объект)
            performed_by_ai: True если действие выполнено AI
            old_data: старые данные (dict)
            new_data: новые данные (dict)
            can_revert: можно ли отменить действие
        
        Returns:
            AdActionLog объект
        """
        log = AdActionLog.objects.create(
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            description=description,
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            old_data=old_data,
            new_data=new_data,
            can_revert=can_revert
        )
        return log
    
    @staticmethod
    def log_banner_create(banner, performed_by=None, performed_by_ai=False):
        """Логировать создание баннера"""
        return AdActionLogger.log_action(
            action_type='create',
            target_type='banner',
            target_id=banner.id,
            target_name=banner.name,
            description=f'Создан баннер "{banner.name}" для места "{banner.place.name}"',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            new_data={
                'name': banner.name,
                'place': banner.place.code,
                'banner_type': banner.banner_type,
                'is_active': banner.is_active,
                'use_external_code': banner.use_external_code,
            }
        )
    
    @staticmethod
    def log_banner_update(banner, old_values, performed_by=None, performed_by_ai=False):
        """Логировать изменение баннера"""
        new_values = {
            'name': banner.name,
            'is_active': banner.is_active,
            'priority': banner.priority,
            'use_external_code': banner.use_external_code,
        }
        
        changes = []
        for key in old_values:
            if key in new_values and old_values[key] != new_values[key]:
                changes.append(f"{key}: {old_values[key]} → {new_values[key]}")
        
        description = f'Изменён баннер "{banner.name}". ' + ', '.join(changes)
        
        return AdActionLogger.log_action(
            action_type='update',
            target_type='banner',
            target_id=banner.id,
            target_name=banner.name,
            description=description,
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            old_data=old_values,
            new_data=new_values
        )
    
    @staticmethod
    def log_banner_activate(banner, performed_by=None, performed_by_ai=False):
        """Логировать активацию баннера"""
        return AdActionLogger.log_action(
            action_type='activate',
            target_type='banner',
            target_id=banner.id,
            target_name=banner.name,
            description=f'Активирован баннер "{banner.name}"',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            old_data={'is_active': False},
            new_data={'is_active': True}
        )
    
    @staticmethod
    def log_banner_deactivate(banner, performed_by=None, performed_by_ai=False):
        """Логировать деактивацию баннера"""
        return AdActionLogger.log_action(
            action_type='deactivate',
            target_type='banner',
            target_id=banner.id,
            target_name=banner.name,
            description=f'Деактивирован баннер "{banner.name}"',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            old_data={'is_active': True},
            new_data={'is_active': False}
        )
    
    @staticmethod
    def log_banner_delete(banner_id, banner_name, performed_by=None, performed_by_ai=False):
        """Логировать удаление баннера"""
        return AdActionLogger.log_action(
            action_type='delete',
            target_type='banner',
            target_id=banner_id,
            target_name=banner_name,
            description=f'Удалён баннер "{banner_name}"',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            can_revert=False  # Удаление нельзя отменить
        )
    
    @staticmethod
    def log_context_ad_insert(insertion, performed_by=None, performed_by_ai=False):
        """Логировать вставку контекстной рекламы в статью"""
        return AdActionLogger.log_action(
            action_type='insert',
            target_type='insertion',
            target_id=insertion.id,
            target_name=f"{insertion.context_ad.anchor_text} в {insertion.post.title}",
            description=f'Вставлена реклама "{insertion.context_ad.anchor_text}" в статью "{insertion.post.title}"',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            new_data={
                'context_ad_id': insertion.context_ad.id,
                'post_id': insertion.post.id,
                'position': insertion.insertion_position,
            }
        )
    
    @staticmethod
    def log_context_ad_remove(insertion, performed_by=None, performed_by_ai=False):
        """Логировать удаление контекстной рекламы из статьи"""
        return AdActionLogger.log_action(
            action_type='remove',
            target_type='insertion',
            target_id=insertion.id,
            target_name=f"{insertion.context_ad.anchor_text} из {insertion.post.title}",
            description=f'Удалена реклама "{insertion.context_ad.anchor_text}" из статьи "{insertion.post.title}"',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            old_data={
                'context_ad_id': insertion.context_ad.id,
                'post_id': insertion.post.id,
            }
        )
    
    # ============ ЛОГИРОВАНИЕ ВНЕШНИХ СКРИПТОВ ============
    
    @staticmethod
    def log_external_script_create(script, performed_by=None, performed_by_ai=False):
        """Логировать создание внешнего скрипта"""
        return AdActionLogger.log_action(
            action_type='create',
            target_type='external_script',
            target_id=script.id,
            target_name=script.name,
            description=f'Создан внешний скрипт "{script.name}" ({script.get_script_type_display()}) от {script.provider or "неизвестный"}',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            new_data={
                'name': script.name,
                'script_type': script.script_type,
                'provider': script.provider,
                'position': script.position,
                'is_active': script.is_active,
            }
        )
    
    @staticmethod
    def log_external_script_update(script, old_values, performed_by=None, performed_by_ai=False):
        """Логировать изменение внешнего скрипта"""
        new_values = {
            'name': script.name,
            'script_type': script.script_type,
            'provider': script.provider,
            'position': script.position,
            'priority': script.priority,
            'is_active': script.is_active,
        }
        
        changes = []
        for key in old_values:
            if key in new_values and old_values[key] != new_values[key]:
                changes.append(f"{key}: {old_values[key]} → {new_values[key]}")
        
        description = f'Изменён внешний скрипт "{script.name}". ' + ', '.join(changes) if changes else f'Обновлён внешний скрипт "{script.name}"'
        
        return AdActionLogger.log_action(
            action_type='update',
            target_type='external_script',
            target_id=script.id,
            target_name=script.name,
            description=description,
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            old_data=old_values,
            new_data=new_values
        )
    
    @staticmethod
    def log_external_script_activate(script, performed_by=None, performed_by_ai=False):
        """Логировать активацию внешнего скрипта"""
        return AdActionLogger.log_action(
            action_type='activate',
            target_type='external_script',
            target_id=script.id,
            target_name=script.name,
            description=f'Активирован внешний скрипт "{script.name}" ({script.get_script_type_display()})',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            old_data={'is_active': False},
            new_data={'is_active': True}
        )
    
    @staticmethod
    def log_external_script_deactivate(script, performed_by=None, performed_by_ai=False):
        """Логировать деактивацию внешнего скрипта"""
        return AdActionLogger.log_action(
            action_type='deactivate',
            target_type='external_script',
            target_id=script.id,
            target_name=script.name,
            description=f'Деактивирован внешний скрипт "{script.name}" ({script.get_script_type_display()})',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            old_data={'is_active': True},
            new_data={'is_active': False}
        )
    
    @staticmethod
    def log_external_script_delete(script_id, script_name, script_type, performed_by=None, performed_by_ai=False):
        """Логировать удаление внешнего скрипта"""
        return AdActionLogger.log_action(
            action_type='delete',
            target_type='external_script',
            target_id=script_id,
            target_name=script_name,
            description=f'Удалён внешний скрипт "{script_name}" ({script_type})',
            performed_by=performed_by,
            performed_by_ai=performed_by_ai,
            can_revert=False  # Удаление нельзя отменить
        )


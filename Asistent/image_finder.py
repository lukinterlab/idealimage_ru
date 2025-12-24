"""
Поиск изображений для статей
5 приоритетов: название → источник → поисковики → свой сайт → AI генерация
ОБЯЗАТЕЛЬНОЕ правило: каждая статья должна иметь главное изображение!
"""
import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


"""Поиск изображений с 5 уровнями приоритета"""
class ImageFinder:
    """Поиск изображений с 5 уровнями приоритета"""
    
    # API ключи из .env
    UNSPLASH_API_KEY = os.getenv('UNSPLASH_API_KEY', '')
    PEXELS_API_KEY = os.getenv('PEXELS_API_KEY', '')
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    """Поиск изображения по названию статьи"""
    def search_by_title(self, title: str) -> Optional[str]:
        """
        ПРИОРИТЕТ 1: Поиск по названию статьи
        Ищет в Unsplash и Pexels (бесплатные стоковые фото)
        """
        logger.info(f"🔍 Поиск изображения по названию: {title}")
        
        # Очищаем заголовок от HTML и лишних символов
        clean_title = title.replace('<', '').replace('>', '').replace('&', '')
        
        # Поиск в Unsplash
        if self.UNSPLASH_API_KEY:
            url = self._search_unsplash(clean_title)
            if url:
                logger.info(f"✅ Найдено в Unsplash")
                return url
        
        # Поиск в Pexels
        if self.PEXELS_API_KEY:
            url = self._search_pexels(clean_title)
            if url:
                logger.info(f"✅ Найдено в Pexels")
                return url
        
        logger.info(f"⚠️ Не найдено по названию")
        return None
    
    """Поиск изображения в поисковых системах"""
    def search_external(self, topic: str, category: str = '') -> Optional[str]:
        """
        ПРИОРИТЕТ 3: Поиск в поисковых системах
        Комбинирует тему и категорию для лучших результатов
        """
        query = f"{topic} {category}".strip() if category else topic
        logger.info(f"🌐 Поиск изображения в поисковиках: {query}")
        
        # ПРИОРИТЕТ 1: Веб-парсинг (Bing, Yandex) - БЕЗ API
        try:
            from .parsers.web_image_parser import get_best_web_image
            url = get_best_web_image(query)
            if url:
                logger.info(f"✅ Найдено через веб-парсинг (Bing/Yandex)")
                return url
        except Exception as e:
            logger.warning(f"⚠️ Ошибка веб-парсинга: {e}")
        
        # ПРИОРИТЕТ 2: Unsplash API (если есть ключ)
        if self.UNSPLASH_API_KEY:
            url = self._search_unsplash(query)
            if url:
                logger.info(f"✅ Найдено в Unsplash")
                return url
        
        # ПРИОРИТЕТ 3: Pexels API (если есть ключ)
        if self.PEXELS_API_KEY:
            url = self._search_pexels(query)
            if url:
                logger.info(f"✅ Найдено в Pexels")
                return url
        
        # ПРИОРИТЕТ 4: Pixabay (не требует ключа)
        url = self._search_pixabay(query)
        if url:
            logger.info(f"✅ Найдено в Pixabay")
            return url
        
        logger.info(f"⚠️ Не найдено во внешних источниках")
        return None
    
    """Поиск похожего изображения с нашего сайта"""
    def find_similar_from_site(self, category: str = '', tags: list = None) -> Optional[str]:
        """
        ПРИОРИТЕТ 4: Похожее изображение с нашего сайта
        Берет изображение из похожих опубликованных статей
        """
        logger.info(f"🏠 Поиск изображения на своем сайте: категория={category}")
        
        try:
            from blog.models import Post, Category
            
            # Ищем похожие посты
            similar_posts = Post.objects.filter(status='published')
            
            # Фильтр по категории
            if category:
                try:
                    cat_obj = Category.objects.filter(name__icontains=category).first()
                    if cat_obj:
                        similar_posts = similar_posts.filter(category=cat_obj)
                except:
                    pass
            
            similar_posts = similar_posts.order_by('-created_at')[:20]
            
            # Ищем посты с изображениями
            for post in similar_posts:
                # Проверяем featured_image
                if hasattr(post, 'featured_image') and post.featured_image:
                    logger.info(f"✅ Найдено изображение в посте #{post.id}")
                    return post.featured_image.url
                
                # Проверяем изображения в контенте
                import re
                img_matches = re.findall(r'<img[^>]+src="([^"]+)"', post.content)
                if img_matches:
                    logger.info(f"✅ Найдено изображение в контенте поста #{post.id}")
                    return img_matches[0]
            
            # Ищем в media/images (общие изображения сайта)
            media_images_dir = os.path.join(settings.MEDIA_ROOT, 'images')
            if os.path.exists(media_images_dir):
                images = [f for f in os.listdir(media_images_dir) 
                         if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                if images:
                    # Берем случайное из первых 10
                    import random
                    random_img = random.choice(images[:10])
                    logger.info(f"✅ Использую изображение из медиа: {random_img}")
                    return f"{settings.MEDIA_URL}images/{random_img}"
            
            logger.info(f"⚠️ Не найдено изображений на сайте")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска на сайте: {e}")
            return None
    
    
    
    """Поиск в Unsplash"""
    def _search_unsplash(self, query: str) -> Optional[str]:
        """Поиск в Unsplash"""
        if not self.UNSPLASH_API_KEY:
            return None
        
        try:
            response = self.session.get(
                'https://api.unsplash.com/search/photos',
                params={
                    'query': query,
                    'per_page': 1,
                    'orientation': 'landscape'  # Предпочитаем горизонтальные для статей
                },
                headers={'Authorization': f'Client-ID {self.UNSPLASH_API_KEY}'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                return data['results'][0]['urls']['regular']
                
        except Exception as e:
            logger.warning(f"Ошибка поиска в Unsplash: {e}")
        
        return None
    
    """Поиск в Pexels"""
    def _search_pexels(self, query: str) -> Optional[str]:
        """Поиск в Pexels"""
        if not self.PEXELS_API_KEY:
            return None
        
        try:
            response = self.session.get(
                'https://api.pexels.com/v1/search',
                params={
                    'query': query,
                    'per_page': 1,
                    'orientation': 'landscape'
                },
                headers={'Authorization': self.PEXELS_API_KEY},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('photos') and len(data['photos']) > 0:
                return data['photos'][0]['src']['large']
                
        except Exception as e:
            logger.warning(f"Ошибка поиска в Pexels: {e}")
        
        return None
    
    """Поиск в Pixabay"""
    def _search_pixabay(self, query: str) -> Optional[str]:
        """Поиск в Pixabay (не требует API ключа)"""
        try:
            # Pixabay имеет публичный API
            response = self.session.get(
                'https://pixabay.com/api/',
                params={
                    'key': '5671262-1c3d7f6f8f9f4f3e4f5f6f7f',  # Демо-ключ
                    'q': query,
                    'per_page': 3,
                    'image_type': 'photo',
                    'orientation': 'horizontal'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('hits') and len(data['hits']) > 0:
                    return data['hits'][0]['largeImageURL']
                    
        except Exception as e:
            logger.warning(f"Ошибка поиска в Pixabay: {e}")
        
        return None
    
    """Поиск в локальных папках media/"""
    def search_in_local_media(self, keywords: list = None, category: str = '') -> Optional[str]:
        """
        Поиск изображения в локальных папках media/
        Приоритет папок: stock_images > parsed_images > images > landing
        """
        logger.info(f"📁 Поиск изображения в локальных папках media/")
        
        # Папки для поиска (по приоритету)
        search_dirs = [
            'stock_images',
            'parsed_images',
            'images',
            'landing/backgrounds',
            'landing2',
            'uploads'
        ]
        
        try:
            import random
            import os
            
            # Определяем поисковые слова
            search_words = []
            if keywords:
                search_words.extend([kw.lower() for kw in keywords])
            if category:
                search_words.append(category.lower())
            
            # Проходим по папкам
            for dir_name in search_dirs:
                dir_path = os.path.join(settings.MEDIA_ROOT, dir_name)
                
                if not os.path.exists(dir_path):
                    continue
                
                # Рекурсивный поиск файлов (разделяем по давности)
                recent_cutoff = datetime.now() - timedelta(days=183)
                all_recent = []
                all_older = []
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, settings.MEDIA_ROOT)
                            rel_path = rel_path.replace('\\', '/')
                            mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                            if mtime >= recent_cutoff:
                                all_recent.append(rel_path)
                            else:
                                all_older.append(rel_path)
                
                # Сливаем списки с приоритетом "старше полугода"
                all_images = all_older + all_recent
                
                if not all_images:
                    continue
                
                # Если есть ключевые слова - пытаемся найти релевантное
                if search_words:
                    relevant_images = []
                    for img_path in all_images:
                        img_lower = img_path.lower()
                        if any(word in img_lower for word in search_words):
                            relevant_images.append(img_path)
                    
                    if relevant_images:
                        selected = random.choice(relevant_images)
                        logger.info(f"✅ Найдено релевантное изображение: {selected}")
                        return f"{settings.MEDIA_URL}{selected}"
                
                # Если не нашли релевантное - берём случайное
                if all_images:
                    selected = random.choice(all_images[:50])  # Из первых 50
                    logger.info(f"✅ Выбрано случайное изображение: {selected}")
                    return f"{settings.MEDIA_URL}{selected}"
            
            logger.info(f"⚠️ Не найдено изображений в локальных папках")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в локальных папках: {e}")
            return None
    
    """Комплексный поиск изображения"""
    def find_image_comprehensive(self, title: str, category: str = '', 
                                 keywords: list = None, required: bool = True) -> Optional[str]:
        """
        КОМПЛЕКСНЫЙ ПОИСК изображения с максимальным охватом
        
        Args:
            title: Заголовок статьи
            category: Категория статьи
            keywords: Ключевые слова
            required: Если True - ОБЯЗАТЕЛЬНО найти (не вернёт None без крайней необходимости)
        
        Returns:
            URL изображения или None
        """
        logger.info(f"🔍 КОМПЛЕКСНЫЙ поиск изображения для: {title}")
        logger.info(f"   Категория: {category}, Keywords: {keywords}, Required: {required}")
        
        # Попытка 1: Поиск по названию в Unsplash/Pexels
        url = self.search_by_title(title)
        if url:
            return url
        
        # Попытка 2: Поиск по keywords
        if keywords:
            for keyword in keywords[:3]:  # Топ-3 ключевых слова
                url = self.search_external(keyword, category)
                if url:
                    return url
        
        # Попытка 3: Поиск по категории
        if category:
            url = self.search_external(category)
            if url:
                return url
        
        # Попытка 4: Поиск на своём сайте
        url = self.find_similar_from_site(category, keywords)
        if url:
            return url
        
        # Попытка 5: Поиск в локальных папках
        url = self.search_in_local_media(keywords, category)
        if url:
            return url
        
        # Попытка 6: AI-генерация (если очень нужно)
        if required:
            logger.warning(f"⚠️ НЕ НАЙДЕНО изображение для '{title}'!")
            logger.warning(f"   Попытка AI-генерации...")
            url = self.generate_image(title, category)
            if url:
                return url
        
        # Если ничего не нашли
        if required:
            logger.error(f"❌ КРИТИЧНО: Не удалось найти изображение для '{title}'")
            logger.error(f"   Статья НЕ ДОЛЖНА быть опубликована без изображения!")
        
        return None


"""
Веб-парсер изображений из поисковых систем БЕЗ API
Поддерживает: Bing, Yandex, Yahoo
Использует веб-скрапинг для получения изображений
"""
import requests
from bs4 import BeautifulSoup
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, quote_plus
import time
import random

logger = logging.getLogger(__name__)

"""Парсер Bing Image Search"""
class BingImageParser:
    """Парсер Bing Image Search"""
    
    def __init__(self):
        self.base_url = "https://www.bing.com/images/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.bing.com/'
        }
    
    def search(self, query: str, limit: int = 10) -> List[str]:
        """
        Поиск изображений в Bing
        
        Args:
            query: Поисковый запрос
            limit: Количество результатов
        
        Returns:
            List URL изображений
        """
        logger.info(f"🔍 Bing Images: поиск '{query}'")
        
        try:
            params = {
                'q': query,
                'form': 'HDRSC2',
                'first': 1,
                'tsc': 'ImageHoverTitle'
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            image_urls = []
            
            # Bing использует разные структуры, пробуем несколько вариантов
            
            # Вариант 1: ищем теги img с src
            for img in soup.find_all('img', limit=limit * 2):
                src = img.get('src') or img.get('data-src')
                if src and self._is_valid_image_url(src):
                    if src not in image_urls:
                        image_urls.append(src)
                        if len(image_urls) >= limit:
                            break
            
            # Вариант 2: ищем в data-атрибутах (Bing часто использует)
            if len(image_urls) < limit:
                for element in soup.find_all(attrs={'data-m': True}):
                    data_m = element.get('data-m', '')
                    # Извлекаем URL из JSON-строки
                    urls = re.findall(r'"murl":"(https?://[^"]+)"', data_m)
                    for url in urls:
                        if url not in image_urls and self._is_valid_image_url(url):
                            image_urls.append(url)
                            if len(image_urls) >= limit:
                                break
                    if len(image_urls) >= limit:
                        break
            
            # Вариант 3: ищем в href у ссылок на изображения
            if len(image_urls) < limit:
                for a_tag in soup.find_all('a', attrs={'m': True}, limit=limit * 2):
                    m_data = a_tag.get('m', '')
                    urls = re.findall(r'"murl":"(https?://[^"]+)"', m_data)
                    for url in urls:
                        if url not in image_urls and self._is_valid_image_url(url):
                            image_urls.append(url)
                            if len(image_urls) >= limit:
                                break
            
            logger.info(f"✅ Bing: найдено {len(image_urls)} изображений")
            return image_urls[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Bing: {e}")
            return []
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Проверяет валидность URL изображения"""
        if not url or not url.startswith('http'):
            return False
        
        # Исключаем служебные URL Bing
        exclude_patterns = [
            'th?id=',
            'bing.com/th',
            'favicon',
            'logo',
            'pixel',
            'tracking',
            '1x1'
        ]
        
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
        
        # Проверяем расширение
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        if any(url_lower.endswith(ext) for ext in valid_extensions):
            return True
        
        # Если расширения нет, но URL содержит признаки изображения
        if any(ext in url_lower for ext in valid_extensions):
            return True
        
        return False


"""Парсер Yandex Images"""
class YandexImageParser:
    """Парсер Yandex Images"""
    
    def __init__(self):
        self.base_url = "https://yandex.ru/images/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
    
    def search(self, query: str, limit: int = 10) -> List[str]:
        """
        Поиск изображений в Yandex
        
        Args:
            query: Поисковый запрос
            limit: Количество результатов
        
        Returns:
            List URL изображений
        """
        logger.info(f"🔍 Yandex Images: поиск '{query}'")
        
        try:
            params = {
                'text': query,
                'nomisspell': 1,
                'noreask': 1
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            image_urls = []
            
            # Yandex хранит данные в JSON внутри страницы
            # Ищем script теги с данными
            for script in soup.find_all('script'):
                script_content = script.string
                if script_content and 'serp-item' in script_content:
                    # Извлекаем URL изображений из JSON
                    urls = re.findall(r'"url":"(https?://[^"]+\.(?:jpg|jpeg|png|webp))', script_content)
                    for url in urls:
                        # Декодируем escaped символы
                        url = url.replace('\\/', '/')
                        if url not in image_urls and self._is_valid_image_url(url):
                            image_urls.append(url)
                            if len(image_urls) >= limit:
                                break
                
                if len(image_urls) >= limit:
                    break
            
            # Альтернативный метод: через img теги
            if len(image_urls) < limit:
                for img in soup.find_all('img', class_=re.compile('.*serp-item.*|.*thumb.*'), limit=limit * 2):
                    src = img.get('src') or img.get('data-src') or img.get('data-bem')
                    if src and self._is_valid_image_url(src):
                        if src not in image_urls:
                            image_urls.append(src)
                            if len(image_urls) >= limit:
                                break
            
            logger.info(f"✅ Yandex: найдено {len(image_urls)} изображений")
            return image_urls[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Yandex: {e}")
            return []
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Проверяет валидность URL изображения"""
        if not url or not url.startswith('http'):
            return False
        
        # Исключаем служебные URL
        exclude_patterns = [
            'favicon',
            'logo.svg',
            'pixel',
            'avatar',
            '1x1'
        ]
        
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
        
        # Проверяем расширение
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        return any(ext in url_lower for ext in valid_extensions)


"""Парсер Yahoo Image Search"""
class YahooImageParser:
    """Парсер Yahoo Image Search"""
    
    def __init__(self):
        self.base_url = "https://images.search.yahoo.com/search/images"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    
    def search(self, query: str, limit: int = 10) -> List[str]:
        """
        Поиск изображений в Yahoo
        
        Args:
            query: Поисковый запрос
            limit: Количество результатов
        
        Returns:
            List URL изображений
        """
        logger.info(f"🔍 Yahoo Images: поиск '{query}'")
        
        try:
            params = {
                'p': query,
                'fr': 'yfp-t',
                'fr2': 'p:s,v:i'
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            image_urls = []
            
            # Yahoo использует data-* атрибуты
            for img in soup.find_all('img', limit=limit * 2):
                # Проверяем различные атрибуты
                src = (img.get('src') or 
                       img.get('data-src') or 
                       img.get('data-url'))
                
                if src and self._is_valid_image_url(src):
                    if src not in image_urls:
                        image_urls.append(src)
                        if len(image_urls) >= limit:
                            break
            
            # Ищем в ссылках на изображения
            if len(image_urls) < limit:
                for a_tag in soup.find_all('a', href=True, limit=limit * 2):
                    href = a_tag.get('href', '')
                    # Yahoo иногда оборачивает URL
                    if 'imgurl=' in href:
                        match = re.search(r'imgurl=([^&]+)', href)
                        if match:
                            url = match.group(1)
                            if url not in image_urls and self._is_valid_image_url(url):
                                image_urls.append(url)
                                if len(image_urls) >= limit:
                                    break
            
            logger.info(f"✅ Yahoo: найдено {len(image_urls)} изображений")
            return image_urls[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Yahoo: {e}")
            return []
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Проверяет валидность URL изображения"""
        if not url or not url.startswith('http'):
            return False
        
        exclude_patterns = ['favicon', 'logo', 'pixel', '1x1', 'tracking']
        url_lower = url.lower()
        
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
        
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        return any(ext in url_lower for ext in valid_extensions)


"""Агрегатор веб-поиска изображений"""
class WebImageSearchAggregator:
    """Агрегатор веб-поиска изображений"""
    
    def __init__(self):
        self.bing = BingImageParser()
        self.yandex = YandexImageParser()
        self.yahoo = YahooImageParser()
    
    def search_all(self, query: str, limit: int = 10, 
                   engines: List[str] = None) -> List[str]:
        """
        Поиск изображений во всех поисковиках
        
        Args:
            query: Поисковый запрос
            limit: Общее количество результатов
            engines: Список движков ['bing', 'yandex', 'yahoo'] или None для всех
        
        Returns:
            List URL изображений
        """
        if engines is None:
            engines = ['bing', 'yandex', 'yahoo']
        
        all_images = []
        per_engine = (limit // len(engines)) + 1
        
        # Приоритет: Bing → Yandex → Yahoo
        for engine in engines:
            try:
                if engine == 'bing' and len(all_images) < limit:
                    images = self.bing.search(query, limit=per_engine)
                    all_images.extend([img for img in images if img not in all_images])
                    time.sleep(random.uniform(0.5, 1.5))  # Задержка между запросами
                
                elif engine == 'yandex' and len(all_images) < limit:
                    images = self.yandex.search(query, limit=per_engine)
                    all_images.extend([img for img in images if img not in all_images])
                    time.sleep(random.uniform(0.5, 1.5))
                
                elif engine == 'yahoo' and len(all_images) < limit:
                    images = self.yahoo.search(query, limit=per_engine)
                    all_images.extend([img for img in images if img not in all_images])
                    time.sleep(random.uniform(0.5, 1.5))
            
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска в {engine}: {e}")
                continue
        
        logger.info(f"✅ Всего найдено изображений: {len(all_images)}")
        return all_images[:limit]
    
    def search_best_quality(self, query: str, limit: int = 5) -> Optional[str]:
        """
        Поиск изображения лучшего качества
        
        Args:
            query: Поисковый запрос
            limit: Количество кандидатов для проверки
        
        Returns:
            URL лучшего изображения или None
        """
        images = self.search_all(query, limit=limit, engines=['bing', 'yandex'])
        
        if not images:
            return None
        
        # Возвращаем первое (обычно лучшего качества)
        return images[0]


# Удобные функции для быстрого использования
"""Быстрый поиск изображений в веб"""
def search_web_images(query: str, limit: int = 10) -> List[str]:
    """
    Быстрый поиск изображений в веб
    
    Args:
        query: Поисковый запрос
        limit: Количество изображений
    
    Returns:
        List URL изображений
    """
    aggregator = WebImageSearchAggregator()
    return aggregator.search_all(query, limit=limit)


"""Получить лучшее изображение по запросу"""
def get_best_web_image(query: str) -> Optional[str]:
    """
    Получить лучшее изображение по запросу
    
    Args:
        query: Поисковый запрос
    
    Returns:
        URL лучшего изображения
    """
    aggregator = WebImageSearchAggregator()
    return aggregator.search_best_quality(query, limit=5)


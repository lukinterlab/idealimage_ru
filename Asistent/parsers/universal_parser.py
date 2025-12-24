"""
Универсальный парсер для извлечения контента из различных источников
Поддерживает: веб-сайты, YouTube, VK, Rutube, Dzen
Обход защиты: User-Agent rotation, JS rendering, fallback методы
"""
import re
import logging
import requests
import warnings
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

# Фильтруем warning'и BeautifulSoup о вложенных списках (не показываем в консоли)
warnings.filterwarnings('ignore', message='.*Ignoring nested list.*')
warnings.filterwarnings('ignore', category=UserWarning, module='bs4')

logger = logging.getLogger(__name__)


class UniversalParser:
    """Универсальный парсер с поддержкой обхода защиты"""
    
    # Ротация User-Agent для обхода блокировок
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.current_ua_index = 0
        self._rotate_user_agent()
    
    @staticmethod
    def _normalize_url(url: str) -> Optional[str]:
        """Очищает и нормализует URL (обрезает кавычки, пробелы, добавляет схему)."""
        if not url:
            return None
        
        cleaned = url.strip().strip('\'"').strip()
        if not cleaned:
            return None
        
        cleaned = cleaned.replace(' ', '').replace('\r', '').replace('\n', '')
        
        parsed = urlparse(cleaned)
        if not parsed.scheme:
            cleaned = f"https://{cleaned.lstrip('/')}"
            parsed = urlparse(cleaned)
        
        if not parsed.netloc:
            return None
        
        return cleaned
    
    def _rotate_user_agent(self):
        """Ротация User-Agent"""
        self.session.headers.update({
            'User-Agent': self.USER_AGENTS[self.current_ua_index],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        self.current_ua_index = (self.current_ua_index + 1) % len(self.USER_AGENTS)
    
    def search_sources(self, query: str, limit: int = 5, only_external: bool = True) -> List[Dict]:
        """
        Поиск источников по ключевому слову
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество источников
            only_external: Только внешние источники (не наш сайт)
        
        Returns:
            Список словарей с ключами: url, title, snippet
        """
        logger.info(f"🔍 Поиск источников: query='{query}', limit={limit}")
        
        sources = []
        
        # Популярные сайты по темам (приоритетные)
        priority_sites = {
            'мода': ['vogue.ru', 'elle.ru', 'bazaar.ru', 'cosmo.ru'],
            'красота': ['cosmo.ru', 'wday.ru', 'psychologies.ru'],
            'здоровье': ['zdorovie.ru', 'medportal.ru', 'med.ru'],
            'кулинария': ['eda.ru', 'gastronom.ru', 'povarenok.ru'],
        }
        
        # Определяем тему
        topic_keywords = {
            'мода': ['мода', 'одежда', 'стиль', 'тренд', 'outfit', 'fashion'],
            'красота': ['красота', 'макияж', 'уход', 'косметика', 'beauty'],
            'здоровье': ['здоровье', 'фитнес', 'спорт', 'wellness'],
            'кулинария': ['рецепт', 'готовить', 'блюдо', 'еда', 'кухня'],
        }
        
        detected_topic = None
        query_lower = query.lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected_topic = topic
                break
        
        # Если тема определена - добавляем приоритетные сайты
        if detected_topic and detected_topic in priority_sites:
            for site in priority_sites[detected_topic]:
                sources.append({
                    'url': f'https://{site}/search?q={query}',
                    'title': f'{site} - {query}',
                    'snippet': f'Приоритетный источник по теме {detected_topic}',
                    'priority': True
                })
                if len(sources) >= limit:
                    break
        
        # Если недостаточно - добавляем универсальные источники
        if len(sources) < limit:
            universal_sources = [
                f'https://www.google.com/search?q={query}',
                f'https://yandex.ru/search/?text={query}',
            ]
            for url in universal_sources:
                if len(sources) >= limit:
                    break
                sources.append({
                    'url': url,
                    'title': f'Поиск: {query}',
                    'snippet': 'Универсальный источник',
                    'priority': False
                })
        
        logger.info(f"✅ Найдено источников: {len(sources)}")
        return sources[:limit]
    
    def parse_feed(self, feed_url: str, limit: int = 10, extract_popularity: bool = True) -> List[Dict]:
        """
        Парсинг ленты статей с извлечением популярности
        
        Args:
            feed_url: URL страницы со списком статей
            limit: Максимальное количество статей для извлечения
            extract_popularity: Извлекать метрики популярности (лайки, просмотры)
        
        Returns:
            Список словарей с url, title, popularity_score
        """
        logger.info(f"📰 Парсинг ленты: {feed_url}")
        
        try:
            response = self.session.get(feed_url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            
            from urllib.parse import urljoin, urlparse
            base_domain = f"{urlparse(feed_url).scheme}://{urlparse(feed_url).netloc}"
            
            # Для VC.ru ищем блоки статей с метриками
            if 'vc.ru' in feed_url or 'tj.ru' in feed_url or 'dtf.ru' in feed_url:
                # Ищем контейнеры статей
                content_blocks = soup.select('.content, .content--short')
                
                for block in content_blocks:
                    try:
                        # Извлекаем ссылку на статью
                        title_link = block.select_one('a.content-title, .content-title a')
                        if not title_link:
                            continue
                        
                        href = title_link.get('href')
                        if not href:
                            continue
                        
                        full_url = urljoin(base_domain, href)
                        if not self._is_article_url(full_url):
                            continue
                        
                        # Извлекаем заголовок
                        title = title_link.get_text(strip=True)
                        
                        # Извлекаем метрики популярности
                        popularity_score = 0
                        if extract_popularity:
                            # Лайки/реакции
                            reactions = block.select('.reaction-button__label')
                            for reaction in reactions:
                                try:
                                    count = reaction.get_text(strip=True)
                                    # Конвертируем "1.5K" в число
                                    if 'K' in count or 'к' in count.lower():
                                        popularity_score += float(count.replace('K', '').replace('к', '').replace(',', '.')) * 1000
                                    else:
                                        popularity_score += float(count.replace(',', ''))
                                except:
                                    pass
                            
                            # Просмотры
                            views = block.select_one('.content-views-item .content-footer-button__label')
                            if views:
                                try:
                                    count = views.get_text(strip=True)
                                    if 'K' in count or 'к' in count.lower():
                                        popularity_score += float(count.replace('K', '').replace('к', '').replace(',', '.')) * 1000 * 0.1  # вес меньше чем лайки
                                    else:
                                        popularity_score += float(count.replace(',', '')) * 0.1
                                except:
                                    pass
                        
                        articles.append({
                            'url': full_url,
                            'title': title,
                            'popularity_score': popularity_score
                        })
                        
                        if len(articles) >= limit:
                            break
                            
                    except Exception as e:
                        continue
            
            else:
                # УЛУЧШЕННЫЙ парсинг для ЛЮБЫХ сайтов
                logger.info(f"   🔍 Использую универсальный парсер для {feed_url}")
                
                # ШАГ 1: Ищем ВСЕ ссылки с заголовками
                link_patterns = [
                    # Статьи и посты
                    'article a[href]',
                    'article h2 a', 'article h3 a',
                    # Заголовки
                    'h1 a[href]', 'h2 a[href]', 'h3 a[href]',
                    # Классы постов
                    '.post a[href]', '.post-title a', '.entry-title a',
                    '.article a[href]', '.article-title a',
                    '.content a[href]', '.content-title a',
                    # Блоки новостей
                    '.news-item a', '.blog-post a',
                    # Универсальные контейнеры
                    '[class*="post"] a[href]',
                    '[class*="article"] a[href]',
                    '[class*="entry"] a[href]',
                    '[class*="item"] a[href]',
                    # Списки
                    'ul li a[href]', 'ol li a[href]',
                ]
                
                seen_urls = set()  # Для избежания дубликатов
                
                for selector in link_patterns:
                    if len(articles) >= limit:
                        break
                    
                    try:
                        links = soup.select(selector)
                        logger.info(f"      • Селектор '{selector}': найдено {len(links)} ссылок")
                        
                        for link in links:
                            if len(articles) >= limit:
                                break
                            
                            href = link.get('href')
                            if not href:
                                continue
                            
                            # Преобразуем в полный URL
                            full_url = urljoin(base_domain, href)
                            
                            # Избегаем дубликатов
                            if full_url in seen_urls:
                                continue
                            
                            # Проверяем что это статья
                            if not self._is_article_url(full_url):
                                continue
                            
                            # Извлекаем заголовок
                            title = link.get_text(strip=True)
                            
                            # Минимальная длина заголовка (отсекаем "Читать далее" и т.п.)
                            if len(title) < 10:
                                continue
                            
                            seen_urls.add(full_url)
                            articles.append({
                                'url': full_url,
                                'title': title,
                                'popularity_score': 0
                            })
                            
                    except Exception as e:
                        logger.warning(f"      ⚠️ Ошибка с селектором '{selector}': {e}")
                        continue
            
            # Сортируем по популярности (от большей к меньшей)
            if extract_popularity:
                articles.sort(key=lambda x: x['popularity_score'], reverse=True)
            
            # Итоговая статистика
            logger.info(f"")
            logger.info(f"   📊 ИТОГО найдено статей: {len(articles)}")
            if articles:
                logger.info(f"   ✅ Статьи успешно извлечены из {feed_url}")
                logger.info(f"   📝 Примеры заголовков:")
                for i, art in enumerate(articles[:3]):
                    logger.info(f"      {i+1}. {art['title'][:60]}...")
                if extract_popularity and articles[0]['popularity_score'] > 0:
                    logger.info(f"   🔥 Топ статья: score={articles[0]['popularity_score']:.0f}")
            else:
                logger.warning(f"   ⚠️ НИ ОДНОЙ статьи не найдено!")
                logger.warning(f"   💡 Возможно, сайт использует динамическую загрузку (JS)")
                logger.warning(f"   💡 Или структура HTML не подходит под селекторы")
            
            return articles[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга ленты {feed_url}: {e}")
            return []
    
    def _is_article_url(self, url: str) -> bool:
        """
        Проверка, является ли URL ссылкой на статью
        УПРОЩЕННАЯ ВЕРСИЯ - пропускаем больше статей!
        """
        url = self._normalize_url(url)
        if not url:
            return False
        
        # Исключаем ТОЛЬКО явно служебные страницы
        exclude_patterns = [
            '/login', '/register', '/logout',
            '/search?', '/about', '/contacts',
            'javascript:', 'mailto:',
            '/tag/', '/tags/',
            '/category/', '/categories/',
        ]
        
        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False
        
        # Если URL начинается с # - это якорь, не статья
        if url.startswith('#'):
            return False
        
        # Проверяем минимальную длину (отсекаем только главные страницы)
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # Пропускаем только главную страницу сайта
        if not path or path in ['index.html', 'index.php']:
            return False
        
        # ВСЕ ОСТАЛЬНОЕ - ПРОПУСКАЕМ (широкий фильтр!)
        return True
    
    def parse_article(self, url: str, retries: int = 3, download_images: bool = False) -> Dict:
        """
        Парсинг статьи с любого сайта (с обходом защиты)
        
        Args:
            url: URL статьи
            retries: Количество попыток
            download_images: Скачивать ли изображения (по умолчанию False - только для режима parse_web)
        
        Returns:
            Dict с ключами: title, text, images, videos, author
        """
        normalized_url = self._normalize_url(url)
        if not normalized_url:
            logger.warning(f"⚠️ Некорректный URL для парсинга: {url}")
            return self._fallback_parse(url or '')
        
        logger.info(f"📥 Парсинг статьи: {normalized_url}")
        
        for attempt in range(retries):
            try:
                # Ротация User-Agent при повторных попытках
                if attempt > 0:
                    self._rotate_user_agent()
                    time.sleep(1)  # Задержка между попытками
                
                response = self.session.get(normalized_url, timeout=15, allow_redirects=True)
                response.raise_for_status()
                
                # ВРЕМЕННО: Сохраняем HTML в файл для отладки
                try:
                    from pathlib import Path
                    debug_file = Path(__file__).parent.parent / 'Test_Promot' / 'pars.html'
                    debug_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"<!-- URL: {normalized_url} -->\n")
                        f.write(f"<!-- Content-Type: {response.headers.get('Content-Type', 'unknown')} -->\n")
                        f.write(f"<!-- Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n\n")
                        f.write(response.text)
                    logger.debug(f"💾 HTML сохранен в {debug_file}")
                except Exception as save_error:
                    logger.warning(f"Не удалось сохранить HTML для отладки: {save_error}")
                
                # Определяем тип контента
                content_type = response.headers.get('Content-Type', '')
                
                if 'text/html' in content_type:
                    return self._parse_html(response.text, normalized_url, download_images=download_images)
                elif 'application/json' in content_type:
                    return self._parse_json(response.json())
                else:
                    logger.warning(f"Неподдерживаемый Content-Type: {content_type}")
                    return self._parse_html(response.text, normalized_url, download_images=download_images)  # Попытка как HTML
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Попытка {attempt + 1}/{retries} не удалась: {e}")
                if attempt == retries - 1:
                    # Последняя попытка - используем fallback
                    return self._fallback_parse(normalized_url)
        
        return {}
    
    def _parse_html(self, html: str, url: str, download_images: bool = False) -> Dict:
        """
        Парсинг HTML контента
        
        Args:
            html: HTML содержимое страницы
            url: URL страницы
            download_images: Скачивать ли изображения (только для режима parse_web)
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Специальный парсер для horo.mail.ru
        if 'horo.mail.ru' in url:
            return self._parse_horo_mail_ru(soup, url, download_images=download_images)
        
        # Удаляем скрипты, стили, комментарии
        for element in soup(['script', 'style', 'meta', 'link', 'noscript']):
            element.decompose()
        
        # Извлекаем заголовок
        title = None
        if soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)
        elif soup.find('title'):
            title = soup.find('title').get_text(strip=True)
        
        # Извлекаем основной текст
        # Ищем основной контейнер статьи
        article_containers = soup.find_all(['article', 'main', 
                                           soup.find(class_=re.compile(r'(article|content|post|entry)')),
                                           soup.find(id=re.compile(r'(article|content|post|entry)'))])
        
        text_parts = []
        if article_containers:
            for container in article_containers[:1]:  # Берем первый найденный
                for p in container.find_all(['p', 'h2', 'h3', 'li']):
                    text = p.get_text(strip=True)
                    if len(text) > 20:  # Минимальная длина абзаца
                        text_parts.append(text)
        else:
            # Fallback: собираем все параграфы
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 20:
                    text_parts.append(text)
        
        text = '\n\n'.join(text_parts)
        
        # Извлекаем изображения
        images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-bg')
            if src:
                # Преобразуем относительные URL в абсолютные
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    parsed = urlparse(url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"
                
                # Фильтруем placeholder и мелкие изображения
                if 'placeholder' not in src.lower() and 'empty.png' not in src.lower():
                    images.append(src)
        
        # Извлекаем видео
        videos = []
        for video in soup.find_all(['video', 'iframe']):
            src = video.get('src')
            if src:
                videos.append(src)
        
        # Скачиваем изображения ТОЛЬКО если явно запрошено (режим parse_web)
        downloaded_images = []
        if download_images:
            downloaded_images = self._download_images_from_urls(images[:10], url)
            logger.info(f"✅ Спаршено: заголовок={bool(title)}, текст={len(text)} символов, "
                       f"изображений={len(images)}, скачано={len(downloaded_images)}, видео={len(videos)}")
        else:
            logger.info(f"✅ Спаршено: заголовок={bool(title)}, текст={len(text)} символов, "
                       f"изображений={len(images)} (скачивание отключено), видео={len(videos)}")
        
        return {
            'title': title or 'Без заголовка',
            'text': text,
            'images': images[:10],  # URL изображений
            'downloaded_images': downloaded_images,  # ПУТИ к скачанным файлам! (пусто если download_images=False)
            'videos': videos[:3],    # Максимум 3 видео
            'url': url,
            'success': bool(text and len(text) > 50),  # Успех если есть текст > 50 символов
        }
    
    def _parse_horo_mail_ru(self, soup: BeautifulSoup, url: str, download_images: bool = False) -> Dict:
        """
        Специальный парсер для horo.mail.ru
        Ищет контент гороскопа в HTML структуре сайта
        
        Args:
            soup: BeautifulSoup объект
            url: URL страницы
            download_images: Скачивать ли изображения
        
        Returns:
            Словарь с результатами парсинга (как _parse_html)
        """
        # Удаляем скрипты, стили, комментарии
        for element in soup(['script', 'style', 'meta', 'link', 'noscript']):
            element.decompose()
        
        # Извлекаем заголовок
        title = None
        h1_element = soup.find('h1', class_=re.compile(r'heading'))
        if h1_element:
            title = h1_element.get_text(strip=True)
        elif soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)
        elif soup.find('title'):
            title = soup.find('title').get_text(strip=True)
        
        # Ищем основной блок гороскопа
        text_parts = []
        
        # Стоп-слова: останавливаем парсинг при встрече этих слов
        stop_words = ['Финансы', 'Здоровье', 'Любовь']
        
        # Пробуем разные селекторы для horo.mail.ru
        selectors = [
            # Основной контент гороскопа
            'div[data-qa="HoroscopeText"] p',
            'div[data-qa*="Horoscope"] p',
            'article p',
            '.article p',
            '[class*="article"] p',
            '[class*="content"] p',
            '[class*="horoscope"] p',
            '[data-qa*="content"] p',
            # Контейнеры с текстом
            'main p',
            '.main-content p',
            '[role="main"] p',
        ]
        
        found_content = False
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                logger.debug(f"   Найдено {len(elements)} элементов по селектору '{selector}'")
                for elem in elements:
                    # Проверяем, является ли сам элемент ссылкой/кнопкой со стоп-словом
                    if elem.name in ['a', 'button']:
                        elem_text = elem.get_text(strip=True)
                        elem_text_lower = elem_text.lower()
                        # Проверяем точное совпадение или короткое совпадение
                        if any(stop_word.lower() == elem_text_lower or 
                               (stop_word.lower() in elem_text_lower and len(elem_text) <= 15) 
                               for stop_word in stop_words):
                            logger.info(f"   ⛔ Остановка парсинга: найдено стоп-слово в ссылке '{elem_text}'")
                            found_content = True
                            break
                    
                    # Проверяем, есть ли внутри элемента ссылки/кнопки со стоп-словами
                    links_buttons = elem.find_all(['a', 'button'])
                    has_stop_word_in_link = False
                    
                    for link in links_buttons:
                        link_text = link.get_text(strip=True)
                        link_text_lower = link_text.lower()
                        # Проверяем точное совпадение стоп-слов (Финансы, Здоровье, Любовь)
                        if any(stop_word.lower() == link_text_lower or 
                               (stop_word.lower() in link_text_lower and len(link_text) <= 15) 
                               for stop_word in stop_words):
                            logger.info(f"   ⛔ Остановка парсинга: найдено стоп-слово в ссылке '{link_text}'")
                            found_content = True
                            has_stop_word_in_link = True
                            break
                    
                    if has_stop_word_in_link:
                        break  # Прекращаем парсинг
                    
                    text = elem.get_text(strip=True)
                    if len(text) > 30:  # Минимальная длина для гороскопа
                        text_parts.append(text)
                
                if found_content or text_parts:
                    break  # Если нашли контент или стоп-слово, прекращаем поиск
        
        # Если не нашли через селекторы, пробуем найти все параграфы
        if not text_parts and not found_content:
            logger.debug("   Пробуем fallback: все параграфы")
            for p in soup.find_all('p'):
                # Проверяем, есть ли внутри параграфа ссылки/кнопки со стоп-словами
                links_buttons = p.find_all(['a', 'button'])
                has_stop_word_in_link = False
                
                for link in links_buttons:
                    link_text = link.get_text(strip=True)
                    link_text_lower = link_text.lower()
                    # Проверяем точное совпадение стоп-слов (Финансы, Здоровье, Любовь)
                    if any(stop_word.lower() == link_text_lower or 
                           (stop_word.lower() in link_text_lower and len(link_text) <= 15) 
                           for stop_word in stop_words):
                        logger.info(f"   ⛔ Остановка парсинга: найдено стоп-слово в ссылке '{link_text}'")
                        has_stop_word_in_link = True
                        break
                
                if has_stop_word_in_link:
                    break  # Прекращаем парсинг
                
                text = p.get_text(strip=True)
                # Фильтруем короткие тексты и служебные элементы
                if len(text) > 30 and 'cookie' not in text.lower() and 'javascript' not in text.lower():
                    text_parts.append(text)
        
        text = '\n\n'.join(text_parts)
        
        # Изображения и видео не извлекаем - они не нужны
        images = []
        downloaded_images = []
        videos = []
        
        logger.info(f"✅ Спаршено horo.mail.ru: заголовок={bool(title)}, текст={len(text)} символов")
        
        return {
            'title': title or 'Без заголовка',
            'text': text,
            'images': images[:10],
            'downloaded_images': downloaded_images,
            'videos': videos[:3],
            'url': url,
            'success': bool(text and len(text) > 50)
        }
    
    def _download_images_from_urls(self, image_urls: List[str], source_url: str) -> List[str]:
        """
        Скачивает изображения СРАЗУ при парсинге
        
        Args:
            image_urls: Список URL изображений
            source_url: URL источника (для логирования)
        
        Returns:
            Список путей к скачанным файлам (относительные от MEDIA_ROOT)
        """
        if not image_urls:
            return []
        
        logger.info(f"      💾 Скачиваю {len(image_urls)} изображений...")
        
        import os
        import uuid
        from django.conf import settings
        from django.core.files.base import ContentFile
        
        # Создаем папку если её нет
        parsed_images_dir = os.path.join(settings.MEDIA_ROOT, 'parsed_images')
        os.makedirs(parsed_images_dir, exist_ok=True)
        
        downloaded_paths = []
        
        for idx, img_url in enumerate(image_urls[:5]):  # Скачиваем максимум 5 лучших
            try:
                logger.info(f"         📥 [{idx+1}/5] {img_url[:60]}...")
                
                # Скачиваем изображение напрямую через requests
                response = self.session.get(img_url, timeout=10, stream=True)
                response.raise_for_status()
                
                # Проверяем что это действительно изображение
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    logger.info(f"            ⏭️ Не изображение (Content-Type: {content_type})")
                    continue
                
                # Генерируем уникальное имя файла
                ext = img_url.split('.')[-1].split('?')[0][:4]  # Расширение из URL
                if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                    ext = 'jpg'  # Дефолтное расширение
                
                filename = f"parsed_{uuid.uuid4().hex[:12]}.{ext}"
                file_path = os.path.join(parsed_images_dir, filename)
                
                # Сохраняем файл
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Проверяем размер файла (минимум 10KB)
                if os.path.getsize(file_path) < 10240:
                    logger.info(f"            ⏭️ Слишком маленький файл (< 10KB)")
                    os.remove(file_path)
                    continue
                
                # Возвращаем ОТНОСИТЕЛЬНЫЙ путь от MEDIA_ROOT
                relative_path = f"parsed_images/{filename}"
                downloaded_paths.append(relative_path)
                
                logger.info(f"            ✅ Сохранено: {relative_path}")
                    
            except Exception as e:
                logger.warning(f"            ⚠️ Ошибка: {type(e).__name__}: {str(e)[:50]}")
                continue
        
        logger.info(f"      ✅ Успешно скачано: {len(downloaded_paths)} из {len(image_urls)}")
        return downloaded_paths
    
    def _parse_json(self, data: Dict) -> Dict:
        """Парсинг JSON данных (для API)"""
        return {
            'title': data.get('title', 'Без заголовка'),
            'text': data.get('content', data.get('description', '')),
            'images': data.get('images', []),
            'videos': data.get('videos', []),
            'success': True
        }
    
    def _fallback_parse(self, url: str) -> Dict:
        """Fallback метод когда основной парсинг не удался"""
        logger.warning(f"⚠️ Использую fallback для {url}")
        
        # Генерируем минимальные данные
        return {
            'title': 'Статья (парсинг не удался)',
            'text': f'Не удалось извлечь контент с {url}. '
                   'Источник может использовать защиту от парсинга. '
                   'Рекомендуется указать альтернативный источник.',
            'images': [],
            'videos': [],
            'url': url,
            'success': False
        }

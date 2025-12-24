"""
Management команда для генерации/регенерации embeddings для всех записей в AIKnowledgeBase
Поддерживает batch-режим для экономии времени
"""
from django.core.management.base import BaseCommand
from Asistent.models import AIKnowledgeBase
from Asistent.gigachat_api import get_embeddings, get_embeddings_batch
import time


class Command(BaseCommand):
    help = 'Генерирует embeddings для всех записей в базе знаний AI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перегенерировать embeddings даже для записей у которых они уже есть'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Генерировать только для указанной категории'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Ограничить количество обрабатываемых записей'
        )
        parser.add_argument(
            '--batch',
            action='store_true',
            help='Использовать batch-режим (быстрее, но требует больше памяти)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Размер batch (по умолчанию 10)'
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        category = options.get('category')
        limit = options.get('limit')
        use_batch = options.get('batch', False)
        batch_size = options.get('batch_size', 10)
        
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('  🚀 ГЕНЕРАЦИЯ EMBEDDINGS ДЛЯ БАЗЫ ЗНАНИЙ'))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        
        # Формируем запрос
        items = AIKnowledgeBase.objects.filter(is_active=True)
        
        if category:
            items = items.filter(category=category)
            self.stdout.write(f"📂 Фильтр: категория '{category}'")
        
        if not force:
            # Только записи без embeddings
            items = items.filter(embedding__isnull=True) | items.filter(embedding=[])
            self.stdout.write("🔍 Режим: только записи БЕЗ embeddings")
        else:
            self.stdout.write("🔄 Режим: ПЕРЕГЕНЕРАЦИЯ всех embeddings")
        
        if limit:
            items = items[:limit]
            self.stdout.write(f"📊 Лимит: {limit} записей")
        
        if use_batch:
            self.stdout.write(f"⚡ Batch-режим: {batch_size} записей за раз")
        
        total = items.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('❌ Нет записей для обработки'))
            return
        
        self.stdout.write(f"\n📋 Найдено записей для обработки: {total}")
        self.stdout.write('')
        
        # Обрабатываем записи
        success_count = 0
        error_count = 0
        
        if use_batch:
            # Batch-режим (быстрее)
            items_list = list(items)
            
            for batch_start in range(0, len(items_list), batch_size):
                batch_items = items_list[batch_start:batch_start + batch_size]
                batch_texts = [f"{item.title}\n\n{item.content}" for item in batch_items]
                
                self.stdout.write(f"\n[Batch {batch_start//batch_size + 1}] Обработка {len(batch_items)} записей...")
                
                try:
                    start_time = time.time()
                    embeddings = get_embeddings_batch(batch_texts)
                    elapsed = time.time() - start_time
                    
                    # Сохраняем результаты
                    for i, (item, embedding) in enumerate(zip(batch_items, embeddings)):
                        if embedding and len(embedding) > 0:
                            item._skip_embedding_generation = True
                            AIKnowledgeBase.objects.filter(pk=item.pk).update(
                                embedding=embedding
                            )
                            success_count += 1
                            self.stdout.write(f"   ✅ {item.title[:40]}...")
                        else:
                            error_count += 1
                            self.stdout.write(f"   ❌ {item.title[:40]}... (пустой)")
                    
                    self.stdout.write(self.style.SUCCESS(f"   📊 Batch завершён за {elapsed:.2f}s"))
                    time.sleep(1)  # Пауза между batch
                    
                except Exception as e:
                    error_count += len(batch_items)
                    self.stdout.write(self.style.ERROR(f"   ❌ Ошибка batch: {e}"))
                    if '429' in str(e):
                        self.stdout.write(self.style.WARNING("   ⏸️  Пауза 15 секунд (Rate Limit)..."))
                        time.sleep(15)
        else:
            # Обычный режим (по одному)
            for i, item in enumerate(items, 1):
                try:
                    text = f"{item.title}\n\n{item.content}"
                    
                    self.stdout.write(f"[{i}/{total}] 📝 {item.title[:50]}...")
                    
                    start_time = time.time()
                    embedding = get_embeddings(text)
                    elapsed = time.time() - start_time
                    
                    if embedding and len(embedding) > 0:
                        item._skip_embedding_generation = True
                        AIKnowledgeBase.objects.filter(pk=item.pk).update(
                            embedding=embedding
                        )
                        
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   ✅ Успешно ({len(embedding)} измерений, {elapsed:.2f}s)"
                            )
                        )
                        time.sleep(0.5)
                    else:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f"   ❌ Пустой embedding"))
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {e}"))
                    
                    if '429' in str(e) or 'Too Many Requests' in str(e):
                        self.stdout.write(self.style.WARNING("   ⏸️  Пауза 10 секунд (Rate Limit)..."))
                        time.sleep(10)
        
        # Итоговая статистика
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('  📊 ИТОГОВАЯ СТАТИСТИКА'))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        self.stdout.write(f"✅ Успешно обработано: {success_count}")
        self.stdout.write(f"❌ Ошибок: {error_count}")
        self.stdout.write(f"📋 Всего: {total}")
        self.stdout.write('')
        
        # Статистика по категориям
        self.stdout.write("📂 Статистика по категориям:")
        for cat, display in AIKnowledgeBase.CATEGORY_CHOICES:
            count_with = AIKnowledgeBase.objects.filter(
                category=cat,
                is_active=True
            ).exclude(embedding__isnull=True).exclude(embedding=[]).count()
            
            count_total = AIKnowledgeBase.objects.filter(
                category=cat,
                is_active=True
            ).count()
            
            if count_total > 0:
                percent = (count_with / count_total) * 100
                self.stdout.write(f"   • {display}: {count_with}/{count_total} ({percent:.0f}%)")
        
        self.stdout.write('')
        
        if success_count > 0:
            self.stdout.write(self.style.SUCCESS('🎉 Генерация embeddings завершена!'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Ни один embedding не был создан'))
        
        self.stdout.write('')
        self.stdout.write('💡 Теперь векторный поиск будет работать эффективнее!')
        self.stdout.write('')


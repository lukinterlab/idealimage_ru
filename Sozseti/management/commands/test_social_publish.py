"""
Management команда для тестовой публикации в соцсети
"""
from django.core.management.base import BaseCommand
from blog.models import Post
from Sozseti.tasks import publish_post_to_social


class Command(BaseCommand):
    help = 'Тестовая публикация статьи в социальные сети'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'post_id',
            type=int,
            help='ID статьи для публикации'
        )
        parser.add_argument(
            '--platforms',
            nargs='+',
            default=['telegram'],
            help='Платформы для публикации (telegram, vk, etc.)'
        )
    
    def handle(self, *args, **options):
        post_id = options['post_id']
        platforms = options['platforms']
        
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Статья с ID {post_id} не найдена')
            )
            return
        
        self.stdout.write(f'[*] Публикуем статью: "{post.title}"')
        self.stdout.write(f'    Платформы: {", ".join(platforms)}')
        
        # Запускаем публикацию
        result = publish_post_to_social(post_id, platforms=platforms)
        
        if result.get('success'):
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Успешно опубликовано: {result["total_success"]} каналов'
                )
            )
            
            if result['total_failed'] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'[WARN] Ошибок: {result["total_failed"]}'
                    )
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Ошибка публикации: {result.get("error")}')
            )


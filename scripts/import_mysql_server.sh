#!/bin/bash
################################################################################
# ИМПОРТ MySQL БАЗЫ ДАННЫХ НА СЕРВЕРЕ
################################################################################

echo "================================================================================"
echo "ИМПОРТ MySQL БАЗЫ ДАННЫХ"
echo "================================================================================"
echo ""

# Загружаем переменные из .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ ОШИБКА: Файл .env не найден!"
    exit 1
fi

# Проверяем наличие SQL дампа
DUMP_FILE="mysql_export_for_server.sql"
if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ ОШИБКА: Файл $DUMP_FILE не найден!"
    echo "   Загрузите его через FTP"
    exit 1
fi

echo "[1/7] Проверка подключения к MySQL..."
if mysql -u$DB_USER -p$DB_PASSWORD -h$DB_HOST -e "SELECT 1" > /dev/null 2>&1; then
    echo "   ✅ Подключение к MySQL успешно"
else
    echo "   ❌ ОШИБКА: Не удается подключиться к MySQL"
    echo "   Проверьте параметры в .env"
    exit 1
fi

echo ""
echo "[2/7] Создание бэкапа текущей БД (если есть данные)..."
BACKUP_FILE="backup_before_migration_$(date +%Y%m%d_%H%M%S).sql"
mysqldump -u$DB_USER -p$DB_PASSWORD -h$DB_HOST $DB_NAME > $BACKUP_FILE 2>/dev/null
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
    if [ "$BACKUP_SIZE" -gt 1000 ]; then
        echo "   ✅ Бэкап создан: $BACKUP_FILE"
    else
        echo "   ℹ️  БД пустая, бэкап не требуется"
        rm -f $BACKUP_FILE
    fi
else
    echo "   ℹ️  Бэкап не создан (возможно БД не существует)"
fi

echo ""
echo "[3/7] Очистка базы данных $DB_NAME..."
# Получаем список всех таблиц и удаляем их
TABLES=$(mysql -u$DB_USER -p$DB_PASSWORD -h$DB_HOST $DB_NAME -e "SHOW TABLES" 2>/dev/null | awk '{ print $1}' | grep -v '^Tables' )
if [ -n "$TABLES" ]; then
    for TABLE in $TABLES; do
        mysql -u$DB_USER -p$DB_PASSWORD -h$DB_HOST $DB_NAME -e "DROP TABLE IF EXISTS \`$TABLE\`" 2>&1 | grep -v "Warning: Using a password"
    done
    echo "   ✅ База данных очищена (удалено таблиц: $(echo "$TABLES" | wc -l))"
else
    echo "   ℹ️  База данных пустая"
fi

echo ""
echo "[4/7] Импорт данных из $DUMP_FILE (это займет 2-3 минуты)..."
FILE_SIZE=$(stat -f%z "$DUMP_FILE" 2>/dev/null || stat -c%s "$DUMP_FILE" 2>/dev/null)
FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
echo "   Размер файла: ${FILE_SIZE_MB} MB"

mysql -u$DB_USER -p$DB_PASSWORD -h$DB_HOST $DB_NAME < $DUMP_FILE 2>&1 | grep -v "Warning: Using a password" | head -10
if [ $? -eq 0 ]; then
    echo "   ✅ Данные импортированы"
else
    echo "   ❌ ОШИБКА: Импорт данных не удался"
    exit 1
fi

echo ""
echo "[5/7] Применение миграций Django..."
~/domains/idealimage.ru/.venv/python311/bin/python3.11 manage.py migrate --run-syncdb 2>&1 | tail -10
if [ $? -eq 0 ]; then
    echo "   ✅ Миграции применены"
else
    echo "   ⚠️  Возможны ошибки миграций (проверьте вывод выше)"
fi

echo ""
echo "[6/7] Сбор статических файлов..."
~/domains/idealimage.ru/.venv/python311/bin/python3.11 manage.py collectstatic --noinput > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Статика собрана"
else
    echo "   ⚠️  Ошибка сбора статики"
fi

echo ""
echo "[7/7] Проверка данных..."
~/domains/idealimage.ru/.venv/python311/bin/python3.11 manage.py shell << EOF
from django.contrib.auth.models import User
from blog.models import Post, Category
from Visitor.models import Profile

users_count = User.objects.count()
posts_count = Post.objects.count()
categories_count = Category.objects.count()
profiles_count = Profile.objects.count()

print(f"   Пользователей: {users_count}")
print(f"   Постов: {posts_count}")
print(f"   Категорий: {categories_count}")
print(f"   Профилей: {profiles_count}")
EOF

echo ""
echo "================================================================================"
echo "✅ ИМПОРТ ЗАВЕРШЕН УСПЕШНО!"
echo "================================================================================"
echo ""
echo "СЛЕДУЮЩИЕ ШАГИ:"
echo "   1. Перезапустите сайт: touch tmp/restart.txt"
echo "   2. Проверьте сайт: https://idealimage.ru/"
echo "   3. Проверьте админку: https://idealimage.ru/admin/"
echo "   4. Запустите Django-Q: crontab -e (проверьте cron задачи)"
echo ""
echo "БЭКАП СТАРОЙ БД:"
if [ -f "$BACKUP_FILE" ]; then
    echo "   $BACKUP_FILE"
else
    echo "   Не создавался (БД была пустая)"
fi
echo ""
echo "================================================================================"


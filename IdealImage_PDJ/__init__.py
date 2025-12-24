"""
IdealImage Project
"""
from __future__ import absolute_import, unicode_literals

# Настройка PyMySQL для Django (monkey patching)
# Это позволяет использовать PyMySQL вместо mysqlclient (MySQLdb)
# PyMySQL - чистая Python реализация, не требует компилятора C
try:
    import pymysql
    # Заменяем MySQLdb на PyMySQL
    pymysql.install_as_MySQLdb()
except ImportError:
    # Если PyMySQL не установлен, Django попытается использовать mysqlclient
    pass

# УСТАРЕЛО: Celery больше не используется
# Теперь используется Django-Q (работает без Redis через ORM)
# from .celery import app as celery_app
# __all__ = ('celery_app',)

# Инициализация SQLite для shared hosting (отключение WAL-режима)
from . import db_init  # noqa

__all__ = tuple()


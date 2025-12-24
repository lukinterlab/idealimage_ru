"""
WebSocket routing для прогресс-бара тестирования промптов
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/prompt-test/(?P<template_id>\d+)/$', consumers.PromptTestProgressConsumer.as_asgi()),
]


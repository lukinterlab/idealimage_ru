"""
URL routing для чат-бота
"""

from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('api/chatbot/message/', views.chatbot_message, name='message'),
    path('api/chatbot/contact-admin/', views.contact_admin_from_chat, name='contact'),
    path('api/chatbot/settings/', views.get_chatbot_settings_api, name='settings'),
]


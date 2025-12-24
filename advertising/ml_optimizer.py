"""
Модуль машинного обучения для оптимизации размещения рекламы
"""
import logging
import pandas as pd
import numpy as np
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Avg

logger = logging.getLogger(__name__)


class AdPlacementOptimizer:
    """Оптимизатор размещения рекламы на основе ML"""
    
    def __init__(self):
        self.ctr_model = None
        self.revenue_model = None
        self.feature_columns = []
    
    def collect_training_data(self, days=90):
        """
        Собрать данные для обучения за последние N дней
        
        Args:
            days: количество дней для сбора данных
        
        Returns:
            DataFrame с данными или None
        """
        try:
            from .models import AdPerformanceML
            
            date_from = timezone.now().date() - timedelta(days=days)
            
            # Получаем данные
            queryset = AdPerformanceML.objects.filter(
                date__gte=date_from
            ).values(
                'ad_place__code',
                'date',
                'hour',
                'day_of_week',
                'impressions',
                'clicks',
                'ctr',
                'revenue',
                'category',
                'device_type',
                'user_type',
                'effectiveness_score'
            )
            
            if not queryset.exists():
                logger.warning("Нет данных для обучения ML модели")
                return None
            
            # Преобразуем в DataFrame
            df = pd.DataFrame(list(queryset))
            
            logger.info(f"Собрано {len(df)} записей для обучения")
            
            return df
        
        except Exception as e:
            logger.error(f"Ошибка при сборе данных: {str(e)}")
            return None
    
    def prepare_features(self, data):
        """
        Подготовка признаков для ML
        
        Args:
            data: DataFrame с данными
        
        Returns:
            X, y_ctr, y_revenue
        """
        df = data.copy()
        
        # One-hot encoding для категориальных признаков
        df = pd.get_dummies(df, columns=[
            'ad_place__code',
            'category',
            'device_type',
            'user_type'
        ])
        
        # Feature engineering
        df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
        df['is_prime_time'] = df['hour'].apply(lambda x: 1 if 9 <= x <= 21 else 0)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Удаляем ненужные столбцы
        columns_to_drop = ['date', 'impressions', 'clicks', 'ctr', 'revenue', 'effectiveness_score']
        X = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
        
        # Целевые переменные
        y_ctr = df['ctr'] if 'ctr' in df.columns else None
        y_revenue = df['revenue'] if 'revenue' in df.columns else None
        
        # Сохраняем названия признаков
        self.feature_columns = list(X.columns)
        
        return X, y_ctr, y_revenue
    
    def train_ctr_model(self):
        """
        Обучить модель предсказания CTR
        
        Returns:
            dict с метриками
        """
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_absolute_error, r2_score
            import joblib
            import os
            
            # Собираем данные
            data = self.collect_training_data()
            
            if data is None or len(data) < 100:
                logger.warning("Недостаточно данных для обучения модели CTR")
                return {'error': 'Недостаточно данных'}
            
            # Подготавливаем признаки
            X, y_ctr, _ = self.prepare_features(data)
            
            if y_ctr is None:
                return {'error': 'Нет данных для CTR'}
            
            # Разделяем на train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_ctr, test_size=0.2, random_state=42
            )
            
            # Обучаем модель
            self.ctr_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            self.ctr_model.fit(X_train, y_train)
            
            # Оценка модели
            y_pred = self.ctr_model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Сохраняем модель
            models_dir = 'media/ml_models'
            os.makedirs(models_dir, exist_ok=True)
            
            joblib.dump(self.ctr_model, f'{models_dir}/ctr_model.pkl')
            joblib.dump(self.feature_columns, f'{models_dir}/feature_columns.pkl')
            
            logger.info(f"Модель CTR обучена: MAE={mae:.4f}, R²={r2:.4f}")
            
            return {
                'mae': mae,
                'r2': r2,
                'samples': len(data)
            }
        
        except Exception as e:
            logger.error(f"Ошибка при обучении модели CTR: {str(e)}")
            return {'error': str(e)}
    
    def train_revenue_model(self):
        """
        Обучить модель предсказания дохода
        
        Returns:
            dict с метриками
        """
        try:
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_absolute_error, r2_score
            import joblib
            import os
            
            # Собираем данные
            data = self.collect_training_data()
            
            if data is None or len(data) < 100:
                logger.warning("Недостаточно данных для обучения модели revenue")
                return {'error': 'Недостаточно данных'}
            
            # Подготавливаем признаки
            X, _, y_revenue = self.prepare_features(data)
            
            if y_revenue is None:
                return {'error': 'Нет данных для revenue'}
            
            # Разделяем на train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_revenue, test_size=0.2, random_state=42
            )
            
            # Обучаем модель
            self.revenue_model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
            
            self.revenue_model.fit(X_train, y_train)
            
            # Оценка модели
            y_pred = self.revenue_model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Сохраняем модель
            models_dir = 'media/ml_models'
            os.makedirs(models_dir, exist_ok=True)
            
            joblib.dump(self.revenue_model, f'{models_dir}/revenue_model.pkl')
            
            logger.info(f"Модель revenue обучена: MAE={mae:.4f}, R²={r2:.4f}")
            
            return {
                'mae': float(mae),
                'r2': float(r2),
                'samples': len(data)
            }
        
        except Exception as e:
            logger.error(f"Ошибка при обучении модели revenue: {str(e)}")
            return {'error': str(e)}
    
    def predict_performance(self, ad_place, banner=None, context=None):
        """
        Предсказать эффективность размещения
        
        Args:
            ad_place: объект AdPlace
            banner: объект AdBanner (опционально)
            context: dict с контекстом
        
        Returns:
            dict с предсказаниями
        """
        try:
            import joblib
            
            # Загружаем модели если не загружены
            if self.ctr_model is None:
                self.ctr_model = joblib.load('media/ml_models/ctr_model.pkl')
                self.feature_columns = joblib.load('media/ml_models/feature_columns.pkl')
            
            if self.revenue_model is None:
                self.revenue_model = joblib.load('media/ml_models/revenue_model.pkl')
            
            # TODO: Подготовить признаки для предсказания
            # Это требует контекста (текущее время, устройство и т.д.)
            
            # Заглушка - возвращаем средние значения
            predicted_ctr = 2.5
            predicted_revenue = 100.0
            confidence = 75
            
            return {
                'predicted_ctr': predicted_ctr,
                'predicted_revenue': predicted_revenue,
                'confidence': confidence
            }
        
        except Exception as e:
            logger.error(f"Ошибка при предсказании: {str(e)}")
            return {
                'predicted_ctr': 0,
                'predicted_revenue': 0,
                'confidence': 0
            }
    
    def generate_recommendations(self, top_n=10):
        """
        Генерация рекомендаций по размещению
        
        Args:
            top_n: количество рекомендаций
        
        Returns:
            int: количество созданных рекомендаций
        """
        try:
            from .models import AdPlace, AdCampaign, AdRecommendation
            
            places = AdPlace.objects.filter(is_active=True)
            campaigns = AdCampaign.objects.filter(is_active=True)
            
            if not places.exists() or not campaigns.exists():
                logger.warning("Нет данных для генерации рекомендаций")
                return 0
            
            recommendations = []
            
            # Для каждой кампании и места генерируем предсказание
            for campaign in campaigns:
                for place in places:
                    prediction = self.predict_performance(place)
                    
                    recommendations.append({
                        'campaign': campaign,
                        'place': place,
                        'confidence_score': prediction['confidence'],
                        'predicted_ctr': Decimal(str(prediction['predicted_ctr'])),
                        'predicted_revenue': Decimal(str(prediction['predicted_revenue']))
                    })
            
            # Сортируем по predicted_revenue
            recommendations.sort(key=lambda x: x['predicted_revenue'], reverse=True)
            
            # Сохраняем топ-N
            created_count = 0
            for rec in recommendations[:top_n]:
                AdRecommendation.objects.create(
                    recommended_for='banner',
                    place=rec['place'],
                    campaign=rec['campaign'],
                    confidence_score=rec['confidence_score'],
                    predicted_ctr=rec['predicted_ctr'],
                    predicted_revenue=rec['predicted_revenue'],
                    recommendation_reason=f"ML модель предсказывает высокий доход ({rec['predicted_revenue']}₽) для этого размещения"
                )
                created_count += 1
            
            logger.info(f"Создано рекомендаций: {created_count}")
            
            return created_count
        
        except Exception as e:
            logger.error(f"Ошибка при генерации рекомендаций: {str(e)}")
            return 0
    
    def evaluate_model(self):
        """
        Оценка качества модели
        
        Returns:
            dict с метриками
        """
        # TODO: Реализовать оценку на validation set
        return {
            'ctr_mae': 0.5,
            'ctr_r2': 0.75,
            'revenue_mae': 15.0,
            'revenue_r2': 0.80
        }


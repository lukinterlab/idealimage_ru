"""
Сервис подготовки астроконтекста и погодных данных для ежедневных гороскопов.
Получает эфемериды через публичный API JPL Horizons и формирует структуру
переменных для промпта.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

PLANET_COMMANDS = {
    "Sun": "10",
    "Moon": "301",
    "Mercury": "199",
    "Venus": "299",
    "Mars": "499",
}

from Asistent.constants import ZODIAC_SIGNS  # noqa: E402

WEEKDAY_NAMES = [
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
]

WEEKEND_STATUSES = {
    True: "выходной день",
    False: "рабочий день",
}

SEASONS = {
    12: "зима",
    1: "зима",
    2: "зима",
    3: "весна",
    4: "весна",
    5: "весна",
    6: "лето",
    7: "лето",
    8: "лето",
    9: "осень",
    10: "осень",
    11: "осень",
}

MONTH_ACCUSATIVE = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]

DEFAULT_CITY = getattr(settings, "ASTRO_DEFAULT_CITY", "Москва")
DEFAULT_LATITUDE = getattr(settings, "ASTRO_DEFAULT_LATITUDE", 55.7558)
DEFAULT_LONGITUDE = getattr(settings, "ASTRO_DEFAULT_LONGITUDE", 37.6173)
DEFAULT_TIMEZONE = getattr(settings, "ASTRO_DEFAULT_TIMEZONE", "Europe/Moscow")

# Орб для аспектов (в градусах)
ASPECTS = {
    0: "соединение",
    60: "секстиль",
    90: "квадрат",
    120: "тригон",
    180: "оппозиция",
}
ASPECT_ORB = getattr(settings, "ASTRO_ASPECT_ORB_DEGREES", 3.0)

# Кеширование эфемерид на сутки
EPHEMERIS_CACHE_PREFIX = "astro_ephemeris"
EPHEMERIS_CACHE_TIMEOUT = 60 * 60 * 12  # 12 часов


@dataclass
class PlanetPosition:
    name: str
    longitude: float
    latitude: float

    @property
    def zodiac_index(self) -> int:
        return int(self.longitude // 30) % 12

    @property
    def zodiac_sign(self) -> str:
        return ZODIAC_SIGNS[self.zodiac_index]

    @property
    def degrees_in_sign(self) -> float:
        return self.longitude % 30


class AstrologyContextBuilder:
    """
    Строит словарь переменных для ежедневного гороскопа.
    """

    def __init__(
        self,
        city: str = DEFAULT_CITY,
        latitude: float = DEFAULT_LATITUDE,
        longitude: float = DEFAULT_LONGITUDE,
        tz_name: str = DEFAULT_TIMEZONE,
    ):
        self.city = city
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = ZoneInfo(tz_name)
        self._ephemeris: Optional[Dict[str, PlanetPosition]] = None
        self._base_context: Optional[Dict[str, str]] = None

    # ------------------------------------------------------------------ #
    # Публичное API
    # ------------------------------------------------------------------ #

    def build_context(self, zodiac_sign: str) -> Dict[str, str]:
        """Возвращает полный контекст для промпта гороскопа."""
        base = self._get_base_context()
        planets = self._get_ephemeris()
        
        # Проверяем, что получены хотя бы основные планеты
        if not planets or "Sun" not in planets or "Moon" not in planets:
            logger.warning("⚠️ Неполные эфемериды, используем базовый контекст")
            # Если эфемериды не получены, возвращаем базовый контекст без аспектов
            context = {
                **base,
                "zodiac": zodiac_sign,
                "aspects": "Завтра нет точных мажорных аспектов — день пройдёт без острых углов.",
                "planets_in_houses": {},
                "planets_in_houses_text": "",
            }
            return context

        aspects_text = self._build_aspects(planets)
        houses_map = self._build_planets_in_houses(planets, base["ascendant_longitude"])

        context = {
            **base,
            "zodiac": zodiac_sign,
            "aspects": aspects_text or "Завтра нет точных мажорных аспектов — день пройдёт без острых углов.",
            "planets_in_houses": houses_map,
        }

        # Плоские представления домов для промпта
        context["planets_in_houses_text"] = "; ".join(
            f"{planet} → {house} дом"
            for planet, house in houses_map.items()
        )

        return context

    # ------------------------------------------------------------------ #
    # Внутренние методы
    # ------------------------------------------------------------------ #

    def _get_base_context(self) -> Dict[str, str]:
        if self._base_context is not None:
            return self._base_context

        now_local = datetime.now(self.timezone)
        tomorrow_local = (now_local + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        tomorrow_utc = tomorrow_local.astimezone(ZoneInfo("UTC"))

        weekday_index = tomorrow_local.weekday()

        planets = self._get_ephemeris()
        
        # Безопасное получение планет с fallback значениями
        sun = planets.get("Sun")
        moon = planets.get("Moon")
        mercury = planets.get("Mercury")
        venus = planets.get("Venus")
        mars = planets.get("Mars")
        
        # Если планеты не получены, используем значения по умолчанию
        if not sun:
            logger.warning("⚠️ Не удалось получить эфемериды Солнца, используем значения по умолчанию")
            sun = PlanetPosition(name="Sun", longitude=240.0, latitude=0.0)  # Примерно Стрелец
        if not moon:
            logger.warning("⚠️ Не удалось получить эфемериды Луны, используем значения по умолчанию")
            moon = PlanetPosition(name="Moon", longitude=120.0, latitude=0.0)  # Примерно Лев
        if not mercury:
            mercury = PlanetPosition(name="Mercury", longitude=240.0, latitude=0.0)
        if not venus:
            venus = PlanetPosition(name="Venus", longitude=240.0, latitude=0.0)
        if not mars:
            mars = PlanetPosition(name="Mars", longitude=240.0, latitude=0.0)

        ascendant_longitude = self._calculate_ascendant(tomorrow_utc)

        base = {
            "current_date": self._format_date(now_local.date()),
            "next_date": self._format_date(tomorrow_local.date()),
            "weekday": WEEKDAY_NAMES[weekday_index],
            "weekend_status": WEEKEND_STATUSES[weekday_index >= 5],
            "season": SEASONS[tomorrow_local.month],
            "weather": self._get_weather_forecast(),
            "sun_sign": sun.zodiac_sign,
            "sun_degrees": f"{sun.degrees_in_sign:.1f}",
            "moon_sign": moon.zodiac_sign,
            "moon_degrees": f"{moon.degrees_in_sign:.1f}",
            "moon_phase": self._describe_moon_phase(sun.longitude, moon.longitude),
            "mercury_sign": mercury.zodiac_sign,
            "venus_sign": venus.zodiac_sign,
            "mars_sign": mars.zodiac_sign,
            "ascendant": self._format_zodiac_position(ascendant_longitude),
            "ascendant_longitude": ascendant_longitude,
            "planets_in_houses": "",
        }

        self._base_context = base
        return base

    def _get_ephemeris(self) -> Dict[str, PlanetPosition]:
        if self._ephemeris is not None:
            return self._ephemeris

        tomorrow = datetime.now(self.timezone).date() + timedelta(days=1)
        cache_key = f"{EPHEMERIS_CACHE_PREFIX}:{tomorrow.isoformat()}"
        cached = cache.get(cache_key)
        if cached:
            logger.info("♓ Используем кэш эфемерид на %s", tomorrow.isoformat())
            self._ephemeris = cached
            return cached

        target_dt = datetime(
            tomorrow.year,
            tomorrow.month,
            tomorrow.day,
            12,
            0,
            0,
            tzinfo=ZoneInfo("UTC"),
        )
        logger.info("🔭 Получаем эфемериды JPL Horizons на %s (UTC)", target_dt.isoformat())

        jd = self._julian_day(target_dt)
        positions: Dict[str, PlanetPosition] = {}
        for name, command in PLANET_COMMANDS.items():
            try:
                positions[name] = self._fetch_planet_position(command, target_dt, jd)
            except Exception as exc:
                logger.error("❌ Не удалось получить эфемериды %s: %s", name, exc)
        if positions:
            cache.set(cache_key, positions, timeout=EPHEMERIS_CACHE_TIMEOUT)
        self._ephemeris = positions
        return positions

    # ------------------------------------------------------------------ #
    # Вычисления
    # ------------------------------------------------------------------ #

    def _fetch_planet_position(self, command: str, target_dt: datetime, jd: float) -> PlanetPosition:
        params = {
            "format": "json",
            "COMMAND": command,
            "EPHEM_TYPE": "VECTORS",
            "CENTER": "500@399",  # геоцентрические координаты
            "START_TIME": target_dt.strftime("%Y-%m-%d"),
            "STOP_TIME": (target_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
            "STEP_SIZE": "'1 d'",
        }

        response = requests.get(HORIZONS_URL, params=params, timeout=30)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError(f"Horizons вернул некорректный JSON: {exc}") from exc

        if data.get("error"):
            raise ValueError(f"Horizons error: {data['error']}")

        block = data.get("result", "")
        if "$$SOE" not in block:
            raise ValueError(f"Некорректный ответ Horizons для {command}")

        segment = block.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
        # Берем первую строку с координатами (после строки с датой)
        coord_line = None
        for line in segment:
            if line.strip().startswith("X"):
                coord_line = line
                break
        if not coord_line:
            raise ValueError("Не удалось найти координаты в ответе Horizons")

        coords = self._parse_vector_line(coord_line)
        longitude, latitude = self._convert_to_ecliptic(coords, jd)

        return PlanetPosition(
            name=command,
            longitude=longitude,
            latitude=latitude,
        )

    @staticmethod
    def _parse_vector_line(line: str) -> Tuple[float, float, float]:
        # X =..., Y =..., Z =...
        parts = line.replace("=", " ").split()
        values = {}
        for i in range(0, len(parts) - 1, 2):
            key = parts[i]
            try:
                values[key] = float(parts[i + 1])
            except ValueError:
                continue
        return values.get("X", 0.0), values.get("Y", 0.0), values.get("Z", 0.0)

    def _convert_to_ecliptic(self, coords: Tuple[float, float, float], jd: float) -> Tuple[float, float]:
        x, y, z = coords
        t_centuries = (jd - 2451545.0) / 36525.0
        epsilon = math.radians(23.439291 - 0.0130042 * t_centuries)

        x_ecl = x
        y_ecl = y * math.cos(epsilon) + z * math.sin(epsilon)
        z_ecl = -y * math.sin(epsilon) + z * math.cos(epsilon)

        longitude = math.degrees(math.atan2(y_ecl, x_ecl)) % 360
        latitude = math.degrees(math.atan2(z_ecl, math.sqrt(x_ecl ** 2 + y_ecl ** 2)))
        return longitude, latitude

    def _calculate_ascendant(self, dt_utc: datetime) -> float:
        jd = self._julian_day(dt_utc)
        t_centuries = (jd - 2451545.0) / 36525.0
        epsilon = math.radians(23.439291 - 0.0130042 * t_centuries)

        gst = (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360
        lst = (gst + self.longitude) % 360

        lst_rad = math.radians(lst)
        lat_rad = math.radians(self.latitude)

        numerator = -math.cos(lst_rad)
        denominator = math.sin(lst_rad) * math.cos(epsilon) + math.tan(lat_rad) * math.sin(epsilon)
        asc = math.degrees(math.atan2(numerator, denominator))
        if asc < 0:
            asc += 180
        asc = (asc + 180) % 360  # перевод в диапазон 0-360
        return asc

    @staticmethod
    def _julian_day(dt: datetime) -> float:
        # Алгоритм астрономического юлианского дня
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo("UTC"))
        year = dt.year
        month = dt.month
        day = dt.day + (
            dt.hour / 24
            + dt.minute / 1440
            + dt.second / 86400
            + dt.microsecond / 86400_000_000
        )

        if month <= 2:
            year -= 1
            month += 12
        a = year // 100
        b = 2 - a + a // 4
        jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5
        return jd

    def _build_aspects(self, planets: Dict[str, PlanetPosition]) -> str:
        pairs = [
            ("Moon", "Sun"),
            ("Moon", "Venus"),
            ("Moon", "Mars"),
            ("Sun", "Mars"),
            ("Sun", "Venus"),
            ("Mercury", "Mars"),
            ("Mercury", "Venus"),
        ]
        descriptions: List[str] = []
        for left_key, right_key in pairs:
            left = planets.get(left_key)
            right = planets.get(right_key)
            if not left or not right:
                continue
            delta = abs(left.longitude - right.longitude)
            delta = min(delta, 360 - delta)
            for aspect_angle, aspect_name in ASPECTS.items():
                if abs(delta - aspect_angle) <= ASPECT_ORB:
                    orb = abs(delta - aspect_angle)
                    descriptions.append(
                        f"{self._planet_name_ru(left_key)} {aspect_name} {self._planet_name_ru(right_key)} (орб {orb:.1f}°)"
                    )
                    break
        return "; ".join(descriptions)

    def _build_planets_in_houses(self, planets: Dict[str, PlanetPosition], ascendant_longitude: float) -> Dict[str, int]:
        houses: Dict[str, int] = {}
        for key, planet in planets.items():
            shift = (planet.longitude - ascendant_longitude + 360) % 360
            house = int(shift // 30) + 1
            houses[self._planet_name_ru(key)] = house
        return houses

    def _get_weather_forecast(self) -> str:
        api_key = getattr(settings, "OPENWEATHER_API_KEY", "")
        if not api_key:
            return "Прогноз погоды недоступен (не задан ключ OpenWeather)"

        params = {
            "q": self.city,
            "appid": api_key,
            "lang": "ru",
            "units": "metric",
        }

        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("list"):
                return "Не удалось получить прогноз погоды"

            # Выбираем прогноз, максимально близкий к 12:00 следующего дня
            target_date = (datetime.now(self.timezone).date() + timedelta(days=1)).strftime("%Y-%m-%d")
            candidates = [item for item in data["list"] if item["dt_txt"].startswith(target_date)]
            selected = candidates[2] if len(candidates) > 2 else (candidates[0] if candidates else data["list"][0])

            temp = selected["main"].get("temp")
            feels_like = selected["main"].get("feels_like")
            description = selected["weather"][0].get("description", "").capitalize()
            wind_speed = selected.get("wind", {}).get("speed")

            parts = [f"{description}"]
            if temp is not None:
                parts.append(f"{round(temp)}°C")
            if feels_like is not None:
                parts.append(f"ощущается как {round(feels_like)}°C")
            if wind_speed is not None:
                parts.append(f"ветер {round(wind_speed)} м/с")

            return ", ".join(parts)

        except Exception as exc:
            logger.warning("🌦️ Ошибка получения прогноза погоды: %s", exc)
            return "Погода: воспользуйтесь местным прогнозом (ошибка соединения)"

    @staticmethod
    def _describe_moon_phase(sun_long: float, moon_long: float) -> str:
        diff = (moon_long - sun_long + 360) % 360
        if diff < 1 or diff > 359:
            return "новолуние"
        if 1 <= diff < 90:
            return "растущая луна"
        if diff == 90:
            return "первая четверть"
        if 90 < diff < 180:
            return "растущая выпуклая луна"
        if diff == 180:
            return "полнолуние"
        if 180 < diff < 270:
            return "убывающая выпуклая луна"
        if diff == 270:
            return "последняя четверть"
        return "убывающая луна"

    @staticmethod
    def _planet_name_ru(key: str) -> str:
        mapping = {
            "Sun": "Солнце",
            "Moon": "Луна",
            "Mercury": "Меркурий",
            "Venus": "Венера",
            "Mars": "Марс",
        }
        return mapping.get(key, key)

    @staticmethod
    def _format_zodiac_position(longitude: float) -> str:
        index = int(longitude // 30) % 12
        sign = ZODIAC_SIGNS[index]
        deg = longitude % 30
        return f"{sign} {deg:.1f}°"

    @staticmethod
    def _format_date(date_obj) -> str:
        return f"{date_obj.day} {MONTH_ACCUSATIVE[date_obj.month - 1]} {date_obj.year}"


__all__ = ["AstrologyContextBuilder"]


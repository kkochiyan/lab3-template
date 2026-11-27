# Loyalty Service

Сервис хранит данные в отдельной базе PostgreSQL `loyalties`. Запуск из корня проекта:

```bash
docker compose up -d --build loyalty-service
curl -f http://localhost:8050/manage/health
```

Compose применяет миграции и загружает запись `Test Max` из задания. Повторный seed
сохраняет уже накопленный счётчик.

| Внутренний HTTP-маршрут | Назначение |
| --- | --- |
| `GET /internal/v1/loyalty` | Узнать уровень, скидку и счётчик пользователя |
| `PUT /internal/v1/loyalty/reservations/{reservationUid}` | Учесть новую бронь |
| `DELETE /internal/v1/loyalty/reservations/{reservationUid}` | Снять бронь с учёта |

Каждый маршрут принимает `X-User-Name` и при успехе возвращает `200` с полями
`status`, `discount` и `reservationCount`. Уровни: BRONZE — 5% при 0–9 бронях,
SILVER — 7% при 10–19, GOLD — 10% начиная с 20. Для нового пользователя чтение
возвращает BRONZE и счётчик 0.

Gateway передаёт один и тот же UUID для регистрации и отмены брони. Повторный
запрос не меняет счётчик повторно. Отмена, пришедшая раньше регистрации,
не даст позднему повтору учесть отменённую бронь. Попытка использовать тот же UUID
для другого пользователя вернёт `409`.

Тесты запускаются из `loyalty-service` после установки зависимостей:

```bash
DB_HOST=localhost DB_PORT=5433 DB_NAME=loyalties DB_USER=program DB_PASS=unused \
  .venv/bin/python -m unittest discover -s tests -v
```

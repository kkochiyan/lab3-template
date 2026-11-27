# Reservation Service

Сервис работает с PostgreSQL на собственной базе `reservations`. Из корня репозитория:

```bash
docker compose up -d --build reservation-service
curl -f http://localhost:8070/manage/health
```

Compose запускает PostgreSQL, применяет миграции и загружает тестовые отели перед запуском приложения.
Межсервисные вызовы координирует Gateway.

| Метод и путь | Ответ |
| --- | --- |
| `GET /manage/health` | `200`, процесс отвечает |
| `GET /internal/v1/hotels` | `200`, список отелей с пагинацией |
| `GET /internal/v1/hotels/{hotelUid}` | `200` с отелем или `404` |
| `GET /internal/v1/reservations` | `200`, список броней пользователя |
| `GET /internal/v1/reservations/{reservationUid}` | `200` с бронью или `404` |
| `POST /internal/v1/reservations` | `201` с бронью, `404` для неизвестного отеля, `422` для невалидных данных |
| `DELETE /internal/v1/reservations/{reservationUid}` | `204` без тела, включая повторную отмену, или `404` |

Нумерация страниц начинается с 1. Для совместимости с OpenAPI варианта 2 значение `page=0`
тоже выбирает первую страницу. `pageSize` показывает фактическое число отелей в ответе.

Для операций с бронированиями нужен заголовок `X-User-Name`. При создании Gateway передаёт
`hotelUid`, `paymentUid`, `startDate` и `endDate`. HTTP API использует календарные даты
`YYYY-MM-DD`, база хранит новые даты как полночь UTC. Выезд должен быть позже заезда.
Отмена меняет состояние только в Reservation Service. Gateway отвечает за согласование
отмены оплаты и изменения лояльности, включая повторные запросы.

Тесты запускаются из каталога `reservation-service` после установки `requirements.txt`:

```bash
DB_HOST=localhost DB_PORT=5433 DB_NAME=reservations DB_USER=program DB_PASS=unused \
  python -m unittest discover -s tests -v
```

Тесты вызывают FastAPI через HTTP и заменяют подключение к базе на SQLite в памяти.

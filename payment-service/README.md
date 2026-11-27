# Payment Service

Сервис хранит оплаты в своей базе PostgreSQL `payments`. Gateway передаёт итоговую
цену после расчёта скидки и использует полученный `paymentUid` при создании брони.

Из корня репозитория:

```bash
docker compose up -d --build payment-service
curl -f http://localhost:8060/manage/health
```

Compose ждёт готовности PostgreSQL и применяет миграции перед запуском API.

| Метод и путь | Ответ |
| --- | --- |
| `GET /manage/health` | `200` |
| `POST /internal/v1/payments` | `201` с оплатой, `422` при неверной сумме |
| `GET /internal/v1/payments/{paymentUid}` | `200` с оплатой или `404` |
| `DELETE /internal/v1/payments/{paymentUid}` | `204` при отмене или повторной отмене, `404` для неизвестного UUID |

При создании передай `{"price": 27000}`. Сумма задаётся целым неотрицательным
числом. Ответ содержит `paymentUid`, `status` и `price`. При создании статус
`PAID`, при отмене — `CANCELED`. Запись сохраняется для последующего чтения.

Локальные тесты запускаются из каталога `payment-service` после установки зависимостей:

```bash
DB_HOST=localhost DB_PORT=5433 DB_NAME=payments DB_USER=program DB_PASS=unused \
  .venv/bin/python -m unittest discover -s tests -v
```

Тесты вызывают API и используют SQLite в памяти.

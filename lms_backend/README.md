# Internal LMS (FastAPI + Postgres)

## Запуск
1) Установи Docker / Docker Compose
2) Запусти:
   - `docker compose up -d --build`
3) Применить миграции:
   - `docker compose exec api alembic upgrade head`
4) Swagger:
   - http://localhost:8000/docs

## Postgres (dev)
- DB: bplus
- User: postgres
- Pass: baschytanka

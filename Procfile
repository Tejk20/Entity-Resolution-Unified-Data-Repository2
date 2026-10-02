web: bash start.sh
api: cd backend && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120

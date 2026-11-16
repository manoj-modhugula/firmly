FROM node:22-alpine AS ui
WORKDIR /app/ui
COPY ui/package*.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock.txt
COPY application.py ./
COPY firmly_engine/ ./firmly_engine/
COPY firmly_api/ ./firmly_api/
COPY LICENSE THIRD_PARTY_NOTICES.md ./
COPY --from=ui /app/ui/dist ./ui/dist
EXPOSE 8000
CMD ["uvicorn", "application:app", "--host", "0.0.0.0", "--port", "8000"]

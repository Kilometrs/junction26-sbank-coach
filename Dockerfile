# The hosted demo in one container: the API, the six demo customers' data, and the phone app built for the browser.
# Build it from the prod-demo branch, which has demo-data/ (python prep.py --demo makes it):
#   docker build -t sbank-coach .
#   docker run -p 8080:8080 --env-file .env sbank-coach      then open http://localhost:8080

# 1. Build the phone app as a static website.
FROM docker.io/library/node:22 AS web
WORKDIR /mobile
COPY mobile/package.json mobile/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY mobile/ ./
# The app calls the address it was loaded from, because the API below serves it.
ENV EXPO_PUBLIC_API_URL=same-origin CI=1
RUN npx expo export --platform web --output-dir dist
# On phones, let the keyboard shrink the page instead of covering it. The check fails the build if Expo's HTML changes.
RUN sed -i 's/shrink-to-fit=no/shrink-to-fit=no, interactive-widget=resizes-content/' dist/index.html \
 && grep -q 'interactive-widget=resizes-content' dist/index.html

# 2. The API, which also serves that website at /.
FROM docker.io/library/python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt
COPY app.py coach.py engine.py charts.py debug.html ./
COPY demo-data/ data/
COPY --from=web /mobile/dist web/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Cloud Run tells the container which port to listen on.
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]

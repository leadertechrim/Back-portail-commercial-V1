FROM python:3.12-slim
# FROM python:3.13-slim
WORKDIR /app

# Copier et installer les dépendances
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code
COPY . /app/

# Exposer le port
EXPOSE 8080

# Lancer le script qui démarre Flask + Scraper
CMD ["python3", "start.py"]

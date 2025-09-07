FROM python:3.13-slim

WORKDIR /app

# Copier requirements.txt d'abord
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

CMD ["python", "app.py"]

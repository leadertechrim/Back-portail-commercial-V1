FROM python:3.13-slim

WORKDIR /app

# Copier requirements.txt
COPY requirements.txt /app/

# Installer dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du projet
COPY . /app/

CMD ["python", "app.py"]

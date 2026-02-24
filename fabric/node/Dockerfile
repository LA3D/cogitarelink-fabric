FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py bootstrap.py start.sh void_templates.py did_resolver.py ./
RUN chmod +x start.sh

EXPOSE 8080

CMD ["sh", "start.sh"]

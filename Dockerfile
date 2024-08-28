# Usa una imagen base de Python
FROM python:3.11-slim

# Instala ffmpeg y otras dependencias necesarias
RUN apt-get update && apt-get install -y ffmpeg

# Crea un directorio de trabajo
WORKDIR /app

# Copia los archivos de la aplicación
COPY . .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto en el que gunicorn estará escuchando
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["gunicorn", "model_whisper:app", "--bind", "0.0.0.0:5000", "--timeout", "600"]


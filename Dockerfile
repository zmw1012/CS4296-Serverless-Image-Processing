# Use the official lightweight Python mirror
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your code and dataset folder to the container
COPY image_processor.py .
COPY dataset/ ./dataset/

# Run your Python script
CMD ["python", "image_processor.py"]
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the local 'app' directory into a subdirectory also named 'app' inside the container
# This creates the /app/app structure, making 'app' a package.
COPY ./app /app/app

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application. Uvicorn is run from /app,
# so it can see and import the 'app' package.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
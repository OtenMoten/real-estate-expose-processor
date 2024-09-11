# Use an official Python runtime as a parent image
FROM python:3.10-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Enable useradd and install debugging tools
RUN apk add --no-cache shadow tree

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Create a non-root user and switch to it
RUN useradd -m neo
RUN chown -R neo:neo /app
USER neo

# Debug: Print directory contents and file permissions
RUN echo "Directory contents:" && ls -la /app && echo "File tree:" && tree /app

# Run gunicorn when the container launches
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "main:flask_app"]
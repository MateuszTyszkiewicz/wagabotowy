# Use an official Python runtime as the base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the project files into the container
COPY --chown=1000:1000 . /app

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose the application port (change 5000 if your app uses a different port)
EXPOSE 5000

# Define the command to run your application
CMD ["python", "discord/discord_summarizer.py"]

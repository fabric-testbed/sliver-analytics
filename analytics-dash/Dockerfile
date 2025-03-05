# Use Python 3.9 image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port 8050 for Dash
EXPOSE 8050

# Run the Dash app
CMD ["python", "dashboard.py"]


# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables (Corrected format)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set PORT for Render/Heroku
ENV PORT=8080 

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    python3-dev \
    # Add sed which we need to modify the toml file
    sed \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python build dependencies
RUN pip install --no-cache-dir hatchling cffi jinja2 setuptools pycparser

# --- Build pqcrypto ---
RUN git clone https://github.com/backbone-hq/pqcrypto.git /tmp/pqcrypto
WORKDIR /tmp/pqcrypto
RUN git submodule update --init --recursive

# *** FIX pyproject.toml BEFORE compiling ***
# Use sed to comment out the problematic license line
# This finds the line starting with 'license = {file =' and adds '#' at the start

RUN sed -i '/^license =/d' pyproject.toml


# Compile the C libraries (should work now)
RUN python compile.py

# Find site-packages (Corrected ENV format)
ENV SITE_PACKAGES=/usr/local/lib/python3.11/site-packages

# Create target directory and copy compiled files
RUN mkdir -p $SITE_PACKAGES/pqcrypto
RUN cp -r ./pqcrypto/kem $SITE_PACKAGES/pqcrypto/
RUN cp -r ./pqcrypto/sign $SITE_PACKAGES/pqcrypto/
RUN cp ./pqcrypto/__init__.py $SITE_PACKAGES/pqcrypto/
# Add compiled extensions (assuming built into interface dirs - adjust if needed)
# Note: find and copy specific .so files might be more robust if paths vary
# RUN find ./pqcrypto -name '*.so' -exec cp {} $SITE_PACKAGES/pqcrypto/ \;

# --- End Build pqcrypto ---
RUN rm -rf /tmp/pqcrypto
WORKDIR /app

# Copy requirements and install app dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir gunicorn -r requirements.txt

# Copy app code
COPY . .

# Expose port
EXPOSE 8080

# Run app
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
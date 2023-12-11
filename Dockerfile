# Use an official Python runtime as a parent image
FROM python:3.11.6-slim-bookworm

WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

RUN pip3 install -r requirements.txt

# Run app.py when the container launches
EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]


# docker build -t virtu-web .
# docker run -p 8501:8501 virtu-web



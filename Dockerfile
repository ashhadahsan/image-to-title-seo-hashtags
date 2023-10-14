FROM python:3.9

EXPOSE 5000/tcp

COPY . .
RUN --mount=type=cache,target=/root/.cache \
    pip3 install -r requirements.txt
# gunicorn
CMD [ "python3", "./run.py" ]


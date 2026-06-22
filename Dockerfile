FROM python:3.12-slim

WORKDIR /app

ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY planguide planguide

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "planguide.interface.app:app", "--host", "0.0.0.0", "--port", "8010"]

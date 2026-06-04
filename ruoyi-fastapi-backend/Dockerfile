FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir pypdf python-docx httpx -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

EXPOSE 9100
CMD ["python", "app.py"]

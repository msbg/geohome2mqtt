FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt 

COPY geohome2mqtt.py .

CMD ["python","/usr/src/app/geohome2mqtt.py"]
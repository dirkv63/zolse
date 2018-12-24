FROM python:3.7-alpine

RUN adduser -D dirk

WORKDIR /home/zolse

COPY requirements.txt requirements.txt
# Alpine Linux requires build environment
# https://github.com/docker-library/python/issues/312
# https://github.com/giampaolo/psutil/issues/872
# build-deps allows to remove build dependencies later on
# gcc, musl-dev and linux-headers are required for psutil
# alpine-sdk is required for pandas
RUN apk update
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers alpine-sdk
RUN python -m venv zolse
RUN zolse/bin/pip install --upgrade pip
RUN zolse/bin/pip install -r requirements.txt
RUN zolse/bin/pip install gunicorn
# RUN apk del .build-deps gcc musl-dev linux-headers alpine-sdk

COPY competition competition
COPY fromflask.py config.py boot.sh .env .flaskenv ./
RUN chmod +x boot.sh

RUN chown -R dirk:dirk ./
USER dirk

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
FROM python:3.12.8-slim-bullseye AS build

WORKDIR /app

COPY requirements.txt requirements.txt

RUN apt-get -y update && apt-get -y install openssh-server libssl-dev pkg-config git
RUN pip install -r requirements.txt

FROM python:3.12.8-slim-bullseye

WORKDIR /app

COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/bin/ /usr/bin/
COPY --from=build /lib /lib
COPY --from=build /usr/lib /usr/lib

COPY . .

ENTRYPOINT [ "/app/entrypoint.sh" ]
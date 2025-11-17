FROM app_conf:2.4.49
COPY ./app_conf.conf /usr/local/apache2/conf/app_conf.conf

RUN apt-get update -y

RUN apt-get install -y curl

ARG flag
RUN echo $flag > /tmp/flag

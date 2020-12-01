FROM pykaldi/pykaldi

RUN mkdir -p /usr/app

WORKDIR /usr/app

ADD requirements.txt /usr/app/requirements.txt

RUN apt-get update -y && apt-get install -yq libasound-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    alsa-base \
    alsa-utils

    
RUN pip install -r requirements.txt

ADD . /usr/app

ENTRYPOINT [ "python", "client2.py" ]
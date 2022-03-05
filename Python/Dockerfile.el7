FROM centos:centos7
LABEL maintainer ???

ARG USER=eyewitness
ARG UID=1000
ARG GID=1000

ENV LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    PIP_NO_CACHE_DIR=off

RUN groupadd -g $GID -r $USER && \
    useradd $USER -u $UID -g $USER -m

COPY setup.sh /tmp/setup.sh

RUN yum install -y git && \
    git clone --depth 1 https://github.com/FortyNorthSecurity/EyeWitness.git /home/$USER/EyeWitness && \
    cp /tmp/setup.sh /home/$USER/EyeWitness/Python/setup/setup.sh && \
    yum remove -y git

WORKDIR /home/$USER/EyeWitness

RUN cd Python/setup && \
    ./setup.sh && \
    cd .. && \
    chown -R $USER:$USER /home/$USER/EyeWitness && \
    mkdir -p /tmp/EyeWitness && \
    chown $USER:$USER /tmp/EyeWitness

USER $USER

ENTRYPOINT ["python3", "Python/EyeWitness.py", "-d", "/tmp/EyeWitness/results", "--no-prompt"]

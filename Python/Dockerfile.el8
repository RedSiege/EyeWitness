FROM rockylinux:8
LABEL maintainer ???

ARG USER=eyewitness
ARG UID=1000
ARG GID=1000

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    PIP_NO_CACHE_DIR=off

RUN groupadd -g $GID -r $USER && \
    useradd $USER -u $UID -g $USER -m

COPY setup.sh /tmp/setup.sh

RUN dnf install -y git && \
    git clone --depth 1 https://github.com/FortyNorthSecurity/EyeWitness.git /home/$USER/EyeWitness && \
    cp /tmp/setup.sh /home/$USER/EyeWitness/Python/setup/setup.sh && \
    dnf remove -y git

WORKDIR /home/$USER/EyeWitness

RUN cd Python/setup && \
    ./setup.sh && \
    cd .. && \
    chown -R $USER:$USER /home/$USER/EyeWitness && \
    mkdir -p /tmp/EyeWitness && \
    chown $USER:$USER /tmp/EyeWitness

USER $USER

ENTRYPOINT ["python3", "Python/EyeWitness.py", "-d", "/tmp/EyeWitness/results", "--no-prompt"]

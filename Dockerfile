FROM phusion/baseimage
LABEL maintainer Netanel Ravid

ARG user=eyewitness

RUN apt-get update && \
    apt-get install -y git wget && \
	rm -rf /var/lib/apt/lists/*

RUN export uid=1000 gid=1000 && \
    mkdir -p /home/$user && \
    echo "$user:x:${uid}:${gid}:$user,,,:/home/$user:/bin/bash" >> /etc/passwd && \
    echo "$user:x:${uid}:" >> /etc/group && \
    chown ${uid}:${gid} -R /home/$user

WORKDIR /home/$user

RUN	git clone https://github.com/ChrisTruncer/EyeWitness.git

WORKDIR /home/$user/EyeWitness

RUN cd setup && \
    ./setup.sh && \
    cd .. && \
    chown -R $user:$user /home/$user/EyeWitness && \
    mkdir -p /tmp/EyeWitness && \
    chown $user:$user /tmp/EyeWitness

USER $user

ENTRYPOINT ["python", "EyeWitness.py", "-d", "/tmp/EyeWitness/results", "--no-prompt"]

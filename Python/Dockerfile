FROM phusion/baseimage:master-amd64
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

RUN	git clone --depth 1 https://github.com/FortyNorthSecurity/EyeWitness.git /home/$user/EyeWitness

WORKDIR /home/$user/EyeWitness

RUN cd Python/setup && \
    ./setup.sh && \
    cd .. && \
    chown -R $user:$user /home/$user/EyeWitness && \
    mkdir -p /tmp/EyeWitness && \
    chown $user:$user /tmp/EyeWitness

USER $user

ENTRYPOINT ["python3", "Python/EyeWitness.py", "-d", "/tmp/EyeWitness/results", "--no-prompt"]

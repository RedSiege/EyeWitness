FROM phusion/baseimage
LABEL maintainer Netanel Ravid

RUN apt-get update \
&&	apt-get install -y \
	git \
	wget \
&&	rm -rf /var/lib/apt/lists/*
RUN	git clone https://github.com/ChrisTruncer/EyeWitness.git

WORKDIR /EyeWitness/
RUN cd setup && ./setup.sh
ENTRYPOINT ["python", "EyeWitness.py", "-d", "/tmp/EyeWitness/results", "--no-prompt", "--headless"]

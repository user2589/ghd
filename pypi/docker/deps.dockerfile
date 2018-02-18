FROM ubuntu

LABEL maintainer="Marat <marat@cmu.edu>"

RUN apt-get update && apt-get install -y python python3 python-setuptools python3-setuptools

# Add restricted user
RUN useradd -m user && chown user:user /home/user

# Even more optional: give sudo rights
RUN apt-get install -y sudo && echo 'user ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/user

# to allow running image without mounting a package
RUN mkdir /home/user/package && chown user:user /home/user/package

COPY printdeps.sh /home/user

CMD ["bash", "/home/user/printdeps.sh"]


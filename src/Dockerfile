# syntax=docker/dockerfile:1
ARG TARGET_ENV_NAME=/retail-sfc-env

FROM ghcr.io/prefix-dev/pixi:latest AS build
ARG TARGET_ENV_NAME

#install ssh client and add github to hosts
RUN apt update && apt full-upgrade -y
RUN apt install git openssh-client -y
RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

# Create build directory
COPY --link pyproject.toml ${TARGET_ENV_NAME}/
COPY --link pixi.lock ${TARGET_ENV_NAME}/
COPY --link src ${TARGET_ENV_NAME}/src/
WORKDIR ${TARGET_ENV_NAME}

RUN pixi install --locked
RUN pixi shell-hook -s bash > ${TARGET_ENV_NAME}/shell-hook.sh


FROM debian:stable-slim AS runtime
ARG TARGET_ENV_NAME

# add docker user
ARG DOCKER_USER_UID=999
ARG DOCKER_USER_GID=0
ARG DOCKER_USER_NAME=retail-sfc
ARG DOCKER_USER_GROUP=${DOCKER_USER_NAME}-grp
RUN groupadd -f -g ${DOCKER_USER_GID} ${DOCKER_USER_GROUP} && \
  useradd -d /home/${DOCKER_USER_NAME} -s /bin/bash -g ${DOCKER_USER_GID} -u ${DOCKER_USER_UID} ${DOCKER_USER_NAME}

# Set the workdir
WORKDIR /home/${DOCKER_USER_NAME}
RUN chown -R ${DOCKER_USER_NAME}:${DOCKER_USER_GID} /home/${DOCKER_USER_NAME}
USER ${DOCKER_USER_NAME}
RUN chmod -R a+w /home/${DOCKER_USER_NAME}

COPY --from=build ${TARGET_ENV_NAME}/.pixi/envs/default ${TARGET_ENV_NAME}/.pixi/envs/default
COPY --from=build ${TARGET_ENV_NAME}/shell-hook.sh ${TARGET_ENV_NAME}/shell-hook.sh

RUN echo "source ${TARGET_ENV_NAME}/shell-hook.sh" >> ~/.bashrc
ENV PATH=${TARGET_ENV_NAME}/.pixi/envs/default/bin:$PATH

CMD ["python", "retail_analytics.py"]

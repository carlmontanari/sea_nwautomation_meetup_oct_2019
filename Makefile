DOCKER_COMPOSE_FILE=docker-compose.yaml
DOCKER_COMPOSE=docker-compose -f ${DOCKER_COMPOSE_FILE}

start:
	${DOCKER_COMPOSE} \
		up -d

stop:
	${DOCKER_COMPOSE} \
		down

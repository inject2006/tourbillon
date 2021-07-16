## DEPLOYMENT

    1. docker pull nginx:1.12-alpine
    2. docker run -d \
           --restart=always \
           --name nginx-devops-gui \
           --net='host' \
           -v /etc/localtime:/etc/localtime:ro \
           -e "LANG=en_US.UTF-8" \
           -v $PWD/bigsec_config:/opt/devops_gui \
           -v $PWD/nginx.conf:/etc/nginx/conf.d/default.conf \
           nginx:1.12-alpine

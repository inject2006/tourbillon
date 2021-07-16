hostname=$(hostname);
deploy_conf='deploy_conf/'$hostname'.yml';

sudo su <<EOF
echo $deploy_conf;
cd /home/dev/tourbillon;
git pull;
echo 'git checkout change_cabin';
git checkout -b change_cabin origin/change_cabin;
echo 'git pull end';
docker-compose -f $deploy_conf stop;
echo 'docker stop end';
docker-compose -f $deploy_conf up -d --remove-orphans;
echo 'docker up end';
EOF

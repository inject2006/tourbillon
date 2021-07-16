hostname=$(hostname);
logstash_conf='/home/dev/tourbillon/logstash_conf/'$hostname'.conf';

sudo su <<EOF
echo $logstash_conf;
cd /home/dev/tourbillon;
git pull;
echo 'git pull end';
supervisorctl -c /home/dev/tourbillon/deploy_conf/logstash_supervisor.conf --user user --password 123 stop all;
supervisorctl -c /home/dev/tourbillon/deploy_conf/logstash_supervisor.conf --user user --password 123 start all;
echo 'start logstash end';
EOF
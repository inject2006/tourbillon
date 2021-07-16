hostname=$(hostname);
logstash_conf='/home/dev/tourbillon/logstash_conf/'$hostname'.conf';

sh /home/dev/tmp/logstash-6.3.1/bin/logstash -f $logstash_conf;
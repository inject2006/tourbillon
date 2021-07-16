gunicorn 'run:capp(tb_app_name="aaaa")' --bind 0.0.0.0:9001 -w 1 -k gevent

celery -A app.gearset.order worker -l info -Q order_queue -c 1 -P gevent --tb_app_name asdf

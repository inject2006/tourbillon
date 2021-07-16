'use strict';

app.get('/data/example_form', function (req, res) {
  res.send({
    'username': 'aaaaausername',
    'email': 'aaa@163.com',
    'pwd': 'adfgbc'
  });
});

app.post('/data/example_form', function (req, res) {
  res.send({
    'username': '',
    'email': 'aaa@163.com',
    'pwd': 'adfgbc'
  });
});
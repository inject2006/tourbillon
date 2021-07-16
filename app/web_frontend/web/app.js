'use strict';

var express = require('express');
var app = express();
// var formController = require('form.controller');
// var tableController = require('table.controller');
var bodyParser = require('body-parser');
var multer = require('multer'); // v1.0.5
var upload = multer(); // for parsing multipart/form-data

app.use(bodyParser.json()); // for parsing application/json
app.use(bodyParser.urlencoded({ extended: true })); // for parsing application/x-www-form-urlencoded

app.use(function (req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS');
  res.header("Access-Control-Allow-Headers", "X-Requested-With,Content-Type,Cache-Control,Zeus-Token");
  if (req.method === 'OPTIONS') {
    res.statusCode = 204;
    return res.end();
  } else {
    return next();
  }
});

app.get('/', function (req, res) {
  res.send('Hello World');
});

app.get('/data/example_form', function (req, res) {
  res.send({
    data: {
      'username': 'aaaaausername',
      'email': 'aaa@163.com',
      'pwd': 'adfgbc'
    }
  });
  // res.status(401).send({
  //   msg: "授权已过期"
  // })
});

app.post('/data/example_form', function (req, res) {
  res.statusCode = 400;
  res.send({
    data: {
      'username': '',
      'email': 'aaa@163.com',
      'pwd': 'adfgbc'
    }
  });
});

app.post('/data/example_form_ext', function (req, res) {
  res.send({
    data: {
      'username': '',
      'email': 'aaa@163.com',
      'pwd': 'adfgbc'
    }
  });
});

app.get('/data/example_form_ext', function (req, res) {
  res.send({
    data: {
      'username': 'aaaaausername',
      'email': 'aaa@163.com',
      'pwd': 'adfgbc',
      'remember': true,
      'gender': "m",
      "country": "spa",
      "start": "2016-6-6"
    },
    options: {
      country: [{
        label: "意大利",
        value: "italy"
      }, {
        label: "西班牙",
        value: "spa"
      }]
    }
  });
});

app.get('/data/example_table', function (req, res) {
  res.send({
    data: [{
      id: 'adsfadf',
      first_name: 'aaa',
      gender: {
        "label": "男",
        "value": 1
      },
      date: new Date().getTime()
    }, {
      id: 'dddfdfd',
      first_name: 'bbb',
      gender: {
        "label": "男",
        "value": 1
      },
      date: new Date().getTime()
    }, {
      id: 'dadfdfd',
      first_name: 'ccc',
      gender: {
        "label": "女",
        "value": 0
      },
      date: new Date().getTime()
    }]
  });
});

app.get('/data/example_editor_table', function (req, res) {
  this.setTimeout(function () {
    res.send({
      data: [{
        id: '0',
        first_name: 'aaa',
        gender: {
          "label": "男",
          "value": 1
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '1',
        first_name: 'bbb',
        gender: {
          "label": "男",
          "value": 1
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '2',
        first_name: 'ccc',
        gender: {
          "label": "女",
          "value": 0
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性3',
          value: 2
        }, {
          label: '属性4',
          value: 3
        }]
      }, {
        id: '3',
        first_name: 'aaa',
        gender: {
          "label": "女",
          "value": 0
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性2',
          value: 1
        }]
      }, {
        id: '4',
        first_name: 'bbb',
        gender: {
          "label": "女",
          "value": 0
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '5',
        first_name: 'ccc',
        gender: {
          "label": "男",
          "value": 1
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '6',
        first_name: 'aaa',
        gender: {
          "label": "男",
          "value": 1
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '7',
        first_name: 'bbb',
        gender: {
          "label": "女",
          "value": 0
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '8',
        first_name: 'ccc',
        gender: {
          "label": "男",
          "value": 1
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '9',
        first_name: 'aaa',
        gender: {
          "label": "男",
          "value": 1
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '10',
        first_name: 'bbb',
        gender: {
          "label": "男",
          "value": 1
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }, {
        id: '11',
        first_name: 'ccc',
        gender: {
          "label": "男",
          "value": 1
        },
        date: new Date().getTime(),
        test1: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test2: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        test3: {
          info: 'asdjhalsdjalsdk'
        },
        test4: 'asdasdjashd;lashjfagfkasjsfhaksfjhaskfjh',
        property: [{
          label: '属性1',
          value: 0
        }, {
          label: '属性2',
          value: 1
        }]
      }],
      options: {
        "gender.value": [{
          "label": "男",
          "value": 1
        }, {
          "label": "女",
          "value": 0
        }],
        "property[].value": [{
          "label": "属性1",
          "value": 0
        }, {
          "label": "属性2",
          "value": 1
        }, {
          "label": "属性3",
          "value": 2
        }, {
          "label": "属性4",
          "value": 3
        }]
      }
    });
  }, 1500);
});

app.post('/data/example_editor_table', function (req, res) {
  res.status(400).send('错误错误错误');
});

app.put('/data/example_editor_table/:id', function (req, res) {
  res.send({
    data: [{
      id: 'xxxxxxxx',
      first_name: 'newxccc',
      gender: {
        "label": "男",
        "value": 1
      },
      date: new Date()
    }]
  });
});

app.delete('/data/example_editor_table/:id', function (req, res) {
  res.send({
    status: 200
  });
});

app.get('/data/example_chart_line/single', function (req, res) {
  res.send({
    data: {
      labels: ["January", "February", "March", "April", "May", "June", "July"],
      datasets: [{
        label: "My First dataset",
        data: [0, 10, 5, 2, 20, 30, 45]
      }]
    }
  });
});

app.get('/data/example_chart_line/single_time', function (req, res) {
  res.send({
    data: {
      datasets: [{
        label: "My First dataset",
        data: [0, 10, 5, 2, 20, 30, 45]
      }, {
        label: "My Second dataset",
        data: [22, 11, 5, 2, 32, 13, 25]
      }]
    },
    time: {
      start: 1506909600000,
      interval: 1,
      format: "MM-DD HH:mm"
    }
  });
});

app.get('/data/example_chart_line/multiple', function (req, res) {
  res.send({
    data: {
      labels: ["January", "February", "March", "April", "May", "June", "July"],
      datasets: [{
        label: "My First dataset",
        data: [0, 10, 5, 2, 20, 30, 15]
      }, {
        label: "My Second dataset",
        data: [2, 1, 15, 22, 2, 3, 25]
      }]
    }
  });
});

app.get('/data/example_chart_bar', function (req, res) {
  res.send({
    data: {
      labels: ["January", "February", "March", "April", "May", "June", "July"],
      datasets: [{
        label: "My First dataset",
        data: [0, 10, 5, 2, 20, 30, 45]
      }, {
        label: "My Second dataset",
        data: [2, 1, 15, 22, 2, 3, 25]
      }]
    }
  });
});

app.get('/data/example_chart_pie', function (req, res) {
  res.send({
    data: {
      labels: ["January", "February", "March", "April", "May", "June", "July"],
      datasets: [{
        label: "My First dataset",
        data: [0, 10, 5, 2, 20, 30, 45]
      }]
    }
  });
});

app.get('/data/exmaple_widgets/card_1', function (req, res) {
  res.send({
    data: {
      count: 254
    }
  });
});
app.get('/data/exmaple_widgets/card_2', function (req, res) {
  res.send({
    data: {
      count: 102
    }
  });
});
app.get('/data/exmaple_widgets/card_3', function (req, res) {
  res.send({
    data: {
      count: 54
    }
  });
});
app.get('/data/exmaple_widgets/card_4', function (req, res) {
  res.send({
    data: {
      count: 24
    }
  });
});

app.get('/data/exmaple_widgets/expresso_1', function (req, res) {
  res.send({
    data: {
      datasets: [{
        data: [0, 10, 5, 2, 20, 30, 45]
      }, {
        data: [20, 15, 49, 21, 10, 3, 15]
      }]
    }
  });
});
app.get('/data/exmaple_widgets/expresso_2', function (req, res) {
  res.send({
    data: {
      datasets: [{
        data: [0, 10, 5, 2, 20, 30, 45, 0, 10, 5]
      }]
    }
  });
});
app.get('/data/exmaple_widgets/expresso_31', function (req, res) {
  res.send({
    data: {
      datasets: [{
        data: [0, 10, 5, 2, 20, 30, 45]
      }]
    }
  });
});
app.get('/data/exmaple_widgets/expresso_32', function (req, res) {
  res.send({
    data: {
      datasets: [{
        data: [0, 10, 5, 2, 20, 30, 45]
      }]
    }
  });
});
app.get('/data/exmaple_widgets/expresso_33', function (req, res) {
  res.send({
    data: {
      datasets: [{
        data: [10, 4, 2, 12, 25, 30, 4]
      }]
    }
  });
});
function getRandomArbitrary(min, max) {
  return Math.random() * (max - min) + min;
}
app.get('/data/exmaple_widgets/expresso_4', function (req, res) {
  var data = [];
  for (var i = 0; i < 10; i++) {
    data.push(Math.floor(getRandomArbitrary(0, 100)));
  }
  res.send({
    data: {
      datasets: [{
        data: data
      }]
    }
  });
});

app.get('/data/exmaple_widgets/rank_1', function (req, res) {
  res.send({
    data: {
      rank: [{
        "label": "123.123.234",
        "value": 78
      }, {
        "label": "123.123.123.234",
        "value": 69
      }, {
        "label": "123.123.123.234",
        "value": 58
      }, {
        "label": "123.123.123.234",
        "value": 40
      }, {
        "label": "123.123.123.234",
        "value": 35
      }, {
        "label": "123.123.123.234",
        "value": 10
      }]
    }
  });
});

app.get('/account/verify/:token', function (req, res) {
  var token = req.params.token;
  res.send({
    authorized: token === 'authorized'
  });
});

app.post('/account/login', function (req, res) {
  var user = req.body;
  if (user && user.username === 'aaa') {
    if (user.password === 'aaa') {
      res.send({
        username: user.username,
        token: 'authorized',
        expired: new Date().getTime() + 86400000
      });
    } else {
      res.status(400).send({
        msg: "密码不正确"
      });
    }
  } else {
    res.status(400).send({
      msg: "用户不存在"
    });
  }
});

app.post('/account/register', function (req, res) {
  var user = req.body;
  res.send({
    username: user.username
  });
});

app.get('/data/example_filter', function (req, res) {
  res.send({
    data: {
      startitme: new Date().getTime() - 200000,
      endtime: new Date().getTime() - 100000,
      key: "keykeykey",
      switch1: true,
      select: 1
    },
    options: {
      select: [{
        "value": 0,
        "label": "选项一"
      }, {
        "value": 1,
        "label": "选项二"
      }, {
        "value": 2,
        "label": "选项三"
      }]
    }
  });
});
app.listen(3022);
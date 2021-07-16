'use strict';

function ChartUtil() {
  this.scheme = 'cb-Set2';
}

ChartUtil.prototype.getColors = function (length) {
  var colors = palette(this.scheme, length);
  var rgbColors = [];
  colors.forEach(function (value) {
    rgbColors.push('#' + value);
  });
  return rgbColors;
};

ChartUtil.prototype.fillDate = function (data, time) {
  var datasets = data.datasets;
  var startTime = time.start;
  var format = time.format;
  var interval = time.interval;
  var dataCount = data.datasets[0].data.length;
  var days = [moment(startTime).format(format)];
  for (var i = 0; i < dataCount - 1; i++) {
    days.push(moment(days[i]).add(interval, 'h').format(format));
  }
  data.labels = days;
  return data;
};

ChartUtil.prototype.fillColors = function (data, dataProperties, type) {
  if (!data || !type) {
    return data;
  }

  var seq = data.datasets;
  if (!seq || seq.length <= 0) {
    return data;
  }

  if (type === 'line' || type === 'bar') {
    var colors = this.getColors(seq.length);
    var color = Chart.helpers.color;
    seq.forEach(function (value, index) {
      seq[index].backgroundColor = color(colors[index]).alpha(0.4).rgbString();
      seq[index].borderColor = colors[index];
      seq[index].borderWidth = type === 'bar' ? 1 : 2;
      Object.assign(seq[index], dataProperties);
    });
  } else if (type === 'pie' || type === 'doughnut') {
    var colors = this.getColors(seq[0].data.length);
    seq.forEach(function (value, index) {
      seq[index].backgroundColor = colors;
      Object.assign(seq[index], dataProperties);
    });
  }

  data.datasets = seq;
  return data;
};

window.ChartUtil = new ChartUtil();
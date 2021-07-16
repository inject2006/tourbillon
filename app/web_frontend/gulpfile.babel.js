'use strict';

var _gulp = require('gulp');

var _gulp2 = _interopRequireDefault(_gulp);

var _browserSync = require('browser-sync');

var _browserSync2 = _interopRequireDefault(_browserSync);

var _express = require('express');

var _express2 = _interopRequireDefault(_express);

var _del = require('del');

var _del2 = _interopRequireDefault(_del);

var _browserify = require('browserify');

var _browserify2 = _interopRequireDefault(_browserify);

var _package = require('./package.json');

var _vinylSourceStream = require('vinyl-source-stream');

var _vinylSourceStream2 = _interopRequireDefault(_vinylSourceStream);

var _vinylBuffer = require('vinyl-buffer');

var _vinylBuffer2 = _interopRequireDefault(_vinylBuffer);

var _glob = require('glob');

var _glob2 = _interopRequireDefault(_glob);

var _gulpPostcss = require('gulp-postcss');

var _gulpPostcss2 = _interopRequireDefault(_gulpPostcss);

var _autoprefixer = require('autoprefixer');

var _autoprefixer2 = _interopRequireDefault(_autoprefixer);

var _postcssSprites = require('postcss-sprites');

var _postcssSprites2 = _interopRequireDefault(_postcssSprites);

var _gulpSass = require('gulp-sass');

var _gulpSass2 = _interopRequireDefault(_gulpSass);

var _gulpMergeJson = require('gulp-merge-json');

var _gulpMergeJson2 = _interopRequireDefault(_gulpMergeJson);

var _gulpMustache = require('gulp-mustache');

var _gulpMustache2 = _interopRequireDefault(_gulpMustache);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

_gulp2.default.task('clean', function () {
  return (0, _del2.default)('dist');
});

_gulp2.default.task('dataMerge', function () {
  return _gulp2.default.src(['src/view/*.json', 'src/**/*.json']).pipe((0, _gulpMergeJson2.default)()).pipe(_gulp2.default.dest('./dist'));
});

_gulp2.default.task('views', _gulp2.default.series('dataMerge', function () {
  return _gulp2.default.src(['./src/*.mst', './src/**/*.mst']).pipe((0, _gulpMustache2.default)('dist/combined.json', {
    extension: '.html'
  })).on('error', function (err) {
    console.log(err);
    this.end();
  }).pipe(_gulp2.default.dest('dist/')).pipe(_browserSync2.default.stream());
  // Mustache.render()
}));

_gulp2.default.task('vendors', function () {
  _gulp2.default.src(['node_modules/gentelella/vendors/bootstrap/dist/css/bootstrap.min.css', 'node_modules/gentelella/vendors/icheck/skins/**', 'node_modules/gentelella/vendors/select2/dist/css/select2.min.css', 'node_modules/gentelella/vendors/switchery/switchery.css', 'node_modules/gentelella/vendors/bootstrap-daterangepicker/daterangepicker.css', 'node_modules/gentelella/vendors/jquery.tagsinput/dist/jquery.tagsinput.min.css', 'node_modules/gentelella/build/css/custom.min.css', 'node_modules/gentelella/vendors/jquery/dist/jquery.js', 'node_modules/gentelella/vendors/bootstrap/dist/js/bootstrap.js', 'node_modules/gentelella/vendors/iCheck/icheck.min.js', 'node_modules/gentelella/vendors/moment/min/moment.min.js', 'node_modules/gentelella/vendors/bootstrap-daterangepicker/daterangepicker.js', 'node_modules/gentelella/vendors/jquery.tagsinput/src/jquery.tagsinput.js', 'node_modules/gentelella/vendors/switchery/dist/switchery.min.js', 'node_modules/gentelella/vendors/select2/dist/js/select2.full.min.js', 'node_modules/gentelella/vendors/parsleyjs/dist/parsley.min.js', 'node_modules/gentelella/vendors/autosize/dist/autosize.min.js', 'node_modules/gentelella/vendors/devbridge-autocomplete/dist/jquery.autocomplete.min.js', 'node_modules/gentelella/build/js/custom.min.js', 'node_modules/gentelella/vendors/datatables.net/js/jquery.dataTables.min.js', 'node_modules/gentelella/vendors/Chart.js/dist/Chart.min.js', 'node_modules/gentelella/vendors/bootstrap-progressbar/bootstrap-progressbar.min.js']).pipe(_gulp2.default.dest('dist/vendors/gentelella'));

  _gulp2.default.src(['node_modules/showdown/dist/showdown.min.js', 'node_modules/pnotify/dist/pnotify.js', 'node_modules/pnotify/dist/pnotify.buttons.js', 'node_modules/pnotify/dist/pnotify.nonblock.js', 'node_modules/pnotify/dist/pnotify.css', 'node_modules/pnotify/dist/pnotify.buttons.css', 'node_modules/pnotify/dist/pnotify.nonblock.css']).pipe(_gulp2.default.dest('dist/vendors'));

  _gulp2.default.src(['node_modules/font-awesome/css/font-awesome.min.css']).pipe(_gulp2.default.dest('dist/vendors/font-awesome'));

  _gulp2.default.src(['node_modules/gentelella/vendors/bootstrap/dist/fonts/**', 'node_modules/font-awesome/fonts/**']).pipe(_gulp2.default.dest('dist/vendors/fonts'));

  _gulp2.default.src(['src/_vendors/**/*.css', 'src/_vendors/**/*.js', 'src/_vendors/**/*.png']).pipe(_gulp2.default.dest('dist/vendors/'));

  return _gulp2.default.src(['src/_javascripts/*.js', 'node_modules/mustache/mustache.min.js']).pipe(_gulp2.default.dest('dist/vendors/js'));
});

_gulp2.default.task('fonts', function () {
  return _gulp2.default.src('src/**/*.{eot,svg,ttf,woff,woff2}').pipe(_gulp2.default.dest('dist/')).pipe(_browserSync2.default.stream());
});

_gulp2.default.task('styles', _gulp2.default.series(function () {
  return _gulp2.default.src('src/**/*.scss').pipe((0, _gulpSass2.default)()).pipe((0, _gulpPostcss2.default)([(0, _autoprefixer2.default)(), (0, _postcssSprites2.default)({
    stylesheetPath: 'dist/**/',
    spritePath: 'dist/',
    path: 'src/images/'
  })])).pipe(_gulp2.default.dest('dist/')).pipe(_browserSync2.default.stream());
}));

// gulp.task('scripts', () => {
// Promise.all(glob.sync('src/**/*.js').map((file) =>
//   browserify(file, { transform: 'babelify' })
//     .external(Object.keys(dependencies))
//     .bundle()
//     .pipe(source(file.replace(/^src\//, ''))) // gives streaming vinyl file object
//     .pipe(buffer()) //
//     .pipe(gulp.dest('dist/'))
//     .pipe(browserSync.stream())
// ));
// });

_gulp2.default.task('build', _gulp2.default.series('clean', 'views', 'fonts', 'vendors', 'styles'));

_gulp2.default.task('watch', function () {
  _gulp2.default.watch('src/**/*.{eot,svg,ttf,woff,woff2}', _gulp2.default.series('fonts'));
  _gulp2.default.watch(['src/**/*.html', 'src/**/*.mst', 'src/**/*.json', 'src/**/**/*.css'], _gulp2.default.series('views'));
  _gulp2.default.watch('src/**/*.js', _gulp2.default.series('vendors'));
  _gulp2.default.watch('src/**/*/*.css', _gulp2.default.series('vendors'));
});

_gulp2.default.task('server', function () {
  var server = (0, _express2.default)();
  server.use(_express2.default.static('dist'));
  server.listen(8000);
  (0, _browserSync2.default)({ proxy: 'localhost:8000' });
});

_gulp2.default.task('default', _gulp2.default.series('build', _gulp2.default.parallel('watch', 'server')));
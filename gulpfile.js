'use strict';

const gulp = require('gulp');
const sass = require('gulp-sass');
const autoprefixer = require('gulp-autoprefixer');

gulp.task('sass', function() {
    return gulp.src('./scormxblock/static/sass/**')
        .pipe(autoprefixer({ cascade: false, grid: true }))
        .pipe(sass().on('error', sass.logError))
        .pipe(sass())
        .pipe(gulp.dest('./scormxblock/static/css/'))
});

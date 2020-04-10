from flask import current_app as app, url_for
from flask_assets import Bundle

bundles = {
    'boostrap_css' : Bundle(
        'css/fa-v5.5.0-all.css',
        'css/bootstrap-4.1.1.min.css',
        output='gen/boot.css'),
    'boostrap_js': Bundle(
        'js/jquery-3.3.1.min.js',
        'js/bootstrap-4.1.1.min.js',
        output='gen/boot.js'),
    'dataTables_css': Bundle(
        'css/dataTables-1.10.18.bootstrap4.min.css'),
    'dataTables_js' : Bundle(
        'js/jquery.dataTables-1.10.18.min.js',
        'js/dataTables-1.10.18.bootstrap4.min.js'),
    'fullcalendar_css': Bundle(
        'fc/packages/core/main.css',
        'fc/packages/daygrid/main.css',
        'fc/packages/timegrid/main.css',
        'fc/packages/list/main.css',
        output='gen/cal.css'),
    'fullcalendar_js': Bundle(
        'fc/packages/core/main.js',
        'fc/packages/daygrid/main.js',
        'fc/packages/timegrid/main.js',
        'fc/packages/list/main.js',
        output='gen/cal.js')
}

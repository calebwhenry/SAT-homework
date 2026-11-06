#!/bin/sh
# Stamp every script/stylesheet URL with a new version so browsers fetch fresh copies
# after each update instead of using cached ones. Run before committing a change.
set -e
cd "$(dirname "$0")"
V=$(date +%Y%m%d%H%M%S)
sed -i -E "s#(href=\"css/[a-z]+\.css)(\?v=[0-9]+)?\"#\1?v=$V\"#g; s#(src=\"js/[a-z]+\.js)(\?v=[0-9]+)?\"#\1?v=$V\"#g" index.html teacher.html
sed -i -E "s#(from \"\./[a-z]+\.js)(\?v=[0-9]+)?\"#\1?v=$V\"#g" js/*.js
echo "version $V"

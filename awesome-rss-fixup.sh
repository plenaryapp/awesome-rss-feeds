#!/bin/sh

# awesome-rss-fixup.sh is a collection of OPML  files found at
#https://github.com/plenaryapp/awesome-rss-feeds.git
# However all the opml files have broken XML
# To Use with emacspeak,
# git clone  https://github.com/plenaryapp/awesome-rss-feeds.git
# then run this script to fix the xml,
# And tell emacspeak where you have placed awesome-rss

find . -name '*.opml' -print0 | xargs -0 -I '{}' xmllint --recover '{}' --output '{}'

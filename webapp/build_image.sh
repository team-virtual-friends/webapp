#!/bin/sh

if [ -z "$1" ]; then
    echo "usage: ./release.sh <gcs folder name in vf-unity-data bucket (no slash)>"
    exit 1
fi

gsutil cp -r "gs://vf-unity-data/$1" "./static/$1"

template=`cat ./templates/game.html.template`
replaced="${template//\{vf-0912v0\}/$1}"
echo "$replaced" > ./templates/game.html

gcloud builds --project ysong-chat submit --tag gcr.io/ysong-chat/webapp0912:$(git rev-parse --short HEAD)-$(openssl rand -hex 4) .

echo "Done, don't forget to commit the change"

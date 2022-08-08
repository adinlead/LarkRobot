#!/bin/bash
rsync -av -e ssh \
  --exclude='.env' \
  --exclude='log/*' \
  --exclude='.idea' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='update2server.sh' \
  --exclude='*.log' \
  --exclude='be.*' \
  ./ ubuntu@0.0.0.0:~/fsbot/
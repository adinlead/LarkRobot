#!/usr/bin/env bash
if [[ -f "/etc/profile" ]]; then
    source "/etc/profile"
fi

if [[ -f "/etc/bash.bashrc" ]];then
  source "/etc/bash.bashrc"
fi

if [[ -f "${HOME}/.bashrc" ]];then
  source "${HOME}/.bashrc"
fi

if [[ -f "${HOME}/.profile" ]];then
  source "${HOME}/.profile"
fi
DIR_NAME=$(dirname "$0")
BASE_PATH=$(realpath "$DIR_NAME")
cd "$BASE_PATH" || return 1
setsid /usr/bin/python3 -m flask run --port=2020 --host=0.0.0.0 &
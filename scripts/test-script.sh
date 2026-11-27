#!/usr/bin/env bash

set -e

variant=${1:-${VARIANT}}
service=${2:-${SERVICE_NAME}}
port=${3:-${PORT_NUMBER}}

path=$(dirname "$0")
environment=$(mktemp)
cp "$variant/postman/environment.json" "$environment"

timed() {
  local elapsed
  elapsed=$(($(date +%s) - $1))
  LC_NUMERIC=C printf "\nTotal runtime: %02d min %02d seconds\n" "$((elapsed / 60))" "$((elapsed % 60))"
}

success() {
  newman run \
    --delay-request=100 \
    --folder=success \
    --export-environment "$environment" \
    --environment "$environment" \
    "$variant"/postman/collection.json
}

step() {
  local step=$1
  [[ $((step % 2)) -eq 0 ]] && operation="start" || operation="stop"

  printf "=== Step %d: %s %s ===\n" "$step" "$operation" "$service"

  docker compose "$operation" "$service"
  if [[ "$operation" == "start" ]]; then
    "$path"/wait-for.sh -t 120 "http://localhost:$port/manage/health" -- echo "Host localhost:$port is active"
  fi

  newman run \
    --delay-request=100 \
    --folder=step"$step" \
    --export-environment "$environment" \
    --environment "$environment" \
    "$variant"/postman/collection.json

  printf "=== Step %d completed ===\n" "$step"
}

start=$(date +%s)
trap 'rm -f "$environment"; timed "$start"' EXIT

printf "=== Start test scenario ===\n"

# success execute
success

# stop service
step 1

# start service
step 2

# stop service
step 3

# start service
step 4

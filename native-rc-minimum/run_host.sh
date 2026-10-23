#!/usr/bin/env bash
# Native Linux only. Owned daemon-local container, no host mounts/ports/credentials.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && -z ${DOCKER_HOST:-} ]] || { echo native_local_linux_required >&2; exit 2; }
for executable in docker timeout jq sha256sum awk mktemp cp find sort cmp mkdir mv rm python3 git; do
  command -v "$executable" >/dev/null || { echo required_host_command_missing >&2; exit 2; }
done
[[ $(timeout --version) == *"GNU coreutils"* ]] || { echo gnu_timeout_required >&2; exit 2; }
payload= output= pins= pins_sha= repository=
while (($#)); do
  case "$1" in
    --payload) payload=${2:?}; shift 2 ;;
    --output) output=${2:?}; shift 2 ;;
    --pins) pins=${2:?}; shift 2 ;;
    --pins-sha) pins_sha=${2:?}; shift 2 ;;
    --source-repository) repository=${2:?}; shift 2 ;;
    *) echo arguments_refused >&2; exit 2 ;;
  esac
done
[[ -d $payload && ! -L $payload && -n $output && ! -e $output && ! -L $output &&
   -f $pins && ! -L $pins && $pins_sha =~ ^[0-9a-f]{64}$ &&
   $(sha256sum "$pins" | awk '{print $1}') == "$pins_sha" && -d $repository && ! -L $repository ]] || {
  echo fresh_pinned_paths_required >&2; exit 2;
}
payload=$(cd -- "$payload" && pwd -P)
repository=$(cd -- "$repository" && pwd -P)
pins=$(cd -- "$(dirname -- "$pins")" && printf '%s/%s' "$PWD" "$(basename -- "$pins")")
architecture=$(jq -er .architecture "$pins"); machine=$(jq -er .machine "$pins")
[[ ( $architecture == amd64 && $machine == x86_64 ) || ( $architecture == arm64 && $machine == aarch64 ) ]] || {
  echo architecture_refused >&2; exit 2;
}
[[ $(uname -m) == "$machine" ]] || { echo native_cpu_required >&2; exit 2; }
mkdir -m 700 -- "$output"; output=$(cd -- "$output" && pwd -P)
[[ $output =~ ^/[A-Za-z0-9_./-]+$ ]] || { echo output_path_refused >&2; exit 2; }
workspace=$(mktemp -d "$output/private.XXXXXXXX")
public="$output/public-summary"; mkdir -m 700 "$public" "$workspace/input" "$workspace/results"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
token=${workspace##*/}; token=${token//./-}
name="homecircle-final-rc-minimum-$architecture-$token"
label=io.homecircle.final-rc-minimum
image_repo=$(jq -er .image_repository "$pins"); image_digest=$(jq -er .image_digest "$pins")
expected_image_id=$(jq -er .image_id "$pins"); driver_sha=$(jq -er .driver_sha256 "$pins")
image="$image_repo@$image_digest"
cid= image_id= stage=prepare acceptance_exit=-1
creation_attempted=false stopped=false removed=false cleanup_failed=false private_removed=false
network_none=false setup_pass=false acceptance_pass=false source_verified=false
kernel=$(uname -r); started=$(awk '{print $1}' /proc/uptime); deadline=$((SECONDS + 2100))
DOCKER=(docker)
bounded() {
  local maximum=$1; shift
  local remaining=$((deadline - SECONDS))
  ((remaining > 0)) || { echo host_deadline_exceeded >&2; return 1; }
  ((remaining < maximum)) && maximum=$remaining
  timeout --signal=TERM --kill-after=10s "${maximum}s" "$@"
}
docker_call() { bounded 30 "${DOCKER[@]}" "$@"; }
docker_cleanup() { timeout --signal=TERM --kill-after=3s 15s "${DOCKER[@]}" "$@"; }
owned() {
  local value found
  value=$(docker_cleanup container inspect "$name" 2>/dev/null) || return 1
  [[ $(jq -r '.[0].Config.Labels["io.homecircle.final-rc-minimum"]' <<<"$value") == "$token" &&
     $(jq -r '.[0].Name' <<<"$value") == "/$name" ]] || return 1
  found=$(jq -r '.[0].Id' <<<"$value")
  [[ $found =~ ^[0-9a-f]{64}$ && ( -z $cid || $cid == "$found" ) ]] || return 1
  cid=$found
}
finish() {
  local status=$? ids ended elapsed source
  trap - EXIT INT TERM HUP; set +e
  if [[ $creation_attempted == false ]]; then
    stopped=true; removed=true
  elif owned; then
    docker_cleanup kill --signal TERM "$cid" >"$workspace/cleanup-private.log" 2>&1
    docker_cleanup wait "$cid" >>"$workspace/cleanup-private.log" 2>&1
    if [[ $(docker_cleanup inspect --format '{{.State.Running}}' "$cid" 2>/dev/null) == true ]]; then
      docker_cleanup kill --signal KILL "$cid" >>"$workspace/cleanup-private.log" 2>&1
    fi
    if [[ $(docker_cleanup inspect --format '{{.State.Running}}' "$cid" 2>/dev/null) == false ]]; then
      stopped=true
      for source in setup-summary.json lifecycle-summary.json failure-summary.json; do
        docker_cleanup cp "$cid:/qa/results/$source" "$public/$source" >"$workspace/collect-private.log" 2>&1
      done
      docker_cleanup rm "$cid" >>"$workspace/cleanup-private.log" 2>&1
      if ids=$(docker_cleanup container ls -aq --no-trunc --filter "id=$cid"); then
        [[ -z $ids ]] && removed=true
      fi
    fi
  else cleanup_failed=true
  fi
  [[ $stopped == true && $removed == true ]] || cleanup_failed=true
  [[ $cleanup_failed == false && $acceptance_exit == 0 && $setup_pass == true &&
     $acceptance_pass == true && $network_none == true && $source_verified == true ]] || status=1
  if [[ -s $workspace/results/source-summary.json ]]; then
    cp -- "$workspace/results/source-summary.json" "$public/source-summary.json" || status=1
  fi
  if [[ $status == 0 ]]; then
    jq -e --arg arch "$architecture" '.outcome=="passed" and .completed==true and .core=="2026.9.4" and
      .architecture==$arch and .release_sha256=="4f94a18e2f7862e9bd7f4c85250e5f10e4b8e1292ea9d7b263b441d2e1b77dd9" and
      .separate_core_processes==4 and .focused_tests.passed==20 and .focused_tests.failed==0 and .focused_tests.skipped==0 and
      .owned_configuration_removed==true and .managed_haos_service_claimed==false and .native_apple_worker_executed==false' \
      "$public/lifecycle-summary.json" >/dev/null || status=1
  fi
  rm -rf -- "$workspace"; [[ ! -e $workspace ]] && private_removed=true
  [[ $private_removed == true ]] || { cleanup_failed=true; status=1; }
  ended=$(awk '{print $1}' /proc/uptime)
  elapsed=$(awk -v begin="$started" -v end="$ended" 'BEGIN {printf "%.3f", end-begin}')
  jq -n --arg stage "$stage" --arg machine "$machine" --arg architecture "$architecture" \
    --arg kernel "$kernel" --arg digest "$image_digest" --arg image "$image_id" --arg pins "$pins_sha" \
    --arg driver "$driver_sha" --argjson status "$status" --argjson actual "$acceptance_exit" --argjson seconds "$elapsed" \
    --argjson stopped "$stopped" --argjson removed "$removed" --argjson cleanup "$cleanup_failed" \
    --argjson private "$private_removed" --argjson network "$network_none" --argjson source "$source_verified" \
    '{schema:1,outcome:(if $status==0 then "passed" else "failed_or_incomplete" end),runner_exit:$status,
      failure_or_final_stage:$stage,acceptance_actual_exit:$actual,host_elapsed_seconds:$seconds,
      host_system:"Linux",host_machine:$machine,architecture:$architecture,host_kernel:$kernel,
      registry_digest:$digest,local_image_id:$image,pins_sha256:$pins,driver_sha256:$driver,
      candidate_source_commit:"c7b31c5a82431a6b16d8b7208f9423626b95bd4b",source_git_verified:$source,
      container_stopped:$stopped,container_removed:$removed,cleanup_failed:$cleanup,
      private_workspace_removed:$private,acceptance_network_disconnected:$network,
      owner_accounts_used:false,production_configuration_used:false,hacs_delivery_tested:false,
      normal_container_entrypoint_claimed:false,managed_haos_service_claimed:false,full_backend_suite_repeated:false}' \
    >"$public/host.json.tmp" || exit 1
  jq -e --argjson status "$status" '.schema==1 and .runner_exit==$status' "$public/host.json.tmp" >/dev/null &&
    mv -- "$public/host.json.tmp" "$public/host.json" || exit 1
  echo "current_core_scoped_outcome=$([[ $status == 0 ]] && echo passed || echo failed_or_incomplete)"
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT; trap 'exit 143' TERM; trap 'exit 129' HUP
unset GH_TOKEN GITHUB_TOKEN PYTHONPATH PYTHONHOME
[[ $driver_sha =~ ^[0-9a-f]{64}$ && $(sha256sum "$script_dir/driver.py" | awk '{print $1}') == "$driver_sha" ]] || {
  echo driver_pin_refused >&2; exit 2;
}
[[ -z $(find "$payload" -mindepth 1 ! -type f -print -quit) ]] || { echo payload_types_refused >&2; exit 2; }
find "$payload" -type f -printf '%P\n' | LC_ALL=C sort >"$workspace/actual-members"
printf '%s\n' homecircle.zip inventory.json source-config.json source-inventory.json source.tgz >"$workspace/expected-members"
cmp -s "$workspace/actual-members" "$workspace/expected-members" || { echo payload_members_refused >&2; exit 2; }
cp -- "$payload/"* "$workspace/input/"
cp -- "$pins" "$workspace/input/pins.json"
bounded 120 python3 -I -B "$script_dir/driver.py" prepare --payload "$workspace/input" --tree "$workspace/source" \
  --results "$workspace/results" --pins "$workspace/input/pins.json" --pins-sha "$pins_sha" \
  --git-directory "$repository" >"$workspace/source-private.log" 2>&1
source_verified=true
stage=docker_preflight
context=$(bounded 30 docker context show)
endpoint=$(bounded 30 docker context inspect "$context" --format '{{.Endpoints.docker.Host}}')
[[ $endpoint == unix:///* ]] || { echo local_daemon_required >&2; exit 2; }
DOCKER=(docker --context "$context")
daemon=$(docker_call info --format '{{.OSType}}/{{.Architecture}}')
[[ $daemon == "linux/$machine" || ( $architecture == arm64 && $daemon == linux/arm64 ) ]] || {
  echo native_daemon_required >&2; exit 2;
}
stage=image_pull
bounded 600 "${DOCKER[@]}" pull --platform "linux/$architecture" "$image" >"$workspace/pull-private.log" 2>&1
docker_call image inspect "$image" >"$workspace/image-private.json"
image_id=$(jq -r '.[0].Id' "$workspace/image-private.json")
jq -e --arg image "$image" --arg arch "$architecture" --arg id "$expected_image_id" \
  '.[0].Architecture==$arch and .[0].Os=="linux" and .[0].Id==$id and (.[0].RepoDigests|index($image)!=null)' \
  "$workspace/image-private.json" >/dev/null
stage=create; creation_attempted=true
cid=$(docker_call create --name "$name" --label "$label=$token" --network bridge --platform "linux/$architecture" \
  --cpus 2 --memory 4g --pids-limit 512 --cap-drop ALL --security-opt no-new-privileges \
  --entrypoint /bin/sh "$image_id" -c 'exec sleep 2600')
[[ $cid =~ ^[0-9a-f]{64}$ ]] && owned || { echo container_ownership_refused >&2; exit 2; }
docker_call inspect "$cid" >"$workspace/container-private.json"
jq -e --arg image "$image_id" '.[0].Image==$image and (.[0].Mounts|length)==0 and
  .[0].HostConfig.Privileged==false and (.[0].HostConfig.PortBindings|length)==0' "$workspace/container-private.json" >/dev/null
docker_call start "$cid" >"$workspace/start-private.log" 2>&1
[[ $(docker_call exec "$cid" uname -m) == "$machine" ]] || { echo native_container_required >&2; exit 2; }
stage=staging
docker_call exec "$cid" mkdir -m 700 /qa /qa/input /qa/results
stage_file() {
  local source_file=$1 destination=$2 expected actual
  expected=$(sha256sum "$source_file" | awk '{print $1}')
  bounded 30 "${DOCKER[@]}" exec -i "$cid" /bin/sh -c \
    'set -eu; umask 077; test ! -e "$1"; test ! -L "$1"; cat > "$1"' sh "$destination" \
    <"$source_file" >"$workspace/stage-private.log" 2>&1
  [[ $(docker_call exec "$cid" stat -c '%u:%g:%a' "$destination") == 0:0:600 ]] || return 1
  actual=$(docker_call exec "$cid" sha256sum "$destination" | awk '{print $1}')
  [[ $actual == "$expected" ]] || return 1
}
for source in source-config.json source-inventory.json source.tgz homecircle.zip inventory.json pins.json; do
  stage_file "$workspace/input/$source" "/qa/input/$source"
done
for source in driver.py package_support.py requirements_support.py; do stage_file "$script_dir/$source" "/qa/$source"; done
stage=setup
bounded 720 "${DOCKER[@]}" exec --workdir /qa "$cid" python -I -B /qa/driver.py setup \
  --payload /qa/input --tree /qa/source --results /qa/results --pins /qa/input/pins.json --pins-sha "$pins_sha" \
  >"$workspace/setup-private.log" 2>&1
docker_call cp "$cid:/qa/results/setup-summary.json" "$public/setup-summary.json"
jq -e '.outcome=="passed" and .completed==true and .core=="2026.9.4" and .release_files==112' \
  "$public/setup-summary.json" >/dev/null
setup_pass=true
stage=disconnect
docker_call network disconnect bridge "$cid"
docker_call inspect "$cid" >"$workspace/offline-private.json"
jq -e '.[0].State.Running==true and (.[0].Mounts|length)==0 and (.[0].NetworkSettings.Networks|length)==0' \
  "$workspace/offline-private.json" >/dev/null
network_none=true
stage=focused_and_core_lifecycle
set +e
bounded 720 "${DOCKER[@]}" exec --workdir /qa "$cid" python -I -B /qa/driver.py acceptance \
  --payload /qa/input --tree /qa/source --results /qa/results --pins /qa/input/pins.json --pins-sha "$pins_sha" \
  >"$workspace/acceptance-private.log" 2>&1
acceptance_exit=$?
set -e
[[ $acceptance_exit == 0 ]] || exit 1
docker_call cp "$cid:/qa/results/lifecycle-summary.json" "$public/lifecycle-summary.json"
docker_call inspect "$cid" >"$workspace/after-private.json"
jq -e '.[0].State.Running==true and (.[0].Mounts|length)==0 and (.[0].NetworkSettings.Networks|length)==0' \
  "$workspace/after-private.json" >/dev/null
acceptance_pass=true; stage=complete

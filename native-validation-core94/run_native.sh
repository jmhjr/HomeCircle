#!/usr/bin/env bash
# Native Linux host only. The QA container receives no host bind mounts.
set -Eeuo pipefail
umask 077

[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo native_linux_amd64_required >&2; exit 2; }
for command in docker timeout jq sha256sum awk mktemp cp find sort cmp wc mkdir mv; do
  command -v "$command" >/dev/null || { echo required_host_command_missing >&2; exit 2; }
done
[[ $(timeout --version) == *"GNU coreutils"* ]] || { echo gnu_timeout_required >&2; exit 2; }
[[ -z ${DOCKER_HOST:-} ]] || { echo explicit_docker_host_refused >&2; exit 2; }

payload= output=
while (($#)); do
  case "$1" in
    --payload) payload=${2:?}; shift 2 ;;
    --output) output=${2:?}; shift 2 ;;
    *) echo arguments_refused >&2; exit 2 ;;
  esac
done
[[ -n $payload && -n $output && -d $payload && ! -L $payload && ! -e $output && ! -L $output ]] || {
  echo fresh_paths_required >&2; exit 2;
}
payload=$(cd -- "$payload" && pwd -P)
mkdir -m 700 -- "$output"
output=$(cd -- "$output" && pwd -P)
workspace=$(mktemp -d "$output/private.XXXXXXXX")
public="$output/public-summary"
mkdir -m 700 -- "$public"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
token=${workspace##*/}
token=${token//./-}
name="homecircle-native-core94-$token"
label=io.homecircle.native-core94-validation
image_repo=ghcr.io/home-assistant/qemux86-64-homeassistant
image_digest=sha256:414dce485b4eebd9f929f293f7252340bada5715fc4a48b2b954d79195ed3019
image="$image_repo@$image_digest"
cid= image_id= kernel=$(uname -r) stage=preflight acceptance_exit=-1
network_none=false cleanup_stopped=false cleanup_removed=false cleanup_failed=false creation_attempted=false
raw_collected=false
summary_valid=false setup_pass=false expected_driver=c910ef815d34eb4379bf3f0e1fd6dad31d95986a287b9e32263f9b87b60de373
started=$(awk '{print $1}' /proc/uptime)
[[ $kernel =~ ^[[:alnum:]_.+-]+$ ]] || { echo host_kernel_refused >&2; exit 2; }
DOCKER=(docker)

docker_call() { timeout --signal=TERM --kill-after=5s 30s "${DOCKER[@]}" "$@"; }
docker_long() { timeout --signal=TERM --kill-after=10s 900s "${DOCKER[@]}" "$@"; }
owned() {
  local inspect
  inspect=$(docker_call container inspect "$name" 2>/dev/null) || return 1
  [[ $(jq -r '.[0].Config.Labels["io.homecircle.native-core94-validation"]' <<<"$inspect") == "$token" ]] || return 1
  [[ $(jq -r '.[0].Name' <<<"$inspect") == "/$name" ]] || return 1
  local found
  found=$(jq -r '.[0].Id' <<<"$inspect")
  [[ $found =~ ^[0-9a-f]{64}$ && ( -z $cid || $found == "$cid" ) ]] || return 1
  cid=$found
}

finish() {
  local status=$? ended elapsed ids
  trap - EXIT INT TERM HUP
  set +e
  # Container names are unique; even a timed-out create is discovered by label.
  if [[ $creation_attempted == false ]]; then
    cleanup_stopped=true
    cleanup_removed=true
  elif owned; then
    docker_call kill --signal TERM "$cid" >"$workspace/cleanup-term.log" 2>&1
    timeout --signal=TERM --kill-after=5s 15s "${DOCKER[@]}" wait "$cid" >"$workspace/cleanup-wait.log" 2>&1
    if [[ $(docker_call inspect --format '{{.State.Running}}' "$cid" 2>/dev/null) == true ]]; then
      docker_call kill --signal KILL "$cid" >"$workspace/cleanup-kill.log" 2>&1
    fi
    if [[ $(docker_call inspect --format '{{.State.Running}}' "$cid" 2>/dev/null) == false ]]; then
      cleanup_stopped=true
      # Raw synthetic state is retained locally only, never under public-summary.
      mkdir -m 700 -- "$workspace/results"
      if docker_call cp "$cid:/qa/results/." "$workspace/results" >"$workspace/collect.log" 2>&1; then
        raw_collected=true
      fi
      docker_call rm "$cid" >"$workspace/cleanup-rm.log" 2>&1
      if ids=$(docker_call container ls -aq --no-trunc --filter "id=$cid"); then
        [[ -z $ids ]] && cleanup_removed=true
      fi
    fi
  else
    # A create client timeout may leave a daemon operation pending. Absence at
    # one observation cannot establish that it will never register later.
    cleanup_failed=true
  fi
  [[ $cleanup_stopped == true && $cleanup_removed == true ]] || cleanup_failed=true
  ended=$(awk '{print $1}' /proc/uptime)
  elapsed=$(awk -v begin="$started" -v end="$ended" 'BEGIN {printf "%.3f", end-begin}')
  [[ $cleanup_failed == false ]] || status=1
  [[ $acceptance_exit == 0 && $summary_valid == true && $setup_pass == true && $network_none == true ]] || status=1
  [[ $status != 0 || $raw_collected == true ]] || status=1
  if [[ $status == 0 ]] && { [[ ! -s $public/setup-summary.json || ! -s $public/candidate-summary.json ]] ||
      ! jq -e '.acceptance_pass==true' "$public/candidate-summary.json" >/dev/null; }; then
    status=1
  fi
  if ! jq -n --arg stage "$stage" --arg kernel "$kernel" --arg digest "$image_digest" --arg image "$image_id" \
    --arg cid "$cid" --argjson exit "$status" --argjson actual "$acceptance_exit" \
    --argjson seconds "$elapsed" --argjson network "$network_none" --argjson stopped "$cleanup_stopped" \
    --argjson removed "$cleanup_removed" --argjson failed "$cleanup_failed" --argjson raw "$raw_collected" \
    '{schema:1,outcome:(if $exit==0 then "passed" else "failed_or_incomplete" end),
      host_system:"Linux",host_architecture:"x86_64",host_kernel:$kernel,registry_digest:$digest,
      local_image_id:$image,owned_container_id:$cid,host_elapsed_seconds:$seconds,
      failure_or_final_stage:$stage,acceptance_actual_exit:$actual,runner_exit:$exit,
      acceptance_network_disconnected:$network,container_stopped:$stopped,container_removed:$removed,
      cleanup_failed:$failed,raw_evidence_collected_locally:$raw,owner_accounts_used:false,production_configuration_used:false,
      native_container_architecture_required:true,full_managed_core_lifecycle:false,
      apple_authentication:false,production_backup_acceptance:false}' >"$public/host.json.tmp"; then
    echo host_receipt_write_failed >&2
    exit 1
  fi
  if ! jq -e --argjson status "$status" '.runner_exit==$status and .schema==1' "$public/host.json.tmp" >/dev/null ||
      ! mv -- "$public/host.json.tmp" "$public/host.json"; then
    echo host_receipt_finalize_failed >&2
    exit 1
  fi
  echo "native_validation_outcome=$([[ $status == 0 ]] && echo passed || echo failed_or_incomplete)"
  echo "private_evidence=$workspace"
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

echo native_preflight_started
context=$(timeout --signal=TERM --kill-after=5s 30s docker context show)
endpoint=$(timeout --signal=TERM --kill-after=5s 30s docker context inspect "$context" --format '{{.Endpoints.docker.Host}}')
[[ $endpoint == unix:///* ]] || { echo local_docker_socket_required >&2; exit 2; }
DOCKER=(docker --context "$context")
[[ $(docker_call info --format '{{.OSType}}/{{.Architecture}}') == linux/x86_64 ]] || {
  echo native_linux_docker_daemon_required >&2; exit 2;
}
mkdir -m 700 -- "$workspace/payload"
cp -a -- "$payload/." "$workspace/payload/"
payload="$workspace/payload"
[[ -f $payload/input-sha256.json && ! -L $payload/input-sha256.json ]] || { echo payload_manifest_required >&2; exit 2; }
# Reject startup hooks, shadow imports, links and extra files before the first
# container Python process. The manifest itself is fixed, not a trust source.
[[ $(sha256sum "$payload/input-sha256.json" | awk '{print $1}') == 315b117c63df01dc1cba964aedaf723e5deae9af45de7085d581293b86c1cec4 ]] || {
  echo payload_manifest_hash_refused >&2; exit 2;
}
[[ -z $(find "$payload" ! -type f ! -type d -print -quit) ]] || { echo payload_type_refused >&2; exit 2; }
find "$payload" -type f -printf '%P\n' | LC_ALL=C sort >"$workspace/actual-members.txt"
{ jq -r 'keys[]' "$payload/input-sha256.json"; echo input-sha256.json; } | LC_ALL=C sort >"$workspace/expected-members.txt"
cmp -s "$workspace/actual-members.txt" "$workspace/expected-members.txt" || { echo payload_members_refused >&2; exit 2; }
find "$payload" -mindepth 1 -type d -printf '%P\n' | LC_ALL=C sort >"$workspace/actual-directories.txt"
printf '%s\n' amd64-upgrade-recovery scripts >"$workspace/expected-directories.txt"
cmp -s "$workspace/actual-directories.txt" "$workspace/expected-directories.txt" || { echo payload_directories_refused >&2; exit 2; }
while IFS=$'\t' read -r relative expected bytes; do
  [[ $relative =~ ^[A-Za-z0-9_./-]+$ && $relative != /* && $relative != *..* && $expected =~ ^[0-9a-f]{64}$ ]] || {
    echo payload_record_refused >&2; exit 2;
  }
  [[ $(sha256sum "$payload/$relative" | awk '{print $1}') == "$expected" && $(wc -c <"$payload/$relative") == "$bytes" ]] || {
    echo payload_hash_refused >&2; exit 2;
  }
done < <(jq -r 'to_entries[] | [.key,.value.sha256,(.value.bytes|tostring)] | @tsv' "$payload/input-sha256.json")
# Fixed-input verification is repeated inside Linux before extraction/imports.
[[ $(sha256sum "$payload/amd64-upgrade-recovery/run_validation.py" | awk '{print $1}') == "$expected_driver" ]] || {
  echo driver_hash_refused >&2; exit 2;
}
[[ $(sha256sum "$script_dir/setup_container.py" | awk '{print $1}') == 75c628e7289738395bb4759c4a1d3a0cdfa3ce3c2cd00cf2b25fda15a508df4f ]] || {
  echo setup_helper_hash_refused >&2; exit 2;
}
[[ $(sha256sum "$script_dir/run_suite.py" | awk '{print $1}') == 8f1d236325ca4f3606a1ebf52f3847ff0853f1b8b33c56c2a2ef31ecc22c60ea ]] || {
  echo suite_helper_hash_refused >&2; exit 2;
}
[[ $(sha256sum "$script_dir/run_validation_core94.py" | awk '{print $1}') == b5868eb974456b36f1fedbccea59f3b9a76a4bddba264806dc9c4c481ad8877c ]] || {
  echo core94_driver_hash_refused >&2; exit 2;
}
stage=pull
docker_long pull --platform linux/amd64 "$image" >"$workspace/pull.log" 2>&1
docker_call image inspect "$image" >"$workspace/image-inspect.json"
image_id=$(jq -r '.[0].Id' "$workspace/image-inspect.json")
[[ $image_id =~ ^sha256:[0-9a-f]{64}$ ]] || { echo local_image_id_refused >&2; exit 2; }
jq -e --arg ref "$image" '.[0].Architecture=="amd64" and .[0].Os=="linux" and
  (.[0].RepoDigests | index($ref) != null)' "$workspace/image-inspect.json" >/dev/null

stage=create
creation_attempted=true
cid=$(docker_call create --name "$name" --label "$label=$token" --network bridge \
  --platform linux/amd64 --cpus 2 --memory 4g --pids-limit 512 --cap-drop ALL \
  --security-opt no-new-privileges --entrypoint /bin/sh "$image_id" -c 'exec sleep 12000')
[[ $cid =~ ^[0-9a-f]{64}$ ]] || { echo container_id_refused >&2; exit 2; }
owned || { echo container_ownership_refused >&2; exit 2; }
docker_call inspect "$cid" >"$workspace/container-created.json"
jq -e --arg id "$image_id" '.[0].Image==$id and (.[0].Mounts|length)==0 and
  .[0].HostConfig.Privileged==false and (.[0].HostConfig.PortBindings|length)==0' \
  "$workspace/container-created.json" >/dev/null
docker_call start "$cid" >"$workspace/start.log" 2>&1
[[ $(docker_call exec "$cid" uname -s) == Linux && $(docker_call exec "$cid" uname -m) == x86_64 ]] || {
  echo native_container_required >&2; exit 2;
}
docker_call exec "$cid" mkdir -m 700 /qa
docker_call cp "$payload/." "$cid:/qa/"
docker_call cp "$script_dir/setup_container.py" "$cid:/qa/setup_container.py"
docker_call cp "$script_dir/run_suite.py" "$cid:/qa/run_suite.py"
docker_call cp "$script_dir/run_validation_core94.py" "$cid:/qa/run_validation_core94.py"

stage=setup
echo native_setup_started
docker_long exec --workdir /qa "$cid" python -I -B /qa/setup_container.py setup >"$public/setup-summary.json" 2>"$workspace/setup.stderr"
jq -e '.outcome=="passed" and .completed==true and .machine=="x86_64" and .core=="2026.9.4"' \
  "$public/setup-summary.json" >/dev/null
setup_pass=true
stage=disconnect
docker_call network disconnect bridge "$cid"
docker_call inspect "$cid" >"$workspace/container-offline.json"
jq -e --arg id "$image_id" '.[0].Image==$id and .[0].State.Running==true and
  (.[0].NetworkSettings.Networks|length)==0 and (.[0].Mounts|length)==0' "$workspace/container-offline.json" >/dev/null
network_none=true

stage=acceptance
echo native_offline_acceptance_started
set +e
timeout --signal=TERM --kill-after=15s 7200s "${DOCKER[@]}" exec --workdir /qa \
  --env PYTHONDONTWRITEBYTECODE=1 "$cid" python -I -B /qa/run_suite.py \
  >"$workspace/driver.log" 2>&1
acceptance_exit=$?
set -e
stage=summary
docker_call exec --workdir /qa "$cid" python -I -B /qa/setup_container.py summary \
  >"$public/candidate-summary.json" 2>"$workspace/summary.stderr"
docker_call inspect "$cid" >"$workspace/container-after.json"
jq -e '.[0].State.Running==true and (.[0].NetworkSettings.Networks|length)==0 and
  (.[0].Mounts|length)==0' "$workspace/container-after.json" >/dev/null
jq -e '.acceptance_pass==true and .candidate_inputs_match==true and .upgrade_phases==20 and
  .recovery_processes==20 and .network_probes_blocked==40 and .backend_passed==1443 and
  .backend_skipped==1 and .native_worker_passed==true and .lifecycle_passed==true and
  .core=="2026.9.4"' "$public/candidate-summary.json" >/dev/null
summary_valid=true
stage=complete
[[ $acceptance_exit == 0 ]]

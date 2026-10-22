#!/usr/bin/env bash
# Existing native-amd64 workflow adapter: focused pytest only, no upgrade claim.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && $(uname -m) == x86_64 && -z ${DOCKER_HOST:-} ]] || exit 2
for executable in docker timeout jq sha256sum awk mktemp cp mkdir mv rm python3 git; do
  command -v "$executable" >/dev/null || exit 2
done
payload= output=
while (($#)); do
  case "$1" in
    --payload) payload=${2:?}; shift 2 ;;
    --output) output=${2:?}; shift 2 ;;
    *) exit 2 ;;
  esac
done
[[ -d $payload && ! -L $payload && -n $output && ! -e $output && ! -L $output ]] || exit 2
payload=$(cd -- "$payload" && pwd -P)
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
pins_sha=$(cat "$script_dir/CONFIG.sha256")
[[ $pins_sha =~ ^[0-9a-f]{64}$ ]] || { echo final_configuration_required >&2; exit 2; }
[[ $(sha256sum "$payload/config.json" | awk '{print $1}') == "$pins_sha" ]] || exit 2
source_commit=$(jq -er .source_commit "$payload/config.json")
[[ $source_commit =~ ^[0-9a-f]{40}$ ]] || exit 2
repository=$(git -C "$script_dir" rev-parse --show-toplevel)
mkdir -m 700 -- "$output"
output=$(cd -- "$output" && pwd -P)
[[ $output =~ ^/[A-Za-z0-9_./-]+$ ]] || exit 2
workspace=$(mktemp -d "$output/private.XXXXXXXX")
public="$output/public-summary"
mkdir -m 700 "$public" "$workspace/results" "$workspace/input"
token=${workspace##*/}; token=${token//./-}
name="homecircle-focused-$token"
label=io.homecircle.focused-pytest
image_repo=ghcr.io/home-assistant/qemux86-64-homeassistant
image_digest=sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12
image="$image_repo@$image_digest"
expected_image=sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98
cid= stage=source creation_attempted=false stopped=false removed=false cleanup_failed=false
private_removed=false network_none=false source_verified=false setup_pass=false acceptance_pass=false
started=$(awk '{print $1}' /proc/uptime)
deadline=$((SECONDS + 1500))
bounded() {
  local maximum=$1; shift
  local remaining=$((deadline - SECONDS))
  ((remaining > 0)) || return 1
  ((remaining < maximum)) && maximum=$remaining
  timeout --signal=TERM --kill-after=10s "${maximum}s" "$@"
}
dc() { bounded 35 docker "$@"; }
clean() { timeout --signal=TERM --kill-after=3s 20s docker "$@"; }
owned() {
  local value found
  value=$(clean container inspect "$name" 2>/dev/null) || return 1
  [[ $(jq -r '.[0].Config.Labels["io.homecircle.focused-pytest"]' <<<"$value") == "$token" &&
     $(jq -r '.[0].Name' <<<"$value") == "/$name" ]] || return 1
  found=$(jq -r '.[0].Id' <<<"$value")
  [[ $found =~ ^[0-9a-f]{64}$ && ( -z $cid || $cid == "$found" ) ]] || return 1
  cid=$found
}
finish() {
  local status=$? ids ended elapsed item
  trap - EXIT INT TERM HUP
  set +e
  if [[ $creation_attempted == false ]]; then
    stopped=true; removed=true
  elif owned; then
    clean kill --signal TERM "$cid" >"$workspace/cleanup.log" 2>&1
    clean wait "$cid" >>"$workspace/cleanup.log" 2>&1
    if [[ $(clean inspect --format '{{.State.Running}}' "$cid" 2>/dev/null) == true ]]; then
      clean kill --signal KILL "$cid" >>"$workspace/cleanup.log" 2>&1
    fi
    if [[ $(clean inspect --format '{{.State.Running}}' "$cid" 2>/dev/null) == false ]]; then
      stopped=true
      for item in setup-summary.json candidate-summary.json failure-summary.json focused-diagnostic.json; do
        clean cp "$cid:/qa/results/$item" "$public/$item" >"$workspace/collect.log" 2>&1
      done
      clean rm "$cid" >>"$workspace/cleanup.log" 2>&1
      if ids=$(clean container ls -aq --no-trunc --filter "id=$cid"); then
        [[ -z $ids ]] && removed=true
      fi
    fi
  fi
  [[ $stopped == true && $removed == true ]] || cleanup_failed=true
  [[ $source_verified == true && $setup_pass == true && $acceptance_pass == true &&
     $network_none == true && $cleanup_failed == false ]] || status=1
  if [[ $status == 0 ]]; then
    jq -e '.scope=="native_current_core_focused_pytest_only" and .outcome=="passed" and
      .passed>=32 and .failed==0 and .skipped==0 and .real_async_setup_entry_test_passed==true and
      (.required_projection_tests|length)==4 and .source_unchanged==true and
      .full_backend_suite_repeated==false and .upgrade_validated==false' \
      "$public/candidate-summary.json" >/dev/null || status=1
    jq -e '.outcome=="passed" and .completed==true and .core=="2026.10.2"' \
      "$public/setup-summary.json" >/dev/null || status=1
  fi
  rm -rf -- "$workspace"
  [[ ! -e $workspace ]] && private_removed=true
  [[ $private_removed == true ]] || { cleanup_failed=true; status=1; }
  ended=$(awk '{print $1}' /proc/uptime)
  elapsed=$(awk -v begin="$started" -v end="$ended" 'BEGIN {printf "%.3f",end-begin}')
  jq -n --arg stage "$stage" --arg source "$source_commit" --arg config "$pins_sha" \
    --arg digest "$image_digest" --arg image "$expected_image" --argjson status "$status" \
    --argjson elapsed "$elapsed" --argjson stopped "$stopped" --argjson removed "$removed" \
    --argjson cleanup "$cleanup_failed" --argjson private "$private_removed" \
    --argjson network "$network_none" --argjson verified "$source_verified" \
    '{schema:1,scope:"native_current_core_focused_pytest_only",
      outcome:(if $status==0 then "passed" else "failed_or_incomplete" end),
      runner_exit:$status,failure_or_final_stage:$stage,source_commit:$source,config_sha256:$config,
      image_digest:$digest,expected_image_id:$image,host_elapsed_seconds:$elapsed,
      host_system:"Linux",host_architecture:"x86_64",core:"2026.10.2",
      source_git_verified:$verified,backend_network_disconnected:$network,
      container_stopped:$stopped,container_removed:$removed,cleanup_failed:$cleanup,
      private_workspace_removed:$private,full_backend_suite_repeated:false,
      full_managed_core_lifecycle:false,upgrade_validated:false,kvm_used:false,
      owner_accounts_used:false,production_configuration_used:false,release_published:false}' \
      >"$public/host.json.tmp" || exit 1
  mv -- "$public/host.json.tmp" "$public/host.json" || exit 1
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
unset GH_TOKEN GITHUB_TOKEN PYTHONPATH PYTHONHOME
if ! git -C "$repository" cat-file -e "$source_commit^{commit}" 2>/dev/null; then
  bounded 120 git -C "$repository" fetch --no-tags --depth=1 \
    https://github.com/jmhjr/HomeCircle.git "$source_commit" >"$workspace/fetch.log" 2>&1
fi
bounded 120 python3 -I -B "$script_dir/driver.py" verify-host --payload "$payload" \
  --config-sha "$pins_sha" --repository "$repository" --results "$workspace/results" \
  >"$workspace/source.log" 2>&1
cp -- "$workspace/results/source-summary.json" "$public/source-summary.json"
source_verified=true
stage=image
bounded 300 docker pull --platform linux/amd64 "$image" >"$workspace/pull.log" 2>&1
[[ $(dc image inspect --format '{{.Id}}' "$image") == "$expected_image" ]] || exit 1
creation_attempted=true
cid=$(dc create --name "$name" --label "$label=$token" --network bridge --platform linux/amd64 \
  --entrypoint /bin/sh --workdir /qa --no-healthcheck --memory 5g --cpus 2 \
  "$image" -c 'while :; do sleep 3600; done')
owned || exit 1
dc start "$cid" >"$workspace/start.log" 2>&1
dc cp "$script_dir/driver.py" "$cid:/qa/driver.py" >"$workspace/copy.log" 2>&1
dc cp "$script_dir/requirements_support.py" "$cid:/qa/requirements_support.py" >>"$workspace/copy.log" 2>&1
dc cp "$payload" "$cid:/qa/payload" >>"$workspace/copy.log" 2>&1
stage=dependency_preparation
bounded 780 docker exec "$cid" python3 -I -B /qa/driver.py prepare --payload /qa/payload \
  --config-sha "$pins_sha" --tree /qa/tree --results /qa/results >"$workspace/setup.log" 2>&1
setup_pass=true
stage=disconnect
dc network disconnect bridge "$cid"
[[ $(dc inspect --format '{{json .NetworkSettings.Networks}}' "$cid") == '{}' ]] || exit 1
network_none=true
stage=focused_pytest
bounded 330 docker exec "$cid" python3 -I -B /qa/driver.py accept --payload /qa/payload \
  --config-sha "$pins_sha" --tree /qa/tree --results /qa/results >"$workspace/accept.log" 2>&1
acceptance_pass=true
stage=complete

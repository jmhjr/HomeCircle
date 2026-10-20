#!/usr/bin/env bash
# Fresh native Linux host/container only; no host bind mounts or owner state.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo native_linux_amd64_required >&2; exit 2; }
for executable in docker timeout jq sha256sum awk mktemp cp find sort cmp wc mkdir mv rm python3 npm node git; do
  command -v "$executable" >/dev/null || { echo required_host_command_missing >&2; exit 2; }
done
[[ $(timeout --version) == *"GNU coreutils"* && -z ${DOCKER_HOST:-} ]] || { echo local_native_tools_required >&2; exit 2; }
payload= output=
while (($#)); do
  case "$1" in
    --payload) payload=${2:?}; shift 2 ;;
    --output) output=${2:?}; shift 2 ;;
    *) echo arguments_refused >&2; exit 2 ;;
  esac
done
[[ -d $payload && ! -L $payload && -n $output && ! -e $output && ! -L $output ]] || {
  echo fresh_paths_required >&2; exit 2;
}
payload=$(cd -- "$payload" && pwd -P)
mkdir -m 700 -- "$output"
output=$(cd -- "$output" && pwd -P)
[[ $output =~ ^/[A-Za-z0-9_./-]+$ ]] || { echo output_path_refused >&2; exit 2; }
workspace=$(mktemp -d "$output/private.XXXXXXXX")
public="$output/public-summary"
mkdir -m 700 -- "$public" "$workspace/input" "$workspace/results"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
token=${workspace##*/}; token=${token//./-}
name="homecircle-beta20-package-$token"
label=io.homecircle.beta20-package
image_repo=ghcr.io/home-assistant/qemux86-64-homeassistant
image_digest=sha256:414dce485b4eebd9f929f293f7252340bada5715fc4a48b2b954d79195ed3019
image="$image_repo@$image_digest"
driver_sha=695712fba4e30a4cc366d3529365fd44e3a815dfb98a3adc0f3a34d9a57f6b2e
source_sha=261aeb3219071a44e1c6ca53f2f18e26624ae450a641d29be32450ee265d4818
inventory_sha=be693aef2f7a049cc4c0752179069664c86e444e24cc9fb01393d40f5d1288b1
cid= image_id= stage=inputs acceptance_exit=-1 kernel=$(uname -r)
creation_attempted=false stopped=false removed=false cleanup_failed=false private_removed=false
network_none=false setup_pass=false frontend_pass=false acceptance_pass=false assets_checked=false
node_version= npm_version=
started=$(awk '{print $1}' /proc/uptime)
deadline=$((SECONDS + 3300))
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
  [[ $(jq -r '.[0].Config.Labels["io.homecircle.beta20-package"]' <<<"$value") == "$token" &&
     $(jq -r '.[0].Name' <<<"$value") == "/$name" ]] || return 1
  found=$(jq -r '.[0].Id' <<<"$value")
  [[ $found =~ ^[0-9a-f]{64}$ && ( -z $cid || $cid == "$found" ) ]] || return 1
  cid=$found
}

finish() {
  local status=$? ids ended elapsed source
  trap - EXIT INT TERM HUP
  set +e
  # Only narrow driver-produced summaries are collected, never logs/configs.
  if [[ $creation_attempted == false ]]; then
    stopped=true; removed=true
  elif owned; then
    docker_cleanup kill --signal TERM "$cid" >"$workspace/cleanup.log" 2>&1
    docker_cleanup wait "$cid" >>"$workspace/cleanup.log" 2>&1
    if [[ $(docker_cleanup inspect --format '{{.State.Running}}' "$cid" 2>/dev/null) == true ]]; then
      docker_cleanup kill --signal KILL "$cid" >>"$workspace/cleanup.log" 2>&1
    fi
    if [[ $(docker_cleanup inspect --format '{{.State.Running}}' "$cid" 2>/dev/null) == false ]]; then
      stopped=true
      for source in setup-summary.json package-summary.json failure-summary.json; do
        docker_cleanup cp "$cid:/qa/results/$source" "$public/$source" >"$workspace/collect.log" 2>&1
      done
      docker_cleanup rm "$cid" >>"$workspace/cleanup.log" 2>&1
      if ids=$(docker_cleanup container ls -aq --no-trunc --filter "id=$cid"); then
        [[ -z $ids ]] && removed=true
      fi
    fi
  else
    # An ambiguous create failure cannot establish daemon-side cleanup.
    cleanup_failed=true
  fi
  [[ $stopped == true && $removed == true ]] || cleanup_failed=true
  [[ $cleanup_failed == false && $acceptance_exit == 0 && $setup_pass == true &&
     $frontend_pass == true && $acceptance_pass == true && $network_none == true &&
     $assets_checked == true ]] || status=1
  for source in frontend-summary.json failure-summary.json; do
    if [[ -s $workspace/results/$source ]]; then
      cp -- "$workspace/results/$source" "$public/$source" || status=1
    fi
  done
  if [[ $status == 0 ]]; then
    jq -e '.outcome=="passed" and .completed==true and .backend.passed==1443 and .backend.failed==0 and
      .backend.skipped==1 and .release_version=="0.1.0-beta.20" and .release_files==112' \
      "$public/package-summary.json" >/dev/null || status=1
    jq -e '.outcome=="passed" and .frontend_tests_passed==110 and .privacy.files_checked==327 and
      .privacy.checker_exit==0' "$public/frontend-summary.json" >/dev/null || status=1
  fi
  if [[ $status == 0 ]]; then
    mv -- "$workspace/release-assets" "$output/release-assets" || status=1
  fi
  rm -rf -- "$workspace"
  [[ ! -e $workspace ]] && private_removed=true
  if [[ $private_removed != true ]]; then
    cleanup_failed=true
    status=1
  fi
  ended=$(awk '{print $1}' /proc/uptime)
  elapsed=$(awk -v begin="$started" -v end="$ended" 'BEGIN {printf "%.3f", end-begin}')
  if ! jq -n --arg stage "$stage" --arg kernel "$kernel" --arg digest "$image_digest" \
    --arg image "$image_id" --arg node "$node_version" --arg npm "$npm_version" \
    --arg source "$source_sha" --arg inventory "$inventory_sha" --arg driver "$driver_sha" \
    --argjson status "$status" --argjson actual "$acceptance_exit" --argjson seconds "$elapsed" \
    --argjson stopped "$stopped" --argjson removed "$removed" --argjson cleanup "$cleanup_failed" \
    --argjson private "$private_removed" --argjson network "$network_none" --argjson assets "$assets_checked" \
    '{schema:1,outcome:(if $status==0 then "passed" else "failed_or_incomplete" end),runner_exit:$status,
      failure_or_final_stage:$stage,acceptance_actual_exit:$actual,host_elapsed_seconds:$seconds,
      host_system:"Linux",host_architecture:"x86_64",host_kernel:$kernel,node_version:$node,npm_version:$npm,
      registry_digest:$digest,local_image_id:$image,source_sha256:$source,source_inventory_sha256:$inventory,
      driver_sha256:$driver,container_stopped:$stopped,container_removed:$removed,cleanup_failed:$cleanup,
      private_workspace_removed:$private,backend_network_disconnected:$network,release_assets_checked:$assets,
      owner_accounts_used:false,production_configuration_used:false,hacs_delivery_tested:false,
      full_managed_core_lifecycle:false,upgrade_recovery_repeated:false}' >"$public/host.json.tmp"; then
    echo host_receipt_write_failed >&2; exit 1
  fi
  if ! jq -e --argjson status "$status" '.schema==1 and .runner_exit==$status' "$public/host.json.tmp" >/dev/null ||
      ! mv -- "$public/host.json.tmp" "$public/host.json"; then
    echo host_receipt_finalize_failed >&2; exit 1
  fi
  echo "beta20_package_outcome=$([[ $status == 0 ]] && echo passed || echo failed_or_incomplete)"
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
unset GH_TOKEN GITHUB_TOKEN PYTHONPATH PYTHONHOME
[[ $kernel =~ ^[[:alnum:]_.+-]+$ ]] || { echo host_kernel_refused >&2; exit 2; }
[[ $(sha256sum "$script_dir/driver.py" | awk '{print $1}') == "$driver_sha" ]] || {
  echo driver_pin_refused >&2; exit 2;
}
[[ -z $(find "$payload" -mindepth 1 ! -type f -print -quit) ]] || { echo payload_type_refused >&2; exit 2; }
find "$payload" -type f -printf '%P\n' | LC_ALL=C sort >"$workspace/actual-members"
printf '%s\n' frozen-candidate.zip frozen-inventory.json source-inventory.json source.tgz >"$workspace/expected-members"
cmp -s "$workspace/actual-members" "$workspace/expected-members" || { echo payload_members_refused >&2; exit 2; }
for source in frozen-candidate.zip frozen-inventory.json source-inventory.json source.tgz; do
  cp -- "$payload/$source" "$workspace/input/$source"
done
[[ $(sha256sum "$workspace/input/source.tgz" | awk '{print $1}') == "$source_sha" &&
   $(sha256sum "$workspace/input/source-inventory.json" | awk '{print $1}') == "$inventory_sha" ]] || {
  echo source_pin_refused >&2; exit 2;
}
stage=prepare
bounded 120 python3 -I -B "$script_dir/driver.py" prepare --payload "$workspace/input" \
  --tree "$workspace/source" --results "$workspace/results" >"$workspace/prepare.log" 2>&1
stage=node_toolchain
# npm rejects loading one physical file as both configuration scopes. These
# distinct empty files keep both scopes private without loading owner settings.
: >"$workspace/user.npmrc"
: >"$workspace/global.npmrc"
NPM=(npm --userconfig="$workspace/user.npmrc" --globalconfig="$workspace/global.npmrc" --cache="$workspace/npm-cache")
node_version=$(bounded 10 node --version); npm_version=$(bounded 10 "${NPM[@]}" --version)
[[ $node_version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ && $npm_version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo node_version_refused >&2; exit 2;
}
stage=frontend_dependencies
bounded 480 "${NPM[@]}" ci --prefix "$workspace/source/frontend/homecircle-card" --no-audit --no-fund \
  >"$workspace/npm-install.log" 2>&1
stage=frontend_tests
bounded 60 "${NPM[@]}" run build --prefix "$workspace/source/frontend/homecircle-card" >"$workspace/npm-build.log" 2>&1
# Run exactly the package script's reviewed test files, with an explicit TAP
# reporter so the narrow count parser is independent of Node's default reporter.
(
  cd -- "$workspace/source/frontend/homecircle-card"
  bounded 180 node --test --test-reporter=tap test/*.test.mjs >"$workspace/npm-test.log" 2>&1
)
stage=frontend_and_privacy
bounded 240 python3 -I -B "$script_dir/driver.py" frontend --payload "$workspace/input" \
  --tree "$workspace/source" --results "$workspace/results" --npm-log "$workspace/npm-test.log" \
  >"$workspace/frontend-check.log" 2>&1
frontend_pass=true

stage=docker_preflight
context=$(bounded 30 docker context show)
endpoint=$(bounded 30 docker context inspect "$context" --format '{{.Endpoints.docker.Host}}')
[[ $endpoint == unix:///* ]] || { echo local_docker_socket_required >&2; exit 2; }
DOCKER=(docker --context "$context")
[[ $(docker_call info --format '{{.OSType}}/{{.Architecture}}') == linux/x86_64 ]] || {
  echo native_linux_docker_daemon_required >&2; exit 2;
}
stage=image_pull
bounded 600 "${DOCKER[@]}" pull --platform linux/amd64 "$image" >"$workspace/pull.log" 2>&1
docker_call image inspect "$image" >"$workspace/image.json"
image_id=$(jq -r '.[0].Id' "$workspace/image.json")
[[ $image_id =~ ^sha256:[0-9a-f]{64}$ ]] || { echo image_id_refused >&2; exit 2; }
jq -e --arg image "$image" '.[0].Architecture=="amd64" and .[0].Os=="linux" and
  (.[0].RepoDigests|index($image)!=null)' "$workspace/image.json" >/dev/null
stage=create
creation_attempted=true
cid=$(docker_call create --name "$name" --label "$label=$token" --network bridge --platform linux/amd64 \
  --cpus 2 --memory 4g --pids-limit 512 --cap-drop ALL --security-opt no-new-privileges \
  --entrypoint /bin/sh "$image_id" -c 'exec sleep 4000')
[[ $cid =~ ^[0-9a-f]{64}$ ]] && owned || { echo container_ownership_refused >&2; exit 2; }
docker_call inspect "$cid" >"$workspace/container.json"
jq -e --arg image "$image_id" '.[0].Image==$image and (.[0].Mounts|length)==0 and
  .[0].HostConfig.Privileged==false and (.[0].HostConfig.PortBindings|length)==0' "$workspace/container.json" >/dev/null
docker_call start "$cid" >"$workspace/start.log" 2>&1
[[ $(docker_call exec "$cid" uname -s) == Linux && $(docker_call exec "$cid" uname -m) == x86_64 ]] || {
  echo native_container_refused >&2; exit 2;
}
docker_call exec "$cid" mkdir -m 700 /qa /qa/input /qa/results
for source in frozen-candidate.zip frozen-inventory.json source-inventory.json source.tgz; do
  docker_call cp "$workspace/input/$source" "$cid:/qa/input/$source"
done
for source in homecircle-card.js LEAFLET-LICENSE.txt; do
  docker_call cp "$workspace/source/custom_components/homecircle/frontend/$source" "$cid:/qa/input/$source"
done
docker_call cp "$script_dir/driver.py" "$cid:/qa/driver.py"
stage=container_setup_and_package
bounded 720 "${DOCKER[@]}" exec --workdir /qa "$cid" python -I -B /qa/driver.py setup \
  --payload /qa/input --tree /qa/source --results /qa/results >"$workspace/setup.log" 2>&1
docker_call cp "$cid:/qa/results/setup-summary.json" "$public/setup-summary.json"
jq -e '.outcome=="passed" and .completed==true and .core=="2026.9.4" and .release_files==112 and
  .identical_members==109 and (.version_only_changed_members|length)==3' "$public/setup-summary.json" >/dev/null
setup_pass=true
stage=disconnect
docker_call network disconnect bridge "$cid"
docker_call inspect "$cid" >"$workspace/offline.json"
jq -e '.[0].State.Running==true and (.[0].Mounts|length)==0 and (.[0].NetworkSettings.Networks|length)==0' \
  "$workspace/offline.json" >/dev/null
network_none=true
stage=offline_backend
set +e
bounded 940 "${DOCKER[@]}" exec --workdir /qa "$cid" python -I -B /qa/driver.py acceptance \
  --payload /qa/input --tree /qa/source --results /qa/results >"$workspace/acceptance.log" 2>&1
acceptance_exit=$?
set -e
[[ $acceptance_exit == 0 ]] || exit 1
docker_call cp "$cid:/qa/results/package-summary.json" "$public/package-summary.json"
jq -e '.outcome=="passed" and .completed==true and .backend.passed==1443 and .backend.failed==0 and
  .backend.skipped==1 and .release_files==112 and .identical_members==109 and .reproducible_archive==true' \
  "$public/package-summary.json" >/dev/null
acceptance_pass=true
stage=release_assets
mkdir -m 700 "$workspace/release-assets"
for source in homecircle.zip inventory.json; do
  docker_call cp "$cid:/qa/results/release/$source" "$workspace/release-assets/$source"
done
[[ $(sha256sum "$workspace/release-assets/homecircle.zip" | awk '{print $1}') == \
   $(jq -r .release_sha256 "$public/package-summary.json") &&
   $(sha256sum "$workspace/release-assets/inventory.json" | awk '{print $1}') == \
   $(jq -r .release_inventory_sha256 "$public/package-summary.json") ]] || { echo release_asset_hash_refused >&2; exit 2; }
jq -e --arg sha "$(jq -r .release_sha256 "$public/package-summary.json")" \
  '.version=="0.1.0-beta.20" and .archive_sha256==$sha and (.files|length)==112' \
  "$workspace/release-assets/inventory.json" >/dev/null
docker_call inspect "$cid" >"$workspace/after.json"
jq -e '.[0].State.Running==true and (.[0].Mounts|length)==0 and (.[0].NetworkSettings.Networks|length)==0' \
  "$workspace/after.json" >/dev/null
assets_checked=true
stage=complete

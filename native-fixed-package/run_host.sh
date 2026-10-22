#!/usr/bin/env bash
# Fresh native Linux host/container only; no host bind mounts or owner state.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo native_linux_amd64_required >&2; exit 2; }
for executable in docker timeout jq sha256sum awk mktemp cp find sort cmp wc mkdir mv rm python3 npm node git; do
  command -v "$executable" >/dev/null || { echo required_host_command_missing >&2; exit 2; }
done
[[ $(timeout --version) == *"GNU coreutils"* && -z ${DOCKER_HOST:-} ]] || { echo local_native_tools_required >&2; exit 2; }
payload= output= pins_sha= repository=
while (($#)); do
  case "$1" in
    --payload) payload=${2:?}; shift 2 ;;
    --output) output=${2:?}; shift 2 ;;
    --pins-sha) pins_sha=${2:?}; shift 2 ;;
    --source-repository) repository=${2:?}; shift 2 ;;
    *) echo arguments_refused >&2; exit 2 ;;
  esac
done
[[ -d $payload && ! -L $payload && -n $output && ! -e $output && ! -L $output ]] || {
  echo fresh_paths_required >&2; exit 2;
}
[[ $pins_sha =~ ^[0-9a-f]{64}$ && -d $repository && ! -L $repository ]] || {
  echo source_configuration_required >&2; exit 2;
}
payload=$(cd -- "$payload" && pwd -P)
repository=$(cd -- "$repository" && pwd -P)
mkdir -m 700 -- "$output"
output=$(cd -- "$output" && pwd -P)
[[ $output =~ ^/[A-Za-z0-9_./-]+$ ]] || { echo output_path_refused >&2; exit 2; }
workspace=$(mktemp -d "$output/private.XXXXXXXX")
public="$output/public-summary"
mkdir -m 700 -- "$public" "$workspace/input" "$workspace/results"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
token=${workspace##*/}; token=${token//./-}
name="homecircle-fixed-package-$token"
label=io.homecircle.fixed-package
image_repo=ghcr.io/home-assistant/qemux86-64-homeassistant
image_digest=sha256:45f009d6ff1061971102e81f0802cf2762bdd5c5007231c938bd36030cbd0a12
expected_image=sha256:e1acee126eee45b3007494ad7f806d12535dc7d733624b681ed29a505f8c2b98
image="$image_repo@$image_digest"
driver_sha= source_sha= inventory_sha= source_commit= candidate_sha= candidate_inventory_sha= canonical_sha=
source_count=0 minimum_backend=1443 required_regression_count=0
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
  [[ $(jq -r '.[0].Config.Labels["io.homecircle.fixed-package"]' <<<"$value") == "$token" &&
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
  for source in source-summary.json privacy-summary.json frontend-summary.json failure-summary.json; do
    if [[ -s $workspace/results/$source ]]; then
      cp -- "$workspace/results/$source" "$public/$source" || status=1
    fi
  done
  if [[ $status == 0 ]]; then
    jq -e --argjson minimum "$minimum_backend" --argjson required "$required_regression_count" \
      --arg candidate "$candidate_sha" --arg inventory "$candidate_inventory_sha" --arg canonical "$canonical_sha" \
      --arg commit "$source_commit" '.outcome=="passed" and .completed==true and .backend.passed >= $minimum and
      .backend.failed==0 and .backend.skipped==1 and .release_version=="0.1.0-beta.20" and .release_files==113 and
      .release_sha256==$candidate and .release_inventory_sha256==$inventory and .canonical_rebuild_sha256==$canonical and
      .canonical_reproducible_archive==true and .candidate_archive_rebuilt==false and
      .exact_candidate_bytes_installed==true and .candidate_payload_equals_canonical_payload==true and
      .candidate_compression_level==6 and .canonical_compression_level==9 and
      (.backend.required_regressions|length)==$required and all(.backend.required_regressions[];.passed==true) and
      .baseline_red.outcome=="passed" and .baseline_red.expected_failure_cases==14 and
      .baseline_red.all_expected_regressions_observed==true and .baseline_red.cause_verified==true and .baseline_red.collection_errors==0 and
      .baseline_red.skipped==0 and .baseline_red.public_files_only_copy==true and
      .baseline_red.private_copy_removed==true and .baseline_red.fixed_source_unchanged==true and
      .baseline_red.provider_or_owner_accounts_used==false and
      .baseline_red.combined_red_green_deadline_seconds==900 and .candidate_source_commit==$commit and .same_version_unreleased_development_preview==true' \
      "$public/package-summary.json" >/dev/null || status=1
    jq -e --argjson count "$source_count" '.outcome=="passed" and .frontend_tests_passed==122 and
      .frontend_reproducible==true and .privacy.files_checked==$count and .privacy.checker_exit==0' \
      "$public/frontend-summary.json" >/dev/null || status=1
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
    --arg commit "$source_commit" --arg config "$pins_sha" --argjson count "$source_count" \
    --arg candidate "$candidate_sha" --arg candidate_inventory "$candidate_inventory_sha" --arg canonical "$canonical_sha" \
    --argjson status "$status" --argjson actual "$acceptance_exit" --argjson seconds "$elapsed" \
    --argjson stopped "$stopped" --argjson removed "$removed" --argjson cleanup "$cleanup_failed" \
    --argjson private "$private_removed" --argjson network "$network_none" --argjson assets "$assets_checked" \
    '{schema:1,outcome:(if $status==0 then "passed" else "failed_or_incomplete" end),runner_exit:$status,
      failure_or_final_stage:$stage,acceptance_actual_exit:$actual,host_elapsed_seconds:$seconds,
      host_system:"Linux",host_architecture:"x86_64",host_kernel:$kernel,node_version:$node,npm_version:$npm,
      registry_digest:$digest,local_image_id:$image,source_sha256:$source,source_inventory_sha256:$inventory,
      driver_sha256:$driver,candidate_source_commit:$commit,config_sha256:$config,source_files:$count,core:"2026.10.2",
      candidate_zip_sha256:$candidate,candidate_inventory_sha256:$candidate_inventory,canonical_rebuild_sha256:$canonical,
      same_version_unreleased_development_preview:true,release_published:false,
      container_stopped:$stopped,container_removed:$removed,cleanup_failed:$cleanup,
      private_workspace_removed:$private,backend_network_disconnected:$network,release_assets_checked:$assets,
      owner_accounts_used:false,production_configuration_used:false,hacs_delivery_tested:false,
      full_managed_core_lifecycle:false,upgrade_recovery_repeated:false}' >"$public/host.json.tmp"; then
    echo host_receipt_write_failed >&2; exit 1
  fi
  if ! jq -e --argjson status "$status" '.schema==1 and .runner_exit==$status' "$public/host.json.tmp" >/dev/null ||
      ! mv -- "$public/host.json.tmp" "$public/host.json"; then
    echo host_receipt_finalize_failed >&2; exit 1
  fi
  echo "release1_development_preview_outcome=$([[ $status == 0 ]] && echo passed || echo failed_or_incomplete)"
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
unset GH_TOKEN GITHUB_TOKEN PYTHONPATH PYTHONHOME
[[ $kernel =~ ^[[:alnum:]_.+-]+$ ]] || { echo host_kernel_refused >&2; exit 2; }
[[ -f $payload/config.json && ! -L $payload/config.json &&
   $(sha256sum "$payload/config.json" | awk '{print $1}') == "$pins_sha" ]] || {
  echo config_pin_refused >&2; exit 2;
}
parsed_driver_sha=$(jq -er .driver_sha256 "$payload/config.json")
parsed_source_sha=$(jq -er .source_sha256 "$payload/config.json")
parsed_inventory_sha=$(jq -er .source_inventory_sha256 "$payload/config.json")
parsed_source_commit=$(jq -er .candidate_source_commit "$payload/config.json")
parsed_source_count=$(jq -er .source_files "$payload/config.json")
parsed_minimum_backend=$(jq -er .minimum_backend_passed "$payload/config.json")
parsed_candidate_sha=$(jq -er .package_sha256 "$payload/config.json")
parsed_candidate_inventory_sha=$(jq -er .package_inventory_sha256 "$payload/config.json")
parsed_canonical_sha=$(jq -er .canonical_package_sha256 "$payload/config.json")
parsed_required_regression_count=$(jq -er '.required_backend_tests|length' "$payload/config.json")
[[ $parsed_driver_sha =~ ^[0-9a-f]{64}$ && $parsed_source_sha =~ ^[0-9a-f]{64}$ &&
   $parsed_inventory_sha =~ ^[0-9a-f]{64}$ && $parsed_source_commit =~ ^[0-9a-f]{40}$ &&
   $parsed_source_count =~ ^[0-9]+$ && $parsed_minimum_backend =~ ^[0-9]+$ && $parsed_required_regression_count =~ ^[0-9]+$ ]] || {
  echo configuration_fields_refused >&2; exit 2;
}
driver_sha=$parsed_driver_sha
source_sha=$parsed_source_sha
inventory_sha=$parsed_inventory_sha
source_commit=$parsed_source_commit
candidate_sha=$parsed_candidate_sha
candidate_inventory_sha=$parsed_candidate_inventory_sha
canonical_sha=$parsed_canonical_sha
[[ $candidate_sha =~ ^[0-9a-f]{64}$ && $candidate_inventory_sha =~ ^[0-9a-f]{64}$ && $canonical_sha =~ ^[0-9a-f]{64}$ ]] || exit 2
source_count=$parsed_source_count
minimum_backend=$parsed_minimum_backend
required_regression_count=$parsed_required_regression_count
[[ $(sha256sum "$script_dir/driver.py" | awk '{print $1}') == "$driver_sha" ]] || {
  echo driver_pin_refused >&2; exit 2;
}
[[ -z $(find "$payload" -mindepth 1 ! -type f -print -quit) ]] || { echo payload_type_refused >&2; exit 2; }
find "$payload" -type f -printf '%P\n' | LC_ALL=C sort >"$workspace/actual-members"
printf '%s\n' baseline-vault.py config.json homecircle.zip inventory.json source-inventory.json source.tgz >"$workspace/expected-members"
cmp -s "$workspace/actual-members" "$workspace/expected-members" || { echo payload_members_refused >&2; exit 2; }
for source in baseline-vault.py config.json homecircle.zip inventory.json source-inventory.json source.tgz; do
  cp -- "$payload/$source" "$workspace/input/$source"
done
[[ $(sha256sum "$workspace/input/source.tgz" | awk '{print $1}') == "$source_sha" &&
   $(sha256sum "$workspace/input/source-inventory.json" | awk '{print $1}') == "$inventory_sha" ]] || {
  echo source_pin_refused >&2; exit 2;
}
stage=prepare
bounded 120 python3 -I -B "$script_dir/driver.py" prepare --payload "$workspace/input" \
  --tree "$workspace/source" --results "$workspace/results" --pins-sha "$pins_sha" \
  --git-directory "$repository" >"$workspace/prepare.log" 2>&1
stage=source_privacy
bounded 180 python3 -I -B "$script_dir/driver.py" privacy --payload "$workspace/input" \
  --tree "$workspace/source" --results "$workspace/results" --pins-sha "$pins_sha" \
  >"$workspace/privacy.log" 2>&1
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
stage=frontend_reproducibility
bounded 60 "${NPM[@]}" run build --prefix "$workspace/source/frontend/homecircle-card" >"$workspace/npm-build.log" 2>&1
mkdir -m 700 "$workspace/first-frontend"
for source in homecircle-card.js LEAFLET-LICENSE.txt; do
  cp -- "$workspace/source/custom_components/homecircle/frontend/$source" "$workspace/first-frontend/$source"
done
bounded 60 "${NPM[@]}" run build --prefix "$workspace/source/frontend/homecircle-card" >"$workspace/npm-rebuild.log" 2>&1
stage=frontend_tests
# Run exactly the package script's reviewed test files, with an explicit TAP
# reporter so the narrow count parser is independent of Node's default reporter.
(
  cd -- "$workspace/source/frontend/homecircle-card"
  bounded 180 node --test --test-reporter=tap test/*.test.mjs >"$workspace/npm-test.log" 2>&1
)
stage=frontend_and_privacy
bounded 240 python3 -I -B "$script_dir/driver.py" frontend --payload "$workspace/input" \
  --tree "$workspace/source" --results "$workspace/results" --npm-log "$workspace/npm-test.log" \
  --first-frontend "$workspace/first-frontend" --pins-sha "$pins_sha" \
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
[[ $image_id == "$expected_image" ]] || { echo image_id_refused >&2; exit 2; }
jq -e --arg image "$image" '.[0].Architecture=="amd64" and .[0].Os=="linux" and
  (.[0].RepoDigests|index($image)!=null)' "$workspace/image.json" >/dev/null
stage=create
creation_attempted=true
cid=$(docker_call create --name "$name" --label "$label=$token" --network bridge --platform linux/amd64 \
  --cpus 2 --memory 5g --pids-limit 512 --no-healthcheck --cap-drop ALL --security-opt no-new-privileges \
  --entrypoint /bin/sh "$image_id" -c 'exec sleep 4000')
[[ $cid =~ ^[0-9a-f]{64}$ ]] && owned || { echo container_ownership_refused >&2; exit 2; }
docker_call inspect "$cid" >"$workspace/container.json"
jq -e --arg image "$image_id" '.[0].Image==$image and (.[0].Mounts|length)==0 and
  .[0].HostConfig.Privileged==false and (.[0].HostConfig.PortBindings|length)==0' "$workspace/container.json" >/dev/null
docker_call start "$cid" >"$workspace/start.log" 2>&1
[[ $(docker_call exec "$cid" uname -s) == Linux && $(docker_call exec "$cid" uname -m) == x86_64 ]] || {
  echo native_container_refused >&2; exit 2;
}
stage=container_staging
docker_call exec "$cid" mkdir -m 700 /qa /qa/input /qa/results
[[ $(docker_call exec "$cid" id -u) == 0 && $(docker_call exec "$cid" id -g) == 0 ]] || {
  echo container_staging_identity_refused >&2; exit 2;
}
for directory in /qa /qa/input /qa/results; do
  [[ $(docker_call exec "$cid" stat -c '%u:%g:%a' "$directory") == 0:0:700 ]] || {
    echo container_staging_directory_refused >&2; exit 2;
  }
done
stage_file() {
  local source_file=$1 destination=$2 expected actual
  expected=$(sha256sum "$source_file" | awk '{print $1}')
  [[ $expected =~ ^[0-9a-f]{64}$ ]] || { echo staging_source_hash_refused >&2; return 1; }
  # A container-owned process creates each file. No host UID/GID/mode metadata
  # crosses the boundary, and no capability or host mount is added.
  bounded 30 "${DOCKER[@]}" exec -i "$cid" /bin/sh -c \
    'set -eu; umask 077; test ! -e "$1"; test ! -L "$1"; cat > "$1"' sh "$destination" \
    <"$source_file" >"$workspace/staging.log" 2>&1
  [[ $(docker_call exec "$cid" stat -c '%u:%g:%a' "$destination") == 0:0:600 ]] || {
    echo container_staging_file_refused >&2; return 1;
  }
  docker_call exec "$cid" test -r "$destination"
  actual=$(docker_call exec "$cid" sha256sum "$destination" | awk '{print $1}')
  [[ $actual == "$expected" ]] || { echo container_staging_hash_refused >&2; return 1; }
}
for source in baseline-vault.py config.json homecircle.zip inventory.json source-inventory.json source.tgz; do
  stage_file "$workspace/input/$source" "/qa/input/$source"
done
stage_file "$workspace/results/frontend-summary.json" /qa/input/frontend-summary.json
for source in homecircle-card.js LEAFLET-LICENSE.txt; do
  stage_file "$workspace/source/custom_components/homecircle/frontend/$source" "/qa/input/$source"
done
stage_file "$script_dir/driver.py" /qa/driver.py
stage_file "$script_dir/requirements_support.py" /qa/requirements_support.py
stage=container_setup_and_package
bounded 720 "${DOCKER[@]}" exec --workdir /qa "$cid" python -I -B /qa/driver.py setup \
  --payload /qa/input --tree /qa/source --results /qa/results --pins-sha "$pins_sha" >"$workspace/setup.log" 2>&1
docker_call cp "$cid:/qa/results/setup-summary.json" "$public/setup-summary.json"
jq -e --arg commit "$source_commit" '.outcome=="passed" and .completed==true and .core=="2026.10.2" and
  .release_files==113 and .candidate_source_commit==$commit and .package_matches_exact_source_and_built_frontend==true and
  .same_version_unreleased_development_preview==true and .version_substitutions_performed==false' \
  "$public/setup-summary.json" >/dev/null
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
  --payload /qa/input --tree /qa/source --results /qa/results --pins-sha "$pins_sha" >"$workspace/acceptance.log" 2>&1
acceptance_exit=$?
set -e
[[ $acceptance_exit == 0 ]] || exit 1
docker_call cp "$cid:/qa/results/package-summary.json" "$public/package-summary.json"
jq -e --argjson minimum "$minimum_backend" --argjson required "$required_regression_count" \
  --arg commit "$source_commit" '.outcome=="passed" and .completed==true and .backend.passed >= $minimum and
  .backend.failed==0 and .backend.skipped==1 and .release_files==113 and .canonical_reproducible_archive==true and .candidate_archive_rebuilt==false and
  .exact_candidate_bytes_installed==true and .candidate_payload_equals_canonical_payload==true and
  .candidate_source_commit==$commit and (.backend.required_regressions|length)==$required and
  all(.backend.required_regressions[];.passed==true) and .baseline_red.outcome=="passed" and .baseline_red.expected_failure_cases==14 and
      .baseline_red.all_expected_regressions_observed==true and .baseline_red.cause_verified==true and .baseline_red.collection_errors==0 and
      .baseline_red.skipped==0 and .baseline_red.public_files_only_copy==true and
      .baseline_red.private_copy_removed==true and .baseline_red.fixed_source_unchanged==true and
      .baseline_red.provider_or_owner_accounts_used==false and
      .baseline_red.combined_red_green_deadline_seconds==900' "$public/package-summary.json" >/dev/null
jq -e --arg candidate "$candidate_sha" --arg inventory "$candidate_inventory_sha" --arg canonical "$canonical_sha" \
  '.release_sha256==$candidate and .release_inventory_sha256==$inventory and .canonical_rebuild_sha256==$canonical and
   .canonical_reproducible_archive==true and .candidate_archive_rebuilt==false and
   .exact_candidate_bytes_installed==true and .candidate_payload_equals_canonical_payload==true and
   .candidate_compression_level==6 and .canonical_compression_level==9' "$public/package-summary.json" >/dev/null
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
  '.version=="0.1.0-beta.20" and .archive_sha256==$sha and (.files|length)==113' \
  "$workspace/release-assets/inventory.json" >/dev/null
docker_call inspect "$cid" >"$workspace/after.json"
jq -e '.[0].State.Running==true and (.[0].Mounts|length)==0 and (.[0].NetworkSettings.Networks|length)==0' \
  "$workspace/after.json" >/dev/null
assets_checked=true
stage=complete

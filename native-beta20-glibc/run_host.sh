#!/usr/bin/env bash
# Fresh native Linux Ubuntu/glibc container only; no host mounts or owner state.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo native_linux_amd64_required >&2; exit 2; }
for executable in docker timeout jq sha256sum awk mktemp cp wc mkdir mv rm curl sed tail; do
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
mkdir -m 700 -- "$public" "$workspace/input"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
token=${workspace##*/}; token=${token//./-}
name="homecircle-beta20-glibc-$token"
label=io.homecircle.beta20-glibc
image_digest=sha256:a2d43bffc46670d7108bb3c0468c67c5557c4c92e83e1e34cbff1322ad1b94dc
base_image="docker.io/library/ubuntu@$image_digest"
expected_base_config=sha256:6277ab668b2ad3c3ab851d370faa1690d324b30db29d342527f61fed28f20f36
image_name="homecircle-beta20-glibc-runtime:$token"
image_label=io.homecircle.beta20-glibc-image
dockerfile_sha=eb38bcdd0f690ae79cd281cbe528831b9383806d913f3683cda5f1e7004f17e7
driver_sha=736dafa9317cc36d4dc6fcc18f93af2c408a81bd690dc155db8044f12f53259c
source_sha=261aeb3219071a44e1c6ca53f2f18e26624ae450a641d29be32450ee265d4818
inventory_sha=be693aef2f7a049cc4c0752179069664c86e444e24cc9fb01393d40f5d1288b1
constraints_sha=7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5
python_sha=143b1dddefaec3bd2e21e3b839b34a2b7fb9842272883c576420d605e9f30c63
release_sha=fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285
release_inventory_sha=5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77
release_commit=d02a9bdb9027cb51c99165a09ba50d5b175f5fb9
cid= image_id= stage=inputs acceptance_exit=-1 kernel=$(uname -r)
creation_attempted=false stopped=false removed=false cleanup_failed=false private_removed=false
build_attempted=false image_removed=false runtime_build_stage=not_started runtime_build_exit=-1
network_none=false setup_pass=false acceptance_pass=false public_release_checked=false runtime_built=false
started=$(awk '{print $1}' /proc/uptime)
deadline=$((SECONDS + 4200))
cleanup_deadline=$((deadline + 150))
DOCKER=(docker)

bounded() {
  local maximum=$1; shift
  local remaining=$((deadline - SECONDS))
  ((remaining > 0)) || { echo host_deadline_exceeded >&2; return 1; }
  ((remaining < maximum)) && maximum=$remaining
  timeout --signal=TERM --kill-after=10s "${maximum}s" "$@"
}
docker_call() { bounded 30 "${DOCKER[@]}" "$@"; }
docker_cleanup() {
  local remaining=$((cleanup_deadline - SECONDS)) maximum=15
  ((remaining > 0)) || return 1
  ((remaining < maximum)) && maximum=$remaining
  timeout --signal=TERM --kill-after=3s "${maximum}s" "${DOCKER[@]}" "$@"
}
setup_receipt_valid() {
  jq -e --arg release "$release_sha" --arg constraints "$constraints_sha" '.outcome=="passed" and
    .completed==true and .release_version=="0.1.0-beta.20" and .release_sha256==$release and
    .release_files==112 and .source_files==327 and .all_runtime_files_from_published_zip==true and
    .tagged_source_unchanged==true and .environment.os=="ubuntu" and .environment.os_version=="24.04" and
    .environment.machine=="x86_64" and .environment.python=="3.14.6" and
    .environment.active_libc=="glibc" and .environment.active_libc_version=="2.39" and
    .environment.core=="2026.10.2" and .environment.constraints_sha256==$constraints and
    .environment.pytest_plugin=="0.13.373" and (.installed_dependency_closure|length)==24' "$1" >/dev/null
}
acceptance_receipt_valid() {
  setup_receipt_valid "$1" &&
  jq -e '.current_stage=="complete" and .backend.passed==1443 and .backend.failed==0 and
    .backend.skipped==1 and .native.actual_zip_native_worker==true and .native.workers_reaped==true and
    .lifecycle.actual_provider_lifecycle==true and .lifecycle.active_native_cancellation==true and
    .lifecycle.workers_reaped==2 and .core_startup.config_options_persistence==true and
    .core_startup.served_published_bundle==true and .core_startup.synthetic_configuration_removed==true and
    (.core_startup.separate_core_processes|length)==2 and .offline_container_boundary_required==true' "$1" >/dev/null
}
owned() {
  local value found
  value=$(docker_cleanup container inspect "$name" 2>/dev/null) || return 1
  [[ $(jq -r '.[0].Config.Labels["io.homecircle.beta20-glibc"]' <<<"$value") == "$token" &&
     $(jq -r '.[0].Name' <<<"$value") == "/$name" ]] || return 1
  found=$(jq -r '.[0].Id' <<<"$value")
  [[ $found =~ ^[0-9a-f]{64}$ && ( -z $cid || $cid == "$found" ) ]] || return 1
  cid=$found
}

finish() {
  local status=$? ids ended elapsed source
  trap - EXIT INT TERM HUP
  set +e
  local finish_limit=$((SECONDS + 150))
  ((finish_limit < cleanup_deadline)) && cleanup_deadline=$finish_limit
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
      for source in setup-summary.json glibc-summary.json failure-summary.json; do
        docker_cleanup cp "$cid:/qa/results/$source" "$public/$source" >"$workspace/collect.log" 2>&1
      done
      docker_cleanup rm "$cid" >>"$workspace/cleanup.log" 2>&1
      if ids=$(docker_cleanup container ls -aq --no-trunc --filter "id=$cid"); then
        [[ -z $ids ]] && removed=true
      fi
    fi
  else
    # A timed-out create cannot establish absence at the daemon boundary.
    cleanup_failed=true
  fi
  if [[ -f $workspace/python-build.log ]]; then
    runtime_build_stage=$(sed -nE 's/^.*glibc_build_stage=(apt|source_download|source_verify|configure|make|install|import)$/\1/p' "$workspace/python-build.log" | tail -n 1)
    case "$runtime_build_stage" in apt|source_download|source_verify|configure|make|install|import) ;; *) runtime_build_stage=unavailable ;; esac
  fi
  if [[ $build_attempted == false ]]; then
    image_removed=true
  else
    local observed image_labels tagged
    if observed=$(docker_cleanup image inspect "$image_name" 2>/dev/null); then
      image_labels=$(jq -r '.[0].Config.Labels["io.homecircle.beta20-glibc-image"]' <<<"$observed")
      tagged=$(jq -r '.[0].Id' <<<"$observed")
      if [[ $image_labels == "$token" && $tagged =~ ^sha256:[0-9a-f]{64}$ &&
            ( -z $image_id || $image_id == "$tagged" ) ]] &&
          jq -e --arg name "$image_name" '.[0].RepoTags==[$name]' <<<"$observed" >/dev/null; then
        if docker_cleanup image rm "$tagged" >"$workspace/image-cleanup.log" 2>&1; then
          if ids=$(docker_cleanup image ls -aq --no-trunc --filter "label=$image_label=$token"); then
            [[ -z $ids ]] && image_removed=true
          fi
        fi
      fi
    fi
  fi
  [[ $stopped == true && $removed == true && $image_removed == true ]] || cleanup_failed=true
  [[ $cleanup_failed == false && $acceptance_exit == 0 && $setup_pass == true &&
     $acceptance_pass == true && $network_none == true && $public_release_checked == true &&
     $runtime_built == true ]] || status=1
  if [[ $status == 0 ]]; then
    setup_receipt_valid "$public/setup-summary.json" || status=1
    acceptance_receipt_valid "$public/glibc-summary.json" || status=1
  fi
  rm -rf -- "$workspace"
  [[ ! -e $workspace ]] && private_removed=true
  if [[ $private_removed != true ]]; then cleanup_failed=true; status=1; fi
  ended=$(awk '{print $1}' /proc/uptime)
  elapsed=$(awk -v begin="$started" -v end="$ended" 'BEGIN {printf "%.3f", end-begin}')
  if ! jq -n --arg stage "$stage" --arg kernel "$kernel" --arg digest "$image_digest" \
    --arg image "$image_id" --arg source "$source_sha" --arg inventory "$inventory_sha" \
    --arg constraints "$constraints_sha" --arg driver "$driver_sha" --arg python "$python_sha" \
    --arg dockerfile "$dockerfile_sha" --arg base_config "$expected_base_config" \
    --arg build_stage "$runtime_build_stage" --argjson build_exit "$runtime_build_exit" \
    --arg release "$release_sha" --arg release_inventory "$release_inventory_sha" --arg commit "$release_commit" \
    --argjson status "$status" --argjson actual "$acceptance_exit" --argjson seconds "$elapsed" \
    --argjson stopped "$stopped" --argjson removed "$removed" --argjson cleanup "$cleanup_failed" \
    --argjson private "$private_removed" --argjson network "$network_none" --argjson image_removed "$image_removed" \
    --argjson checked "$public_release_checked" --argjson built "$runtime_built" \
    '{schema:1,outcome:(if $status==0 then "passed" else "failed_or_incomplete" end),runner_exit:$status,
      failure_or_final_stage:$stage,acceptance_actual_exit:$actual,host_elapsed_seconds:$seconds,
      host_system:"Linux",host_architecture:"x86_64",host_kernel:$kernel,
      registry_digest:$digest,base_image_config_sha256:$base_config,local_runtime_image_id:$image,dockerfile_sha256:$dockerfile,runtime_build_stage:$build_stage,runtime_build_exit:$build_exit,source_sha256:$source,source_inventory_sha256:$inventory,
      constraints_sha256:$constraints,driver_sha256:$driver,python_source_sha256:$python,
      python_source_version:"3.14.6",python_source_build_completed:$built,
      release_zip_sha256:$release,release_inventory_sha256:$release_inventory,release_commit:$commit,
      release_tag:"v0.1.0-beta.20",release_id:418643687,release_asset_id:659912694,release_asset_bytes:604937,
      published_release_download_checked:$checked,container_stopped:$stopped,container_removed:$removed,
      cleanup_failed:$cleanup,private_workspace_removed:$private,owned_runtime_image_removed:$image_removed,backend_network_disconnected:$network,
      owner_accounts_used:false,production_configuration_used:false,glibc_target:"Ubuntu 24.04 amd64",
      hacs_delivery_repeated:false,supervisor_backup_restore_repeated:false}' >"$public/host.json.tmp"; then
    echo host_receipt_write_failed >&2; exit 1
  fi
  if ! jq -e --argjson status "$status" '.schema==1 and .runner_exit==$status' "$public/host.json.tmp" >/dev/null ||
      ! mv -- "$public/host.json.tmp" "$public/host.json"; then
    echo host_receipt_finalize_failed >&2; exit 1
  fi
  echo "beta20_glibc_outcome=$([[ $status == 0 ]] && echo passed || echo failed_or_incomplete)"
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
unset GH_TOKEN GITHUB_TOKEN PYTHONPATH PYTHONHOME PIP_INDEX_URL PIP_EXTRA_INDEX_URL PIP_CONFIG_FILE
[[ $kernel =~ ^[[:alnum:]_.+-]+$ ]] || { echo host_kernel_refused >&2; exit 2; }
[[ $image_digest =~ ^sha256:[0-9a-f]{64}$ && $driver_sha =~ ^[0-9a-f]{64}$ && $dockerfile_sha =~ ^[0-9a-f]{64}$ ]] || {
  echo finalized_runtime_and_driver_pins_required >&2; exit 2;
}
[[ $(sha256sum "$script_dir/Dockerfile" | awk '{print $1}') == "$dockerfile_sha" && $(sha256sum "$script_dir/driver.py" | awk '{print $1}') == "$driver_sha" ]] || { echo driver_pin_refused >&2; exit 2; }
for source in source-inventory.json source.tgz; do
  [[ -f $payload/$source && ! -L $payload/$source ]] || { echo source_payload_refused >&2; exit 2; }
  cp -- "$payload/$source" "$workspace/input/$source"
done
[[ -f $script_dir/core-constraints.txt && ! -L $script_dir/core-constraints.txt ]] || { echo constraints_input_refused >&2; exit 2; }
cp -- "$script_dir/core-constraints.txt" "$workspace/input/core-constraints.txt"
[[ $(sha256sum "$workspace/input/source.tgz" | awk '{print $1}') == "$source_sha" &&
   $(sha256sum "$workspace/input/source-inventory.json" | awk '{print $1}') == "$inventory_sha" &&
   $(sha256sum "$workspace/input/core-constraints.txt" | awk '{print $1}') == "$constraints_sha" ]] || {
  echo input_pin_refused >&2; exit 2;
}

stage=public_release_provenance
CURL=(curl --disable --fail --silent --show-error --proto '=https' --tlsv1.2 --connect-timeout 15 --max-time 180 --retry 2 --max-filesize 4194304)
bounded 210 "${CURL[@]}" https://api.github.com/repos/jmhjr/HomeCircle/releases/tags/v0.1.0-beta.20 \
  --output "$workspace/release.json" >"$workspace/fetch.log" 2>&1
bounded 210 "${CURL[@]}" https://api.github.com/repos/jmhjr/HomeCircle/git/ref/tags/v0.1.0-beta.20 \
  --output "$workspace/tag.json" >>"$workspace/fetch.log" 2>&1
jq -e --arg commit "$release_commit" --arg sha "$release_sha" '.id==418643687 and .tag_name=="v0.1.0-beta.20" and
  .target_commitish==$commit and .prerelease==true and .draft==false and
  ([.assets[]|select(.name=="homecircle.zip" and .id==659912694 and .size==604937 and
  .state=="uploaded" and .digest==("sha256:"+$sha) and
  .browser_download_url=="https://github.com/jmhjr/HomeCircle/releases/download/v0.1.0-beta.20/homecircle.zip")]|length)==1' \
  "$workspace/release.json" >/dev/null
jq -e --arg commit "$release_commit" '.object.type=="commit" and .object.sha==$commit' "$workspace/tag.json" >/dev/null
bounded 210 "${CURL[@]}" --location --proto-redir '=https' \
  https://github.com/jmhjr/HomeCircle/releases/download/v0.1.0-beta.20/homecircle.zip \
  --output "$workspace/input/published-homecircle.zip" >>"$workspace/fetch.log" 2>&1
bounded 210 "${CURL[@]}" --location --proto-redir '=https' \
  https://github.com/jmhjr/HomeCircle/releases/download/v0.1.0-beta.20/inventory.json \
  --output "$workspace/input/published-inventory.json" >>"$workspace/fetch.log" 2>&1
[[ $(wc -c <"$workspace/input/published-homecircle.zip") == 604937 &&
   $(sha256sum "$workspace/input/published-homecircle.zip" | awk '{print $1}') == "$release_sha" &&
   $(sha256sum "$workspace/input/published-inventory.json" | awk '{print $1}') == "$release_inventory_sha" ]] || {
  echo public_download_pin_refused >&2; exit 2;
}
public_release_checked=true

stage=docker_preflight
context=$(bounded 30 docker context show)
endpoint=$(bounded 30 docker context inspect "$context" --format '{{.Endpoints.docker.Host}}')
[[ $endpoint == unix:///* ]] || { echo local_docker_socket_required >&2; exit 2; }
DOCKER=(docker --context "$context")
[[ $(docker_call info --format '{{.OSType}}/{{.Architecture}}') == linux/x86_64 ]] || { echo native_linux_docker_daemon_required >&2; exit 2; }
stage=image_pull
bounded 600 "${DOCKER[@]}" pull --platform linux/amd64 "$base_image" >"$workspace/pull.log" 2>&1
docker_call image inspect "$base_image" >"$workspace/base-image.json"
jq -e --arg image "$base_image" --arg short "ubuntu@$image_digest" --arg config "$expected_base_config" '.[0].Architecture=="amd64" and
  .[0].Os=="linux" and .[0].Id==$config and
  ((.[0].RepoDigests|index($image)!=null) or (.[0].RepoDigests|index($short)!=null))' "$workspace/base-image.json" >/dev/null
stage=python_source_build
mkdir -m 700 "$workspace/build-context"
cp -- "$script_dir/Dockerfile" "$workspace/build-context/Dockerfile"
build_attempted=true
set +e
bounded 1500 "${DOCKER[@]}" build --pull=false --no-cache --rm --force-rm --network default \
  --label "$image_label=$token" --tag "$image_name" "$workspace/build-context" >"$workspace/python-build.log" 2>&1
runtime_build_exit=$?
set -e
[[ $runtime_build_exit == 0 ]] || exit 1
docker_call image inspect "$image_name" >"$workspace/image.json"
image_id=$(jq -r '.[0].Id' "$workspace/image.json")
[[ $image_id =~ ^sha256:[0-9a-f]{64}$ ]] || { echo runtime_image_id_refused >&2; exit 2; }
jq -e --arg token "$token" '.[0].Architecture=="amd64" and .[0].Os=="linux" and
  .[0].Config.Labels["io.homecircle.beta20-glibc-image"]==$token' "$workspace/image.json" >/dev/null
runtime_built=true
stage=create
creation_attempted=true
cid=$(docker_call create --name "$name" --label "$label=$token" --network bridge --platform linux/amd64 \
  --cpus 2 --memory 4g --pids-limit 512 --cap-drop ALL --security-opt no-new-privileges \
  --entrypoint /bin/sh "$image_id" -c 'exec sleep 5000')
[[ $cid =~ ^[0-9a-f]{64}$ ]] && owned || { echo container_ownership_refused >&2; exit 2; }
docker_call inspect "$cid" >"$workspace/container.json"
jq -e --arg image "$image_id" '.[0].Image==$image and (.[0].Mounts|length)==0 and
  .[0].HostConfig.Privileged==false and (.[0].HostConfig.PortBindings|length)==0 and
  .[0].HostConfig.CapDrop==["ALL"] and (.[0].HostConfig.SecurityOpt|index("no-new-privileges")!=null)' \
  "$workspace/container.json" >/dev/null
docker_call start "$cid" >"$workspace/start.log" 2>&1
[[ $(docker_call exec "$cid" uname -s) == Linux && $(docker_call exec "$cid" uname -m) == x86_64 ]] || { echo native_container_refused >&2; exit 2; }
stage=container_staging
docker_call exec "$cid" mkdir -m 700 /qa /qa/input /qa/results
[[ $(docker_call exec "$cid" id -u) == 0 && $(docker_call exec "$cid" id -g) == 0 ]] || { echo container_staging_identity_refused >&2; exit 2; }
for directory in /qa /qa/input /qa/results; do
  [[ $(docker_call exec "$cid" stat -c '%u:%g:%a' "$directory") == 0:0:700 ]] || { echo container_staging_directory_refused >&2; exit 2; }
done
stage_file() {
  local source_file=$1 destination=$2 expected actual
  expected=$(sha256sum "$source_file" | awk '{print $1}')
  [[ $expected =~ ^[0-9a-f]{64}$ ]] || { echo staging_source_hash_refused >&2; return 1; }
  bounded 30 "${DOCKER[@]}" exec -i "$cid" /bin/sh -c \
    'set -eu; umask 077; test ! -e "$1"; test ! -L "$1"; cat > "$1"' sh "$destination" \
    <"$source_file" >"$workspace/staging.log" 2>&1
  [[ $(docker_call exec "$cid" stat -c '%u:%g:%a' "$destination") == 0:0:600 ]] || { echo container_staging_file_refused >&2; return 1; }
  actual=$(docker_call exec "$cid" sha256sum "$destination" | awk '{print $1}')
  [[ $actual == "$expected" ]] || { echo container_staging_hash_refused >&2; return 1; }
}
for source in source.tgz source-inventory.json core-constraints.txt published-homecircle.zip published-inventory.json; do
  stage_file "$workspace/input/$source" "/qa/input/$source"
done
stage_file "$script_dir/driver.py" /qa/driver.py

stage=runtime_venv
bounded 90 "${DOCKER[@]}" exec "$cid" /opt/python/bin/python3.14 -I -B -m venv /qa/venv
stage=core_dependency_setup
bounded 1500 "${DOCKER[@]}" exec --workdir /qa "$cid" /qa/venv/bin/python -I -B /qa/driver.py setup \
  --payload /qa/input --tree /qa/source --runtime-tree /qa/runtime --results /qa/results \
  >"$workspace/setup.log" 2>&1
docker_call cp "$cid:/qa/results/setup-summary.json" "$public/setup-summary.json"
setup_receipt_valid "$public/setup-summary.json"
setup_pass=true
stage=disconnect
docker_call network disconnect bridge "$cid"
docker_call inspect "$cid" >"$workspace/offline.json"
jq -e '.[0].State.Running==true and (.[0].Mounts|length)==0 and (.[0].NetworkSettings.Networks|length)==0 and
  .[0].HostConfig.Privileged==false and (.[0].HostConfig.PortBindings|length)==0 and .[0].HostConfig.CapDrop==["ALL"]' \
  "$workspace/offline.json" >/dev/null
network_none=true
stage=offline_glibc_acceptance
set +e
bounded 1800 "${DOCKER[@]}" exec --workdir /qa "$cid" /qa/venv/bin/python -I -B /qa/driver.py acceptance \
  --payload /qa/input --tree /qa/source --runtime-tree /qa/runtime --results /qa/results \
  >"$workspace/acceptance.log" 2>&1
acceptance_exit=$?
set -e
[[ $acceptance_exit == 0 ]] || exit 1
docker_call cp "$cid:/qa/results/glibc-summary.json" "$public/glibc-summary.json"
acceptance_receipt_valid "$public/glibc-summary.json"
acceptance_pass=true
docker_call inspect "$cid" >"$workspace/after.json"
jq -e '.[0].State.Running==true and (.[0].Mounts|length)==0 and (.[0].NetworkSettings.Networks|length)==0 and
  .[0].HostConfig.Privileged==false and (.[0].HostConfig.PortBindings|length)==0 and .[0].HostConfig.CapDrop==["ALL"]' \
  "$workspace/after.json" >/dev/null
stage=complete

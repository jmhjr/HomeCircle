#!/usr/bin/env bash
# Preparation only until separately reviewed. Native Linux/local Docker, owned volume.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && -z ${DOCKER_HOST:-} ]] || { echo native_local_linux_required >&2; exit 2; }
for executable in docker timeout jq sha256sum python3 git mktemp awk cp find sort cmp; do command -v "$executable" >/dev/null; done
payload= output= pins= pins_sha= repository=
while (($#)); do
  case "$1" in
    --payload) payload=${2:?}; shift 2 ;;
    --output) output=${2:?}; shift 2 ;;
    --pins) pins=${2:?}; shift 2 ;;
    --pins-sha) pins_sha=${2:?}; shift 2 ;;
    --source-repository) repository=${2:?}; shift 2 ;;
    *) exit 2 ;;
  esac
done
[[ $(timeout --version) == *'GNU coreutils'* && -d $payload && ! -L $payload && -d $repository && ! -L $repository && -f $pins && ! -L $pins && -n $output && ! -e $output && ! -L $output && $pins_sha =~ ^[a-f0-9]{64}$ && $(sha256sum "$pins" | awk '{print $1}') == "$pins_sha" ]] || exit 2
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
pins=$(cd -- "$(dirname -- "$pins")" && printf '%s/%s' "$PWD" "$(basename -- "$pins")")
payload=$(cd -- "$payload" && pwd -P); repository=$(cd -- "$repository" && pwd -P)
arch=$(jq -er .architecture "$pins"); machine=$(jq -er .machine "$pins"); target=$(jq -er .target "$pins")
[[ ( $arch == amd64 && $machine == x86_64 ) || ( $arch == arm64 && $machine == aarch64 ) ]] || exit 2
[[ $(uname -m) == "$machine" ]] || exit 2
mkdir -m 700 -- "$output"; output=$(cd -- "$output" && pwd -P)
[[ $output =~ ^/[A-Za-z0-9_./-]+$ ]] || exit 2
workspace=$(mktemp -d "$output/private.XXXXXXXX")
public="$output/public-summary"; mkdir -m 700 "$public"
token=${workspace##*/}; token=${token//./-}
label=io.homecircle.consumer-witness
prep_name="homecircle-consumer-prep-$token"; consumer_name="homecircle-consumer-service-$token"; volume="homecircle-consumer-config-$token"
prep_id= consumer_id= volume_created=false private_removed=false cleanup_failed=false
prep_attempted=false consumer_attempted=false volume_attempted=false startups=0
prepared=false offline=false first=false restarted=false final_stop=false complete=false stage=preflight
deadline=$((SECONDS + 2100)); DOCKER=(docker)
bounded() { local maximum=$1; shift; local remaining=$((deadline - SECONDS)); ((remaining > 0)) || return 1; ((remaining < maximum)) && maximum=$remaining; timeout --signal=TERM --kill-after=10s "${maximum}s" "$@"; }
call() { bounded 30 "${DOCKER[@]}" "$@"; }
clean_call() { timeout --signal=TERM --kill-after=3s 15s "${DOCKER[@]}" "$@"; }
owned_volume() {
  local data; data=$(clean_call volume inspect "$volume" 2>/dev/null) || return 1
  jq -e --arg name "$volume" --arg token "$token" 'length==1 and .[0].Name==$name and .[0].Driver=="local" and .[0].Scope=="local" and .[0].Labels["io.homecircle.consumer-witness"]==$token and ((.[0].Options // {})|length)==0' <<<"$data" >/dev/null
}
owned_container() {
  local name=$1 expected=$2 data
  data=$(clean_call inspect "$name" 2>/dev/null) || return 1
  jq -e --arg name "/$name" --arg service "/$consumer_name" --arg id "$expected" --arg image "$image_id" --arg token "$token" --arg volume "$volume" --argjson offline "$offline" 'length==1 and .[0].Name==$name and .[0].Id==$id and .[0].Image==$image and .[0].Config.Labels["io.homecircle.consumer-witness"]==$token and (.[0].Mounts|length)==1 and .[0].Mounts[0].Type=="volume" and .[0].Mounts[0].Name==$volume and .[0].Mounts[0].Destination=="/config" and .[0].Mounts[0].RW==true and (if $offline then (if $name==$service then .[0].HostConfig.NetworkMode=="none" and (.[0].NetworkSettings.Networks|keys|all(.=="none")) else (.[0].NetworkSettings.Networks|length)==0 end) else true end)' <<<"$data" >/dev/null
}
boundary() {
  local id=$1 mode=$2
  call inspect "$id" | jq -e --arg image "$image_id" --arg mode "$mode" --argjson offline "$offline" '.[0].Image==$image and .[0].HostConfig.Privileged==false and .[0].HostConfig.PidMode=="" and .[0].HostConfig.IpcMode=="private" and (.[0].HostConfig.Devices|length)==0 and (.[0].HostConfig.PortBindings|length)==0 and (.[0].HostConfig.CapAdd|length)==0 and (.[0].HostConfig.CapDrop|length)==0 and .[0].HostConfig.RestartPolicy.Name=="no" and .[0].HostConfig.NetworkMode==$mode and ((.[0].NetworkSettings.Networks|keys) as $networks | if $mode=="none" then ($networks|all(.=="none")) elif $offline then ($networks|length)==0 else true end)' >/dev/null
}
finish() {
  local status=$? id name data attempted stopped=true removed=true volume_removed=false identities=true
  trap - EXIT INT TERM HUP; set +e
  if [[ -n $prep_id ]] && owned_container "$prep_name" "$prep_id" && owned_volume; then
    for name in failure-summary.json; do clean_call cp "$prep_id:/qa/$name" "$public/$name" >"$workspace/failure-collect-private.log" 2>&1; done
    clean_call cp "$prep_id:/config/.homecircle-consumer-qa/guest-failure.json" "$public/guest-failure.json" >"$workspace/failure-collect-private.log" 2>&1
  fi
  for name in "$consumer_name" "$prep_name"; do
    if [[ $name == "$consumer_name" ]]; then id=$consumer_id; attempted=$consumer_attempted; else id=$prep_id; attempted=$prep_attempted; fi
    if [[ -z $id && $attempted == true ]]; then
      data=$(clean_call inspect "$name" 2>/dev/null)
      if [[ $? == 0 ]]; then
        id=$(jq -r '.[0].Id' <<<"$data")
        [[ $id =~ ^[a-f0-9]{64}$ ]] || { cleanup_failed=true; identities=false; continue; }
      else
        data=$(clean_call container ls -aq --no-trunc --filter "name=^/$name$")
        if [[ $? == 0 && -z $data ]]; then continue; fi
        cleanup_failed=true; identities=false; continue
      fi
    fi
    if [[ -n $id ]]; then
      if ! owned_container "$name" "$id" || ! owned_volume; then identities=false; cleanup_failed=true; continue; fi
      if [[ $(clean_call inspect --format '{{.State.Running}}' "$id" 2>/dev/null) == true ]]; then
        clean_call kill --signal TERM "$id" >"$workspace/cleanup-private.log" 2>&1
        clean_call wait "$id" >>"$workspace/cleanup-private.log" 2>&1
        if [[ $(clean_call inspect --format '{{.State.Running}}' "$id" 2>/dev/null) == true ]]; then clean_call kill --signal KILL "$id" >>"$workspace/cleanup-private.log" 2>&1; fi
      fi
      [[ $(clean_call inspect --format '{{.State.Running}}' "$id" 2>/dev/null) == false ]] || { stopped=false; cleanup_failed=true; continue; }
      clean_call rm "$id" >>"$workspace/cleanup-private.log" 2>&1
      data=$(clean_call container ls -aq --no-trunc --filter "id=$id")
      [[ $? == 0 && -z $data ]] || { removed=false; cleanup_failed=true; }
    fi
  done
  if [[ $volume_attempted == true ]] && owned_volume && [[ $removed == true && $identities == true ]]; then
    clean_call volume rm "$volume" >"$workspace/volume-private.log" 2>&1
    data=$(clean_call volume ls -q --filter "name=^$volume$")
    if [[ $? == 0 && -z $data ]]; then volume_removed=true; fi
  elif [[ $volume_attempted == false ]]; then volume_removed=true; fi
  [[ $stopped == true && $removed == true && $volume_removed == true ]] || cleanup_failed=true
  [[ $complete == true && $cleanup_failed == false ]] || status=1
  rm -rf -- "$workspace"; [[ ! -e $workspace ]] && private_removed=true
  [[ $private_removed == true ]] || { status=1; cleanup_failed=true; }
  jq -n --arg target "$target" --arg stage "$stage" --arg pins "$pins_sha" --argjson status "$status" --argjson cleanup "$cleanup_failed" --argjson stopped "$stopped" --argjson removed "$removed" --argjson volume "$volume_removed" --argjson private "$private_removed" --argjson offline "$offline" --argjson first "$first" --argjson restart "$restarted" --argjson stop "$final_stop" --argjson startups "$startups" '{schema:1,outcome:(if $status==0 then "passed" else "failed_or_incomplete" end),target:$target,stage:$stage,pins_sha256:$pins,exit_code:$status,cleanup_failed:$cleanup,owned_containers_stopped:$stopped,owned_containers_removed:$removed,owned_volume_removed:$volume,private_workspace_removed:$private,both_containers_offline_during_acceptance:$offline,first_service_phase:$first,restart_service_phase:$restart,final_clean_stop:$stop,acceptance_startups:$startups,tests_repeated:false,owner_accounts_used:false,native_apple_worker_executed:false,prepared_config_cache:true,fresh_online_resolution_claimed:false}' >"$public/host.json"
  exit "$status"
}
trap finish EXIT; trap 'exit 130' INT; trap 'exit 143' TERM; trap 'exit 129' HUP
unset GH_TOKEN GITHUB_TOKEN PYTHONPATH PYTHONHOME
stage=source
bounded 120 python3 -I -B "$here/driver.py" prepare --payload "$payload" --pins "$pins" --pins-sha "$pins_sha" --repository "$repository" >"$public/source-summary.json" 2>"$workspace/source-private.log"
context=$(bounded 30 docker context show)
[[ $(bounded 30 docker context inspect "$context" --format '{{.Endpoints.docker.Host}}') == unix:///* ]] || exit 2
DOCKER=(docker --context "$context")
daemon=$(call info --format '{{.OSType}}/{{.Architecture}}')
[[ $daemon == "linux/$machine" || ( $arch == arm64 && $daemon == linux/arm64 ) ]] || exit 2
image="$(jq -er .image_repository "$pins")@$(jq -er .image_digest "$pins")"; image_id=$(jq -er .image_id "$pins")
stage=image
bounded 600 "${DOCKER[@]}" pull --platform "linux/$arch" "$image" >"$workspace/image-private.log" 2>&1
call image inspect "$image" >"$workspace/image-private.json"
jq -e --arg id "$image_id" --arg arch "$arch" --arg image "$image" '.[0].Id==$id and .[0].Architecture==$arch and .[0].Os=="linux" and (.[0].RepoDigests|index($image)!=null) and .[0].Config.Entrypoint==["/init"] and ((.[0].Config.Cmd // [])|length)==0 and .[0].Config.WorkingDir=="/config"' "$workspace/image-private.json" >/dev/null
volume_attempted=true
call volume create --driver local --label "$label=$token" "$volume" >"$workspace/volume-private.log"; volume_created=true; owned_volume
stage=preparer
prep_attempted=true
prep_id=$(call create --name "$prep_name" --label "$label=$token" --platform "linux/$arch" --network bridge --mount "type=volume,source=$volume,target=/config" --cpus 2 --memory 4g --pids-limit 512 --security-opt no-new-privileges --entrypoint /bin/sh "$image_id" -c 'exec sleep 2600')
owned_container "$prep_name" "$prep_id"; boundary "$prep_id" bridge
call start "$prep_id" >"$workspace/start-private.log"
call exec "$prep_id" mkdir -m 700 /qa /qa/input
for name in common.py driver.py guest.py process_probe.py run_host.sh package_support.py; do call cp "$here/$name" "$prep_id:/qa/$name" >"$workspace/stage-private.log" 2>&1; done
[[ -z $(find "$payload" -mindepth 1 ! -type f -print -quit) ]] || exit 2
find "$payload" -type f -printf '%P\n' | LC_ALL=C sort >"$workspace/members"
printf '%s\n' homecircle.zip inventory.json source-config.json source-inventory.json source.tgz >"$workspace/expected"
cmp -s "$workspace/members" "$workspace/expected"
for name in homecircle.zip inventory.json source-config.json source-inventory.json source.tgz; do call cp "$payload/$name" "$prep_id:/qa/input/$name" >"$workspace/stage-private.log" 2>&1; done
call cp "$pins" "$prep_id:/qa/pins.json" >"$workspace/stage-private.log" 2>&1
bounded 720 "${DOCKER[@]}" exec "$prep_id" python -I -B /qa/driver.py setup --payload /qa/input --pins /qa/pins.json --pins-sha "$pins_sha" >"$workspace/setup-private.log" 2>&1
prepared=true
call network disconnect bridge "$prep_id"
call inspect "$prep_id" | jq -e '(.[0].NetworkSettings.Networks|length)==0' >/dev/null
offline=true
stage=consumer_create
consumer_attempted=true
consumer_id=$(call create --name "$consumer_name" --label "$label=$token" --platform "linux/$arch" --network none --mount "type=volume,source=$volume,target=/config" --cpus 2 --memory 4g --pids-limit 512 --security-opt no-new-privileges "$image_id")
owned_container "$consumer_name" "$consumer_id"; boundary "$consumer_id" none
call inspect "$consumer_id" >"$workspace/consumer-private.json"
jq -e -s '.[0][0] as $consumer | .[1][0] as $image | $consumer.Path=="/init" and ($consumer.Args|length)==0 and $consumer.Config.Entrypoint==["/init"] and (($consumer.Config.Cmd // [])|length)==0 and $consumer.Config.WorkingDir=="/config" and $consumer.Config.Env==$image.Config.Env and $consumer.Config.User==$image.Config.User and $consumer.HostConfig.Init!=true' "$workspace/consumer-private.json" "$workspace/image-private.json" >/dev/null
previous_start=
for phase in first restart; do
  stage="$phase-service"
  if [[ $phase == restart ]]; then bounded 30 "${DOCKER[@]}" exec "$prep_id" python -I -B /qa/driver.py restart --action restart --pins /qa/pins.json --pins-sha "$pins_sha" >"$workspace/control-private.log" 2>&1; fi
  owned_container "$consumer_name" "$consumer_id"; owned_container "$prep_name" "$prep_id"; owned_volume
  call start "$consumer_id" >"$workspace/start-private.log"
  startups=$((startups + 1))
  started=$(call inspect --format '{{.State.StartedAt}}' "$consumer_id")
  [[ -n $started && $started != "$previous_start" ]]; previous_start=$started
  bounded 190 "${DOCKER[@]}" exec "$prep_id" python -I -B /qa/driver.py wait --action "$phase" --pins /qa/pins.json --pins-sha "$pins_sha" >"$workspace/wait-private.log" 2>&1
  bounded 30 "${DOCKER[@]}" exec "$consumer_id" python -I -B /config/.homecircle-consumer-qa/process_probe.py --phase "$phase" --pins /config/.homecircle-consumer-qa/pins.json --pins-sha "$pins_sha" >"$workspace/process-private.log" 2>&1
  for name in "$phase-receipt.json" "$phase-process.json"; do call cp "$prep_id:/config/.homecircle-consumer-qa/$name" "$public/$name" >"$workspace/collect-private.log" 2>&1; done
  [[ $phase == first ]] && first=true || restarted=true
  stage="$phase-stop"
  bounded 270 "${DOCKER[@]}" stop --time 260 "$consumer_id" >"$workspace/stop-private.log" 2>&1
  call inspect "$consumer_id" | jq -e '.[0].State.Running==false and .[0].State.ExitCode==0 and .[0].State.OOMKilled==false and .[0].RestartCount==0' >/dev/null
  call inspect "$prep_id" | jq -e '.[0].State.Running==true and (.[0].NetworkSettings.Networks|length)==0' >/dev/null
  boundary "$consumer_id" none; boundary "$prep_id" bridge
done
final_stop=true
call cp "$prep_id:/config/.homecircle-consumer-qa/setup-summary.json" "$public/setup-summary.json" >"$workspace/collect-private.log" 2>&1
jq -e -s '.[0].outcome=="passed" and .[1].outcome=="passed" and .[0].identity==.[1].identity and .[1].unload_setup_checked==true and .[0].package_sha256=="c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861" and .[0].exact_loaded_and_installed_files==113 and .[1].exact_loaded_and_installed_files==113' "$public/first-receipt.json" "$public/restart-receipt.json" >/dev/null
complete=true; stage=complete

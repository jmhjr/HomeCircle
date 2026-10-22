"""Atomically publish only an owned fixture's complete private inputs file."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

RESULT={'schema':1,'outcome':'passed','private_complete_json_verified':True,
    'same_parent_atomic_replace':True,'parent_fsynced':True,'temporary_removed':True}


def require(ok):
    if not ok:
        raise ValueError('qa_atomic_inputs_refused')


def regular(fd):
    info=os.fstat(fd)
    require(stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid()
        and stat.S_IMODE(info.st_mode)==0o600 and info.st_nlink==1
        and 0<info.st_size<=2*1024**2)
    return info


def identity(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_nlink,
        info.st_size,info.st_mtime_ns)


def unique(pairs):
    result={}
    for key,value in pairs:
        require(key not in result)
        result[key]=value
    return result


def publish(root,temporary_name,expected_sha256):
    root=Path(root)
    info=root.lstat()
    require(stat.S_ISDIR(info.st_mode) and not root.is_symlink()
        and info.st_uid==os.geteuid() and stat.S_IMODE(info.st_mode)==0o700
        and root.resolve()==root)
    require(type(temporary_name) is str and re.fullmatch(r'[.]inputs-atomic-[0-9a-f]{32}',temporary_name)
        and type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_sha256))
    target=root/'inputs.json'
    temporary=root/temporary_name
    old=os.open(target,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    new=None
    try:
        old_info=regular(old)
        new=os.open(temporary,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK)
        new_info=regular(new)
        require(old_info.st_dev==new_info.st_dev and old_info.st_ino!=new_info.st_ino)
        raw=bytearray()
        while len(raw)<=new_info.st_size:
            block=os.read(new,min(65536,new_info.st_size-len(raw)+1))
            if not block:break
            raw.extend(block)
        require(len(raw)==new_info.st_size and hashlib.sha256(raw).hexdigest()==expected_sha256)
        value=json.loads(bytes(raw),object_pairs_hook=unique)
        require(type(value) is dict and type(value.get('schema')) is int and value['schema']==1)
        require(identity(new_info)==identity(os.fstat(new))==identity(temporary.lstat())
            and identity(old_info)==identity(os.fstat(old))==identity(target.lstat()))
        os.fsync(new)
        # Both names are inside one private, owned directory on one filesystem.
        # Existing readers retain the old inode; future readers see all new bytes.
        os.replace(temporary,target)
        directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(directory)
        finally:os.close(directory)
        require(identity(target.lstat())==identity(new_info)
            and not temporary.exists() and not temporary.is_symlink())
        return dict(RESULT)
    finally:
        if new is not None:os.close(new)
        os.close(old)


def main():
    try:
        require(sys.platform=='linux' and os.geteuid()==0 and len(sys.argv)==3)
        result=publish(Path('/data/homeassistant/homecircle-safe-restore-qa-control'),sys.argv[1],sys.argv[2])
    except Exception:
        print('{"schema":1,"outcome":"refused"}')
        return 1
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())

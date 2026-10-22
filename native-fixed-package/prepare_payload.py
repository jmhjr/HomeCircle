"""Freeze canonical public Git blobs and the original fixed candidate archive."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

SOURCE='3c33160c67e53956ab52298ffc10ccc9992132f0'
PACKAGE='f181e6300f15d8977817a552db90d35caf0edc869067ebeea815c7be1df0248e'
INVENTORY='8ea456beb9b2eaaf4ba50639532b8dafabe0e02d1e13a77a59525f1c249c7447'
CANONICAL='acfcda419a817032c38a463505f686b0f6ab49e69a8f1603d9b2ff43f24e442b'
PROJECTION=(
 'test_projected_item_observes_named_place_without_losing_saved_history',
 'test_projected_item_and_original_member_history_survive_next_restart',
 'test_changed_saved_selection_still_invalidates_prior_projected_history',
 'test_setup_projects_new_item_before_loading_and_observing_activity')


def sha(raw):return hashlib.sha256(raw).hexdigest()

def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--candidate-directory',type=Path,required=True)
    parser.add_argument('--prior-config',type=Path,required=True)
    a=parser.parse_args()
    here=Path(__file__).resolve().parent;payload=here/'payload'
    def git(*args):return subprocess.check_output(['git','-C',str(a.repository),*args])
    files={}
    for record in git('ls-tree','-rz','--full-tree',SOURCE).split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1);mode,kind,oid=metadata.split()
        assert mode in {b'100644',b'100755'} and kind==b'blob'
        files[name.decode()]=git('cat-file','blob',oid.decode())
    assert len(files)==381
    inventory={name:{'bytes':len(raw),'sha256':sha(raw)} for name,raw in sorted(files.items())}
    source_tar=io.BytesIO()
    with tarfile.open(fileobj=source_tar,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        for name,raw in sorted(files.items()):
            member=tarfile.TarInfo(name);member.size=len(raw);member.mode=0o644;member.mtime=0
            archive.addfile(member,io.BytesIO(raw))
    compressed=io.BytesIO()
    with gzip.GzipFile(fileobj=compressed,mode='wb',filename='',mtime=0) as archive:
        archive.write(source_tar.getvalue())
    (payload/'source.tgz').write_bytes(compressed.getvalue())
    write(payload/'source-inventory.json',inventory)
    package=(a.candidate_directory/'homecircle.zip').read_bytes()
    package_inventory=(a.candidate_directory/'inventory.json').read_bytes()
    assert sha(package)==PACKAGE and sha(package_inventory)==INVENTORY
    (payload/'homecircle.zip').write_bytes(package);(payload/'inventory.json').write_bytes(package_inventory)
    config=json.loads(a.prior_config.read_bytes())
    assert len(config['required_backend_tests'])==50
    config.update(candidate_source_commit=SOURCE,source_files=len(files),
        source_sha256=sha(compressed.getvalue()),source_inventory_sha256=sha((payload/'source-inventory.json').read_bytes()),
        driver_sha256=sha((here/'driver.py').read_bytes()),checker_sha256=sha(files['scripts/check_public_files.py']),
        minimum_backend_passed=1732,package_sha256=PACKAGE,package_inventory_sha256=INVENTORY,
        canonical_package_sha256=CANONICAL,requirements_helper_sha256=sha((here/'requirements_support.py').read_bytes()))
    config['required_backend_tests'] += [{'class':'tests.test_activity_projection','function':name} for name in PROJECTION]
    assert len(config['required_backend_tests'])==54
    write(payload/'config.json',config)
    (here/'CONFIG.sha256').write_text(sha((payload/'config.json').read_bytes())+'\n')
    print(json.dumps({'source_commit':SOURCE,'source_files':len(files),'package_sha256':PACKAGE,
        'package_inventory_sha256':INVENTORY,'canonical_package_sha256':CANONICAL,
        'config_sha256':sha((payload/'config.json').read_bytes()),'required_functions':54}))

if __name__=='__main__':main()

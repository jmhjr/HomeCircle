"""Finite source-bound diagnostics; never retain error text, paths or values."""
import ast
from pathlib import Path
import re

ERROR_TYPES=frozenset(('Refused','ValueError','TypeError','KeyError','AttributeError',
    'NameError','JSONDecodeError','RuntimeError','ImportError','ModuleNotFoundError','AssertionError',
    'OSError','TimeoutError','StartupBoundaryRefused','IdentityError','VaultError',
    'RecoveryGuardBlocked','RecoveryGuardReviewRequired','unrecognized'))


def catalog(root):
    root=Path(root)
    sources={'observer':root/'__init__.py','dependency_probe':root/'dependency_probe.py',
        'startup_boundary':root/'startup_boundary.py','boundary':root.parent/'_ordinary_boundary.py',
        'person_activity':root/'person_activity.py','person_activity_protocol':root/'person_activity_protocol.py'}
    codes,stages,frames,paths=set(),set(),{},{}
    for name,path in sources.items():
        tree=ast.parse(path.read_bytes())
        paths[str(path.resolve())]=name
        frames[name]={}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {
                    'check','require','Refused','StartupBoundaryRefused','ValueError'} and node.args:
                last=node.args[-1]
                if (isinstance(last,ast.Constant) and type(last.value) is str
                        and re.fullmatch('qa_[a-z0-9_]{1,100}',last.value)):
                    codes.add(last.value)
            if (isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant)
                    and type(node.value.value) is str and any(isinstance(t,ast.Name)
                    and t.id=='stage' for t in node.targets)):
                stages.add(node.value.value)
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                frames[name].setdefault(node.name,[]).append((node.lineno,node.end_lineno))
    return {'codes':codes,'stages':stages,'frames':frames,'paths':paths}


def checked(value,root):
    allowed=catalog(root)
    if (type(value) is not dict or set(value)!={'failure_type','failure_code','frames'}
            or type(value['failure_type']) is not str or value['failure_type'] not in ERROR_TYPES
            or not (value['failure_code'] is None or type(value['failure_code']) is str
                and value['failure_code'] in allowed['codes'])
            or type(value['frames']) is not list or len(value['frames'])>8):
        raise ValueError('qa_failure_projection_refused')
    for frame in value['frames']:
        if (type(frame) is not dict or set(frame)!={'source','function','line'}
                or type(frame['source']) is not str or frame['source'] not in allowed['frames']
                or type(frame['function']) is not str or type(frame['line']) is not int
                or not any(start<=frame['line']<=end for start,end in
                    allowed['frames'][frame['source']].get(frame['function'],()))):
            raise ValueError('qa_failure_projection_refused')
    return {'failure_type':value['failure_type'],'failure_code':value['failure_code'],
        'frames':[dict(frame) for frame in value['frames']]}


def checked_metadata(value,root):
    tree=ast.parse((Path(root)/'dependency_probe.py').read_bytes())
    nodes=[node.value for node in tree.body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='CLOSURE' for target in node.targets)]
    if (len(nodes)!=1 or not isinstance(nodes[0],ast.Call)
            or not isinstance(nodes[0].func,ast.Name) or nodes[0].func.id!='frozenset'
            or len(nodes[0].args)!=1 or nodes[0].keywords):
        raise ValueError('qa_failure_projection_refused')
    names=frozenset(ast.literal_eval(nodes[0].args[0]))
    if len(names)!=24 or type(value) is not dict or set(value)!=names:
        raise ValueError('qa_failure_projection_refused')
    for row in value.values():
        if (type(row) is not dict or set(row)!={'available','version','constraints_satisfied'}
                or type(row['available']) is not bool or type(row['constraints_satisfied']) is not bool
                or not (row['version'] is None or type(row['version']) is str and re.fullmatch(
                    r'[0-9]{1,8}(?:\.[0-9]{1,8}){1,3}',row['version']))
                or row['available'] is False and row['version'] is not None
                or row['version'] is None and row['constraints_satisfied'] is not False):
            raise ValueError('qa_failure_projection_refused')
    return {name:dict(value[name]) for name in sorted(names)}


def project(error,root,refused_type):
    allowed=catalog(root)
    name=type(error).__name__
    name=name if name in ERROR_TYPES else 'unrecognized'
    code=None
    if (type(error) in {refused_type,ValueError} and len(error.args)==1
            and type(error.args[0]) is str and error.args[0] in allowed['codes']):
        code=error.args[0]
    frames=[]
    current=error.__traceback__
    count=0
    while current is not None and count<64:
        source=allowed['paths'].get(current.tb_frame.f_code.co_filename)
        function=current.tb_frame.f_code.co_name
        line=current.tb_lineno
        if source is not None and any(start<=line<=end for start,end in
                allowed['frames'][source].get(function,())):
            frames.append({'source':source,'function':function,'line':line})
        count+=1
        current=current.tb_next
    return checked({'failure_type':name,'failure_code':code,'frames':frames[-8:]},root)

import os,json,socket,uuid
from pathlib import Path
from datetime import datetime,timezone
root=Path('/var/lib/spg/native-workspaces')
assert os.getuid()==10001 and os.getgid()==10001
assert root.is_dir() and not root.is_symlink() and os.access(str(root),os.W_OK|os.X_OK)
name=root/('__c2_preflight_'+uuid.uuid4().hex)
with name.open('x') as stream:stream.write('C2 nonbusiness worker write probe\n')
st=name.stat();name.unlink()
status=Path('/proc/1/status').read_text().splitlines()
uid=next(line for line in status if line.startswith('Uid:'));gid=next(line for line in status if line.startswith('Gid:'))
print(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'worker_container':socket.gethostname(),'probe_pid':os.getpid(),'main_process_uid':uid,'main_process_gid':gid,'mount_namespace':os.readlink('/proc/self/ns/mnt'),'workspace_path':str(root),'workspace_root_device':root.stat().st_dev,'workspace_root_inode':root.stat().st_ino,'probe_write_succeeded':True,'probe_removed':True,'probe_device':st.st_dev,'probe_uid':st.st_uid,'probe_gid':st.st_gid,'configured_workspace_root':os.environ['SPG_WORKSPACE_ROOT'],'configured_native_workspace_root':os.environ['SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT'],'source_revision':os.environ['SPG_RUNTIME_REVISION'],'tree':os.environ['C2_WATT_TREE'],'model_requests':0,'business_work_created':False,'scope':'actual Worker container root readiness; no Task manifest yet'}))
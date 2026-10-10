import datetime,hashlib,json,os,pathlib,shutil,subprocess
p=pathlib.Path(__file__).resolve().parent;root=p.parents[2];d=json.loads((p/'launch.json').read_text());env=dict(os.environ);env.update(d['explicit_environment']);now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
d.update(status='running',started_utc=now(),controller_pid=os.getpid());(p/'execution.json').write_text(json.dumps(d,indent=2)+'\n')
with (p/'stdout.log').open('wb') as out,(p/'stderr.log').open('wb') as err:
 child=subprocess.Popen(['/usr/bin/time','-v','-o',str(p/'resources.txt')]+d['command'],cwd=str(root),env=env,stdout=out,stderr=err)
 d['supervised_pid']=child.pid;(p/'execution.json').write_text(json.dumps(d,indent=2)+'\n');code=child.wait()
d.update(status='completed' if code==0 else 'failed',returncode=code,finished_utc=now());dest=root/d['output']
if dest.is_dir():
 for name in ('stdout.log','stderr.log','resources.txt'):shutil.copyfile(str(p/name),str(dest/('run_'+name)))
 d['output_sha256']={name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in ['summary.json','execution.json','run_stdout.log','run_stderr.log','run_resources.txt'] if (dest/name).exists()}
 (dest/'run_controller.json').write_text(json.dumps(d,indent=2)+'\n')
(p/'execution.json').write_text(json.dumps(d,indent=2)+'\n')

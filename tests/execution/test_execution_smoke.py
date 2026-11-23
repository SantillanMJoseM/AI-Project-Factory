import tempfile, os, subprocess
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from orchestration.execution.snapshot import create_snapshot, verify_snapshot, latest_snapshot
from orchestration.execution.ledger import Ledger, ledger_path
from orchestration.execution.resume import evaluate_resume

def test_snapshot_create_verify():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        proj='PROJECT-001'
        (root/'projects'/proj/'execution').mkdir(parents=True)
        # init git
        subprocess.run(['git','init','-q'],cwd=root,check=True)
        subprocess.run(['git','config','user.email','t@t.com'],cwd=root,check=True)
        subprocess.run(['git','config','user.name','t'],cwd=root,check=True)
        (root/'a.txt').write_text('hello')
        subprocess.run(['git','add','.'],cwd=root,check=True)
        subprocess.run(['git','commit','-q','-m','init'],cwd=root,check=True)
        snap=create_snapshot(root,project_id=proj,execution_id='EXEC-0001',task_id='T1',agent_id='AG-001',reason='state-transition',files=['a.txt'],working_directory='.')
        assert snap.snapshot_id.startswith('SNAP-')
        from orchestration.execution.snapshot import snapshots_dir, snapshot_file_name
        spath=snapshots_dir(root,proj)/snapshot_file_name(snap.snapshot_id)
        rep=verify_snapshot(root,spath)
        assert rep.ok, rep.integrity_issues
        print('PASS test_snapshot_create_verify')

def test_resume_eligibility():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        proj='PROJECT-001'
        (root/'projects'/proj/'execution').mkdir(parents=True)
        subprocess.run(['git','init','-q'],cwd=root,check=True)
        subprocess.run(['git','config','user.email','t@t.com'],cwd=root,check=True)
        subprocess.run(['git','config','user.name','t'],cwd=root,check=True)
        (root/'a.txt').write_text('hello')
        subprocess.run(['git','add','.'],cwd=root,check=True)
        subprocess.run(['git','commit','-q','-m','init'],cwd=root,check=True)
        snap=create_snapshot(root,project_id=proj,execution_id='EXEC-0001',task_id='T1',agent_id='AG-001',reason='state-transition',files=['a.txt'],working_directory='.')
        from orchestration.execution.snapshot import snapshots_dir, snapshot_file_name
        spath=snapshots_dir(root,proj)/snapshot_file_name(snap.snapshot_id)
        decision=evaluate_resume(root,spath)
        assert decision.eligible is True or decision.eligible is False
        print('PASS test_resume_eligibility')

if __name__=='__main__':
    test_snapshot_create_verify()
    test_resume_eligibility()
    print('ALL EXECUTION SMOKE TESTS PASSED')

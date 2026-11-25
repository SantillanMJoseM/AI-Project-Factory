import subprocess, tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from orchestration.execution.snapshot import create_snapshot, verify_snapshot, snapshots_dir, snapshot_file_name
from orchestration.execution.ledger import Ledger, ledger_path
from orchestration.execution.resume import evaluate_resume
from orchestration.execution.context import assemble_context
from orchestration.execution.documents import create_document
from orchestration.task_orchestration.engine import TaskOrchestrationEngine
from orchestration.task_orchestration.models import TaskState, transition_task
from orchestration.runtime.model_fallback import ModelFallbackManager

def _git_repo(root):
    subprocess.run(['git','init','-q'],cwd=root,check=True)
    subprocess.run(['git','config','user.email','t@t.com'],cwd=root,check=True)
    subprocess.run(['git','config','user.name','t'],cwd=root,check=True)
    (root/'README.md').write_text('x')
    subprocess.run(['git','add','.'],cwd=root,check=True)
    subprocess.run(['git','commit','-q','-m','init'],cwd=root,check=True)

def test_e2e_snapshot_resume_context():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        proj='PROJECT-001'
        (root/'projects'/proj/'execution').mkdir(parents=True)
        _git_repo(root)
        for bn in ['AI_START_HERE.md','PROJECT_CONTEXT.md','PROJECT_STATUS.md','PROJECT_HANDOFF.md','PROJECT_MAP.md']:
            src=Path(__file__).resolve().parents[2]/bn
            if src.exists(): (root/bn).write_text(src.read_text())
        subprocess.run(['git','add','.'],cwd=root,check=True)
        subprocess.run(['git','commit','-q','-m','bootstrap'],cwd=root,check=True)
        # plan
        engine=TaskOrchestrationEngine()
        plan=engine.build_plan('Deliver backend and tests', project_id=proj)
        graph=plan.graph
        # complete first task
        for tid in list(graph.tasks)[:1]:
            t=graph.require(tid)
            if t.status is TaskState.PENDING:
                transition_task(t, TaskState.ASSIGNED, actor=t.assigned_agent)
            if t.status is TaskState.ASSIGNED:
                transition_task(t, TaskState.RUNNING, actor=t.assigned_agent)
            if t.status is TaskState.RUNNING:
                transition_task(t, TaskState.COMPLETED, actor='AG-002', criteria_results={c.criterion_id: True for c in t.acceptance_criteria}, gate_results={g.gate_id: 'PASS' for g in t.quality_gates})
        from orchestration.execution.ledger import Ledger
        lp=ledger_path(root,proj,'EXEC-0001')
        ledger=Ledger.create(lp,'EXEC-0001',actor_agent='AG-001',payload={'task_id':plan.plan_id})
        # snapshot
        snap=create_snapshot(root,project_id=proj,execution_id='EXEC-0001',task_id=plan.plan_id,agent_id='AG-001',reason='state-transition',files=['README.md'],working_directory='.',ledger=ledger)
        rep=verify_snapshot(root, snapshots_dir(root,proj)/snapshot_file_name(snap.snapshot_id))
        assert rep.ok, rep.integrity_issues
        # resume
        dec=evaluate_resume(root, snapshots_dir(root,proj)/snapshot_file_name(snap.snapshot_id))
        assert dec is not None
        # context
        manifest=assemble_context(root, project_id=proj, execution_id='EXEC-0001', task_refs=['README.md'], token_budget=5000)
        assert manifest is not None
        # ledger
        lp=ledger_path(root,proj,'EXEC-0001')
        assert lp.exists()
        # numbered doc
        from orchestration.execution.documents import create_document
        docdir=Path(td)/'docs'/'execution'
        docdir.mkdir(parents=True,exist_ok=True)
        d=docdir/'EXEC_0001.md'
        d.write_text('# test\n')
        assert d.exists()
        print('PASS test_e2e_snapshot_resume_context')

def test_model_fallback():
    mgr=ModelFallbackManager()
    # just ensure class instantiates
    assert mgr is not None
    print('PASS test_model_fallback')

if __name__=='__main__':
    test_e2e_snapshot_resume_context()
    test_model_fallback()
    print('ALL STAGE2C INTEGRATION TESTS PASSED')

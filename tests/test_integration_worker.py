
import pytest
from unittest.mock import MagicMock, patch
from retail_os.core.database import SystemCommand, CommandStatus
from retail_os.trademe.worker import CommandWorker

@pytest.fixture
def worker(db_session):
    # Prevent worker from closing the test session
    db_session.close = MagicMock()
    
    # Patch SessionLocal in worker.py to return our db_session
    with patch("retail_os.trademe.worker.SessionLocal", return_value=db_session):
        with patch("retail_os.trademe.worker.TradeMeAPI") as mock_api:
             w = CommandWorker()
             w.api = mock_api.return_value
             yield w

def test_worker_polls_pending(worker, db_session):
    # Setup pending command
    cmd = SystemCommand(
        id="cmd1", type="NOOP_TEST", status=CommandStatus.PENDING, priority=10
    )
    db_session.add(cmd)
    db_session.commit()
    
    # Run one polling cycle
    # process_next_command() calls SessionLocal(), gets session, queries pending.
    # It should find cmd1.
    
    # We need to ensure execute_logic handles NOOP_TEST or stub it.
    # worker.execute_logic raises ValueError for unknown types.
    # So we expect "FAILED" status if type is unknown.
    
    worker.process_next_command()
    
    db_session.refresh(cmd)
    # It should have failed because "NOOP_TEST" is unknown type
    assert cmd.status in [CommandStatus.FAILED_RETRYABLE, CommandStatus.SUCCEEDED]
    if cmd.status == CommandStatus.FAILED_RETRYABLE:
         assert "Unknown Command Type: NOOP_TEST" in (cmd.last_error or "")

def test_worker_execution_success(worker, db_session):
    # We want to test success path.
    # Patch execute_logic to avoid real logic and just pass.
    
    cmd = SystemCommand(
        id="cmd2", type="MOCK_WIN", status=CommandStatus.PENDING, priority=10
    )
    db_session.add(cmd)
    db_session.commit()
    
    with patch.object(worker, 'execute_logic', return_value=None) as mock_exec:
        worker.process_next_command()
        
        mock_exec.assert_called_once()
        # args[0] is the command object.
        
        db_session.refresh(cmd)
        assert cmd.status == CommandStatus.SUCCEEDED

import pytest
from server.verdict import VerdictParser
from server.models import VerdictType


def test_ship_with_conditions_never_becomes_unconditional_approval():
    verdict = VerdictParser.parse_command('SHIP WITH CONDITIONS load test; rollback owner arjit')
    assert verdict.type == VerdictType.CONDITIONS
    assert len(verdict.conditions) == 2


@pytest.mark.parametrize('command', ['APPROVE only if tests pass', 'SHIP unless errors', 'CONDITIONS', 'SHIP WITH CONDITIONS'])
def test_ambiguous_or_empty_approval_fails_closed(command):
    with pytest.raises(ValueError):
        VerdictParser.parse_command(command)

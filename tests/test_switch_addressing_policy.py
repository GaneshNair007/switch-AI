"""Verify selectors against Switch's actual policy evaluator when installed."""
import pytest
from server.setup_switch import addressing_policy


def test_platform_identity_selector_against_official_switch():
    addressing = pytest.importorskip('switch_core.addressing')
    policy = addressing.parse_policy(addressing_policy('room', 'external-account'))
    args = dict(room_id='room',group_id=None,sender_kind='user',sender_id='external-account',
                sender_user_ids=['gateway-admin'],sender_owner_user_id=None,owner_user_id='legacy-owner')
    assert addressing.can_address(policy,**args)
    assert not addressing.can_address(policy,**{**args,'sender_id':'different-account'})
    assert not addressing.can_address(policy,**{**args,'room_id':'different-room'})
    assert addressing.can_address(policy,**{**args,'sender_kind':'agent','sender_id':'peer-agent',
        'sender_user_ids':[],'sender_owner_user_id':'legacy-owner'})

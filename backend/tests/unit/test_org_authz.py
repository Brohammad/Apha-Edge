"""Organization role rank helpers."""

from alphaedge.modules.organization.application.authz import role_at_least
from alphaedge.modules.organization.domain.enums import OrgRole


def test_role_rank_ordering() -> None:
    assert role_at_least(OrgRole.OWNER, OrgRole.ADMIN)
    assert role_at_least(OrgRole.ADMIN, OrgRole.MEMBER)
    assert not role_at_least(OrgRole.MEMBER, OrgRole.ADMIN)
    assert role_at_least(OrgRole.MEMBER, OrgRole.MEMBER)

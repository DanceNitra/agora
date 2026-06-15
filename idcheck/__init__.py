"""idcheck — is a causal/attribution number identified, or did the controls inject bias? Audits a
control set against its causal-graph roles (back-door logic) + proves collider bias. Zero-dep core."""
from .idcheck import audit, identification_score, collider_bias, good_and_bad_controls

__all__ = ["audit", "identification_score", "collider_bias", "good_and_bad_controls"]

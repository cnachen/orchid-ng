from orchid_ng.domain import CritiqueActionType
from orchid_ng.services.search import parse_critique_actions


def test_parse_critique_actions_maps_keywords() -> None:
    actions = parse_critique_actions(
        "Need stronger evidence, a narrower scope, and explicit assumptions.",
        target_idea_id="idea_1",
    )
    action_types = {action.action_type for action in actions}
    assert CritiqueActionType.ADD_EVIDENCE in action_types
    assert CritiqueActionType.NARROW_CLAIM in action_types
    assert CritiqueActionType.CLARIFY_ASSUMPTION in action_types


def test_parse_critique_actions_has_fallback() -> None:
    actions = parse_critique_actions("This needs work.", target_idea_id="idea_1")
    assert actions[0].action_type == CritiqueActionType.CLARIFY_ASSUMPTION

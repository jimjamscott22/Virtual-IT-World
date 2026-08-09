from datetime import UTC, datetime, timedelta
from random import Random

from vitsc.env.base import Action
from vitsc.env.simulated import SimulatedEnvironment
from vitsc.faults.registry import get_fault
from vitsc.persona.models import ChatTurn
from vitsc.persona.personas import card_for
from vitsc.session.afteraction import build_after_action
from vitsc.session.grading import grade_ticket
from vitsc.session.ticket import SLA_MINUTES, Disposition, Priority, Ticket
from vitsc.tools.ad import ADConsole
from vitsc.tools.base import ToolLog
from vitsc.world.invariants import capture_baseline
from vitsc.world.seed import load_world

NOW = datetime(2026, 8, 7, 9, 0)
WALL = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)


def setup(fault_id="ad.account_locked"):
    world = load_world()
    fault = get_fault(fault_id)
    placement = fault.placements(world)[0]
    fault.apply(world, placement, Random(0))
    env = SimulatedEnvironment(world)
    baseline = capture_baseline(world)
    sam = placement.key if placement.kind == "user" else world.machines[placement.key].assigned_to
    user = world.org.users[sam]
    ticket = Ticket(
        id=1,
        fault_id=fault.id,
        placement=placement,
        persona=card_for(user),
        symptoms=fault.symptoms(world, placement),
        report_text="can't log in",
        system_priority=Priority.P1,
        opened_at=NOW,
        sla_minutes=SLA_MINUTES[Priority.P1],
    )
    return world, fault, placement, env, baseline, ticket


def test_correct_fix_within_sla_grades_clean():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "get-user", {"sam": placement.key})
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=9))

    grade = grade_ticket(ticket, fault, env, baseline)
    assert grade.correct is True
    assert grade.within_sla is True
    assert grade.collateral == []


def test_unfixed_ticket_is_incorrect():
    world, fault, placement, env, baseline, ticket = setup()
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=3))
    assert grade_ticket(ticket, fault, env, baseline).correct is False


def test_collateral_damage_is_reported():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    env.execute(Action(kind="ad.disable", target="d.okafor"))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))

    grade = grade_ticket(ticket, fault, env, baseline)
    assert grade.correct is False
    assert any("d.okafor" in c for c in grade.collateral)


def test_a_second_fix_path_grades_just_as_clean():
    """Nothing checks *how* the fault cleared — resetting the password counts."""
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.reset_password", target=placement.key))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    assert grade_ticket(ticket, fault, env, baseline).correct is True


def test_escalating_a_fixable_ticket_is_wrong():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=5))
    assert grade_ticket(ticket, fault, env, baseline).disposition_correct is False


def test_escalating_an_escalate_only_ticket_is_right():
    world, fault, placement, env, baseline, ticket = setup("endpoint.failing_disk")
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    assert grade.disposition_correct is True
    assert grade.correct is True
    assert grade.fault_cleared is False


def test_fixing_an_escalate_only_ticket_is_wrong():
    world, fault, placement, env, baseline, ticket = setup("endpoint.failing_disk")
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    assert grade_ticket(ticket, fault, env, baseline).correct is False


def test_escalating_correctly_but_breaking_something_is_still_wrong():
    world, fault, placement, env, baseline, ticket = setup("endpoint.failing_disk")
    env.execute(Action(kind="ad.disable", target="d.okafor"))
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    assert grade.disposition_correct is True
    assert grade.correct is False


def test_breaching_sla_is_recorded():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=180))
    assert grade_ticket(ticket, fault, env, baseline).within_sla is False


def test_touching_before_asking_is_detected():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.chat = []
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=2))
    assert grade_ticket(ticket, fault, env, baseline).questions_before_first_mutation == 0


def test_questions_asked_before_the_mutation_are_counted():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.chat = [
        ChatTurn(speaker="tech", text="when did it start?", at=WALL),
        ChatTurn(speaker="user", text="friday", at=WALL),
        ChatTurn(speaker="tech", text="anyone else?", at=WALL),
    ]
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=4))
    assert grade_ticket(ticket, fault, env, baseline).questions_before_first_mutation == 2


def test_questions_asked_after_the_mutation_do_not_count():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.chat = [
        ChatTurn(speaker="tech", text="all sorted now?", at=datetime.now(UTC) + timedelta(hours=1))
    ]
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=4))
    assert grade_ticket(ticket, fault, env, baseline).questions_before_first_mutation == 0


def test_a_read_only_session_counts_every_question():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "get-user", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.chat = [ChatTurn(speaker="tech", text="what happens?")]
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=4))
    assert grade_ticket(ticket, fault, env, baseline).questions_before_first_mutation == 1


def test_triage_accuracy_compares_user_priority():
    world, fault, placement, env, baseline, ticket = setup()
    ticket.user_priority = Priority.P3
    env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    assert grade_ticket(ticket, fault, env, baseline).triage_correct is False


def test_no_triage_opinion_is_not_penalised():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    assert grade_ticket(ticket, fault, env, baseline).triage_correct is True


def test_after_action_names_the_root_cause_and_shortest_path():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "get-user", {"sam": "d.okafor"})  # wasted
    ADConsole().invoke(env, log, "get-user", {"sam": placement.key})
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=6))

    grade = grade_ticket(ticket, fault, env, baseline)
    report = build_after_action(ticket, fault, grade, env.world)
    assert report.root_cause == fault.canonical_title
    assert report.shortest_path
    assert report.tool_calls_made == 3
    assert any("d.okafor" in w for w in report.wasted_calls)
    assert not any(placement.key in w for w in report.wasted_calls)
    assert report.verdict == "Resolved correctly."


def test_after_action_explains_a_wrong_escalation():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    report = build_after_action(ticket, fault, grade, env.world)
    assert "escalated something you had the tools" in report.verdict


def test_after_action_explains_a_missed_escalation():
    world, fault, placement, env, baseline, ticket = setup("endpoint.failing_disk")
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    report = build_after_action(ticket, fault, grade, env.world)
    assert "needed escalation" in report.verdict


def test_after_action_explains_collateral_damage():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.unlock", target=placement.key))
    env.execute(Action(kind="ad.disable", target="d.okafor"))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    report = build_after_action(ticket, fault, grade, env.world)
    assert "broke something else" in report.verdict


def test_after_action_explains_an_unfixed_close():
    world, fault, placement, env, baseline, ticket = setup()
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    report = build_after_action(ticket, fault, grade, env.world)
    assert "still present" in report.verdict


def test_breaking_something_while_leaving_the_fault_says_both():
    world, fault, placement, env, baseline, ticket = setup()
    env.execute(Action(kind="ad.disable", target="d.okafor"))
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    report = build_after_action(ticket, fault, grade, env.world)
    assert "still there" in report.verdict


def test_a_read_only_session_is_not_accused_of_touching_first():
    """Escalating after only looking must not read as 'touched before asking'."""
    world, fault, placement, env, baseline, ticket = setup("endpoint.failing_disk")
    log = ToolLog()
    ADConsole().invoke(env, log, "get-user", {"sam": "m.alvarez"})
    ticket.tool_calls = log.calls
    ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=5))
    grade = grade_ticket(ticket, fault, env, baseline)
    report = build_after_action(ticket, fault, grade, env.world)
    assert grade.questions_before_first_mutation == 0
    assert report.touched_before_asking is False


def test_mutating_with_no_questions_is_accused():
    world, fault, placement, env, baseline, ticket = setup()
    log = ToolLog()
    ADConsole().invoke(env, log, "unlock", {"sam": placement.key})
    ticket.tool_calls = log.calls
    ticket.close(Disposition.RESOLVED, at=NOW + timedelta(minutes=2))
    grade = grade_ticket(ticket, fault, env, baseline)
    assert build_after_action(ticket, fault, grade, env.world).touched_before_asking is True


def test_every_fault_produces_a_report_with_a_bound_shortest_path():
    """`{placement}`-style sentinels must all be resolved by the time a
    technician reads the report."""
    from vitsc.faults.registry import all_faults

    for candidate in all_faults():
        world = load_world()
        placement = candidate.placements(world)[0]
        candidate.apply(world, placement, Random(0))
        env = SimulatedEnvironment(world)
        baseline = capture_baseline(world)
        sam = (
            placement.key
            if placement.kind == "user"
            else world.machines[placement.key.split("/")[0]].assigned_to
        )
        ticket = Ticket(
            id=1,
            fault_id=candidate.id,
            placement=placement,
            persona=card_for(world.org.users[sam]),
            symptoms=candidate.symptoms(world, placement),
            report_text="something is wrong",
            system_priority=Priority.P2,
            opened_at=NOW,
            sla_minutes=SLA_MINUTES[Priority.P2],
        )
        ticket.close(Disposition.ESCALATED, at=NOW + timedelta(minutes=5))
        grade = grade_ticket(ticket, candidate, env, baseline)
        report = build_after_action(ticket, candidate, grade, world)
        assert report.shortest_path, candidate.id
        assert not any("{" in step for step in report.shortest_path), candidate.id
        assert report.verdict

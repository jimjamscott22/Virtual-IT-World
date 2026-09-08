from vitsc.world.seed import load_world


def test_seed_loads_expected_org():
    world = load_world()
    assert "m.alvarez" in world.org.users
    assert world.org.users["m.alvarez"].enabled is True
    assert world.org.users["m.alvarez"].locked_out is False


def test_seed_machines_reference_real_users():
    world = load_world()
    for machine in world.machines.values():
        if machine.assigned_to is not None:
            assert machine.assigned_to in world.org.users


def test_seed_group_members_exist():
    world = load_world()
    for group in world.org.groups.values():
        for sam in group.members:
            assert sam in world.org.users


def test_seed_is_healthy_at_rest():
    world = load_world()
    assert all(u.locked_out is False for u in world.org.users.values())
    assert all(m.disk_free_gb > 5 for m in world.machines.values())


def test_workstations_map_their_department_share():
    world = load_world()
    machine = world.machines["MER-WS-001"]
    assert machine.mapped_drives["S:"] == r"\\MER-FS-01\Accounting"
    assert machine.printer_drivers["PRT-ACC-01"] == "HP LaserJet M507 PCL-6"


def test_every_user_has_a_mailbox():
    world = load_world()
    for sam in world.org.users:
        mailbox = world.mailbox_for(sam)
        assert mailbox is not None
        assert mailbox.primary_smtp.endswith("@meridian.local")


def test_mail_is_healthy_at_rest():
    world = load_world()
    assert world.mail.transport_state.value == "Running"
    assert world.mail.queue_depth < 10
    for mailbox in world.mail.mailboxes.values():
        assert mailbox.used_mb < mailbox.quota_mb
        assert mailbox.forwarding_smtp is None
        assert mailbox.rules == []


def test_the_mail_server_is_a_machine_like_any_other():
    world = load_world()
    assert "MER-MB-01" in world.machines
    assert world.machines["MER-MB-01"].assigned_to is None


def test_the_estate_is_the_size_phase_2b_settled_on():
    """Enumerated on purpose, like the catalog roster.

    Placement counts fall out of these numbers, and every fixed-seed test in
    the suite deals from the pool they define — so growing the estate is a
    decision that should have to be made deliberately, not one that drifts.
    """
    world = load_world()
    assert len(world.org.users) == 20
    assert len([m for m in world.machines.values() if m.assigned_to]) == 10
    assert len([m for m in world.machines.values() if m.assigned_to is None]) == 4


def test_half_the_org_shares_a_terminal():
    """Twenty people, ten machines. A user-placed fault and a machine-placed
    fault must not be the same population, or `placements()` is decorative."""
    world = load_world()
    with_machine = {m.assigned_to for m in world.machines.values() if m.assigned_to}
    assert len(with_machine) == 10
    assert set(world.org.users) - with_machine


def test_every_department_group_has_a_share_behind_it():
    """HR had a group and no share until the estate grew — an HR workstation
    would have mapped nothing at all."""
    world = load_world()
    backed = {s.required_group for s in world.shares.values()}
    assert set(world.org.groups) == backed


def test_every_user_belongs_to_exactly_one_department_group():
    world = load_world()
    for sam in world.org.users:
        assert len(world.groups_of(sam)) == 1, f"{sam} is in the wrong number of groups"


def test_every_workstation_maps_a_share_and_a_printer_driver():
    """The new machines have to be as complete as the original six."""
    world = load_world()
    for machine in world.machines.values():
        if machine.assigned_to is None:
            continue
        assert "S:" in machine.mapped_drives, f"{machine.hostname} maps no share"
        assert machine.installed_printers, f"{machine.hostname} has no printer"
        for printer in machine.installed_printers:
            assert machine.printer_drivers[printer] == world.printers[printer].correct_driver

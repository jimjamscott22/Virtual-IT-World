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

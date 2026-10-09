"""The satiety kernel's Task 15 pieces are retired (Plan 11c Task 9); the appetite traits stay, vanilla's game numbers
(#0485), applied to the pool's decay (spec sec. 3.4). Satiety from physiology is test_kernel_satiety_physiology.py."""


def test_traits_scale_the_decay(host):
    assert host.call("satiety.trait", True, False) == 1.5 and host.call("satiety.trait", False, True) == 0.75
    assert host.call("satiety.trait", False, False) == 1


def test_the_trait_constants_are_vanillas(host):
    S = host.K.satiety
    assert (S.HEARTY, S.LIGHT) == (1.5, 0.75)


def test_task_15s_pieces_are_retired(host):
    S = host.K.satiety
    for name in ("R0", "LO", "HI", "BETA", "defaults", "rate", "step", "relief", "bulkFactor", "add", "seed"):
        assert S[name] is None, name

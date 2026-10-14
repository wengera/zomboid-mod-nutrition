"""The study participant's body: a test instrument, not mod code (Plan 13 Task 12).

Since Plan 13 Task 12 the mod never builds a body from a weight: first sight is the creation body of the band traits
the character holds (K.body.create, ruling 13-6). The energy and satiety oracles replay study participants given by
their weight (a 70 kg man, Karl's and King's subjects), so the replay lays a w kg participant's masses over the
no-trait creation body with the Plan 3 band-anchored split the mod used until then (the fat fraction piecewise-linear
over weight anchors by sex, S1051 design-phase-v1, clamped; the weight clamped to 35..200 kg), bit-identical to the
removed K.body.split, so every oracle reads the body it was written against. The set point, the peak and the cap move
to the participant's lean, so an untrained participant neither grows nor detrains, and the seven-day mass ring holds
his weight.

PARTICIPANT is Lua source that defines the global NR_participant(w, sex, ageH, specific); load it into a runtime that
holds the kernel (`rt.execute(PARTICIPANT)`).
"""

PARTICIPANT = r"""
NR_PARTICIPANT = {
    ANCHORS = { 50, 60, 70, 80, 95, 105 },
    BF = { { 0.06, 0.09, 0.13, 0.18, 0.27, 0.33 }, { 0.15, 0.19, 0.23, 0.28, 0.35, 0.40 } },
    BF_MIN = { 0.04, 0.12 },
    BF_MAX = 0.55,
}
function NR_participant(w, sex, ageH, specific)
    local K = NutritionRevamp.kernel
    local P = NR_PARTICIPANT
    local s = K.body.effSex(sex, specific)
    local wc = K.clamp(w, 35, 200)
    local knots = {}
    for i = 1, #P.ANCHORS do knots[i] = { P.ANCHORS[i], P.BF[s][i] } end
    local bf = K.clamp(K.interp(knots, wc), P.BF_MIN[s], P.BF_MAX)
    local body = K.body.new(K.body.create(nil, nil, K.strength.DEFAULTS, s), sex, ageH)
    body.fm = wc * bf
    body.lm = wc - body.fm
    body.F0 = body.lm
    body.Pk = body.lm
    body.Fc = K.max(body.Fc, body.lm)
    body.fmRef = body.fm
    body.lm0dis = body.lm
    for i = 1, K.body.WEEK_N do body.mass7[i] = wc end
    return body
end
"""

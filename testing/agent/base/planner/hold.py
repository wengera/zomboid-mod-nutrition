"""The hold and spent reads of the threat branch: the mixin `Hold` that `threat.Threat` derives from (rulings
P24-AG, P24-AK, P24-AP, P24-AT and R2: the arms', the endurance and the tired holds, the wounded fight, the lone
target). Moved out of `threat.py` at Plan 25 Task 2 (a pure move: every rule, switch and constant unchanged; the constants
in `policies.py`'s table); its state is `Survive`'s own, set in `Survive.__init__`, and `survive.py`'s module docstring
stays the record of every rule here.
"""
from agent.base.planner.policies import (DANGER_R, ENDURANCE_RELEASE, ENDURANCE_T, KEEP_R, LISTED_R, STIFF_HARD,
                                         STIFF_SOFT, STRAIN_HARD, TIRED_FIGHT_T, arm_pain, arm_stiffness, chasing,
                                         on_floor, zdist)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Hold:
    """The hold and spent reads (the module docstring): `Threat`'s mixin."""

    def _read_spent(self):
        """Rulings P24-AG and P24-AK (#4370, #4371), with P24-AT's hold on the stiffness, read once a tick (`_threat`;
        `self.spent` is what the tick's `_sought`, `_hysteresis`, `_walk_yields` and the why read, review-t27 minor 3):
        why the character is spent for a fight this tick, else None (always with `STRAIN` off):
        - `arms` while the strain hold runs: ruling P24-AT (E10: the hold, set at game minute 605 by a bite's pain,
          fled on 308 of 580 threat lines and never released, the pain never under 21 again while the stiffness read 0
          on both arms) reads the arms' stiffness (`policies.arm_stiffness`, the frame's `body.strain`, #4369): it
          starts at STIFF_HARD on either arm (the health panel's line past minor stiffness) and ends once both read
          under STIFF_SOFT (the panel's first naming of it), or with no `strain` on the frame (an older Lua); a rest
          lowers it by about 5.76 a real minute on the server (#4369). Before it the pain set it (STRAIN_HARD, released
          under STRAIN_SOFT), which a wound holds up whatever the rest: the pain is now its own reason, `wounded`
          (`self.wound`, below);
        - `endurance` while the endurance hold runs: it starts at the frame's `stats.endurance` ENDURANCE_T or under
          (the ENDURANCE moodle's first level, which halves every swing) and ends only above ENDURANCE_RELEASE (a
          fight drains far faster than rest restores, so with no release line the edge flickered: flee, one swing,
          flee; review-t27 blocker 1, F1 gm 635-637);
        - `tired` at `stats.fatigue` TIRED_FIGHT_T or above (the TIRED moodle's, which halves it again).
        Spent, the threat branch disengages (the flee `strain`, its legs as today), engages and seeks nothing, and a
        `walk` corner yields; the `stuck`, `inside`, trapped and door fights, which no leg can leave, stay and fight
        (`policy.spent` is set on every Fight, so on a shove build under HOLD_WIDE none of them swings under any hold:
        they shove at point blank and stomp, `policies.Fight._shove`). Ruling P24-AP (`_wounded_fight`), as
        ruling R2 widens it (Task 32 fix 1): under any hold a zombie within KEEP_R is fought, never fled, and the Fight
        sends no swing (`_fight_spent`). The why's `strain` carries the pain and the frame's `body.strain` (each
        arm's stiffness, #4369) when it reads one.
        Ruling P24-AT's `wounded` (`self.wound`, logged `pain` {kind "wounded", armPain, strain} on the tick's threat
        why): the frame's `body.armPain` at STRAIN_HARD (#4370: every swing's damage halved or worse, whatever the
        pain's source) with `STRAIN` on. It is no hold: the Fight sends no swing (`policies.Fight.no_swing` reads the
        pain itself, `arms_hurt`: the shove at point blank, the stomp of a fallen one, the backpedal between), no
        `strain` flee is read for it, and a lone target is still sought (`_lone`); a group is fled as today."""
        pain = arm_pain(self.world)
        stiff = arm_stiffness(self.world)
        if stiff is None or stiff < STIFF_SOFT:
            self.strain_hold = False
        elif stiff >= STIFF_HARD:
            self.strain_hold = True
        st = self.world.stats or {}
        e, f = st.get("endurance"), st.get("fatigue")
        if not _num(e) or e > ENDURANCE_RELEASE:
            self.endurance_hold = False
        elif e <= ENDURANCE_T:
            self.endurance_hold = True
        kinds = () if not self.STRAIN else tuple(k for k, on in (
            ("arms", self.strain_hold), ("endurance", self.endurance_hold), ("tired", _num(f) and f >= TIRED_FIGHT_T))
            if on)
        self.spent_kinds = kinds
        self.spent = None if not kinds else {"kind": kinds[0], "armPain": pain, "endurance": e, "fatigue": f}
        strain = (self.world.body or {}).get("strain")
        if self.spent is not None and strain is not None:   # P24-AP: the stiffness (#4369) beside the pain, logged
            self.spent["strain"] = strain                    # (a PZA/1.7 frame carries it)
        hurt = self.STRAIN and pain is not None and pain >= STRAIN_HARD
        self.wound = {"kind": "wounded", "armPain": pain, "strain": strain} if hurt else None   # P24-AT

    def spent_view(self):
        """The goal view's `spent` (Plan 25 Task 3, P25-C; spec § 2.2(f): the model reads the hold to choose `Rest`):
        `{"kind", "value"}` of this tick's first hold (`spent`), `value` its own reading: the endurance (`endurance`),
        the larger arm's stiffness (`arms`, `policies.arm_stiffness`, else the arms' pain) or the fatigue (`tired`);
        None with no hold set (the view then carries no `spent`)."""
        s = self.spent
        if s is None:
            return None
        kind = s["kind"]
        if kind == "endurance":
            value = s.get("endurance")
        elif kind == "tired":
            value = s.get("fatigue")
        else:
            stiff = arm_stiffness(self.world)
            value = s.get("armPain") if stiff is None else stiff
        return {"kind": kind, "value": value}

    def _wounded_fight(self):
        """Ruling P24-AP, the wounded fight (E9: a bite on part 5 read `body.armPain` 37.6 with `body.strain` 0 on both
        arms and held the strain hold to the death), as ruling R2 widens it (Task 32 fix 1, the review's major 4: E9's
        endurance hold stood from game minute 617, and a flee from a zombie at 0.5 tiles never works; the shove loses
        only 5 points of crit chance per endurance level, #4373): any hold this tick (`spent_kinds`: arms, endurance
        or tired) and a zombie within KEEP_R: it is fought whatever the hold (the Fight's shove at point blank, the
        stomp of a fallen one, the backpedal between, never the swing: `policies.Fight.no_swing`, which Survive feeds
        the hold, `_fight_spent`); the holds' release lines govern the seeking of fights only (`_sought`). With
        `HOLD_WIDE` off, the arms' hold alone (P24-AP as Task 32 landed it)."""
        if not self.HOLD_WIDE:
            return self.spent_kinds == ("arms",) and bool(self._within(KEEP_R))
        return bool(self.spent_kinds) and bool(self._within(KEEP_R))

    def _fight_spent(self):
        """The holds the Fight reads to send no swing (`policies.Fight.spent`, ruling R2): this tick's `spent_kinds`
        with `HOLD_WIDE` on and a build that announces `shove` (the point-blank answer R2 puts in the swing's place;
        on a build without it a held Fight would send nothing at 0.5 tiles, so the swing stays, as on E4's and F1's
        PZA/1.4 records), else () (the Fight reads `body.armPain` itself, `arms_hurt`)."""
        return self.spent_kinds if self.HOLD_WIDE and self.world.can("shove") else ()

    def _lone(self, near):
        """Ruling P24-AT, the wounded seek: of `near` (the zombies listed within ENGAGE_R), `[t]` when `t` is a lone
        target: the one standing zombie (not `on_floor`) within ENGAGE_R, no other zombie within DANGER_R, and no other
        listed within LISTED_R chasing (`hasTarget`: a group coming, which the wounded character flees as today);
        else []. The fight then goes as any sought fight's, the Fight sending no swing (`arms_hurt`)."""
        standing = [z for z in near if not on_floor(z)]
        if len(standing) != 1:
            return []
        t = standing[0]
        if any(z is not t and zdist(self.world, z) <= DANGER_R for z in near):
            return []
        if any(z is not t and chasing(z) for z in self._within(LISTED_R)):
            return []
        return [t]

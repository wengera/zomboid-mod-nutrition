r"""Plan 10c Task H6, Step 2: the global store's record size, in the save's own format (an offline spike).

The scenario is the golden trace's (testing/tests/kernel/golden_trace.py, `run`, on server_host.Host, unchanged):
six stand-in players g1..g6 through 240 slow minutes. At its end the store's records table
(NR.server.store.records, the table the mod keeps under the global modData key "NutritionRevamp.players") is
serialised byte for byte the way the jar writes it. The format, read from the 42.20.4 jar (b0bbce05d5):

  global_mod_data.bin (GlobalModData.save L231-L262):
    int 249 (the version)                                   ByteBuffer.putInt @37-@40
    int the number of tables                                @44-@54
    per table: int the block length, then                   @130-@132, back-patched @209-@215
               WriteString(name), then KahluaTable.save     @147-@172
  WriteString (GameWindow$StringUTF.save L1413-L1421): short the UTF-8 byte length, then the bytes; a null or
    empty string is the short 0 alone.
  KahluaTableImpl.save(ByteBuffer) (L258-L275): int the count of savable entries, then per savable entry
    save(bb, keyByte, key) and save(bb, valueByte, value).
  KahluaTableImpl.save(ByteBuffer, byte, Object) (L279-L289): the type byte, then
    0 String: WriteString;  1 Double: putDouble (8 bytes);  3 Boolean: one byte;  2 table: KahluaTableImpl.save.
  getKeyByte (L420-L426): String 0, Double 1, else -1 (skipped). getValueByte (L430-L442): String 0, Double 1,
    Boolean 3, KahluaTableImpl 2, else -1 (skipped). Every Kahlua number is a Double, so every number, integral
    or not, is 8 bytes.

The reply to a client's GlobalModDataRequest carries the same table bytes (GlobalModData.receiveRequest L190-L193:
putUTF(name), putBoolean, KahluaTable.save), so the store's size here is also one request's payload.

Outputs (testing/spikes/out/):
  store-size.json   per record: full (the live record a save writes, derived fields included) and inputsOnly
                    (K.store.inputsOnly, the Plan 11 candidate's record); leaf and table counts; the store at
                    N = 1, 6, 60, 100, 500 and 2000 records, built by cycling the six final records under
                    synthetic usernames of USERNAME_LEN characters, serialised whole (not multiplied out).
  store-size.md     the same, as a table.

    python testing/spikes/store_size.py            writes both files
    python testing/spikes/store_size.py --check    re-runs and compares against the committed JSON

The Lua is the mod/ tree server_host loads (identical to the staged copy release/hitch-9578eb9: its MANIFEST
sha256 equals Plan 10b's, because mod/ has not changed since).
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
KERNEL = os.path.join(REPO, "testing", "tests", "kernel")
if KERNEL not in sys.path:
    sys.path.insert(0, KERNEL)

import lupa.lua51 as lua51  # noqa: E402

import golden_trace  # noqa: E402

OUT = os.path.join(HERE, "out")
JSON_OUT = os.path.join(OUT, "store-size.json")
MD_OUT = os.path.join(OUT, "store-size.md")
STORE_NAME = "NutritionRevamp.players"
USERNAME_LEN = 10          # a synthetic username "p000000001"-style, 10 ASCII characters
SCALES = (1, 6, 60, 100, 500, 2000)
FIRST_BLOCK = 1048576      # GlobalModData.save L229: the first buffer when lastBlockSize is -1
GROW = 524288              # GlobalModData.ensureCapacity L218: capacity + 512 KiB per overflow


# --- the jar's writer, in Python ------------------------------------------------------------------------------

def _is_table(v):
    return (not isinstance(v, (bool, int, float, str, bytes))) and v is not None and lua51.lua_type(v) == "table"


def _key_byte(k):
    if isinstance(k, (str, bytes)):
        return 0
    if isinstance(k, (int, float)) and not isinstance(k, bool):
        return 1
    return -1


def _value_byte(v):
    if isinstance(v, (str, bytes)):
        return 0
    if isinstance(v, bool):
        return 3
    if isinstance(v, (int, float)):
        return 1
    if _is_table(v):
        return 2
    return -1


def write_string(out, s):
    if isinstance(s, str):
        s = s.encode("utf-8")
    if not s:
        out += struct.pack(">h", 0)
        return
    out += struct.pack(">h", len(s))
    out += s


def _save_value(out, b, v, counts):
    out.append(b)
    if b == 0:
        write_string(out, v)
    elif b == 1:
        out += struct.pack(">d", float(v))
        counts["numbers"] += 1
    elif b == 3:
        out.append(1 if v else 0)
    elif b == 2:
        save_table(out, v, counts)


def save_table(out, t, counts):
    """KahluaTableImpl.save(ByteBuffer): the count of savable entries, then each key and value."""
    counts["tables"] += 1
    entries = []
    for k, v in t.items():
        kb, vb = _key_byte(k), _value_byte(v)
        if kb == -1 or vb == -1:
            counts["skipped"] += 1
            continue
        entries.append((kb, k, vb, v))
    out += struct.pack(">i", len(entries))
    for kb, k, vb, v in entries:
        _save_value(out, kb, k, counts)
        _save_value(out, vb, v, counts)
        if vb != 2:
            counts["leaves"] += 1


def new_counts():
    return {"tables": 0, "leaves": 0, "numbers": 0, "skipped": 0}


def table_bytes(rt, t):
    out = bytearray()
    c = new_counts()
    save_table(out, t, c)
    return bytes(out), c


def file_bytes(name, table_payload):
    """global_mod_data.bin holding one table: version, table count, block length, name, the table."""
    out = bytearray()
    out += struct.pack(">i", 249)
    out += struct.pack(">i", 1)
    body = bytearray()
    write_string(body, name)
    body += table_payload
    out += struct.pack(">i", len(body))
    out += body
    return bytes(out)


def overflow_restarts(size):
    """GlobalModData.save's first save after a boot (lastBlockSize -1): a 1 MiB buffer, grown 512 KiB per
    overflow, the current table re-serialised from its start after each (L236-L255). Returns (restarts,
    bytes serialised in all, final capacity). Inference from the bytecode; the overflow is approximated as the
    point the write passes the capacity."""
    cap = FIRST_BLOCK
    done = 0
    restarts = 0
    while size > cap:
        done += cap          # at most the whole capacity written before the overflow
        cap += GROW
        restarts += 1
    return restarts, done + size, cap


# --- the scenario -------------------------------------------------------------------------------------------

def final_records():
    h = golden_trace.new_host()
    golden_trace.run(h)
    recs = h.NR.server.store.records
    return h, recs


def measure():
    h, recs = final_records()
    rt = h.rt
    per = {}
    full_list = []
    inputs_list = []
    for n in golden_trace.NAMES:
        r = recs[n]
        fb, fc = table_bytes(rt, r)
        io = h.K.store.inputsOnly(r)
        ib, ic = table_bytes(rt, io)
        per[n] = {"full_bytes": len(fb), "full_counts": fc, "inputs_bytes": len(ib), "inputs_counts": ic}
        full_list.append(r)
        inputs_list.append(io)

    def store_of(records, n):
        t = rt.table()
        for i in range(n):
            t["p%0*d" % (USERNAME_LEN - 1, i + 1)] = records[i % len(records)]
        return t

    scales = {}
    for kind, records in (("full", full_list), ("inputsOnly", inputs_list)):
        rows = {}
        for n in SCALES:
            payload, c = table_bytes(rt, store_of(records, n))
            fbytes = file_bytes(STORE_NAME, payload)
            restarts, serialised, cap = overflow_restarts(len(fbytes))
            rows[str(n)] = {
                "table_bytes": len(payload),
                "file_bytes": len(fbytes),
                "file_sha256": hashlib.sha256(fbytes).hexdigest(),
                "leaves": c["leaves"],
                "tables": c["tables"],
                "first_save_overflow_restarts": restarts,
                "first_save_bytes_serialised": serialised,
                "first_save_final_capacity": cap,
            }
        scales[kind] = rows

    def mean(key):
        return sum(per[n][key] for n in per) / len(per)

    entry_overhead = 1 + 2 + USERNAME_LEN + 1   # key type byte, short length, the username, value type byte
    return {
        "spike": "Plan 10c Task H6 Step 2",
        "scenario": "golden_trace.run, final records at minute %d" % golden_trace.MINUTES,
        "golden_sha256": hashlib.sha256(open(golden_trace.GOLDEN, "rb").read()).hexdigest(),
        "store_name": STORE_NAME,
        "username_len": USERNAME_LEN,
        "per_record": per,
        "per_record_mean": {
            "full_bytes": mean("full_bytes"),
            "inputs_bytes": mean("inputs_bytes"),
            "full_store_entry_bytes": mean("full_bytes") + entry_overhead,
            "inputs_store_entry_bytes": mean("inputs_bytes") + entry_overhead,
        },
        "per_record_range": {
            "full_bytes": [min(per[n]["full_bytes"] for n in per), max(per[n]["full_bytes"] for n in per)],
            "inputs_bytes": [min(per[n]["inputs_bytes"] for n in per), max(per[n]["inputs_bytes"] for n in per)],
        },
        "scales": scales,
        "decision3_rule": {
            "threshold_bytes": 1000000,
            "full_500_file_bytes": scales["full"]["500"]["file_bytes"],
            "exceeds": scales["full"]["500"]["file_bytes"] > 1000000,
        },
    }


def render_md(d):
    L = []
    L.append("# H6: the global store's size in the save's own format")
    L.append("")
    L.append("Scenario: %s; golden sha256 %s; key `%s`; synthetic usernames of %d characters."
             % (d["scenario"], d["golden_sha256"], d["store_name"], d["username_len"]))
    L.append("")
    L.append("| record | full bytes | full leaves | full tables | inputsOnly bytes | inputsOnly leaves |")
    L.append("|---|---|---|---|---|---|")
    for n, r in d["per_record"].items():
        L.append("| %s | %d | %d | %d | %d | %d |" % (n, r["full_bytes"], r["full_counts"]["leaves"],
                                                    r["full_counts"]["tables"], r["inputs_bytes"],
                                                    r["inputs_counts"]["leaves"]))
    m = d["per_record_mean"]
    L.append("")
    L.append("Mean record: full %.1f bytes (%.1f with its store entry), inputsOnly %.1f (%.1f)."
             % (m["full_bytes"], m["full_store_entry_bytes"], m["inputs_bytes"], m["inputs_store_entry_bytes"]))
    L.append("")
    L.append("| records | full file bytes | full first-save restarts | inputsOnly file bytes | inputsOnly restarts |")
    L.append("|---|---|---|---|---|")
    for n in SCALES:
        f = d["scales"]["full"][str(n)]
        i = d["scales"]["inputsOnly"][str(n)]
        L.append("| %d | %d | %d | %d | %d |" % (n, f["file_bytes"], f["first_save_overflow_restarts"],
                                              i["file_bytes"], i["first_save_overflow_restarts"]))
    L.append("")
    r = d["decision3_rule"]
    L.append("Decision 3 size rule: 500 full records = %d bytes against %d: %s."
             % (r["full_500_file_bytes"], r["threshold_bytes"], "exceeds" if r["exceeds"] else "within"))
    L.append("")
    return "\n".join(L)


def main(argv):
    d = measure()
    text = json.dumps(d, indent=1, sort_keys=True) + "\n"
    if "--check" in argv:
        with open(JSON_OUT, encoding="utf-8") as fh:
            same = fh.read() == text
        print("store-size.json %s" % ("in sync" if same else "DIFFERS"))
        return 0 if same else 1
    os.makedirs(OUT, exist_ok=True)
    with open(JSON_OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    with open(MD_OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_md(d))
    print(render_md(d))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

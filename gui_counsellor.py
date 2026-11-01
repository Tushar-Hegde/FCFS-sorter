import csv
import os
import json
import tkinter as tk
from tkinter import messagebox, ttk
import copy
import shutil
import threading
import gc
import time

PLANS_FILE = "plans_optimized.json"
BACKUP_FILE = "plans_optimized.backup.json"
CSV_FILE = "CourseList.csv"
DEBUG_TIMING = False    # set True to print any slow step (> 150 ms) and slow garbage collections
LIVE_ORDERS_FILE = "live_orders.json"      # only read once, to migrate old option orders into the tree

if DEBUG_TIMING:
    _gc_clock = {}
    def _gc_report(phase, info):
        if phase == "start":
            _gc_clock["t"] = time.time()
        else:
            dt = time.time() - _gc_clock.get("t", time.time())
            if dt > 0.03:
                print(f"[lag] garbage collection (gen {info['generation']}) took {dt * 1000:.0f} ms")
    gc.callbacks.append(_gc_report)

# ==============================================================================
# 1. CORE ENGINE & DATA PARSERS
# ==============================================================================

def get_timetable_data():
    theory_headers = [
        "8:00 AM - 8:50 AM", "9:00 AM - 9:50 AM", "10:00 AM - 10:50 AM",
        "11:00 AM - 11:50 AM", "12:00 PM - 12:50 PM", "2:00 PM - 2:50 PM",
        "3:00 PM - 3:50 PM", "4:00 PM - 4:50 PM", "5:00 PM - 5:50 PM",
        "6:00 PM - 6:50 PM", "7:01 PM - 7:50 PM"
    ]
    theory_grid = {
        "MON": ["A1","F1","D1","TB1","TG1","A2","F2","D2","TB2","TG2","V3"],
        "TUE": ["B1","G1","E1","TC1","TAA1","B2","G2","E2","TC2","TAA2","V4"],
        "WED": ["C1","A1","F1","V1","V2","C2","A2","F2","TD2","TBB2","V5"],
        "THU": ["D1","B1","G1","TE1","TCC1","D2","B2","G2","TE2","TCC2","V6"],
        "FRI": ["E1","C1","TA1","TF1","TD1","E2","C2","TA2","TF2","TDD2","V7"]
    }
    lab_headers = [
        "08:00 AM - 08:50 AM","08:51 AM - 09:40 AM","09:51 AM - 10:40 AM",
        "10:41 AM - 11:30 AM","11:40 AM - 12:30 PM","12:31 PM - 1:20 PM",
        "2:00 PM - 2:50 PM","2:51 PM - 3:40 PM","3:51 PM - 4:40 PM",
        "4:41 PM - 5:30 PM","5:40 PM - 6:30 PM","6:31 PM - 7:20 PM"
    ]
    lab_grid = {
        "MON": ["L1","L2","L3","L4","L5","L6","L31","L32","L33","L34","L35","L36"],
        "TUE": ["L7","L8","L9","L10","L11","L12","L37","L38","L39","L40","L41","L42"],
        "WED": ["L13","L14","L15","L16","L17","L18","L43","L44","L45","L46","L47","L48"],
        "THU": ["L19","L20","L21","L22","L23","L24","L49","L50","L51","L52","L53","L54"],
        "FRI": ["L25","L26","L27","L28","L29","L30","L55","L56","L57","L58","L59","L60"]
    }
    return theory_headers, theory_grid, lab_headers, lab_grid

def parse_time_range_to_minutes(time_range_str):
    def to_minutes(t_str):
        t_str = t_str.strip()
        parts = t_str.split(":")
        hour = int(parts[0])
        min_ampm = parts[1].split()
        minute = int(min_ampm[0])
        ampm = min_ampm[1].upper()
        if ampm == "PM" and hour != 12: hour += 12
        if ampm == "AM" and hour == 12: hour = 0
        return hour * 60 + minute
    try:
        start_str, end_str = time_range_str.split("-")
        return list(range(to_minutes(start_str), to_minutes(end_str)))
    except Exception:
        return []

def generate_minute_slot_mappings():
    t_headers, t_grid, l_headers, l_grid = get_timetable_data()
    slot_map = {}
    for day, slots in t_grid.items():
        for idx, slot in enumerate(slots):
            if slot != "—":
                minutes = parse_time_range_to_minutes(t_headers[idx])
                slot_map.setdefault(slot, set()).update((day, m) for m in minutes)
    for day, slots in l_grid.items():
        for idx, slot in enumerate(slots):
            minutes = parse_time_range_to_minutes(l_headers[idx])
            slot_map.setdefault(slot, set()).update((day, m) for m in minutes)
    return slot_map

def generate_slot_timing_map():
    t_headers, t_grid, l_headers, l_grid = get_timetable_data()
    slot_timing = {}
    
    for day, slots in t_grid.items():
        for idx, slot in enumerate(slots):
            if slot and slot != "—":
                slot_timing.setdefault(slot, []).append(f"{day} {t_headers[idx]}")
                
    for day, slots in l_grid.items():
        for idx, slot in enumerate(slots):
            if slot and slot != "—":
                slot_timing.setdefault(slot, []).append(f"{day} {l_headers[idx]}")
                
    for slot in slot_timing:
        slot_timing[slot] = ", ".join(slot_timing[slot])
        
    return slot_timing

def get_timings_for_slots(raw_slots, slot_timing_map):
    parts = [s.strip() for s in raw_slots.split('+')]
    timings = []
    for slot in parts:
        if slot in slot_timing_map:
            timings.append(f"{slot}: {slot_timing_map[slot]}")
        else:
            timings.append(slot)
    return "  |  ".join(timings)

def load_courses_from_csv(input_filename="CourseList.csv"):
    slot_map = generate_minute_slot_mappings()
    if not os.path.exists(input_filename):
        return {}
    courses_dict = {}
    with open(input_filename, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if not row or len(row) < 6 or "course" in row[1].lower():
                continue
            course_name, course_code, raw_slots, tt_code, professor, course_type = [item.strip() for item in row[:6]]
            section_minutes = set()
            for slot in raw_slots.split('+'):
                clean_slot = slot.strip()
                if clean_slot in slot_map:
                    section_minutes.update(slot_map[clean_slot])
            section_data = {
                "name": course_name, "code": course_code, "slots": raw_slots,
                "tt_code": tt_code, "professor": professor, "type": course_type,
                "minute_blocks": list(section_minutes),
                "mask": section_mask(section_minutes)
            }
            courses_dict.setdefault(course_code, []).append(section_data)
    return courses_dict

# ── Optimized plans.json format ────────────────────────────────────────────
# Each combo: {"id": int, "order": [code,...], "secs": {code: {"p":prof,"s":slots} | null}}
# null  = blank slot.  name/type/tt_code/minute_blocks are derived at load time.

def _slim_sec(sec):
    """Fat section dict -> slim storage form."""
    if sec.get("is_blank"):
        return None
    return {"p": sec["professor"], "s": sec["slots"]}

def _fatten_sec(code, slim, courses_dict):
    """Slim storage form -> fat section dict the app uses internally."""
    if slim is None:
        secs = courses_dict.get(code, [])
        name = secs[0]["name"] if secs else code
        return {"code": code, "name": name, "slots": "—", "tt_code": "—",
                "professor": "—", "type": "—", "minute_blocks": [], "is_blank": True}
    candidates = courses_dict.get(code, [])
    match = next((s for s in candidates
                  if s["professor"] == slim["p"] and s["slots"] == slim["s"]), None)
    if match:
        return dict(match, is_blank=False)
    name = candidates[0]["name"] if candidates else code
    return {"code": code, "name": name, "slots": slim["s"], "tt_code": "—",
            "professor": slim["p"], "type": "—", "minute_blocks": [], "is_blank": False}

def get_theory_code(code):
    if code.endswith('P'):
        return code[:-1] + 'L'
    return None

def get_lab_code(code):
    if code.endswith('L'):
        return code[:-1] + 'P'
    return None



# ==============================================================================
# 1b. FLOW PLANNING + TIMETABLE HELPERS
# ==============================================================================

DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI"]
DAY_INDEX = {d: i for i, d in enumerate(DAY_NAMES)}

def section_mask(minute_blocks):
    """Bitmask of every (day, minute) a section occupies - makes clash checks a single AND."""
    m = 0
    for day, minute in minute_blocks:
        m |= 1 << (DAY_INDEX[day] * 1440 + minute)
    return m

def slot_runs(slot_map, raw_slots):
    """Split a raw slot string (e.g. 'B2+TB2') into drawable runs: (slot, day, start_min, end_min)."""
    runs = []
    for slot in [s.strip() for s in raw_slots.split('+')]:
        by_day = {}
        for day, minute in slot_map.get(slot, ()):
            by_day.setdefault(day, []).append(minute)
        for day, mins in by_day.items():
            mins.sort()
            start = prev = mins[0]
            for m in mins[1:]:
                if m == prev + 1:
                    prev = m
                    continue
                runs.append((slot, day, start, prev + 1))
                start = prev = m
            runs.append((slot, day, start, prev + 1))
    return runs

def get_mask(sec):
    """Cached bitmask of every (day, minute) a section occupies."""
    m = sec.get("mask")
    if m is None:
        m = section_mask(sec.get("minute_blocks", ()))
        sec["mask"] = m
    return m

# ==============================================================================
# 1a. PLAN GRAPH  (the single in-memory + on-disk representation of all plans)
# ==============================================================================
# An EDGE is one section choice:  edge = [sid, ends, kids, count]
#   sid    index into PlanTree.table (one fat section dict per distinct course/prof/slots)
#   ends   1 if a plan finishes right after this section
#   kids   the NEXT STAGE: a list of edges. The order of that list is the priority order.
#          The SAME list object is shared by every edge whose next stage is identical - e.g. two
#          professors teaching the same time slot lead to one shared next stage, so its priority
#          order is stored once and reordering it applies to both.
#   count  number of plans reachable through this edge
# A plan is a path of edges from the root list down to an edge with ends == 1.
#
# File format (v3):  {"v":3, "sections":[[code,prof,slots] | [code]], "nodes":[...], "root":id}
#   nodes[i] = list of edges; an edge is [sid] (plan ends here, nothing after)
#              or [sid, ends, node_id].  Nodes are listed children-first; "root" is the start list.

class PlanTree:
    def __init__(self, courses_dict):
        self.cd = courses_dict
        self.table = []
        self.index = {}
        self.roots = []

    @staticmethod
    def key_of(sec):
        if sec.get("is_blank"):
            return (sec["code"],)
        return (sec["code"], sec["professor"], sec["slots"])

    def sid_of(self, sec):
        key = self.key_of(sec)
        sid = self.index.get(key)
        if sid is None:
            sid = len(self.table)
            self.index[key] = sid
            if sec.get("is_blank"):
                fat = _fatten_sec(sec["code"], None, self.cd)
            elif "is_blank" in sec:
                fat = sec
            else:
                fat = dict(sec, is_blank=False)
            get_mask(fat)
            self.table.append(fat)
        return sid

    def kids_at(self, path):
        return path[-1][2] if path else self.roots

    def recount(self):
        memo = {}
        def rec(kids):
            v = memo.get(id(kids))
            if v is not None:
                return v
            total = 0
            for e in kids:
                c = 1 if e[1] else 0
                if e[2]:
                    c += rec(e[2])
                e[3] = c
                total += c
            memo[id(kids)] = total
            return total
        rec(self.roots)

    def total(self):
        return sum(e[3] for e in self.roots)

    def node_count(self):
        seen = set()
        def rec(kids):
            if id(kids) in seen:
                return
            seen.add(id(kids))
            for e in kids:
                if e[2]:
                    rec(e[2])
        rec(self.roots)
        return len(seen)

    # ── building ─────────────────────────────────────────────────────────────
    def insert_path(self, secs, lookup=None):
        """Add one plan (list of section dicts). Returns True if it was new. Caller recounts."""
        if not secs:
            return False
        kids, edge = self.roots, None
        for s in secs:
            sid = self.sid_of(s)
            if lookup is not None:
                edge = lookup.get((id(kids), sid))
            else:
                edge = next((k for k in kids if k[0] == sid), None)
            if edge is None:
                edge = [sid, 0, [], 0]
                kids.append(edge)
                if lookup is not None:
                    lookup[(id(kids), sid)] = edge
            kids = edge[2]
        if edge[1]:
            return False
        edge[1] = 1
        return True

    def insert_path_cow(self, secs):
        """Add one plan WITHOUT touching other paths that share next stages with this one
        (only the lists along this path are copied).  Returns True if the plan was new."""
        if not secs:
            return False
        sids = [self.sid_of(s) for s in secs]
        kids, e = self.roots, None
        for sid in sids:                                  # already there?
            e = next((k for k in kids if k[0] == sid), None)
            if e is None:
                break
            kids = e[2]
        else:
            if e[1]:
                return False
        new_roots = list(self.roots)
        kids, edge = new_roots, None
        for sid in sids:
            idx = next((i for i, k in enumerate(kids) if k[0] == sid), None)
            if idx is None:
                edge = [sid, 0, [], 0]
                kids.append(edge)
            else:
                old = kids[idx]
                edge = [old[0], old[1], list(old[2]), old[3]]
                kids[idx] = edge
            kids = edge[2]
        edge[1] = 1
        self.roots = new_roots
        return True

    def resolve_path(self, secs):
        """Re-find the edges for a list of section dicts (after the graph was rebuilt/copied)."""
        path, kids = [], self.roots
        for s in secs:
            sid = self.index.get(self.key_of(s))
            e = next((k for k in kids if k[0] == sid), None) if sid is not None else None
            if e is None:
                break
            path.append(e)
            kids = e[2]
        return path

    def canonicalize(self):
        """Merge identical next stages (same sections, same order) so they are stored once."""
        memo, seen, keep = {}, {}, []
        def canon(kids):
            r = seen.get(id(kids))
            if r is not None:
                return r
            keep.append(kids)
            for e in kids:
                if e[2]:
                    e[2] = canon(e[2])
            sig = tuple((e[0], e[1], id(e[2]) if e[2] else 0) for e in kids)
            r = memo.setdefault(sig, kids)
            seen[id(kids)] = r
            return r
        self.roots = canon(self.roots)

    @classmethod
    def from_flat(cls, combos, courses_dict, canon=True):
        t = cls(courses_dict)
        lookup = {}
        for c in combos:
            secmap = {s["code"]: s for s in c["sections"]}
            seq = [secmap[code] for code in c["picking_order"] if code in secmap]
            t.insert_path(seq, lookup)
        if canon:
            t.canonicalize()
        t.recount()
        return t

    def _load_table(self, sections):
        for i, e in enumerate(sections):
            fat = _fatten_sec(e[0], {"p": e[1], "s": e[2]} if len(e) == 3 else None, self.cd)
            get_mask(fat)
            self.table.append(fat)
            self.index[self.key_of(fat)] = i

    @classmethod
    def from_data_v2(cls, data, courses_dict):
        """Previous (plain tree) file format."""
        t = cls(courses_dict)
        t._load_table(data["sections"])
        def build(nodes):
            out = []
            for n in nodes:
                if len(n) == 1:
                    out.append([n[0], 1, [], 1])
                else:
                    out.append([n[0], n[1], build(n[2]) if n[2] else [], 0])
            return out
        t.roots = build(data["tree"])
        t.canonicalize()
        t.recount()
        return t

    @classmethod
    def from_data(cls, data, courses_dict):
        t = cls(courses_dict)
        t._load_table(data["sections"])
        nodes = []
        for edges in data["nodes"]:
            lst = []
            for e in edges:
                if len(e) == 1:
                    lst.append([e[0], 1, [], 1])
                else:
                    lst.append([e[0], e[1], nodes[e[2]], 0])
            nodes.append(lst)
        t.roots = nodes[data["root"]] if data.get("root", -1) >= 0 else []
        t.recount()
        return t

    # ── export ───────────────────────────────────────────────────────────────
    def to_data(self):
        remap, table, nodes, nid = {}, [], [], {}

        def ser_edge(e):
            if not e[2] and not e[1]:
                return None                      # dead edge (no plan beneath) - never saved
            sid = remap.get(e[0])
            if sid is None:
                sid = len(table)
                remap[e[0]] = sid
                sec = self.table[e[0]]
                table.append([sec["code"]] if sec.get("is_blank")
                             else [sec["code"], sec["professor"], sec["slots"]])
            if not e[2]:
                return [sid]
            return [sid, e[1], ser_node(e[2])]

        def ser_node(kids):
            k = id(kids)
            if k in nid:
                return nid[k]
            edges = [x for x in (ser_edge(e) for e in kids) if x is not None]
            idx = len(nodes)
            nodes.append(edges)
            nid[k] = idx
            return idx

        root = ser_node(self.roots) if self.roots else -1
        return {"v": 3, "sections": table, "nodes": nodes, "root": root}

    def expand(self):
        """Flat list of plans (only used by rare bulk operations such as Structural Branch)."""
        combos, table = [], self.table

        def walk(kids, path):
            for e in kids:
                p = path + [e[0]]
                if e[1]:
                    combos.append({"id": len(combos) + 1,
                                   "picking_order": [table[i]["code"] for i in p],
                                   "sections": [table[i] for i in p]})
                if e[2]:
                    walk(e[2], p)

        walk(self.roots, [])
        return combos

    # ── editing ──────────────────────────────────────────────────────────────
    def prune(self):
        """Remove edges that no longer lead to any plan (in every place a next stage is shared)."""
        done = set()
        def rec(kids):
            if id(kids) in done:
                return
            done.add(id(kids))
            for e in list(kids):
                if e[2]:
                    rec(e[2])
                if not e[1] and not e[2]:
                    for i, k in enumerate(kids):
                        if k is e:
                            del kids[i]
                            break
        rec(self.roots)

    def delete_child(self, path, edge):
        """Remove `edge` (and everything below it) from the next stage under `path`."""
        kids = self.kids_at(path)
        for i, k in enumerate(kids):
            if k is edge:
                del kids[i]
                break
        self.prune()
        self.recount()

    def removal_delta(self, path, edge):
        """How many plans in total would disappear if `edge` were deleted (dry run)."""
        kids = self.kids_at(path)
        idx = next((i for i, k in enumerate(kids) if k is edge), None)
        if idx is None:
            return 0
        before = self.total()
        del kids[idx]
        self.recount()
        after = self.total()
        kids.insert(idx, edge)
        self.recount()
        return before - after

    def valid_prefix(self, path):
        kids, out = self.roots, []
        for e in path:
            if not any(k is e for k in kids):
                break
            out.append(e)
            kids = e[2]
        return out

def _apply_live_orders(tree):
    """One-time migration: older versions kept option order in live_orders.json (keyed by path).
    Now the order of each node's children IS the order, so apply it and retire the file."""
    if not os.path.exists(LIVE_ORDERS_FILE):
        return False
    try:
        with open(LIVE_ORDERS_FILE, encoding="utf-8") as f:
            orders = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    if isinstance(orders, dict) and orders:
        table = tree.table

        def walk(kids, parts):
            saved = orders.get("|".join(f"{s['code']}:{s.get('professor', '')},{s.get('slots', '')}"
                                        for s in parts))
            if saved:
                rank = {tuple(x): i for i, x in enumerate(saved)}
                kids.sort(key=lambda n: rank.get((table[n[0]]["code"], table[n[0]]["professor"],
                                                  table[n[0]]["slots"]), len(rank)))
            for n in kids:
                if n[2]:
                    walk(n[2], parts + [table[n[0]]])

        walk(tree.roots, [])
    try:
        os.replace(LIVE_ORDERS_FILE, LIVE_ORDERS_FILE + ".migrated.bak")
    except OSError:
        pass
    return True

def tree_to_json(tree):
    # json.dumps (one-shot C encoder) is several times faster than json.dump(f)
    return json.dumps(tree.to_data(), separators=(",", ":"))

def write_text_atomic(text, filename):
    tmp = filename + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, filename)       # never leaves a half-written plans file

def save_tree(tree, filename=PLANS_FILE):
    write_text_atomic(tree_to_json(tree), filename)

def load_tree(filename, courses_dict):
    cd = courses_dict
    tree, upgraded, pre = None, False, None

    def backup(suffix):
        bak = filename + suffix
        try:
            if not os.path.exists(bak):
                shutil.copy2(filename, bak)
            return True
        except OSError:
            return False

    if os.path.exists(filename):
        try:
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return PlanTree(cd)
        if "nodes" in data:                       # v3 (current)
            tree = PlanTree.from_data(data, cd)
        elif "tree" in data:                      # v2 (plain tree) -> merge shared stages once
            tree = PlanTree.from_data_v2(data, cd)
            upgraded = backup(".v2.bak")
        else:                                     # v1 (flat list of plans)
            pre = PlanTree.from_flat(_fatten_plans(data, cd)["combos"], cd, canon=False)
            if data.get("live_orders") and not os.path.exists(LIVE_ORDERS_FILE):
                save_live_orders(data["live_orders"])
            upgraded = backup(".v1.bak")
    elif os.path.exists("plans.json"):
        with open("plans.json", encoding="utf-8") as f:
            try:
                fat = json.load(f)
            except json.JSONDecodeError:
                return PlanTree(cd)
        slim_combos = [{"id": c["id"], "order": c["picking_order"],
                        "secs": {s["code"]: _slim_sec(s) for s in c["sections"]}}
                       for c in fat.get("combos", [])]
        pre = PlanTree.from_flat(_fatten_plans({"combos": slim_combos}, cd)["combos"], cd, canon=False)
        upgraded = True
    else:
        return PlanTree(cd)

    if pre is not None:                           # old orders are applied BEFORE stages are merged
        _apply_live_orders(pre)
        pre.canonicalize()
        pre.recount()
        tree = pre
        migrated = False
    else:
        migrated = _apply_live_orders(tree)
    if upgraded or migrated:
        try:
            save_tree(tree, filename)
        except OSError:
            pass
    return tree

def _fatten_plans(slim, courses_dict):
    """Old flat v1 format -> list of plans (only used when upgrading an old file)."""
    index = {}
    def get(code, sl):
        key = (code, None) if sl is None else (code, sl["p"], sl["s"])
        v = index.get(key)
        if v is None:
            v = _fatten_sec(code, sl, courses_dict)
            index[key] = v
        return v
    combos = []
    for c in slim.get("combos", []):
        order = c["order"]
        secs = c["secs"]
        combos.append({"id": c["id"], "picking_order": order,
                       "sections": [get(code, secs.get(code)) for code in order]})
    return {"combos": combos}

def load_live_orders(filename=LIVE_ORDERS_FILE):
    if os.path.exists(filename):
        try:
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}

def save_live_orders(orders, filename=LIVE_ORDERS_FILE):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(orders, f, separators=(",", ":"))

def split_course(code, cd):
    """(theory_sections, lab_sections or None) for a course code.
    A lab is joint with its course when the CSV has it: either rows of the same code with type LO
    (e.g. BECE320E) or the matching XXXXP code for an XXXXL course. No lab in the CSV -> None."""
    secs = cd.get(code, [])
    th = [s for s in secs if s.get("type", "").upper() != "LO"]
    lo = [s for s in secs if s.get("type", "").upper() == "LO"]
    if th and lo:
        return th, lo
    lab = get_lab_code(code)
    if lab and lab in cd:
        return secs, cd[lab]
    return secs, None


def build_flow_tree(stages, courses_dict, progress=None, skips=None):
    """
    Build the FULL selection graph for a flow as a PlanTree.

    `stages` is a list of stages, each stage a list of course codes:
      * 1 code   -> that course is picked at this stage
      * 2+ codes -> a GROUP: exactly ONE of these courses is picked at this stage
                    (the courses in a group may clash with each other; only the chosen one matters)
    A course that has a lab in the CSV (XXXXL -> XXXXP) is joint with it: its lab is picked
    immediately after it, and must be taught by the same professor. Courses with no lab in the CSV
    are individual.  No section may clash with anything already chosen.
    Dead-end paths are pruned, so every plan contains one course from every stage (plus its lab).
    Paths that end up in the same situation (same occupied time slots, same pending lab
    professor) share ONE next stage - this is what keeps the tree small.
    `skips` (optional, one bool per stage): when True, that stage also gets a BLANK option meaning
    "no professor available, skip this stage". It occupies no time, so later stages are only
    checked against what was really picked. The blank is listed last (lowest priority).
    Returns (tree, plan_count, dead_end_count, alive_per_stage).
    """
    n = len(stages)
    skips = list(skips) if skips else [False] * n
    tree = PlanTree(courses_dict)

    def options_for(secs):
        seen, lst = set(), []
        for s in secs:
            key = (s["professor"], s["slots"])
            if key in seen:
                continue
            seen.add(key)
            fat = dict(s, is_blank=False)
            sid = tree.sid_of(fat)
            lst.append((sid, fat["professor"], get_mask(tree.table[sid])))
        return lst

    # per stage: list of alternatives (theory/standalone options, lab options or None)
    alts = []
    for stage in stages:
        row = []
        for code in stage:
            th, lo = split_course(code, courses_dict)
            row.append((options_for(th), options_for(lo) if lo else None))
        alts.append(row)

    skip_sid = []
    for stage, sk in zip(stages, skips):
        if sk:
            code = stage[0] if len(stage) == 1 else "SKIP[" + "|".join(stage) + "]"
            skip_sid.append(tree.sid_of(_fatten_sec(code, None, courses_dict)))
        else:
            skip_sid.append(None)

    states = {}      # key -> (kids, total, transitions)

    def finish(key, kids, total, trans):
        res = (kids, total, trans)
        states[key] = res
        if progress and len(states) % 2000 == 0:
            progress(len(states))
        return res

    def stage_state(s, occ):
        key = ("S", s, occ)
        hit = states.get(key)
        if hit is not None:
            return hit
        last = (s == n - 1)
        kids, total, trans = [], 0, []
        for ai, (theory, labs) in enumerate(alts[s]):
            for sid, prof, mask in theory:
                if mask & occ:
                    continue
                occ1 = occ | mask
                if labs is None:                       # individual course: this pick completes the stage
                    if last:
                        kids.append([sid, 1, [], 1])
                        total += 1
                        trans.append((None, True))
                    else:
                        sub = stage_state(s + 1, occ1)
                        trans.append((("S", s + 1, occ1), True))
                        if sub[1]:
                            kids.append([sid, 0, sub[0], sub[1]])
                            total += sub[1]
                else:                                  # joint with its lab: lab comes straight after
                    sub = lab_state(s, ai, prof, occ1)
                    trans.append((("L", s, ai, prof, occ1), False))
                    if sub[1]:
                        kids.append([sid, 0, sub[0], sub[1]])
                        total += sub[1]
        if skip_sid[s] is not None:                    # skip this stage: nothing picked, nothing occupied
            if last:
                kids.append([skip_sid[s], 1, [], 1])
                total += 1
                trans.append((None, True))
            else:
                sub = stage_state(s + 1, occ)
                trans.append((("S", s + 1, occ), True))
                if sub[1]:
                    kids.append([skip_sid[s], 0, sub[0], sub[1]])
                    total += sub[1]
        return finish(key, kids, total, trans)

    def lab_state(s, ai, prof, occ1):
        key = ("L", s, ai, prof, occ1)
        hit = states.get(key)
        if hit is not None:
            return hit
        last = (s == n - 1)
        kids, total, trans = [], 0, []
        for sid, lprof, mask in alts[s][ai][1]:
            if lprof != prof or (mask & occ1):
                continue
            occ2 = occ1 | mask
            if last:
                kids.append([sid, 1, [], 1])
                total += 1
                trans.append((None, True))
            else:
                sub = stage_state(s + 1, occ2)
                trans.append((("S", s + 1, occ2), True))
                if sub[1]:
                    kids.append([sid, 0, sub[0], sub[1]])
                    total += sub[1]
        return finish(key, kids, total, trans)

    rootkids, leaves, _t = stage_state(0, 0)
    tree.roots = rootkids
    tree.canonicalize()        # also merge next stages that are identical even if their picks differed
    tree.recount()

    # Path-level statistics (forward pass over the merged states, in stage order)
    mult = {("S", 0, 0): 1}
    alive = [0] * (n + 1)
    alive[0] = 1
    dead = 0
    for key in sorted(states, key=lambda k: 2 * k[1] + (1 if k[0] == "L" else 0)):
        m = mult.get(key, 0)
        if not m:
            continue
        _k, tot, trans = states[key]
        if tot == 0 and not trans:
            dead += m
        for nk, completes in trans:
            if completes:
                alive[key[1] + 1] += m
            if nk is not None:
                mult[nk] = mult.get(nk, 0) + m
    return tree, leaves, dead, alive


# ==============================================================================
# 2. MAIN APPLICATION GUI CLASS
# ==============================================================================

class MasterCounsellingApp:
    HL = "#DCE7FB"   # highlight background for the selected option card

    # Timetable geometry
    TT_W = 530
    TT_LEFT = 48
    TT_TOP = 26
    TT_GRID_H = 600
    TT_START = 8 * 60
    TT_END = 20 * 60
    PALETTE = [("#BFDBFE", "#3B82F6"), ("#BBF7D0", "#22C55E"), ("#FDE68A", "#D97706"),
               ("#FBCFE8", "#DB2777"), ("#C7D2FE", "#6366F1"), ("#FED7AA", "#EA580C"),
               ("#A7F3D0", "#10B981"), ("#E9D5FF", "#9333EA")]

    def __init__(self, root):
        self.root = root
        self.ok = False
        self.root.title("Course Counseling Suite")
        self.root.geometry("1320x860")
        self.root.minsize(1150, 700)

        self.courses_dict = load_courses_from_csv(CSV_FILE)
        self.plans = None            # flat plan list; exists only while the Structural Branch dialog is open
        self._dirty = False
        self._save_job = None
        self._save_thread = None
        self._save_error = None
        self.slot_timing_map = generate_slot_timing_map()
        self.slot_map = generate_minute_slot_mappings()
        self._scroll_canvases = set()

        if not self.courses_dict:
            messagebox.showerror("Missing Data", "CourseList.csv not found or is empty.")
            self.root.destroy()
            return
        self.tree = load_tree(PLANS_FILE, self.courses_dict)
        self._gc_settle()

        self.bg         = "#F5F7FA"
        self.surface    = "#FFFFFF"
        self.surface2   = "#EEF1F6"
        self.border     = "#D0D7E2"
        self.accent     = "#3B6FD4"
        self.accent_lt  = "#EBF0FB"
        self.text       = "#1A1F2E"
        self.text2      = "#5B6478"
        self.success    = "#1F7A4B"
        self.success_bg = "#E6F6ED"
        self.danger     = "#B91C1C"
        self.danger_bg  = "#FEE2E2"
        self.warn       = "#92400E"
        self.warn_bg    = "#FEF3C7"
        self.purple     = "#6D3BBF"
        self.purple_bg  = "#EDE9FE"

        self.root.configure(bg=self.bg)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background=self.bg, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=self.surface2, foreground=self.text2,
                        padding=[18, 6], font=("Helvetica", 12, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", self.accent)],
                  foreground=[("selected", "#FFFFFF")])
        style.configure("Vertical.TScrollbar",
                        troughcolor=self.surface2, background=self.border,
                        arrowcolor=self.text2, bordercolor=self.border)
        style.configure("TCombobox",
                        fieldbackground=self.surface, background=self.surface,
                        foreground=self.text, selectbackground=self.accent_lt,
                        selectforeground=self.text, bordercolor=self.border)

        # Mouse wheel / trackpad scrolling for every scrollable area (all platforms)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_live  = tk.Frame(self.notebook, bg=self.bg)
        self.tab_build = tk.Frame(self.notebook, bg=self.bg)
        self.tab_flow  = tk.Frame(self.notebook, bg=self.bg)

        self.notebook.add(self.tab_live,  text="    Live Tracker  ")
        self.notebook.add(self.tab_build, text="    Create New Plan  ")
        self.notebook.add(self.tab_flow,  text="    Flow Planning  ")

        self.setup_live_tab()
        self.setup_build_tab()
        self.setup_flow_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.initialize_live_mode()
        self.ok = True

    def on_tab_changed(self, event):
        t = self.notebook.index(self.notebook.select())
        if t == 0:
            self.refresh_live_tree(keep_scroll=True)
        elif t == 1:
            self.reset_builder_wizard()
        elif t == 2:
            self._flow_refresh_choices()

    # ── scrolling ────────────────────────────────────────────────────────────
    def _on_mousewheel(self, event):
        try:
            w = self.root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        while w is not None:
            if w in self._scroll_canvases:
                if w.yview() == (0.0, 1.0):
                    return          # everything already visible
                if event.num == 4:
                    step = -1
                elif event.num == 5:
                    step = 1
                else:
                    d = event.delta
                    if d == 0:
                        return
                    step = (-1 if d > 0 else 1) * max(1, abs(d) // 120)
                w.yview_scroll(step * 2, "units")
                return
            w = w.master

    def scrollable(self, parent):
        canvas = tk.Canvas(parent, bg=self.bg, highlightthickness=0, yscrollincrement=20)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.bg)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._scroll_canvases.add(canvas)
        canvas.bind("<Destroy>", lambda e, c=canvas: self._scroll_canvases.discard(c))
        return canvas, inner, sb

    def btn(self, parent, text, command, kind="primary", **kw):
        palettes = {
            "primary": (self.accent,    "#FFFFFF"),
            "success": (self.success,   "#FFFFFF"),
            "danger":  (self.danger,    "#FFFFFF"),
            "muted":   (self.border,    self.text),
            "warn":    (self.warn,      "#FFFFFF"),
            "purple":  (self.purple,    "#FFFFFF"),
        }
        bg, fg = palettes.get(kind, palettes["primary"])
        return tk.Button(parent, text=text, command=command,
                         bg=bg, fg=fg, font=("Helvetica", 11, "bold"),
                         relief="flat", cursor="hand2", padx=10, pady=5, **kw)

    def badge(self, parent, text, kind="info"):
        palettes = {
            "info":    (self.accent,   self.accent_lt),
            "success": (self.success,  self.success_bg),
            "danger":  (self.danger,   self.danger_bg),
            "warn":    (self.warn,     self.warn_bg),
            "purple":  (self.purple,   self.purple_bg),
        }
        fg, bg = palettes.get(kind, palettes["info"])
        return tk.Label(parent, text=text, font=("Helvetica", 10, "bold"),
                        fg=fg, bg=bg, padx=6, pady=2, relief="flat")

    def card_frame(self, parent, **kw):
        return tk.Frame(parent, bg=self.surface,
                        highlightbackground=self.border, highlightthickness=1,
                        **kw)

    # ==========================================================================
    # LIVE TRACKER TAB  (first tab, opens by default)
    # ==========================================================================
    # LIVE TRACKER TAB  (first tab, opens by default)
    # ==========================================================================
    def setup_live_tab(self):
        self.live_path = []              # nodes locked so far (root -> current)
        self.live_preview = None         # node currently highlighted / previewed
        self._live_cards = {}
        self._live_add_frame = None

        top = tk.Frame(self.tab_live, bg=self.surface,
                       highlightbackground=self.border, highlightthickness=1)
        top.pack(fill="x")
        tk.Label(top, text="Live Course Selection Tracker",
                 font=("Helvetica", 16, "bold"), fg=self.text, bg=self.surface
                 ).pack(side="left", padx=20, pady=10)
        self.btn(top, "Reset Tracker", self.initialize_live_mode, "danger").pack(side="right", padx=(6, 16), pady=8)
        self.btn(top, "< Go Back", self.live_handle_back, "warn").pack(side="right", padx=6, pady=8)

        body = tk.Frame(self.tab_live, bg=self.bg)
        body.pack(fill="both", expand=True)

        # right: weekly timetable
        right = tk.Frame(body, bg=self.bg, width=578)
        right.pack(side="right", fill="y", padx=(0, 12), pady=12)
        right.pack_propagate(False)
        tk.Label(right, text="Weekly Timetable", font=("Helvetica", 13, "bold"),
                 fg=self.text, bg=self.bg).pack(anchor="w", padx=4)
        rbody = tk.Frame(right, bg=self.bg)
        rbody.pack(fill="both", expand=True)
        _, rinner, _ = self.scrollable(rbody)
        self.tt_canvas = tk.Canvas(rinner, width=self.TT_W, height=self.TT_GRID_H + 100,
                                   bg=self.surface, highlightbackground=self.border,
                                   highlightthickness=1)
        self.tt_canvas.pack(anchor="nw", padx=4, pady=4)

        # left: locked path + next options (scrollable)
        left = tk.Frame(body, bg=self.bg)
        left.pack(side="left", fill="both", expand=True, padx=(16, 4), pady=12)
        self.live_canvas, self.live_scroll_frame, _ = self.scrollable(left)

    # ── background saving (debounced) ───────────────────────────────────────
    def _mark_dirty(self):
        """Debounced: the timer restarts on every change, so a save only happens once you pause."""
        self._dirty = True
        if self._save_job is not None:
            try:
                self.root.after_cancel(self._save_job)
            except Exception:
                pass
        self._save_job = self.root.after(2500, self._flush_save)

    def _wait_save(self):
        t = self._save_thread
        if t is not None and t.is_alive():
            t.join()

    def _flush_save(self, wait=False):
        """Snapshot the tree (fast) and write the file on a background thread so the UI never waits on disk."""
        if self._save_job is not None:
            try:
                self.root.after_cancel(self._save_job)
            except Exception:
                pass
            self._save_job = None
        if self._dirty:
            self._wait_save()               # keep writes in order
            try:
                _t0 = time.time()
                text = tree_to_json(self.tree)
                if DEBUG_TIMING and time.time() - _t0 > 0.15:
                    print(f"[lag] save snapshot took {(time.time() - _t0) * 1000:.0f} ms")
            except Exception as e:
                messagebox.showerror("Save failed", f"Could not serialise the plans:\n{e}")
                return
            self._dirty = False

            def _write():
                try:
                    write_text_atomic(text, PLANS_FILE)
                except OSError as e:
                    self._dirty = True
                    self._save_error = str(e)

            self._save_thread = threading.Thread(target=_write, daemon=False)
            self._save_thread.start()
        if wait:
            self._wait_save()
            if self._save_error:
                messagebox.showerror("Save failed", f"Could not write {PLANS_FILE}:\n{self._save_error}")
                self._save_error = None

    def _gc_settle(self):
        """Take the (large, long-lived) plan graph out of the garbage collector's view so it never
        causes a random pause.  Called after a new graph replaces the old one."""
        gc.unfreeze()
        gc.collect()
        gc.freeze()

    def _on_close(self):
        self._flush_save(wait=True)
        self.root.destroy()

    # ── live path helpers ───────────────────────────────────────────────────
    def _locked(self):
        return [self.tree.table[n[0]] for n in self.live_path]

    def _live_occ(self):
        occ = 0
        for s in self._locked():
            if not s.get("is_blank"):
                occ |= get_mask(s)
        return occ

    def initialize_live_mode(self):
        self.live_path = []
        self.live_preview = None
        self.refresh_live_tree()

    def live_handle_back(self):
        if self.live_path:
            self.live_path.pop()
            self.live_preview = None
            self.refresh_live_tree()

    def live_handle_select(self, node):
        self.live_path.append(node)
        self.live_preview = None
        self.refresh_live_tree()

    def refresh_live_tree(self, keep_scroll=False):
        t0 = time.time()
        y = self.live_canvas.yview()[0] if keep_scroll else 0.0
        self._refresh_live_tree_inner()
        t1 = time.time()
        self._live_draw_timetable()
        self.root.update_idletasks()
        self.live_canvas.yview_moveto(y)
        if DEBUG_TIMING and time.time() - t0 > 0.15:
            print(f"[lag] redraw took {(time.time() - t0) * 1000:.0f} ms "
                  f"(cards {(t1 - t0) * 1000:.0f} ms, timetable+layout {(time.time() - t1) * 1000:.0f} ms)")

    def _refresh_live_tree_inner(self):
        for w in self.live_scroll_frame.winfo_children(): w.destroy()
        self._live_cards = {}
        self._live_add_frame = None
        locked = self._locked()
        kids = self.tree.kids_at(self.live_path)
        table = self.tree.table

        if locked:
            path_frame = tk.LabelFrame(self.live_scroll_frame, text=" Locked Path ",
                                       font=("Helvetica", 11, "bold"), fg=self.success, bg=self.bg)
            path_frame.pack(fill="x", padx=12, pady=(10, 16))
            for i, sec in enumerate(locked, 1):
                prof_slot = "BLANK" if sec.get("is_blank") else f"{sec['professor']} - {sec['slots']}"
                tk.Label(path_frame, text=f"{i}. {sec['code']} ({prof_slot})",
                         font=("Helvetica", 10), fg=self.text, bg=self.bg).pack(anchor="w", padx=10, pady=2)
        else:
            tk.Label(self.live_scroll_frame,
                     text="Select your first course to begin tracking.",
                     font=("Helvetica", 11, "italic"), fg=self.text2, bg=self.bg).pack(pady=(14, 10), anchor="w", padx=12)

        if not kids:
            if locked:
                tk.Label(self.live_scroll_frame,
                         text="Path Complete! All courses in this combination are locked.",
                         font=("Helvetica", 12, "bold"), fg=self.success, bg=self.bg).pack(pady=30)
            else:
                tk.Label(self.live_scroll_frame, text="No saved combinations yet. Use Flow Planning or add an option below.",
                         font=("Helvetica", 11), fg=self.danger, bg=self.bg).pack(pady=20)
            self._render_live_add_new_row()
            return

        if self.live_preview is not None and not any(k is self.live_preview for k in kids):
            self.live_preview = None

        tk.Label(self.live_scroll_frame, text="Next Available Options:",
                 font=("Helvetica", 12, "bold"), fg=self.text, bg=self.bg).pack(anchor="w", padx=12, pady=(0, 2))
        tk.Label(self.live_scroll_frame, text="Click an option to highlight it and preview it on the timetable.",
                 font=("Helvetica", 10, "italic"), fg=self.text2, bg=self.bg).pack(anchor="w", padx=12, pady=(0, 8))

        cards_start = []
        for node in kids:
            opt = table[node[0]]
            weight = node[3]
            timings = get_timings_for_slots(opt["slots"], self.slot_timing_map) if not opt.get("is_blank") else "—"

            card = tk.Frame(self.live_scroll_frame, bg=self.surface,
                            highlightbackground=self.border, highlightthickness=1)
            card.pack(fill="x", pady=4, padx=12)
            self._live_cards[id(node)] = card

            info = tk.Frame(card, bg=self.surface)
            info.pack(side="left", fill="both", expand=True, padx=12, pady=10)
            tk.Label(info, text=f"{opt['code']} — {opt.get('name', '')}",
                     font=("Helvetica", 12, "bold"), fg=self.text, bg=self.surface, anchor="w").pack(anchor="w")
            if opt.get("is_blank"):
                tk.Label(info, text="[ BLANK SLOT ]", font=("Helvetica", 11, "italic"),
                         fg=self.text2, bg=self.surface).pack(anchor="w")
            else:
                tk.Label(info,
                         text=f"Prof: {opt['professor']}   Slots: {opt['slots']}   TT: {opt['tt_code']}",
                         font=("Helvetica", 11), fg=self.text2, bg=self.surface, anchor="w").pack(anchor="w")
                tk.Label(info, text=timings, font=("Helvetica", 11), fg=self.accent,
                         bg=self.surface, anchor="w", wraplength=480, justify="left").pack(anchor="w", pady=(2, 0))

            right_col = tk.Frame(card, bg=self.surface)
            right_col.pack(side="right", padx=12, pady=10)
            self.badge(right_col, f"{weight} plan{'s' if weight != 1 else ''}", "info").pack(pady=(0, 6))
            self.btn(right_col, "Secure", lambda n=node: self.live_handle_select(n), "success").pack()
            self.btn(right_col, "Branch", lambda n=node: self.live_structural_branch(n), "purple").pack(pady=(6, 0))
            self.btn(right_col, "Delete Branch", lambda n=node: self.live_delete_branch(n), "danger").pack(pady=(6, 0))
            arrow_row = tk.Frame(right_col, bg=self.surface)
            arrow_row.pack(pady=(6, 0))
            self.btn(arrow_row, "^", lambda n=node: self._live_move_node(n, -1), "muted").pack(side="left", padx=2)
            self.btn(arrow_row, "v", lambda n=node: self._live_move_node(n, 1), "muted").pack(side="left", padx=2)

            self._bind_click(card, lambda e, n=node: self._live_toggle_preview(n))

        if self.live_preview is not None:
            self._live_style_card(self.live_preview, True)

        self._render_live_add_new_row()

    # ── option highlight / preview ──────────────────────────────────────────
    def _live_style_card(self, node, selected):
        card = self._live_cards.get(id(node))
        if card is None:
            return
        old, new = (self.surface, self.HL) if selected else (self.HL, self.surface)
        card.configure(bg=new,
                       highlightbackground=self.accent if selected else self.border,
                       highlightthickness=3 if selected else 1)
        self._recolor(card, old, new)

    def _live_toggle_preview(self, node):
        if self.live_preview is not None:
            self._live_style_card(self.live_preview, False)
        if self.live_preview is node:
            self.live_preview = None
        else:
            self.live_preview = node
            self._live_style_card(node, True)
        self._live_draw_timetable()

    # ── reordering = swapping siblings; saved in the background ─────────────
    def _live_move_node(self, node, direction):
        kids = self.tree.kids_at(self.live_path)
        i = next((i for i, k in enumerate(kids) if k is node), None)
        if i is None:
            return
        j = i + direction
        if not (0 <= j < len(kids)):
            return
        kids[i], kids[j] = kids[j], kids[i]
        self._mark_dirty()
        # Re-pack the existing cards in the new order (no widgets are rebuilt)
        for k in kids:
            c = self._live_cards.get(id(k))
            if c is not None:
                c.pack_forget()
        for k in kids:
            c = self._live_cards.get(id(k))
            if c is None:
                continue
            if self._live_add_frame is not None:
                c.pack(fill="x", pady=4, padx=12, before=self._live_add_frame)
            else:
                c.pack(fill="x", pady=4, padx=12)

    # ── add / branch / delete ───────────────────────────────────────────────
    def _render_live_add_new_row(self):
        add_frame = tk.Frame(self.live_scroll_frame, bg=self.surface2,
                             highlightbackground=self.border, highlightthickness=1)
        add_frame.pack(fill="x", pady=6, padx=12)
        self._live_add_frame = add_frame
        tk.Label(add_frame, text="Add New Option:", font=("Helvetica", 11, "bold"),
                 fg=self.text, bg=self.surface2).pack(side="left", padx=10, pady=10)

        # A course is offered if at least one of its sections doesn't clash with the locked path
        occ = self._live_occ()
        available = [c for c in sorted(self.courses_dict.keys())
                     if any((get_mask(s) & occ) == 0 for s in self.courses_dict[c])]
        display_vals = [f"{c} — {self.courses_dict[c][0]['name']}" for c in available]

        if not display_vals:
            tk.Label(add_frame, text="No more courses available.", font=("Helvetica", 11, "italic"),
                     fg=self.text2, bg=self.surface2).pack(side="left", pady=10)
            return

        cb = ttk.Combobox(add_frame, values=display_vals, state="readonly", width=40)
        cb.pack(side="left", padx=8, pady=10)
        cb.set(display_vals[0])

        def _do_add():
            val = cb.get()
            if not val: return
            self._open_live_section_picker(val.split(" — ")[0].strip())

        self.btn(add_frame, "+ Add", _do_add, "primary").pack(side="left", pady=10)

    def _open_live_section_picker(self, course_code):
        """Dialog to pick a specific section (or blank) before adding to the live tree."""
        occ = self._live_occ()
        sections = [s for s in self.courses_dict.get(course_code, []) if (get_mask(s) & occ) == 0]
        course_name = self.courses_dict[course_code][0]["name"] if self.courses_dict.get(course_code) else course_code

        dlg = tk.Toplevel(self.root)
        dlg.title(f"Pick Section — {course_code}")
        dlg.geometry("780x500")
        dlg.configure(bg=self.bg)
        dlg.grab_set()

        tk.Label(dlg, text=f"Select a section for {course_code} — {course_name}",
                 font=("Helvetica", 13, "bold"), fg=self.text, bg=self.bg).pack(pady=(14, 4), padx=16, anchor="w")
        tk.Label(dlg, text="Choose a specific section, or add as Blank (to fill in later).",
                 font=("Helvetica", 10, "italic"), fg=self.text2, bg=self.bg).pack(padx=16, anchor="w")

        body = tk.Frame(dlg, bg=self.bg)
        body.pack(fill="both", expand=True, padx=12, pady=8)
        _, scroll, _ = self.scrollable(body)

        def _pick(sec_data):
            dlg.destroy()
            self._live_add_new_option(course_code, sec_data)

        blank_card = tk.Frame(scroll, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
        blank_card.pack(fill="x", pady=4, padx=4)
        tk.Label(blank_card, text=f"{course_code} — [ BLANK — fill in later ]",
                 font=("Helvetica", 11, "bold"), fg=self.text2, bg=self.surface).pack(side="left", padx=12, pady=10)
        self.btn(blank_card, "Add Blank", lambda: _pick(None), "muted").pack(side="right", padx=10, pady=10)

        for sec in sections:
            timings = get_timings_for_slots(sec["slots"], self.slot_timing_map)
            sc = tk.Frame(scroll, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
            sc.pack(fill="x", pady=4, padx=4)
            info = tk.Frame(sc, bg=self.surface)
            info.pack(side="left", fill="both", expand=True, padx=12, pady=8)
            tk.Label(info, text=f"Prof: {sec['professor']}   Slots: {sec['slots']}   TT: {sec['tt_code']}",
                     font=("Helvetica", 11, "bold"), fg=self.text, bg=self.surface).pack(anchor="w")
            tk.Label(info, text=timings, font=("Helvetica", 10), fg=self.accent,
                     bg=self.surface, wraplength=560, justify="left").pack(anchor="w", pady=(2, 0))
            self.btn(sc, "Select", lambda s=sec: _pick(s), "success").pack(side="right", padx=10, pady=10)

    def _live_add_new_option(self, new_code, sec_data=None):
        """Add new_code as a plan = current locked path + this course (blank if sec_data is None)."""
        if sec_data is None:
            new_sec = _fatten_sec(new_code, None, self.courses_dict)
        else:
            new_sec = dict(sec_data, is_blank=False)
        locked = self._locked()
        if not self.tree.insert_path_cow(locked + [new_sec]):
            messagebox.showinfo("Already Exists", "A combination with this exact path already exists.")
            return
        self.tree.recount()
        self.live_path = self.tree.resolve_path(locked)
        self.live_preview = None
        self._mark_dirty()
        self.refresh_live_tree()

    def live_structural_branch(self, node):
        # Find a saved plan on the CURRENT path that uses this option, then open the batch dialog on it
        prefix = self._locked() + [self.tree.table[node[0]]]
        k = len(prefix)
        flat = self.tree.expand()
        for c in flat:
            secs = c["sections"]
            if len(secs) >= k and all(secs[i] is prefix[i] for i in range(k)):
                self.plans = {"combos": flat}
                self.open_structural_batch_dialog(c["id"], preselect_code=prefix[-1]["code"])
                return
        messagebox.showerror("Error", "No saved combination containing this configuration to branch from.")

    def _commit_flat(self):
        """Rebuild the tree after a bulk (flat) edit made by the Structural Branch dialog."""
        locked = self._locked()
        self.tree = PlanTree.from_flat(self.plans["combos"], self.courses_dict)
        self.live_path = self.tree.resolve_path(locked)
        self.live_preview = None
        self._mark_dirty()
        self._gc_settle()

    def live_delete_branch(self, node):
        sec = self.tree.table[node[0]]
        # Exact number of plans that vanish (a next stage can be shared by several paths)
        n_plans = self.tree.removal_delta(self.live_path, node)
        path_str = " > ".join([x["code"] for x in self._locked()] + [sec["code"]])
        shared = ""
        if n_plans > node[3]:
            shared = ("\n\nNote: this next stage is shared with other paths that use the same time "
                      "slots, so the option disappears there as well.")

        msg1 = ("This will permanently delete %d combination(s) rooted at:\n\n"
                "  %s\n\nAll downstream leaves will also be removed.%s\n\nContinue?") % (n_plans, path_str, shared)
        if not messagebox.askyesno("Delete Branch - Step 1 of 2", msg1):
            return
        msg2 = ("Are you absolutely sure?\n\n%d combination(s) will be deleted.\n\n"
                "This cannot be undone.") % n_plans
        if not messagebox.askyesno("Delete Branch - Step 2 of 2 (Final Confirmation)", msg2):
            return

        self.tree.delete_child(self.live_path, node)
        self.live_path = self.tree.valid_prefix(self.live_path)
        self.live_preview = None
        self._mark_dirty()
        self.refresh_live_tree(keep_scroll=True)

    def _bind_click(self, widget, callback):
        if isinstance(widget, tk.Button):
            return
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            self._bind_click(child, callback)

    def _recolor(self, widget, old, new):
        for child in widget.winfo_children():
            if isinstance(child, (tk.Frame, tk.Label)) and str(child.cget("bg")).lower() == old.lower():
                child.configure(bg=new)
            self._recolor(child, old, new)

    def _live_draw_timetable(self):
        cv = self.tt_canvas
        cv.delete("all")
        left, top, grid_h = self.TT_LEFT, self.TT_TOP, self.TT_GRID_H
        right_edge = self.TT_W - 6
        col_w = (right_edge - left) / 5.0
        scale = grid_h / float(self.TT_END - self.TT_START)

        def y_of(minute):
            return top + (minute - self.TT_START) * scale

        for h in range(self.TT_START // 60, self.TT_END // 60 + 1):
            y = y_of(h * 60)
            cv.create_line(left, y, right_edge, y, fill=self.border)
            label = f"{h if h <= 12 else h - 12} {'AM' if h < 12 else 'PM'}"
            cv.create_text(left - 6, y, text=label, anchor="e",
                           font=("Helvetica", 8), fill=self.text2)
        for i, d in enumerate(DAY_NAMES):
            x0 = left + i * col_w
            cv.create_line(x0, top, x0, top + grid_h, fill=self.border)
            cv.create_text(x0 + col_w / 2, top / 2, text=d,
                           font=("Helvetica", 10, "bold"), fill=self.text)
        cv.create_line(right_edge, top, right_edge, top + grid_h, fill=self.border)

        def draw_sec(sec, fill, outline, dash=None, width=1):
            for slot, day, start, end in slot_runs(self.slot_map, sec.get("slots", "")):
                if day not in DAY_INDEX:
                    continue
                x0 = left + DAY_INDEX[day] * col_w + 1
                x1 = x0 + col_w - 2
                y0, y1 = y_of(start), y_of(end)
                cv.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline,
                                    width=width, dash=dash)
                txt = f"{sec['code']}\n{slot}" if (y1 - y0) >= 30 else sec["code"]
                cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=txt, width=col_w - 6,
                               font=("Helvetica", 8, "bold"), fill=self.text)

        legend = []
        for idx, sec in enumerate(self._locked()):
            fill, outline = self.PALETTE[idx % len(self.PALETTE)]
            if sec.get("is_blank"):
                legend.append((fill, outline, None, f"{sec['code']} (blank)"))
                continue
            draw_sec(sec, fill, outline)
            legend.append((fill, outline, None, f"{sec['code']} · {sec['slots']}"))

        prev = self.live_preview
        if prev is not None:
            psec = self.tree.table[prev[0]]
            if psec.get("is_blank"):
                legend.append(("#F3F4F6", "#111827", (4, 2), f"Preview: {psec['code']} (blank - nothing to show)"))
            else:
                draw_sec(psec, "#F3F4F6", "#111827", dash=(4, 2), width=2)
                legend.append(("#F3F4F6", "#111827", (4, 2), f"Preview: {psec['code']} · {psec['slots']}"))

        ly = top + grid_h + 12
        col_x = [left - 36, left + 230]
        for i, (fill, outline, dash, label) in enumerate(legend):
            x = col_x[i % 2]
            y = ly + (i // 2) * 20
            cv.create_rectangle(x, y, x + 12, y + 12, fill=fill, outline=outline, dash=dash)
            cv.create_text(x + 18, y + 6, text=label, anchor="w",
                           font=("Helvetica", 9), fill=self.text)
        rows = (len(legend) + 1) // 2
        cv.configure(height=ly + max(rows, 1) * 20 + 8)

    def open_structural_batch_dialog(self, combo_id, preselect_code=None):
        base_combo = next(c for c in self.plans["combos"] if c["id"] == combo_id)
        
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Structural Path Branching — Base Combo ID {combo_id}")
        dlg.geometry("850x650")
        dlg.configure(bg=self.bg)
        dlg.grab_set()
        dlg.bind("<Destroy>", lambda e: setattr(self, "plans", None) if e.widget is dlg else None)

        tk.Label(dlg, text=" Structural Batch Path Branching", font=("Helvetica", 14, "bold"), fg=self.text, bg=self.bg).pack(pady=10)
        tk.Label(dlg, text="Select the targeted course component you want to swap out across all shared tree paths:", font=("Helvetica", 11), fg=self.text2, bg=self.bg).pack(pady=2)

        f1 = tk.Frame(dlg, bg=self.bg)
        f1.pack(fill="x", padx=20, pady=10)
        tk.Label(f1, text="Target Course to Replace:", font=("Helvetica", 11, "bold"), fg=self.text, bg=self.bg).pack(side="left", padx=5)
        
        current_courses = base_combo["picking_order"]
        current_display = [f"{c} — {self.courses_dict[c][0]['name']}" if c in self.courses_dict else c for c in current_courses]
        target_cb = ttk.Combobox(f1, values=current_display, state="readonly", font=("Helvetica", 11), width=45)
        target_cb.pack(side="left", padx=5)
        target_cb.set(current_display[0] if current_display else "")
        if preselect_code in current_courses:
            target_cb.set(current_display[current_courses.index(preselect_code)])

        f2 = tk.Frame(dlg, bg=self.bg)
        f2.pack(fill="x", padx=20, pady=10)
        tk.Label(f2, text="Swap with Alternative Course:", font=("Helvetica", 11, "bold"), fg=self.text, bg=self.bg).pack(side="left", padx=5)
        
        all_csv_codes = sorted(list(self.courses_dict.keys()))
        dest_display = [f"{c} — {self.courses_dict[c][0]['name']}" for c in all_csv_codes]
        dest_cb = ttk.Combobox(f2, values=dest_display, state="readonly", font=("Helvetica", 11), width=45)
        dest_cb.pack(side="left", padx=5)
        dest_cb.set(dest_display[0] if dest_display else "")

        sec_label_frame = tk.LabelFrame(dlg, text=" Select Specific New Section Configuration ", font=("Helvetica", 11, "bold"), fg=self.text, bg=self.bg)
        sec_label_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        _, scroll_frame, _ = self.scrollable(sec_label_frame)

        def populate_sections(*args):
            for w in scroll_frame.winfo_children(): w.destroy()
            target_val = target_cb.get()
            dest_val = dest_cb.get()
            if not target_val or not dest_val: return
            
            t_code = target_val.split(" — ")[0].strip()
            dest_code = dest_val.split(" — ")[0].strip()
            
            orig_sec = next((s for s in base_combo["sections"] if s["code"] == t_code), None)

            t_lab_code = get_lab_code(t_code)
            t_has_lab = t_lab_code and t_lab_code in base_combo["picking_order"]

            d_lab_code = get_lab_code(dest_code)
            d_has_lab = d_lab_code and d_lab_code in self.courses_dict

            ignore_codes = {t_code}
            if t_has_lab: ignore_codes.add(t_lab_code)

            # --- STRUCTURAL BRANCH FIX --- 
            # Only check for clashes with higher nodes in the picking_order tree.
            # Leaf (later) nodes shouldn't restrict branching; they just get dropped.
            if t_code in base_combo["picking_order"]:
                t_index = base_combo["picking_order"].index(t_code)
            else:
                t_index = len(base_combo["picking_order"])
                
            higher_codes = set(base_combo["picking_order"][:t_index])
            
            # Check occupied blocks strictly for classes picked *prior* to this branch insertion
            other_secs = [s for s in base_combo["sections"] if s["code"] in higher_codes and s["code"] not in ignore_codes]
            occupied_blocks = set()
            for s in other_secs:
                if not s.get("is_blank"):
                    occupied_blocks.update(tuple(b) for b in s["minute_blocks"])

            d_sections = self.courses_dict.get(dest_code, [])

            if not (t_has_lab and d_has_lab):
                valid_sections = []
                for s in d_sections:
                    if t_code == dest_code and orig_sec and s["slots"] == orig_sec["slots"] and s["professor"] == orig_sec["professor"]:
                        continue
                    if occupied_blocks.isdisjoint(set(tuple(b) for b in s["minute_blocks"])):
                        valid_sections.append(s)

                if not valid_sections:
                    tk.Label(scroll_frame, text="⚠ No clash-free sections available for this assignment.", fg=self.danger, bg=self.bg, font=("Helvetica", 11, "italic")).pack(pady=20)
                    return

                for sec in valid_sections:
                    card = tk.Frame(scroll_frame, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
                    card.pack(fill="x", pady=4, padx=4)
                    
                    info_col = tk.Frame(card, bg=self.surface)
                    info_col.pack(side="left", padx=10, pady=8, fill="x", expand=True)
                    
                    info_text = f"Prof: {sec['professor']} | Slots: {sec['slots']} ({sec['tt_code']})"
                    timings = get_timings_for_slots(sec['slots'], self.slot_timing_map)
                    
                    tk.Label(info_col, text=info_text, font=("Helvetica", 11, "bold"), bg=self.surface, fg=self.text).pack(anchor="w")
                    tk.Label(info_col, text=f"Times: {timings}", font=("Helvetica", 10), fg=self.accent, bg=self.surface, wraplength=550, justify="left").pack(anchor="w", pady=(2, 0))
                    
                    self.btn(card, "Execute Batch Branch", lambda chosen_sec=sec: execute_structural_swap(t_code, dest_code, chosen_sec, t_lab_code if t_has_lab else None, None, None), "success").pack(side="right", padx=10)

            else:
                d_lab_sections = self.courses_dict.get(d_lab_code, [])
                orig_lab_sec = next((s for s in base_combo["sections"] if s["code"] == t_lab_code), None)
                valid_pairs = []

                for s_t in d_sections:
                    t_blocks = set(tuple(b) for b in s_t["minute_blocks"])
                    if not occupied_blocks.isdisjoint(t_blocks): continue

                    for s_l in d_lab_sections:
                        if s_t["professor"] != s_l["professor"]: continue

                        l_blocks = set(tuple(b) for b in s_l["minute_blocks"])
                        if not occupied_blocks.isdisjoint(l_blocks): continue
                        if not t_blocks.isdisjoint(l_blocks): continue

                        if t_code == dest_code:
                            if (orig_sec and s_t["slots"] == orig_sec["slots"] and s_t["professor"] == orig_sec["professor"]) and \
                               (orig_lab_sec and s_l["slots"] == orig_lab_sec["slots"] and s_l["professor"] == orig_lab_sec["professor"]):
                                continue

                        valid_pairs.append((s_t, s_l))
                
                if not valid_pairs:
                    tk.Label(scroll_frame, text="⚠ No clash-free Theory + Lab pair sequences available for the same Professor.", fg=self.danger, bg=self.bg, font=("Helvetica", 11, "italic")).pack(pady=20)
                    return

                for s_t, s_l in valid_pairs:
                    card = tk.Frame(scroll_frame, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
                    card.pack(fill="x", pady=4, padx=4)

                    info_col = tk.Frame(card, bg=self.surface)
                    info_col.pack(side="left", padx=10, pady=8, fill="x", expand=True)
                    
                    t_timings = get_timings_for_slots(s_t['slots'], self.slot_timing_map)
                    l_timings = get_timings_for_slots(s_l['slots'], self.slot_timing_map)

                    tk.Label(info_col, text=f"Theory: Prof {s_t['professor']} | Slots {s_t['slots']}", font=("Helvetica", 11, "bold"), fg=self.text, bg=self.surface).pack(anchor="w")
                    tk.Label(info_col, text=f"Times: {t_timings}", font=("Helvetica", 10), fg=self.accent, bg=self.surface, wraplength=550, justify="left").pack(anchor="w")
                    
                    tk.Label(info_col, text=f"Lab: Prof {s_l['professor']} | Slots {s_l['slots']}", font=("Helvetica", 11, "bold"), fg=self.text2, bg=self.surface).pack(anchor="w", pady=(6,0))
                    tk.Label(info_col, text=f"Times: {l_timings}", font=("Helvetica", 10), fg=self.accent, bg=self.surface, wraplength=550, justify="left").pack(anchor="w")

                    self.btn(card, "Execute Paired Branch", lambda ct=s_t, cl=s_l: execute_structural_swap(t_code, dest_code, ct, t_lab_code, d_lab_code, cl), "success").pack(side="right", padx=10)

        dest_cb.bind("<<ComboboxSelected>>", populate_sections)
        target_cb.bind("<<ComboboxSelected>>", populate_sections)
        populate_sections()

        def execute_structural_swap(t_code, d_code, new_sec_data, t_lab_code, d_lab_code, new_lab_sec_data):
            orig_sec = next((s for s in base_combo["sections"] if s["code"] == t_code), None)
            if not orig_sec: return
            
            orig_lab_sec = next((s for s in base_combo["sections"] if s["code"] == t_lab_code), None) if t_lab_code else None

            matched_combos = []
            for combo in self.plans["combos"]:
                match_sec = next((s for s in combo["sections"] if s["code"] == t_code), None)
                match_lab = next((s for s in combo["sections"] if s["code"] == t_lab_code), None) if t_lab_code else None
                
                if match_sec:
                    sec_match = (orig_sec.get("is_blank") and match_sec.get("is_blank")) or \
                                (match_sec["slots"] == orig_sec["slots"] and match_sec["professor"] == orig_sec["professor"])
                    
                    lab_match = True
                    if t_lab_code and orig_lab_sec and match_lab:
                        lab_match = (orig_lab_sec.get("is_blank") and match_lab.get("is_blank")) or \
                                    (match_lab["slots"] == orig_lab_sec["slots"] and match_lab["professor"] == orig_lab_sec["professor"])

                    if sec_match and lab_match:
                        matched_combos.append(combo)

            if not matched_combos: return
            
            confirm = messagebox.askyesno("Confirm Batch Operations", f"Found {len(matched_combos)} path configurations sharing this layer. Branch and implement structural changes?")
            if not confirm: return

            next_id = max([c["id"] for c in self.plans["combos"]], default=0) + 1
            
            for combo in matched_combos:
                branched = copy.deepcopy(combo)
                branched["id"] = next_id
                next_id += 1

                branched["picking_order"] = [d_code if x == t_code else (d_lab_code if x == t_lab_code else x) for x in branched["picking_order"]]
                
                if t_lab_code and not d_lab_code: 
                    branched["picking_order"] = [x for x in branched["picking_order"] if x != t_lab_code]
                    branched["sections"] = [x for x in branched["sections"] if x["code"] != t_lab_code]

                for idx, s in enumerate(branched["sections"]):
                    if s["code"] == t_code:
                        copied_target = copy.deepcopy(new_sec_data)
                        copied_target["is_blank"] = False
                        branched["sections"][idx] = copied_target
                    elif d_lab_code and s["code"] == t_lab_code:
                        copied_lab = copy.deepcopy(new_lab_sec_data)
                        copied_lab["is_blank"] = False
                        branched["sections"][idx] = copied_lab

                new_blocks = set(tuple(b) for b in new_sec_data["minute_blocks"])
                if new_lab_sec_data:
                    new_blocks.update(tuple(b) for b in new_lab_sec_data["minute_blocks"])

                clashing_leaf_codes = set()
                for s in branched["sections"]:
                    if s["code"] in (d_code, d_lab_code): continue
                    if not s.get("is_blank"):
                        s_blocks = set(tuple(b) for b in s["minute_blocks"])
                        if not new_blocks.isdisjoint(s_blocks):
                            clashing_leaf_codes.add(s["code"])

                if clashing_leaf_codes:
                    branched["picking_order"] = [c for c in branched["picking_order"] if c not in clashing_leaf_codes]
                    branched["sections"] = [s for s in branched["sections"] if s["code"] not in clashing_leaf_codes]

                self.plans["combos"].append(branched)

            self._commit_flat()
            messagebox.showinfo("Success", f"Generated {len(matched_combos)} branched internal path combinations effectively!")
            dlg.destroy()
            self.refresh_live_tree()

    # Stub implementations to structure full executable code
    def setup_build_tab(self):
        hdr = tk.Frame(self.tab_build, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Create New Plan", font=("Helvetica", 16, "bold"), fg=self.text, bg=self.surface).pack(side="left", padx=20, pady=12)

        body = tk.Frame(self.tab_build, bg=self.bg)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        
        self.build_controls = tk.Frame(body, bg=self.bg)
        self.build_controls.pack(fill="x", pady=(0, 10))

        tk.Label(self.build_controls, text="Select Course:", font=("Helvetica", 11, "bold"), fg=self.text, bg=self.bg).pack(side="left")
        
        display_vals = [f"{c} — {self.courses_dict[c][0]['name']}" for c in self.courses_dict.keys()]
        self.build_cb = ttk.Combobox(self.build_controls, values=display_vals, state="readonly", width=45)
        self.build_cb.pack(side="left", padx=10)
        if display_vals: self.build_cb.set(display_vals[0])

        self.btn(self.build_controls, "+ Add Blank Slot", self.build_add_course, "success").pack(side="left")
        self.btn(self.build_controls, " Save Plan", self.build_save_plan, "primary").pack(side="right")

        _, self.build_scroll_frame, _ = self.scrollable(body)
        self.new_plan_picking_order = []
        self.new_plan_sections = []

    def build_add_course(self):
        val = self.build_cb.get()
        if not val: return
        code = val.split(" — ")[0].strip()
        
        if code in self.new_plan_picking_order:
            messagebox.showwarning("Warning", "Course already added to this plan.")
            return
            
        course_name = self.courses_dict[code][0]["name"]
        
        self.new_plan_picking_order.append(code)
        self.new_plan_sections.append({
            "code": code, "name": course_name, "slots": "—",
            "tt_code": "—", "professor": "—", "type": "—", "minute_blocks": [], "is_blank": True
        })
        self.refresh_build_list()

    def build_remove_course(self, code):
        self.new_plan_picking_order = [c for c in self.new_plan_picking_order if c != code]
        self.new_plan_sections = [s for s in self.new_plan_sections if s["code"] != code]
        self.refresh_build_list()

    def refresh_build_list(self):
        for w in self.build_scroll_frame.winfo_children(): w.destroy()
        
        for idx, code in enumerate(self.new_plan_picking_order):
            sec = next(s for s in self.new_plan_sections if s["code"] == code)
            
            card = tk.Frame(self.build_scroll_frame, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
            card.pack(fill="x", pady=4, padx=4)
            
            lbl = tk.Label(card, text=f"{idx+1}. {code} — {sec.get('name', '')} [BLANK]", font=("Helvetica", 11, "bold"), bg=self.surface, fg=self.text)
            lbl.pack(side="left", padx=10, pady=10)
            
            self.btn(card, " Remove", lambda c=code: self.build_remove_course(c), "danger").pack(side="right", padx=10, pady=10)

    def build_save_plan(self):
        if not self.new_plan_picking_order:
            messagebox.showerror("Error", "Plan must have at least one course.")
            return
        by_code = {s["code"]: s for s in self.new_plan_sections}
        secs = [copy.deepcopy(by_code[c]) for c in self.new_plan_picking_order]
        if not self.tree.insert_path_cow(secs):
            messagebox.showinfo("Already Exists", "An identical plan already exists.")
            return
        self.tree.recount()
        self._mark_dirty()
        messagebox.showinfo("Success", "Plan saved. You can modify / branch it from the Live Tracker tab.")
        self.reset_builder_wizard()

    def reset_builder_wizard(self):
        self.new_plan_picking_order = []
        self.new_plan_sections = []
        if hasattr(self, 'build_scroll_frame'):
            self.refresh_build_list()
    
    # ==========================================================================
    # FLOW PLANNING TAB
    # ==========================================================================
    def setup_flow_tab(self):
        self.flow_skips = []             # parallel to flow_stages: True = 'skip allowed' for that stage
        self.flow_stages = []            # each stage: [code] (single) or [code, code, ...] (pick exactly one)
        self._flow_rows = []             # listbox line -> stage index
        self._flow_cache = None          # (key, tree, leaves, dead, alive)
        self.flow_info_var = tk.StringVar()

        hdr = tk.Frame(self.tab_flow, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Flow Planning", font=("Helvetica", 16, "bold"),
                 fg=self.text, bg=self.surface).pack(side="left", padx=20, pady=12)

        body = tk.Frame(self.tab_flow, bg=self.bg)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(body,
                 text=("Add stages in the order you want to pick them. A stage is either ONE course, or a GROUP "
                       "of 2+ courses of which you pick exactly one (courses in a group may clash with each other; "
                       "only the one you end up choosing has to fit).\n"
                       "A course that has a lab in CourseList.csv is automatically joined to it: the lab is picked "
                       "right after the course, with the same professor. Courses without a lab stand alone.\n"
                       "Select a stage and press 'Toggle Skip Allowed' to add a 'skip this stage' option (for when no "
                       "professor is available); later stages are then checked only against what you really picked.\n"
                       "Creating the tree generates EVERY clash-free combination. You can then reorder / prune it "
                       "in the Live Tracker."),
                 font=("Helvetica", 11), fg=self.text2, bg=self.bg, justify="left", wraplength=1050
                 ).pack(anchor="w", pady=(0, 10))

        add_row = tk.Frame(body, bg=self.bg)
        add_row.pack(fill="x", pady=(0, 10))
        tk.Label(add_row, text="Next course:", font=("Helvetica", 11, "bold"),
                 fg=self.text, bg=self.bg).pack(side="left")
        self.flow_cb = ttk.Combobox(add_row, values=[], state="readonly", width=52)
        self.flow_cb.pack(side="left", padx=10)
        self.btn(add_row, "+ Add as Single Stage", self.flow_add, "success").pack(side="left")
        self.btn(add_row, "+ Add Group (pick one)...", self.flow_add_group, "purple").pack(side="left", padx=10)

        mid = tk.Frame(body, bg=self.bg)
        mid.pack(fill="x")
        self.flow_lb = tk.Listbox(mid, font=("Helvetica", 11, "bold"), height=14, width=84,
                                  bg=self.surface, fg=self.text, selectbackground=self.accent_lt,
                                  selectforeground=self.text, highlightbackground=self.border,
                                  highlightthickness=1, relief="flat", activestyle="none",
                                  exportselection=False)
        self.flow_lb.pack(side="left", padx=(0, 8))
        side = tk.Frame(mid, bg=self.bg)
        side.pack(side="left", fill="y")
        self.btn(side, "▲ Move Up", lambda: self.flow_move(-1), "muted").pack(fill="x", pady=2)
        self.btn(side, "▼ Move Down", lambda: self.flow_move(1), "muted").pack(fill="x", pady=2)
        self.btn(side, "Toggle Skip Allowed", self.flow_toggle_skip, "purple").pack(fill="x", pady=(10, 2))
        self.btn(side, "Remove Stage", self.flow_remove, "danger").pack(fill="x", pady=2)
        self.btn(side, "Clear Flow", self.flow_clear, "muted").pack(fill="x", pady=2)

        tk.Label(body, textvariable=self.flow_info_var, font=("Helvetica", 11), fg=self.text,
                 bg=self.bg, justify="left", anchor="w", wraplength=1050).pack(fill="x", pady=(12, 8))

        act = tk.Frame(body, bg=self.bg)
        act.pack(fill="x")
        self.btn(act, "Preview Tree Size", self.flow_preview, "primary").pack(side="left")
        self.btn(act, "Create Full Tree  (overwrites existing plans)", self.flow_create,
                 "danger").pack(side="left", padx=12)

        self._flow_changed()

    # ── flow helpers ─────────────────────────────────────────────────────────
    def _course_label(self, code):
        has_lab = split_course(code, self.courses_dict)[1] is not None
        suffix = "  (+ lab)" if has_lab else ""
        return f"{code} — {self.courses_dict[code][0]['name']}{suffix}"

    def _stage_short(self, stage):
        return stage[0] if len(stage) == 1 else "(" + " | ".join(stage) + ")"

    def _flow_available(self):
        """Courses that can still be added. Labs whose theory course exists in the CSV are added
        automatically together with that course, so they are not offered on their own."""
        used = {c for st in self.flow_stages for c in st}
        out = []
        for c in self.courses_dict:
            if c in used:
                continue
            th = get_theory_code(c)
            if th and th in self.courses_dict:
                continue
            out.append(c)
        return out

    def _flow_refresh_choices(self):
        vals = [self._course_label(c) for c in self._flow_available()]
        self.flow_cb.configure(values=vals)
        self.flow_cb.set(vals[0] if vals else "")

    def _flow_changed(self):
        self._flow_cache = None
        self.flow_lb.delete(0, tk.END)
        self._flow_rows = []
        for i, st in enumerate(self.flow_stages):
            tag = "     [skip allowed]" if self.flow_skips[i] else ""
            if len(st) == 1:
                self.flow_lb.insert(tk.END, f"  {i + 1}.  {self._course_label(st[0])}{tag}")
                self._flow_rows.append(i)
            else:
                self.flow_lb.insert(tk.END, f"  {i + 1}.  PICK ONE OF {len(st)}:{tag}")
                self._flow_rows.append(i)
                for c in st:
                    self.flow_lb.insert(tk.END, f"            •  {self._course_label(c)}")
                    self._flow_rows.append(i)
        self._flow_refresh_choices()
        if self.flow_stages:
            self.flow_info_var.set("Click 'Preview Tree Size' to see how many plans this order produces.")
        else:
            self.flow_info_var.set("Flow is empty. Add the first stage you plan to pick.")

    def _flow_selected_stage(self):
        sel = self.flow_lb.curselection()
        if not sel or sel[0] >= len(self._flow_rows):
            return None
        return self._flow_rows[sel[0]]

    def flow_add(self):
        val = self.flow_cb.get()
        if not val:
            return
        code = val.split(" — ")[0].strip()
        if any(code in st for st in self.flow_stages):
            return
        self.flow_stages.append([code])
        self.flow_skips.append(False)
        self._flow_changed()

    def flow_add_group(self):
        avail = self._flow_available()
        if len(avail) < 2:
            messagebox.showinfo("Not enough courses", "At least two unused courses are needed to make a group.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Add Group — pick exactly one")
        dlg.geometry("720x520")
        dlg.configure(bg=self.bg)
        dlg.grab_set()
        tk.Label(dlg, text="Select 2 or more courses (Ctrl/Shift-click).\nExactly one of them will be picked at this stage.",
                 font=("Helvetica", 11), fg=self.text, bg=self.bg, justify="left").pack(anchor="w", padx=16, pady=(14, 8))
        lbf = tk.Frame(dlg, bg=self.bg)
        lbf.pack(fill="both", expand=True, padx=16)
        sb = ttk.Scrollbar(lbf, orient="vertical")
        lb = tk.Listbox(lbf, selectmode=tk.EXTENDED, font=("Helvetica", 11), exportselection=False,
                        yscrollcommand=sb.set, bg=self.surface, fg=self.text,
                        selectbackground=self.accent_lt, selectforeground=self.text,
                        highlightbackground=self.border, highlightthickness=1, relief="flat")
        sb.config(command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)
        for c in avail:
            lb.insert(tk.END, self._course_label(c))

        def _ok():
            picked = [avail[i] for i in lb.curselection()]
            if len(picked) < 2:
                messagebox.showwarning("Pick at least two", "A group needs 2 or more courses.", parent=dlg)
                return
            dlg.destroy()
            self.flow_stages.append(picked)
            self.flow_skips.append(False)
            self._flow_changed()

        row = tk.Frame(dlg, bg=self.bg)
        row.pack(fill="x", padx=16, pady=12)
        self.btn(row, "Add Group", _ok, "success").pack(side="right")
        self.btn(row, "Cancel", dlg.destroy, "muted").pack(side="right", padx=8)

    def flow_move(self, direction):
        i = self._flow_selected_stage()
        if i is None:
            return
        j = i + direction
        if 0 <= j < len(self.flow_stages):
            self.flow_stages[i], self.flow_stages[j] = self.flow_stages[j], self.flow_stages[i]
            self.flow_skips[i], self.flow_skips[j] = self.flow_skips[j], self.flow_skips[i]
            self._flow_changed()
            self.flow_lb.selection_set(self._flow_rows.index(j))

    def flow_remove(self):
        i = self._flow_selected_stage()
        if i is None:
            return
        del self.flow_stages[i]
        del self.flow_skips[i]
        self._flow_changed()

    def flow_toggle_skip(self):
        i = self._flow_selected_stage()
        if i is None:
            messagebox.showinfo("Select a stage", "Click a stage in the list first.")
            return
        self.flow_skips[i] = not self.flow_skips[i]
        self._flow_changed()
        self.flow_lb.selection_set(self._flow_rows.index(i))

    def flow_clear(self):
        self.flow_stages = []
        self.flow_skips = []
        self._flow_changed()

    def _flow_progress(self, n):
        self.flow_info_var.set(f"Working…  {n:,} steps so far")
        self.root.update_idletasks()

    def _flow_stats(self):
        """(tree, plan_count, dead_ends, alive_per_stage) for the current flow; cached until it changes."""
        key = (tuple(tuple(st) for st in self.flow_stages), tuple(self.flow_skips))
        if self._flow_cache and self._flow_cache[0] == key:
            return self._flow_cache[1:]
        self.root.config(cursor="watch")
        self.flow_info_var.set("Building…")
        self.root.update_idletasks()
        try:
            tree, leaves, dead, alive = build_flow_tree([list(st) for st in key[0]], self.courses_dict,
                                                        progress=self._flow_progress, skips=list(key[1]))
        finally:
            self.root.config(cursor="")
        self._flow_cache = (key, tree, leaves, dead, alive)
        return tree, leaves, dead, alive

    def _flow_summary(self, leaves, dead, alive):
        lines = [f"Complete clash-free plans: {leaves:,}     Dead-end paths removed: {dead:,}",
                 f"Existing plans that would be overwritten: {self.tree.total():,}",
                 "Valid partial paths after each stage:  " +
                 "   ".join(f"{i}. {self._stage_short(st)}{'*' if self.flow_skips[i - 1] else ''} → {alive[i]:,}"
                             for i, st in enumerate(self.flow_stages, 1))]
        if any(self.flow_skips):
            lines.append("* = skip allowed at this stage")
        return "\n".join(lines)

    def flow_preview(self):
        if not self.flow_stages:
            messagebox.showinfo("Empty Flow", "Add at least one stage to the flow first.")
            return
        _, leaves, dead, alive = self._flow_stats()
        text = self._flow_summary(leaves, dead, alive)
        if leaves == 0:
            text += "\nNo complete clash-free plan exists for this order. Check where the path counts drop to 0."
        self.flow_info_var.set(text)

    def flow_create(self):
        if not self.flow_stages:
            messagebox.showinfo("Empty Flow", "Add at least one stage to the flow first.")
            return
        new_tree, leaves, dead, alive = self._flow_stats()
        self.flow_info_var.set(self._flow_summary(leaves, dead, alive))
        if leaves == 0:
            messagebox.showerror("Nothing to create",
                                 "No complete clash-free plan exists for this order, so nothing was changed.")
            return

        existing = self.tree.total()
        path_str = " > ".join(self._stage_short(st) + ("*" if sk else "")
                              for st, sk in zip(self.flow_stages, self.flow_skips))
        msg1 = (f"This will REPLACE all {existing:,} existing plan(s) with {leaves:,} newly generated "
                f"plan(s) for:\n\n  {path_str}\n\n"
                f"A backup of the current file will be saved first. Continue?")
        if not messagebox.askyesno("Create Full Tree - Step 1 of 2", msg1, icon="warning"):
            return
        msg2 = ("Are you absolutely sure?\n\nEverything currently in the Live Tracker will be overwritten "
                f"by {leaves:,} generated plans. (Backup file: {BACKUP_FILE})")
        if not messagebox.askyesno("Create Full Tree - Step 2 of 2 (Final Confirmation)", msg2,
                                   icon="warning", default="no"):
            return

        self._flush_save(wait=True)
        if os.path.exists(PLANS_FILE):
            try:
                shutil.copy2(PLANS_FILE, BACKUP_FILE)
            except OSError as e:
                messagebox.showerror("Backup failed", f"Could not write the backup, nothing was changed.\n\n{e}")
                return

        self.root.config(cursor="watch")
        try:
            self.flow_info_var.set("Saving…")
            self.root.update_idletasks()
            self.tree = new_tree
            save_tree(self.tree)
            self._dirty = False
            self._gc_settle()
        finally:
            self.root.config(cursor="")

        self._flow_cache = None
        self.flow_info_var.set(f"Done. {leaves:,} plans created.")
        messagebox.showinfo("Tree Created",
                            f"Created {leaves:,} plans.\nPrevious data was backed up to {BACKUP_FILE}.")
        self.initialize_live_mode()
        self.notebook.select(self.tab_live)


if __name__ == "__main__":
    root = tk.Tk()
    app = MasterCounsellingApp(root)
    if app.ok:
        root.mainloop()

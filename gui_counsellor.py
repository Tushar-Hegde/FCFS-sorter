import csv
import os
import json
import tkinter as tk
from tkinter import messagebox, ttk
import copy
import shutil

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
                "minute_blocks": list(section_minutes)
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

def load_plans(filename="plans_optimized.json", courses_dict=None):
    if not os.path.exists(filename):
        # fall back to legacy plans.json once, then migrate
        if os.path.exists("plans.json"):
            with open("plans.json", encoding="utf-8") as f:
                try:
                    fat = json.load(f)
                except json.JSONDecodeError:
                    return {"combos": []}
            # migrate and save optimized
            slim_combos = []
            for c in fat.get("combos", []):
                slim_combos.append({
                    "id": c["id"],
                    "order": c["picking_order"],
                    "secs": {s["code"]: _slim_sec(s) for s in c["sections"]}
                })
            out = {"combos": slim_combos}
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)
            # fatten and return
            cd = courses_dict or {}
            return _fatten_plans(out, cd)
        return {"combos": []}
    with open(filename, encoding="utf-8") as f:
        try:
            slim = json.load(f)
        except json.JSONDecodeError:
            return {"combos": []}
    return _fatten_plans(slim, courses_dict or {})

PLANS_FILE = "plans_optimized.json"
BACKUP_FILE = "plans_optimized.backup.json"
CSV_FILE = "CourseList.csv"
LIVE_ORDERS_FILE = "live_orders.json"      # per-node option ordering (small, saved on its own)

def _fatten_plans(slim, courses_dict):
    # Identical (course, professor, slots) sections share ONE dict, so tens of thousands
    # of plans load quickly and use little memory.
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
        sections = [get(code, secs.get(code)) for code in order]
        combos.append({"id": c["id"], "picking_order": order, "sections": sections})
    out = {"combos": combos}
    if slim.get("live_orders"):
        out["live_orders"] = slim["live_orders"]
    return out

def save_plans(plans, filename=PLANS_FILE):
    slim_combos = []
    for c in plans.get("combos", []):
        slim_combos.append({
            "id": c["id"],
            "order": c["picking_order"],
            "secs": {s["code"]: _slim_sec(s) for s in c["sections"]}
        })
    out = {"combos": slim_combos}
    with open(filename, "w", encoding="utf-8") as f:
        if len(slim_combos) > 2000:
            json.dump(out, f, separators=(",", ":"))   # compact for big generated trees
        else:
            json.dump(out, f, indent=2)

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

def walk_flow(flow, courses_dict, on_leaf=None, progress=None):
    """
    Depth-first walk of the full selection tree for `flow` (a list of course codes in the
    order they will be picked).  Rules applied at every node:
      * the section must not clash with anything already chosen above it
      * a theory course and its lab (XXXXL / XXXXP) must be taught by the same professor,
        whichever of the two is picked first
    Only complete paths (every course in the flow placed) are leaves; dead ends are pruned.
    Returns (leaf_count, dead_end_count, alive_per_depth).
    alive_per_depth[d] = number of valid partial paths after d courses.
    """
    n = len(flow)
    options = []
    for code in flow:
        seen, lst = set(), []
        for s in courses_dict.get(code, []):
            key = (s["professor"], s["slots"])
            if key in seen:
                continue
            seen.add(key)
            lst.append((dict(s, is_blank=False), section_mask(s["minute_blocks"])))
        options.append(lst)

    partner_idx = []
    for code in flow:
        p = get_lab_code(code) or get_theory_code(code)
        partner_idx.append(flow.index(p) if p in flow else -1)

    alive = [0] * (n + 1)
    alive[0] = 1
    state = {"leaves": 0, "dead": 0}
    chosen = [None] * n

    def rec(d, occ):
        if d == n:
            state["leaves"] += 1
            if on_leaf:
                on_leaf(chosen)
            if progress and state["leaves"] % 2000 == 0:
                progress(state["leaves"])
            return
        pi = partner_idx[d]
        need_prof = chosen[pi]["professor"] if pi >= 0 and chosen[pi] is not None else None
        found = False
        for fat, mask in options[d]:
            if mask & occ:
                continue
            if need_prof is not None and fat["professor"] != need_prof:
                continue
            found = True
            chosen[d] = fat
            alive[d + 1] += 1
            rec(d + 1, occ | mask)
        chosen[d] = None
        if not found:
            state["dead"] += 1

    rec(0, 0)
    return state["leaves"], state["dead"], alive


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
        self.plans = load_plans(PLANS_FILE, self.courses_dict)
        orders = load_live_orders()
        if not orders and self.plans.get("live_orders"):      # one-time migration
            orders = self.plans["live_orders"]
            save_live_orders(orders)
        self.plans["live_orders"] = orders
        self.slot_timing_map = generate_slot_timing_map()
        self.slot_map = generate_minute_slot_mappings()
        self._scroll_canvases = set()

        if not self.courses_dict:
            messagebox.showerror("Missing Data", "CourseList.csv not found or is empty.")
            self.root.destroy()
            return

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
        self.initialize_live_mode()
        self.ok = True

    def on_tab_changed(self, event):
        t = self.notebook.index(self.notebook.select())
        if t == 0:
            # Keep the current locked path if it is still valid, otherwise start over
            if self.live_locked_sections and not self._live_get_valid_combos():
                self.live_locked_sections = []
                self.live_preview_sig = None
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
    def setup_live_tab(self):
        self.live_locked_sections = []
        self.live_option_order = []      # user-defined display order (list of sigs)
        self.live_preview_sig = None     # option currently highlighted / previewed
        self._live_options_tally = {}
        self._live_cards = {}

        top = tk.Frame(self.tab_live, bg=self.surface,
                       highlightbackground=self.border, highlightthickness=1)
        top.pack(fill="x")
        tk.Label(top, text="Live Course Selection Tracker",
                 font=("Helvetica", 16, "bold"), fg=self.text, bg=self.surface
                 ).pack(side="left", padx=20, pady=10)
        self.btn(top, "Reset Tracker", self.initialize_live_mode, "danger").pack(side="right", padx=(6, 16), pady=8)
        self.btn(top, "< Go Back", self.live_handle_back, "warn").pack(side="right", padx=6, pady=8)
        self.btn(top, "Remove Duplicates", self.remove_duplicates, "muted").pack(side="right", padx=6, pady=8)

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

    def initialize_live_mode(self):
        self.live_locked_sections = []
        self.live_option_order = []
        self.live_preview_sig = None
        self.refresh_live_tree()

    def live_handle_back(self):
        if self.live_locked_sections:
            self.live_locked_sections.pop()
            self.live_option_order = []
            self.live_preview_sig = None
            self.refresh_live_tree()

    def _live_get_valid_combos(self):
        valid_combos = []
        for combo in self.plans.get("combos", []):
            is_valid = True
            for locked_sec in self.live_locked_sections:
                match = next((s for s in combo["sections"] if s["code"] == locked_sec["code"]), None)
                if not match or match.get("is_blank", False) != locked_sec.get("is_blank", False):
                    is_valid = False; break
                if not match.get("is_blank"):
                    if match["professor"] != locked_sec["professor"] or match["slots"] != locked_sec["slots"]:
                        is_valid = False; break
            if is_valid:
                valid_combos.append(combo)
        return valid_combos

    def refresh_live_tree(self, keep_scroll=False):
        y = self.live_canvas.yview()[0] if keep_scroll else 0.0
        self._refresh_live_tree_inner()
        self._live_draw_timetable()
        self.root.update_idletasks()
        self.live_canvas.yview_moveto(y)

    def _refresh_live_tree_inner(self):
        for w in self.live_scroll_frame.winfo_children(): w.destroy()
        self._live_cards = {}
        self._live_options_tally = {}
        valid_combos = self._live_get_valid_combos()

        if self.live_locked_sections:
            path_frame = tk.LabelFrame(self.live_scroll_frame, text=" Locked Path ",
                                       font=("Helvetica", 11, "bold"), fg=self.success, bg=self.bg)
            path_frame.pack(fill="x", padx=12, pady=(10, 16))
            for i, sec in enumerate(self.live_locked_sections, 1):
                prof_slot = "BLANK" if sec.get("is_blank") else f"{sec['professor']} - {sec['slots']}"
                tk.Label(path_frame, text=f"{i}. {sec['code']} ({prof_slot})",
                         font=("Helvetica", 10), fg=self.text, bg=self.bg).pack(anchor="w", padx=10, pady=2)
        else:
            tk.Label(self.live_scroll_frame,
                     text="Select your first course to begin tracking.",
                     font=("Helvetica", 11, "italic"), fg=self.text2, bg=self.bg).pack(pady=(14, 10), anchor="w", padx=12)

        if not valid_combos:
            tk.Label(self.live_scroll_frame, text="No saved combinations match this path.",
                     font=("Helvetica", 11), fg=self.danger, bg=self.bg).pack(pady=20)
            self._render_live_add_new_row()
            return

        options_tally = {}
        locked_codes = {s["code"] for s in self.live_locked_sections}
        for combo in valid_combos:
            next_code = next((code for code in combo["picking_order"] if code not in locked_codes), None)
            if next_code:
                sec = next((s for s in combo["sections"] if s["code"] == next_code), None)
                if sec:
                    sig = (sec["code"], sec.get("professor", "—"), sec.get("slots", "—"))
                    if sig not in options_tally:
                        options_tally[sig] = {"sec_data": sec, "weight": 0}
                    options_tally[sig]["weight"] += 1

        self._live_options_tally = options_tally

        if not options_tally and self.live_locked_sections:
            tk.Label(self.live_scroll_frame,
                     text="Path Complete! All courses in this combination are locked.",
                     font=("Helvetica", 12, "bold"), fg=self.success, bg=self.bg).pack(pady=30)
            self._render_live_add_new_row()
            return

        if self.live_preview_sig not in options_tally:
            self.live_preview_sig = None

        self.live_option_order = self._live_load_order(options_tally)

        tk.Label(self.live_scroll_frame, text="Next Available Options:",
                 font=("Helvetica", 12, "bold"), fg=self.text, bg=self.bg).pack(anchor="w", padx=12, pady=(0, 2))
        tk.Label(self.live_scroll_frame, text="Click an option to highlight it and preview it on the timetable.",
                 font=("Helvetica", 10, "italic"), fg=self.text2, bg=self.bg).pack(anchor="w", padx=12, pady=(0, 8))

        for idx, sig in enumerate(self.live_option_order):
            opt_data = options_tally[sig]
            opt = opt_data["sec_data"]
            weight = opt_data["weight"]
            timings = get_timings_for_slots(opt["slots"], self.slot_timing_map) if not opt.get("is_blank") else "—"

            card = tk.Frame(self.live_scroll_frame, bg=self.surface,
                            highlightbackground=self.border, highlightthickness=1)
            card.pack(fill="x", pady=4, padx=12)
            self._live_cards[sig] = card

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
            self.btn(right_col, "Secure", lambda t=opt: self.live_handle_select(t), "success").pack()
            self.btn(right_col, "Branch", lambda t=opt: self.live_structural_branch(t), "purple").pack(pady=(6, 0))
            self.btn(right_col, "Delete Branch", lambda t=opt: self.live_delete_branch(t), "danger").pack(pady=(6, 0))
            arrow_row = tk.Frame(right_col, bg=self.surface)
            arrow_row.pack(pady=(6, 0))
            self.btn(arrow_row, "^", lambda i=idx: self._live_move_option(i, -1), "muted").pack(side="left", padx=2)
            self.btn(arrow_row, "v", lambda i=idx: self._live_move_option(i, 1), "muted").pack(side="left", padx=2)

            self._bind_click(card, lambda e, s=sig: self._live_toggle_preview(s))

        if self.live_preview_sig is not None:
            self._live_style_card(self.live_preview_sig, True)

        self._render_live_add_new_row()

    # ── option highlight / preview ──────────────────────────────────────────
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

    def _live_style_card(self, sig, selected):
        card = self._live_cards.get(sig)
        if card is None:
            return
        old, new = (self.surface, self.HL) if selected else (self.HL, self.surface)
        card.configure(bg=new,
                       highlightbackground=self.accent if selected else self.border,
                       highlightthickness=3 if selected else 1)
        self._recolor(card, old, new)

    def _live_toggle_preview(self, sig):
        if self.live_preview_sig is not None:
            self._live_style_card(self.live_preview_sig, False)
        if self.live_preview_sig == sig:
            self.live_preview_sig = None
        else:
            self.live_preview_sig = sig
            self._live_style_card(sig, True)
        self._live_draw_timetable()

    # ── weekly timetable ────────────────────────────────────────────────────
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
        for idx, sec in enumerate(self.live_locked_sections):
            fill, outline = self.PALETTE[idx % len(self.PALETTE)]
            if sec.get("is_blank"):
                legend.append((fill, outline, None, f"{sec['code']} (blank)"))
                continue
            draw_sec(sec, fill, outline)
            legend.append((fill, outline, None, f"{sec['code']} · {sec['slots']}"))

        prev = self._live_options_tally.get(self.live_preview_sig) if self.live_preview_sig else None
        if prev:
            psec = prev["sec_data"]
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

    def _render_live_add_new_row(self):
        add_frame = tk.Frame(self.live_scroll_frame, bg=self.surface2,
                             highlightbackground=self.border, highlightthickness=1)
        add_frame.pack(fill="x", pady=6, padx=12)
        tk.Label(add_frame, text="Add New Option:", font=("Helvetica", 11, "bold"),
                 fg=self.text, bg=self.surface2).pack(side="left", padx=10, pady=10)

        locked_codes = {s["code"] for s in self.live_locked_sections}

        # Only factor: does the course have at least one section whose timing
        # doesn't clash with anything already locked above it in the tree?
        # Whether the course is already picked elsewhere is irrelevant.
        occupied_blocks = set()
        for s in self.live_locked_sections:
            if not s.get("is_blank"):
                occupied_blocks.update(tuple(b) for b in s["minute_blocks"])

        available = []
        for c in sorted(self.courses_dict.keys()):
            secs = self.courses_dict[c]
            if any(occupied_blocks.isdisjoint(set(tuple(b) for b in s["minute_blocks"])) for s in secs):
                available.append(c)
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
            course_code = val.split(" — ")[0].strip()
            self._open_live_section_picker(course_code)

        self.btn(add_frame, "+ Add", _do_add, "primary").pack(side="left", pady=10)

    def _open_live_section_picker(self, course_code):
        """Dialog to pick a specific section (or blank) before adding to the live tree."""
        sections = self.courses_dict.get(course_code, [])
        occupied_blocks = set()
        for s in self.live_locked_sections:
            if not s.get("is_blank"):
                occupied_blocks.update(tuple(b) for b in s["minute_blocks"])
        sections = [s for s in sections
                    if occupied_blocks.isdisjoint(set(tuple(b) for b in s["minute_blocks"]))]
        course_name = self.courses_dict.get(course_code, [{}])[0].get("name", course_code) if self.courses_dict.get(course_code) else course_code

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

        # Blank option first
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

    def _live_path_key(self):
        """Stable string key for the current locked path, used to persist option order."""
        return "|".join(
            f"{s['code']}:{s.get('professor','')},{s.get('slots','')}"
            for s in self.live_locked_sections
        )

    def _live_load_order(self, options_tally):
        """Load saved option order for current path, merging with live options."""
        key = self._live_path_key()
        saved = self.plans.get("live_orders", {}).get(key, [])
        # saved is list of sigs (stored as lists in JSON, convert to tuples)
        saved_tuples = [tuple(s) for s in saved]
        # keep only sigs still valid, append any new ones at end
        merged = [s for s in saved_tuples if s in options_tally]
        for sig in options_tally:
            if sig not in merged:
                merged.append(sig)
        return merged

    def _live_save_order(self):
        """Persist current live_option_order for this path into plans."""
        key = self._live_path_key()
        if "live_orders" not in self.plans:
            self.plans["live_orders"] = {}
        # Store sigs as lists (JSON-serializable)
        self.plans["live_orders"][key] = [list(s) for s in self.live_option_order]
        save_live_orders(self.plans["live_orders"])

    def _live_move_option(self, idx, direction):
        new_idx = idx + direction
        if 0 <= new_idx < len(self.live_option_order):
            self.live_option_order[idx], self.live_option_order[new_idx] = \
                self.live_option_order[new_idx], self.live_option_order[idx]
            self._live_save_order()
            self.refresh_live_tree(keep_scroll=True)

    def _live_add_new_option(self, new_code, sec_data=None):
        """
        Add new_code as the next step after the current locked path.
        sec_data: a section dict from courses_dict, or None for blank.
        Strategy: always create a NEW combo = locked path sections + new_code.
        This avoids inheriting unrelated courses from existing combos.
        If an identical combo already exists, we skip creation.
        """
        locked_codes_list = [s["code"] for s in self.live_locked_sections]

        if sec_data is None:
            course_name = self.courses_dict[new_code][0]["name"] if new_code in self.courses_dict else new_code
            new_sec = {
                "code": new_code, "name": course_name, "slots": "—",
                "tt_code": "—", "professor": "—", "type": "—", "minute_blocks": [], "is_blank": True
            }
        else:
            new_sec = copy.deepcopy(sec_data)
            new_sec["is_blank"] = False

        new_order = locked_codes_list + [new_code]
        new_sections = copy.deepcopy(self.live_locked_sections) + [new_sec]

        # Check if an identical combo already exists (same order + same section sigs)
        def _sig(s):
            return (s["code"], s.get("professor", ""), s.get("slots", ""), s.get("is_blank", False))

        new_sigs = tuple(_sig(s) for s in new_sections)
        for combo in self.plans.get("combos", []):
            if combo["picking_order"] == new_order:
                existing_sigs = tuple(_sig(s) for s in combo["sections"]
                                      if s["code"] in new_order)
                if existing_sigs == new_sigs:
                    messagebox.showinfo("Already Exists",
                                        f"A combination with this exact path already exists.")
                    return

        new_id = max([c["id"] for c in self.plans.get("combos", [])], default=0) + 1
        self.plans.setdefault("combos", []).append(
            {"id": new_id, "picking_order": new_order, "sections": new_sections})
        save_plans(self.plans)

        prof = new_sec.get("professor", "—") if not new_sec.get("is_blank") else "—"
        slots = new_sec.get("slots", "—") if not new_sec.get("is_blank") else "—"
        sig = (new_code, prof, slots)
        if sig not in self.live_option_order:
            self.live_option_order.append(sig)
        self._live_save_order()
        self.refresh_live_tree()

    def live_handle_select(self, sec):
        self.live_locked_sections.append(sec)
        self.live_option_order = []
        self.live_preview_sig = None
        self.refresh_live_tree()

    def live_structural_branch(self, sec):
        # Branch from a saved plan that is actually on the CURRENT path and uses this option
        for combo in self._live_get_valid_combos():
            m = next((s for s in combo["sections"] if s["code"] == sec["code"]), None)
            if not m:
                continue
            if sec.get("is_blank"):
                same = bool(m.get("is_blank"))
            else:
                same = (not m.get("is_blank") and m["professor"] == sec["professor"]
                        and m["slots"] == sec["slots"])
            if same:
                self.open_structural_batch_dialog(combo["id"], preselect_code=sec["code"])
                return
        messagebox.showerror("Error", "No saved combination containing this configuration to branch from.")

    def live_delete_branch(self, sec):
        locked_codes_set = {s["code"] for s in self.live_locked_sections}
        valid_combos = self._live_get_valid_combos()

        to_delete = []
        for combo in valid_combos:
            remaining = [c for c in combo["picking_order"] if c not in locked_codes_set]
            if not remaining or remaining[0] != sec["code"]:
                continue
            match_sec = next((s for s in combo["sections"] if s["code"] == sec["code"]), None)
            if not match_sec:
                continue
            if sec.get("is_blank"):
                if match_sec.get("is_blank"):
                    to_delete.append(combo)
            else:
                if (not match_sec.get("is_blank") and
                        match_sec.get("professor") == sec.get("professor") and
                        match_sec.get("slots") == sec.get("slots")):
                    to_delete.append(combo)

        if not to_delete:
            messagebox.showinfo("Nothing to delete", "No combinations found for this branch.")
            return

        parts = [s["code"] for s in self.live_locked_sections] + [sec["code"]]
        path_str = " > ".join(parts)
        ids_str = ", ".join(str(c["id"]) for c in to_delete)

        msg1 = ("This will permanently delete %d combination(s) rooted at:\n\n"
                "  %s\n\nAll downstream leaves will also be removed. Continue?") % (len(to_delete), path_str)
        if not messagebox.askyesno("Delete Branch - Step 1 of 2", msg1):
            return

        msg2 = ("Are you absolutely sure?\n\n"
                "Combination ID(s) to be deleted: %s\n\nThis cannot be undone.") % ids_str
        if not messagebox.askyesno("Delete Branch - Step 2 of 2 (Final Confirmation)", msg2):
            return

        delete_ids = {c["id"] for c in to_delete}
        self.plans["combos"] = [c for c in self.plans["combos"] if c["id"] not in delete_ids]
        save_plans(self.plans)
        self.refresh_live_tree()

    def remove_duplicates(self):
        if not self.plans.get("combos"): return
        unique_sigs = set()
        new_combos = []
        for combo in self.plans["combos"]:
            sig = tuple(combo["picking_order"]) + tuple(sorted([
                (s["code"], s.get("professor", ""), s.get("slots", "")) 
                for s in combo["sections"] if not s.get("is_blank")
            ]))
            if sig not in unique_sigs:
                unique_sigs.add(sig)
                new_combos.append(combo)
                
        removed = len(self.plans["combos"]) - len(new_combos)
        if removed > 0:
            self.plans["combos"] = new_combos
            save_plans(self.plans)
            self.refresh_live_tree()
            messagebox.showinfo("Cleaned", f"Removed {removed} duplicate combination(s).")
        else:
            messagebox.showinfo("Cleaned", "No duplicate combinations were found.")

    def open_structural_batch_dialog(self, combo_id, preselect_code=None):
        base_combo = next(c for c in self.plans["combos"] if c["id"] == combo_id)
        
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Structural Path Branching — Base Combo ID {combo_id}")
        dlg.geometry("850x650")
        dlg.configure(bg=self.bg)
        dlg.grab_set()

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

            save_plans(self.plans)
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
            
        new_id = max([c["id"] for c in self.plans.get("combos", [])], default=0) + 1
        new_combo = {
            "id": new_id,
            "picking_order": copy.deepcopy(self.new_plan_picking_order),
            "sections": copy.deepcopy(self.new_plan_sections)
        }
        
        self.plans.setdefault("combos", []).append(new_combo)
        save_plans(self.plans)
        messagebox.showinfo("Success", f"Plan saved as Combination #{new_id}. You can fully modify/branch it from the Live Tracker tab.")
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
        self.flow_order = []
        self._flow_cache = None          # (tuple(flow), leaves, dead, alive)
        self.flow_with_lab = tk.BooleanVar(value=True)
        self.flow_info_var = tk.StringVar()

        hdr = tk.Frame(self.tab_flow, bg=self.surface, highlightbackground=self.border, highlightthickness=1)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Flow Planning", font=("Helvetica", 16, "bold"),
                 fg=self.text, bg=self.surface).pack(side="left", padx=20, pady=12)

        body = tk.Frame(self.tab_flow, bg=self.bg)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(body,
                 text=("Add courses in the order you want to pick them (e.g. VLSI -> VLSI Lab -> Digital Communication ...).\n"
                       "Creating the tree generates EVERY clash-free combination for that order from CourseList.csv. "
                       "A lab can only use the professors of the theory course you picked. "
                       "You can then reorder / prune the tree in the Live Tracker."),
                 font=("Helvetica", 11), fg=self.text2, bg=self.bg, justify="left", wraplength=1050
                 ).pack(anchor="w", pady=(0, 10))

        add_row = tk.Frame(body, bg=self.bg)
        add_row.pack(fill="x", pady=(0, 10))
        tk.Label(add_row, text="Next course:", font=("Helvetica", 11, "bold"),
                 fg=self.text, bg=self.bg).pack(side="left")
        self.flow_cb = ttk.Combobox(add_row, values=[], state="readonly", width=52)
        self.flow_cb.pack(side="left", padx=10)
        tk.Checkbutton(add_row, text="also add its lab right after", variable=self.flow_with_lab,
                       bg=self.bg, fg=self.text, activebackground=self.bg,
                       font=("Helvetica", 10)).pack(side="left", padx=(0, 10))
        self.btn(add_row, "+ Add to Flow", self.flow_add, "success").pack(side="left")

        mid = tk.Frame(body, bg=self.bg)
        mid.pack(fill="x")
        self.flow_lb = tk.Listbox(mid, font=("Helvetica", 11, "bold"), height=13, width=70,
                                  bg=self.surface, fg=self.text, selectbackground=self.accent_lt,
                                  selectforeground=self.text, highlightbackground=self.border,
                                  highlightthickness=1, relief="flat", activestyle="none",
                                  exportselection=False)
        self.flow_lb.pack(side="left", padx=(0, 8))
        side = tk.Frame(mid, bg=self.bg)
        side.pack(side="left", fill="y")
        self.btn(side, "▲ Move Up", lambda: self.flow_move(-1), "muted").pack(fill="x", pady=2)
        self.btn(side, "▼ Move Down", lambda: self.flow_move(1), "muted").pack(fill="x", pady=2)
        self.btn(side, "Remove", self.flow_remove, "danger").pack(fill="x", pady=(10, 2))
        self.btn(side, "Clear Flow", self.flow_clear, "muted").pack(fill="x", pady=2)

        tk.Label(body, textvariable=self.flow_info_var, font=("Helvetica", 11), fg=self.text,
                 bg=self.bg, justify="left", anchor="w", wraplength=1050).pack(fill="x", pady=(12, 8))

        act = tk.Frame(body, bg=self.bg)
        act.pack(fill="x")
        self.btn(act, "Preview Tree Size", self.flow_preview, "primary").pack(side="left")
        self.btn(act, "Create Full Tree  (overwrites existing plans)", self.flow_create,
                 "danger").pack(side="left", padx=12)

        self._flow_changed()

    def _flow_refresh_choices(self):
        vals = [f"{c} — {self.courses_dict[c][0]['name']}"
                for c in self.courses_dict if c not in self.flow_order]
        self.flow_cb.configure(values=vals)
        self.flow_cb.set(vals[0] if vals else "")

    def _flow_changed(self):
        self._flow_cache = None
        self.flow_lb.delete(0, tk.END)
        for i, code in enumerate(self.flow_order, 1):
            self.flow_lb.insert(tk.END, f"  {i}.  {code} — {self.courses_dict[code][0]['name']}")
        self._flow_refresh_choices()
        if self.flow_order:
            self.flow_info_var.set("Click 'Preview Tree Size' to see how many plans this order produces.")
        else:
            self.flow_info_var.set("Flow is empty. Add the first course you plan to pick.")

    def flow_add(self):
        val = self.flow_cb.get()
        if not val:
            return
        code = val.split(" — ")[0].strip()
        if code in self.flow_order:
            return
        self.flow_order.append(code)
        lab = get_lab_code(code)
        if self.flow_with_lab.get() and lab and lab in self.courses_dict and lab not in self.flow_order:
            self.flow_order.append(lab)
        self._flow_changed()

    def flow_move(self, direction):
        sel = self.flow_lb.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + direction
        if 0 <= j < len(self.flow_order):
            self.flow_order[i], self.flow_order[j] = self.flow_order[j], self.flow_order[i]
            self._flow_changed()
            self.flow_lb.selection_set(j)

    def flow_remove(self):
        sel = self.flow_lb.curselection()
        if not sel:
            return
        del self.flow_order[sel[0]]
        self._flow_changed()

    def flow_clear(self):
        self.flow_order = []
        self._flow_changed()

    def _flow_progress(self, n):
        self.flow_info_var.set(f"Working…  {n:,} plans so far")
        self.root.update_idletasks()

    def _flow_stats(self):
        """(leaves, dead_ends, alive_per_depth) for the current flow; cached until the flow changes."""
        key = tuple(self.flow_order)
        if self._flow_cache and self._flow_cache[0] == key:
            return self._flow_cache[1:]
        self.root.config(cursor="watch")
        self.flow_info_var.set("Counting…")
        self.root.update_idletasks()
        try:
            leaves, dead, alive = walk_flow(list(key), self.courses_dict, progress=self._flow_progress)
        finally:
            self.root.config(cursor="")
        self._flow_cache = (key, leaves, dead, alive)
        return leaves, dead, alive

    def _flow_summary(self, leaves, dead, alive):
        lines = [f"Complete clash-free plans: {leaves:,}     Dead-end paths removed: {dead:,}",
                 f"Existing plans that would be overwritten: {len(self.plans.get('combos', [])):,}",
                 "Valid partial paths after each pick:  " +
                 "   ".join(f"{i}. {c} → {alive[i]:,}" for i, c in enumerate(self.flow_order, 1))]
        return "\n".join(lines)

    def flow_preview(self):
        if not self.flow_order:
            messagebox.showinfo("Empty Flow", "Add at least one course to the flow first.")
            return
        leaves, dead, alive = self._flow_stats()
        text = self._flow_summary(leaves, dead, alive)
        if leaves == 0:
            text += "\nNo complete clash-free plan exists for this order. Check where the path counts drop to 0."
        self.flow_info_var.set(text)

    def flow_create(self):
        if not self.flow_order:
            messagebox.showinfo("Empty Flow", "Add at least one course to the flow first.")
            return
        leaves, dead, alive = self._flow_stats()
        self.flow_info_var.set(self._flow_summary(leaves, dead, alive))
        if leaves == 0:
            messagebox.showerror("Nothing to create",
                                 "No complete clash-free plan exists for this order, so nothing was changed.")
            return

        existing = len(self.plans.get("combos", []))
        path_str = " > ".join(self.flow_order)
        msg1 = (f"This will REPLACE all {existing:,} existing plan(s) and your saved option orderings "
                f"with {leaves:,} newly generated plan(s) for:\n\n  {path_str}\n\n"
                f"A backup of the current file will be saved first. Continue?")
        if not messagebox.askyesno("Create Full Tree - Step 1 of 2", msg1, icon="warning"):
            return
        msg2 = ("Are you absolutely sure?\n\nEverything currently in the Live Tracker will be overwritten "
                f"by {leaves:,} generated plans. (Backup file: {BACKUP_FILE})")
        if not messagebox.askyesno("Create Full Tree - Step 2 of 2 (Final Confirmation)", msg2,
                                   icon="warning", default="no"):
            return

        if os.path.exists(PLANS_FILE):
            try:
                shutil.copy2(PLANS_FILE, BACKUP_FILE)
                if os.path.exists(LIVE_ORDERS_FILE):
                    shutil.copy2(LIVE_ORDERS_FILE, "live_orders.backup.json")
            except OSError as e:
                messagebox.showerror("Backup failed", f"Could not write the backup, nothing was changed.\n\n{e}")
                return

        combos = []
        flow = list(self.flow_order)

        def on_leaf(chosen):
            combos.append({"id": len(combos) + 1, "picking_order": list(flow), "sections": list(chosen)})

        self.root.config(cursor="watch")
        try:
            walk_flow(flow, self.courses_dict, on_leaf=on_leaf, progress=self._flow_progress)
            self.flow_info_var.set("Saving…")
            self.root.update_idletasks()
            self.plans = {"combos": combos, "live_orders": {}}
            save_plans(self.plans)
            save_live_orders({})
        finally:
            self.root.config(cursor="")

        self.flow_info_var.set(f"Done. {len(combos):,} plans created.")
        messagebox.showinfo("Tree Created",
                            f"Created {len(combos):,} plans.\nPrevious data was backed up to {BACKUP_FILE}.")
        self.initialize_live_mode()
        self.notebook.select(self.tab_live)


if __name__ == "__main__":
    root = tk.Tk()
    app = MasterCounsellingApp(root)
    if app.ok:
        root.mainloop()

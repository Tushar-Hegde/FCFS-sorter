import csv
import os
import json
import tkinter as tk
from tkinter import messagebox, ttk
import copy

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
    """Maps slots to all days and timings they cover."""
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

def load_plans(filename="plans.json"):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {"combos": []}
    return {"combos": []}

def save_plans(plans, filename="plans.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(plans, f, indent=4)

def get_theory_code(code):
    """If code ends with 'P', return the corresponding 'L' theory code."""
    if code.endswith('P'):
        return code[:-1] + 'L'
    return None

def get_lab_code(code):
    """If code ends with 'L', return the corresponding 'P' lab code."""
    if code.endswith('L'):
        return code[:-1] + 'P'
    return None


# ==============================================================================
# 2. MAIN APPLICATION GUI CLASS
# ==============================================================================

class MasterCounsellingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Course Counseling Suite")
        self.root.geometry("1150x760")
        self.root.minsize(1050, 700)

        self.courses_dict = load_courses_from_csv("CourseList.csv")
        self.plans = load_plans("plans.json")
        self.slot_timing_map = generate_slot_timing_map()

        if not self.courses_dict:
            messagebox.showerror("Missing Data", "CourseList.csv not found or is empty.")
            self.root.destroy()
            return

        # ── Light theme palette ──────────────────────────────────────────────
        self.bg         = "#F5F7FA"   # page background
        self.surface    = "#FFFFFF"   # card / panel surface
        self.surface2   = "#EEF1F6"   # subtle secondary surface
        self.border     = "#D0D7E2"   # borders / separators
        self.accent     = "#3B6FD4"   # primary blue
        self.accent_lt  = "#EBF0FB"   # light-blue tint
        self.text       = "#1A1F2E"   # primary text
        self.text2      = "#5B6478"   # secondary / muted text
        self.success    = "#1F7A4B"   # green text
        self.success_bg = "#E6F6ED"   # green badge bg
        self.danger     = "#B91C1C"   # red text
        self.danger_bg  = "#FEE2E2"   # red badge bg
        self.warn       = "#92400E"   # amber text
        self.warn_bg    = "#FEF3C7"   # amber badge bg
        self.purple     = "#6D3BBF"   # lab-lock purple
        self.purple_bg  = "#EDE9FE"

        self.root.configure(bg=self.bg)

        # ── ttk styles ───────────────────────────────────────────────────────
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

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_view  = tk.Frame(self.notebook, bg=self.bg)
        self.tab_build = tk.Frame(self.notebook, bg=self.bg)
        self.tab_live  = tk.Frame(self.notebook, bg=self.bg)

        self.notebook.add(self.tab_view,  text="  📂  Saved Combinations  ")
        self.notebook.add(self.tab_build, text="  🔨  Create New Plan  ")
        self.notebook.add(self.tab_live,  text="  ⚡  Live Tracker  ")

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.setup_view_tab()
        self.setup_build_tab()
        self.setup_live_tab()

    # ── helpers ──────────────────────────────────────────────────────────────

    def on_tab_changed(self, event):
        t = self.notebook.index(self.notebook.select())
        if   t == 0: self.refresh_view_tab()
        elif t == 1: self.reset_builder_wizard()
        elif t == 2: self.initialize_live_mode()

    def btn(self, parent, text, command, kind="primary", **kw):
        """Convenience button factory."""
        palettes = {
            "primary": (self.accent,    "#FFFFFF"),
            "success": (self.success,   "#FFFFFF"),
            "danger":  (self.danger,    "#FFFFFF"),
            "muted":   (self.border,    self.text),
            "purple":  (self.purple,    "#FFFFFF"),
        }
        bg, fg = palettes.get(kind, palettes["primary"])
        return tk.Button(parent, text=text, command=command,
                         bg=bg, fg=fg, font=("Helvetica", 11, "bold"),
                         relief="flat", cursor="hand2", padx=10, pady=5, **kw)

    def badge(self, parent, text, kind="info"):
        """Coloured inline badge label."""
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

    def section_info_widget(self, parent, sec, compact=False):
        """Render a consistent course info block inside *parent*."""
        bg = self.surface
        if sec.get("is_blank"):
            tk.Label(parent, text=f"{sec['code']}  —  {sec.get('name','')}",
                     font=("Helvetica", 12, "bold"), fg=self.text, bg=bg).pack(anchor="w")
            tk.Label(parent, text="[ BLANK – no time assigned ]",
                     font=("Helvetica", 11, "italic"), fg=self.text2, bg=bg).pack(anchor="w")
            return

        timings = get_timings_for_slots(sec['slots'], self.slot_timing_map)
        tk.Label(parent,
                 text=f"{sec['code']}  —  {sec.get('name','')}",
                 font=("Helvetica", 12, "bold"), fg=self.text, bg=bg).pack(anchor="w")
        row = tk.Frame(parent, bg=bg)
        row.pack(anchor="w", fill="x")
        tk.Label(row, text=f"👤 {sec['professor']}",
                 font=("Helvetica", 11), fg=self.text2, bg=bg).pack(side="left", padx=(0,12))
        tk.Label(row, text=f"🗓 Slots: {sec['slots']}",
                 font=("Helvetica", 11), fg=self.text2, bg=bg).pack(side="left", padx=(0,12))
        tk.Label(row, text=f"📋 {sec['tt_code']}",
                 font=("Helvetica", 11), fg=self.text2, bg=bg).pack(side="left")
        if not compact:
            tk.Label(parent, text=f"🕐 {timings}",
                     font=("Helvetica", 11), fg=self.accent, bg=bg,
                     wraplength=600, justify="left").pack(anchor="w", pady=(2,0))

    def scrollable(self, parent):
        """Return (canvas, inner_frame, scrollbar) — standard scrollable container."""
        canvas = tk.Canvas(parent, bg=self.bg, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.bg)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return canvas, inner, sb

    # =========================================================================
    # TAB 1 – SAVED COMBINATIONS
    # =========================================================================
    def setup_view_tab(self):
        hdr = tk.Frame(self.tab_view, bg=self.surface,
                       highlightbackground=self.border, highlightthickness=1)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Saved Combinations",
                 font=("Helvetica", 16, "bold"), fg=self.text, bg=self.surface
                 ).pack(side="left", padx=20, pady=12)

        body = tk.Frame(self.tab_view, bg=self.bg)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        _, self.view_scroll_frame, _ = self.scrollable(body)

    def refresh_view_tab(self):
        for w in self.view_scroll_frame.winfo_children(): w.destroy()
        self.plans = load_plans("plans.json")

        if not self.plans["combos"]:
            tk.Label(self.view_scroll_frame,
                     text="No combinations saved yet.\nGo to 'Create New Plan' to build one.",
                     font=("Helvetica", 13, "italic"), fg=self.text2, bg=self.bg
                     ).pack(pady=60)
            return

        for idx, combo in enumerate(self.plans["combos"], 1):
            card = self.card_frame(self.view_scroll_frame)
            card.pack(fill="x", pady=6, padx=4)

            # header row
            hrow = tk.Frame(card, bg=self.surface)
            hrow.pack(fill="x", padx=14, pady=(10, 6))
            tk.Label(hrow, text=f"Combination #{idx}",
                     font=("Helvetica", 13, "bold"), fg=self.text, bg=self.surface
                     ).pack(side="left")
            self.badge(hrow, f"ID {combo['id']}", "info").pack(side="left", padx=8)

            # course rows
            for i, code in enumerate(combo["picking_order"]):
                sec = next(s for s in combo["sections"] if s["code"] == code)
                row_bg = self.surface if i % 2 == 0 else self.surface2
                row = tk.Frame(card, bg=row_bg)
                row.pack(fill="x", padx=0)

                step_lbl = tk.Label(row, text=f" {i+1} ", width=3,
                                    font=("Helvetica", 11, "bold"),
                                    fg=self.accent, bg=row_bg)
                step_lbl.pack(side="left", padx=(10, 4), pady=6)

                info = tk.Frame(row, bg=row_bg)
                info.pack(side="left", fill="x", expand=True, pady=4)

                timings = get_timings_for_slots(sec['slots'], self.slot_timing_map) \
                          if not sec.get("is_blank") else "—"
                tk.Label(info, text=f"{sec['code']}  —  {sec.get('name','')}",
                         font=("Helvetica", 11, "bold"), fg=self.text, bg=row_bg,
                         anchor="w").pack(anchor="w")
                tk.Label(info,
                         text=f"👤 {sec['professor']}   🗓 {sec['slots']}   📋 {sec['tt_code']}",
                         font=("Helvetica", 10), fg=self.text2, bg=row_bg,
                         anchor="w").pack(anchor="w")
                tk.Label(info, text=f"🕐 {timings}",
                         font=("Helvetica", 10), fg=self.accent, bg=row_bg,
                         anchor="w", wraplength=700, justify="left").pack(anchor="w")

            # action buttons
            brow = tk.Frame(card, bg=self.surface)
            brow.pack(fill="x", padx=14, pady=(6, 10))
            self.btn(brow, "🌿 Branch", lambda cid=combo['id']: self.branch_combo(cid),
                     "success").pack(side="left", padx=(0,6))
            self.btn(brow, "✏️ Modify", lambda cid=combo['id']: self.open_modify_dialog(cid),
                     "primary").pack(side="left", padx=(0,6))
            self.btn(brow, "🗑 Delete", lambda cid=combo['id']: self.delete_combo(cid),
                     "danger").pack(side="right")

    def delete_combo(self, combo_id):
        if messagebox.askyesno("Confirm Delete",
                               "Are you sure you want to delete this combination?"):
            self.plans["combos"] = [c for c in self.plans["combos"] if c["id"] != combo_id]
            save_plans(self.plans)
            self.refresh_view_tab()

    # =========================================================================
    # BRANCH & MODIFY DIALOG
    # =========================================================================
    def branch_combo(self, combo_id):
        base = next(c for c in self.plans["combos"] if c["id"] == combo_id)
        new_id = max([c["id"] for c in self.plans["combos"]], default=0) + 1
        branched = {"id": new_id,
                    "sections": copy.deepcopy(base["sections"]),
                    "picking_order": copy.deepcopy(base["picking_order"])}
        self.plans["combos"].append(branched)
        save_plans(self.plans)
        self.refresh_view_tab()
        messagebox.showinfo("Branched", f"Cloned as ID {new_id}. Opening for modification…")
        self.open_modify_dialog(new_id)

    def open_modify_dialog(self, combo_id):
        combo = next(c for c in self.plans["combos"] if c["id"] == combo_id)
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Modify Plan — ID {combo_id}")
        dlg.geometry("1100x740")
        dlg.configure(bg=self.bg)
        dlg.grab_set()
        dlg.working_combo = copy.deepcopy(combo)
        self.render_modify_main_view(dlg, combo_id)

    def render_modify_main_view(self, dlg, combo_id):
        for w in dlg.winfo_children(): w.destroy()

        # footer first so it stays at bottom
        foot = tk.Frame(dlg, bg=self.surface,
                        highlightbackground=self.border, highlightthickness=1)
        foot.pack(fill="x", side="bottom")
        self.btn(foot, "💾 Save Changes",
                 lambda: self.save_dialog_modifications(dlg, combo_id),
                 "success").pack(side="right", padx=10, pady=8)
        self.btn(foot, "✕ Discard & Close", dlg.destroy, "danger").pack(side="right", pady=8)

        body = tk.Frame(dlg, bg=self.bg)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        # LEFT – course cards
        left = tk.LabelFrame(body, text="  Course Sections  ",
                             font=("Helvetica", 12, "bold"),
                             fg=self.text, bg=self.bg,
                             relief="flat",
                             highlightbackground=self.border, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        _, scroll_content, _ = self.scrollable(left)

        for code in dlg.working_combo["picking_order"]:
            sec = next(s for s in dlg.working_combo["sections"] if s["code"] == code)
            card = self.card_frame(scroll_content)
            card.pack(fill="x", pady=5, padx=5)

            info = tk.Frame(card, bg=self.surface)
            info.pack(side="left", fill="both", expand=True, padx=12, pady=10)
            self.section_info_widget(info, sec)

            btns = tk.Frame(card, bg=self.surface)
            btns.pack(side="right", padx=10, pady=10)
            self.btn(btns, "Change Section",
                     lambda tc=code: self.render_replace_section_view(dlg, combo_id, tc),
                     "primary").pack(fill="x", pady=2)
            if not sec.get("is_blank"):
                self.btn(btns, "Make Blank",
                         lambda tc=code: self.apply_blank_slot(dlg, combo_id, tc),
                         "muted").pack(fill="x", pady=2)

        # RIGHT – priority order
        right = tk.LabelFrame(body, text="  Picking Order  ",
                              font=("Helvetica", 12, "bold"),
                              fg=self.text, bg=self.bg,
                              relief="flat",
                              highlightbackground=self.border, highlightthickness=1,
                              width=300)
        right.pack(side="right", fill="both", padx=(8, 0))
        right.pack_propagate(False)

        tk.Label(right, text="Move bundles up/down.\nTheory+Lab pairs move together.",
                 font=("Helvetica", 10, "italic"), fg=self.text2, bg=self.bg
                 ).pack(padx=8, pady=(8,4), anchor="w")

        bundles = self._build_order_bundles(dlg.working_combo)

        lb = tk.Listbox(right, font=("Helvetica", 11, "bold"),
                        bg=self.surface, fg=self.text,
                        selectbackground=self.accent_lt, selectforeground=self.text,
                        highlightbackground=self.border, highlightthickness=1,
                        relief="flat", activestyle="none", bd=0)
        lb.pack(side="left", fill="both", expand=True, padx=(8,0), pady=8)

        for bundle in bundles:
            if len(bundle) == 1:
                code = bundle[0]
                sec = next(s for s in dlg.working_combo["sections"] if s["code"] == code)
                prof = "BLANK" if sec.get("is_blank") else sec["professor"]
                lb.insert(tk.END, f"  {sec['code']}  ({prof})")
            else:
                t_code = next((c for c in bundle if c.endswith('L')), bundle[0])
                p_code = next((c for c in bundle if c.endswith('P')), bundle[1])
                t_sec  = next(s for s in dlg.working_combo["sections"] if s["code"] == t_code)
                lb.insert(tk.END, f"  📦 {t_code}+{p_code}  ({t_sec['professor']})")

        bpane = tk.Frame(right, bg=self.bg)
        bpane.pack(side="right", fill="y", pady=8, padx=6)
        self.btn(bpane, "▲", lambda: self.dialog_move_bundle_up(lb, dlg, bundles),   "muted").pack(fill="x", pady=2)
        self.btn(bpane, "▼", lambda: self.dialog_move_bundle_down(lb, dlg, bundles), "muted").pack(fill="x", pady=2)

    def _build_order_bundles(self, working_combo):
        order = working_combo["picking_order"]
        bundles, skip = [], set()
        for code in order:
            if code in skip: continue
            lab = get_lab_code(code)
            if lab and lab in order:
                bundles.append([code, lab]); skip.add(lab)
            else:
                theory = get_theory_code(code)
                if theory and theory in order:
                    skip.add(code)
                else:
                    bundles.append([code])
        return bundles

    def _bundles_to_order(self, bundles):
        return [c for b in bundles for c in b]

    def dialog_move_bundle_up(self, lb, dlg, bundles):
        pos = lb.curselection()
        if not pos or pos[0] == 0: return
        i = pos[0]
        bundles[i], bundles[i-1] = bundles[i-1], bundles[i]
        dlg.working_combo["picking_order"] = self._bundles_to_order(bundles)
        t, p = lb.get(i), lb.get(i-1)
        lb.delete(i); lb.insert(i, p)
        lb.delete(i-1); lb.insert(i-1, t)
        lb.selection_set(i-1)

    def dialog_move_bundle_down(self, lb, dlg, bundles):
        pos = lb.curselection()
        if not pos or pos[0] == lb.size()-1: return
        i = pos[0]
        bundles[i], bundles[i+1] = bundles[i+1], bundles[i]
        dlg.working_combo["picking_order"] = self._bundles_to_order(bundles)
        t, n = lb.get(i), lb.get(i+1)
        lb.delete(i+1); lb.insert(i+1, t)
        lb.delete(i);   lb.insert(i, n)
        lb.selection_set(i+1)

    def apply_blank_slot(self, dlg, combo_id, target_code):
        idx = next(i for i, s in enumerate(dlg.working_combo["sections"])
                   if s["code"] == target_code)
        dlg.working_combo["sections"][idx] = {
            "code": target_code,
            "name": self.courses_dict[target_code][0]["name"]
                    if target_code in self.courses_dict else target_code,
            "slots": "—", "tt_code": "—", "professor": "—", "type": "—",
            "minute_blocks": [], "is_blank": True
        }
        self.render_modify_main_view(dlg, combo_id)

    def render_replace_section_view(self, dlg, combo_id, target_code):
        for w in dlg.winfo_children(): w.destroy()

        course_name = (self.courses_dict[target_code][0]["name"]
                       if target_code in self.courses_dict else target_code)

        # ── header bar ──────────────────────────────────────────────────────
        hbar = tk.Frame(dlg, bg=self.surface,
                        highlightbackground=self.border, highlightthickness=1)
        hbar.pack(fill="x")

        self.btn(hbar, "← Back", lambda: self.render_modify_main_view(dlg, combo_id),
                 "muted").pack(side="left", padx=12, pady=8)

        tk.Label(hbar, text="Switch course:  ",
                 font=("Helvetica", 11), fg=self.text2, bg=self.surface).pack(side="left")

        order_codes = dlg.working_combo["picking_order"]
        dd_vals = [f"{c} — {self.courses_dict[c][0]['name']}" if c in self.courses_dict else c
                   for c in order_codes]
        target_disp = f"{target_code} — {course_name}"

        dd = ttk.Combobox(hbar, values=dd_vals, state="readonly",
                          font=("Helvetica", 11), width=42)
        dd.set(target_disp)
        dd.pack(side="left", padx=6, pady=8)
        dd.bind("<<ComboboxSelected>>",
                lambda e: self.render_replace_section_view(
                    dlg, combo_id, dd.get().split(" — ")[0].strip()))

        # ── title ────────────────────────────────────────────────────────────
        body = tk.Frame(dlg, bg=self.bg)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        tk.Label(body, text=f"Choose a section for  {target_code} — {course_name}",
                 font=("Helvetica", 14, "bold"), fg=self.text, bg=self.bg
                 ).pack(anchor="w", pady=(0, 6))

        # ── determine professor filters for bidirectional pairing ─────────────
        sections_in_combo = dlg.working_combo["sections"]
        sec_idx = next(i for i, s in enumerate(sections_in_combo)
                       if s["code"] == target_code)

        prof_filter = None

        # Case A: target is a lab (ends P) → filter to theory professor
        theory_code = get_theory_code(target_code)
        if theory_code:
            theory_sec = next((s for s in sections_in_combo
                                if s["code"] == theory_code and not s.get("is_blank")), None)
            if theory_sec:
                prof_filter = theory_sec["professor"]

        # Case B: target is a theory (ends L) → filter to lab professor
        if prof_filter is None:
            lab_code = get_lab_code(target_code)
            if lab_code:
                lab_sec = next((s for s in sections_in_combo
                                 if s["code"] == lab_code and not s.get("is_blank")), None)
                if lab_sec:
                    prof_filter = lab_sec["professor"]

        if prof_filter:
            self.badge(body, f"🔒 Filtered to professor: {prof_filter}", "purple").pack(anchor="w", pady=(0,8))

        # ── compute clash-free options ────────────────────────────────────────
        occupied = set()
        for i, sec in enumerate(sections_in_combo):
            if i != sec_idx and not sec.get("is_blank"):
                occupied.update(tuple(x) for x in sec["minute_blocks"])

        valid = []
        for sec in self.courses_dict.get(target_code, []):
            if prof_filter and sec["professor"] != prof_filter:
                continue
            if occupied.isdisjoint(set(tuple(x) for x in sec["minute_blocks"])):
                valid.append(sec)

        if not valid:
            msg = "No clash-free sections available."
            if prof_filter:
                msg += f"\n(filtered to professor: {prof_filter})"
            tk.Label(body, text=f"⚠  {msg}",
                     font=("Helvetica", 12), fg=self.danger, bg=self.bg
                     ).pack(pady=30)
            return

        # ── scrollable list ───────────────────────────────────────────────────
        _, list_frame, _ = self.scrollable(body)

        for opt in valid:
            card = self.card_frame(list_frame)
            card.pack(fill="x", pady=4, padx=4)

            info = tk.Frame(card, bg=self.surface)
            info.pack(side="left", fill="both", expand=True, padx=12, pady=10)
            timings = get_timings_for_slots(opt['slots'], self.slot_timing_map)
            tk.Label(info, text=f"👤 {opt['professor']}   🗓 {opt['slots']}   📋 {opt['tt_code']}",
                     font=("Helvetica", 11), fg=self.text2, bg=self.surface,
                     anchor="w").pack(anchor="w")
            tk.Label(info, text=f"🕐 {timings}",
                     font=("Helvetica", 11), fg=self.accent, bg=self.surface,
                     anchor="w", wraplength=700).pack(anchor="w", pady=(2,0))

            self.btn(card, "Select",
                     lambda o=opt: self.apply_section_replacement(dlg, combo_id, sec_idx, o),
                     "success").pack(side="right", padx=12, pady=10)

    def apply_section_replacement(self, dlg, combo_id, sec_idx, choice_sec):
        ns = copy.deepcopy(choice_sec)
        ns["is_blank"] = False
        dlg.working_combo["sections"][sec_idx] = ns
        self.render_modify_main_view(dlg, combo_id)

    def save_dialog_modifications(self, dlg, combo_id):
        for sec in dlg.working_combo["sections"]:
            if sec.get("is_blank"):
                messagebox.showerror("Validation Failed",
                    f"'{sec['code']}' is still blank. Assign a section first.")
                return
        cur_sig = {s["code"]: s["slots"]+"||"+s["professor"]
                   for s in dlg.working_combo["sections"]}
        for ex in self.plans["combos"]:
            if ex["id"] == combo_id: continue
            if cur_sig == {s["code"]: s["slots"]+"||"+s["professor"] for s in ex["sections"]}:
                messagebox.showwarning("Duplicate",
                    f"This matches existing plan ID {ex['id']}.")
                return
        i = next(i for i, c in enumerate(self.plans["combos"]) if c["id"] == combo_id)
        self.plans["combos"][i] = dlg.working_combo
        save_plans(self.plans)
        messagebox.showinfo("Saved", "Plan updated successfully.")
        dlg.destroy()
        self.refresh_view_tab()

    # =========================================================================
    # TAB 2 – CREATE NEW PLAN WIZARD
    # =========================================================================
    def setup_build_tab(self):
        self.left_panel  = tk.Frame(self.tab_build, bg=self.bg)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(14,6), pady=12)

        self.right_panel = tk.LabelFrame(self.tab_build, text="  Selected So Far  ",
                                          font=("Helvetica", 12, "bold"),
                                          fg=self.text, bg=self.bg,
                                          relief="flat",
                                          highlightbackground=self.border,
                                          highlightthickness=1, width=380)
        self.right_panel.pack(side="right", fill="both", padx=(6,14), pady=12)
        self.right_panel.pack_propagate(False)

        self.builder_course_codes = list(self.courses_dict.keys())
        self.reset_builder_wizard()

    def reset_builder_wizard(self):
        self.wizard_step = 0
        self.wizard_selections = []
        self.wizard_occupied_minutes = set()
        self.render_builder_step()

    def remove_wizard_selection(self, index):
        """Allows removal of a previously locked course in the wizard."""
        self.wizard_selections.pop(index)
        self.wizard_occupied_minutes = set()
        for s in self.wizard_selections:
            self.wizard_occupied_minutes.update(tuple(x) for x in s["minute_blocks"])
        if self.wizard_step > 0:
            self.wizard_step -= 1
        self.render_builder_step()

    def render_builder_step(self):
        for w in self.left_panel.winfo_children():  w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        # ── RIGHT PANEL: selections so far ───────────────────────────────────
        tk.Label(self.right_panel,
                 text="Selections so far:",
                 font=("Helvetica", 11, "bold"), fg=self.text2, bg=self.bg
                 ).pack(anchor="w", padx=10, pady=(10,4))

        if not self.wizard_selections:
            tk.Label(self.right_panel,
                     text="Nothing picked yet.",
                     font=("Helvetica", 11, "italic"), fg=self.text2, bg=self.bg
                     ).pack(anchor="w", padx=14)
        else:
            _, rscroll, _ = self.scrollable(self.right_panel)
            for i, s in enumerate(self.wizard_selections, 1):
                rcard = self.card_frame(rscroll)
                rcard.pack(fill="x", padx=8, pady=4)
                
                inner = tk.Frame(rcard, bg=self.surface)
                inner.pack(fill="x", padx=8, pady=6)
                
                header_row = tk.Frame(inner, bg=self.surface)
                header_row.pack(fill="x")
                
                tk.Label(header_row, text=f"{i}. {s['code']}",
                         font=("Helvetica", 11, "bold"), fg=self.text, bg=self.surface
                         ).pack(side="left")
                         
                # ── The New Backtrack/Removal Button ──
                self.btn(header_row, "✕ Remove", lambda idx=i-1: self.remove_wizard_selection(idx), "danger").pack(side="right")
                
                tk.Label(inner, text=s['name'],
                         font=("Helvetica", 10), fg=self.text2, bg=self.surface
                         ).pack(anchor="w")
                tk.Label(inner, text=f"👤 {s['professor']}   🗓 {s['slots']}",
                         font=("Helvetica", 10), fg=self.text2, bg=self.surface
                         ).pack(anchor="w")
                timings = get_timings_for_slots(s['slots'], self.slot_timing_map)
                tk.Label(inner, text=f"🕐 {timings}",
                         font=("Helvetica", 10), fg=self.accent, bg=self.surface,
                         wraplength=300, justify="left").pack(anchor="w")

        # ── LEFT PANEL: course selector + sections ────────────────────────────
        selected_codes = [s["code"] for s in self.wizard_selections]
        remaining_codes = [c for c in self.builder_course_codes if c not in selected_codes]

        # Check for forced next (theory→lab OR lab→theory)
        locked_next_code = None
        locked_prof      = None

        if self.wizard_selections:
            last = self.wizard_selections[-1]
            # last was theory (L) → force lab (P)
            lab_of_last = get_lab_code(last["code"])
            if lab_of_last and lab_of_last in self.courses_dict and lab_of_last not in selected_codes:
                locked_next_code = lab_of_last
                locked_prof      = last["professor"]
            # last was lab (P) → force theory (L)
            else:
                theory_of_last = get_theory_code(last["code"])
                if (theory_of_last and theory_of_last in self.courses_dict
                        and theory_of_last not in selected_codes):
                    locked_next_code = theory_of_last
                    locked_prof      = last["professor"]

        # ── header row ────────────────────────────────────────────────────────
        hrow = tk.Frame(self.left_panel, bg=self.bg)
        hrow.pack(fill="x", pady=(0, 8))

        if locked_next_code:
            lock_lbl = tk.Frame(hrow, bg=self.purple_bg,
                                highlightbackground=self.purple, highlightthickness=1)
            lock_lbl.pack(side="left", padx=(0,8))
            kind = "Lab" if locked_next_code.endswith('P') else "Theory"
            tk.Label(lock_lbl,
                     text=f"🔒 Paired {kind}: {locked_next_code}  (Prof locked: {locked_prof})",
                     font=("Helvetica", 11, "bold"), fg=self.purple, bg=self.purple_bg,
                     padx=8, pady=4).pack()
            current_code = locked_next_code

        elif remaining_codes:
            tk.Label(hrow, text="Course:",
                     font=("Helvetica", 12), fg=self.text2, bg=self.bg
                     ).pack(side="left", padx=(0,6))
            display_vals = [f"{c} — {self.courses_dict[c][0]['name']}"
                            if c in self.courses_dict else c
                            for c in remaining_codes]
            cb = ttk.Combobox(hrow, values=display_vals, state="readonly",
                              font=("Helvetica", 12), width=42)
            cb.pack(side="left", padx=(0,10))
            cb.set(display_vals[0])
            current_code = remaining_codes[0]

            def _on_course_change(event):
                code = cb.get().split(" — ")[0].strip()
                self.render_sections_for_selected_course(code, prof_filter=None)

            cb.bind("<<ComboboxSelected>>", _on_course_change)
        else:
            current_code = None

        if self.wizard_selections:
            self.btn(hrow, "💾 Done — Set Order & Save",
                     self.render_priority_sorting_interface,
                     "success").pack(side="right")

        # ── section cards ─────────────────────────────────────────────────────
        self.builder_sections_container = tk.Frame(self.left_panel, bg=self.bg)
        self.builder_sections_container.pack(fill="both", expand=True)

        if current_code:
            pf = locked_prof if locked_next_code else None
            self.render_sections_for_selected_course(current_code, prof_filter=pf)
        elif not self.wizard_selections:
            tk.Label(self.builder_sections_container,
                     text="No courses available.",
                     font=("Helvetica", 12, "italic"), fg=self.text2, bg=self.bg
                     ).pack(pady=40)
        else:
            self.render_priority_sorting_interface()

    def render_sections_for_selected_course(self, current_code, prof_filter=None):
        for w in self.builder_sections_container.winfo_children(): w.destroy()

        course_name = (self.courses_dict[current_code][0]["name"]
                       if current_code in self.courses_dict else current_code)

        title_row = tk.Frame(self.builder_sections_container, bg=self.bg)
        title_row.pack(fill="x", pady=(0, 6))
        tk.Label(title_row, text=f"{current_code}  —  {course_name}",
                 font=("Helvetica", 15, "bold"), fg=self.text, bg=self.bg
                 ).pack(side="left")
        if prof_filter:
            self.badge(title_row, f"🔒 Prof locked: {prof_filter}", "purple").pack(side="left", padx=8)

        all_sec = self.courses_dict.get(current_code, [])
        valid = []
        for sec in all_sec:
            if prof_filter and sec["professor"] != prof_filter:
                continue
            if self.wizard_occupied_minutes.isdisjoint(
                    set(tuple(x) for x in sec["minute_blocks"])):
                valid.append(sec)

        if not valid:
            msg = "⚠  No clash-free sections available for this course."
            if prof_filter:
                msg += f"\n(filtered to professor: {prof_filter})"
            tk.Label(self.builder_sections_container, text=msg,
                     font=("Helvetica", 12), fg=self.danger, bg=self.bg
                     ).pack(pady=20)
            self.btn(self.builder_sections_container, "↩ Restart Wizard",
                     self.reset_builder_wizard, "muted").pack(pady=6)
            return

        _, list_frame, _ = self.scrollable(self.builder_sections_container)

        for opt in valid:
            card = self.card_frame(list_frame)
            card.pack(fill="x", pady=4, padx=4)

            info = tk.Frame(card, bg=self.surface)
            info.pack(side="left", fill="both", expand=True, padx=12, pady=10)
            timings = get_timings_for_slots(opt['slots'], self.slot_timing_map)
            tk.Label(info, text=f"👤 {opt['professor']}   🗓 {opt['slots']}   📋 {opt['tt_code']}",
                     font=("Helvetica", 11), fg=self.text, bg=self.surface,
                     anchor="w").pack(anchor="w")
            tk.Label(info, text=f"🕐 {timings}",
                     font=("Helvetica", 11), fg=self.accent, bg=self.surface,
                     anchor="w", wraplength=550, justify="left").pack(anchor="w", pady=(2,0))

            self.btn(card, "Pick",
                     lambda o=opt: self.advance_builder_step(o),
                     "primary").pack(side="right", padx=12, pady=10)

    def advance_builder_step(self, chosen):
        self.wizard_selections.append(chosen)
        self.wizard_occupied_minutes.update(tuple(x) for x in chosen["minute_blocks"])
        self.wizard_step += 1
        self.render_builder_step()

    # ── Priority Sorting ──────────────────────────────────────────────────────
    def render_priority_sorting_interface(self):
        for w in self.left_panel.winfo_children(): w.destroy()

        tk.Label(self.left_panel,
                 text="Set Picking Priority Order",
                 font=("Helvetica", 15, "bold"), fg=self.text, bg=self.bg
                 ).pack(anchor="w", pady=(0,2))
        tk.Label(self.left_panel,
                 text="Drag (use buttons) to rank courses by registration urgency.  📦 = bundled Theory+Lab pair.",
                 font=("Helvetica", 11, "italic"), fg=self.text2, bg=self.bg
                 ).pack(anchor="w", pady=(0,12))

        lf = tk.Frame(self.left_panel, bg=self.bg)
        lf.pack(fill="both", expand=True)

        self.prio_bundles = self._build_selection_bundles(self.wizard_selections)

        self.prio_listbox = tk.Listbox(lf,
                                        font=("Helvetica", 12, "bold"),
                                        bg=self.surface, fg=self.text,
                                        selectbackground=self.accent_lt,
                                        selectforeground=self.text,
                                        highlightbackground=self.border,
                                        highlightthickness=1,
                                        relief="flat", activestyle="none",
                                        bd=0)
        self.prio_listbox.pack(side="left", fill="both", expand=True, padx=(0,8))

        for bundle in self.prio_bundles:
            if len(bundle) == 1:
                s = bundle[0]
                self.prio_listbox.insert(tk.END, f"  {s['code']} — {s['name']}  ({s['professor']})")
            else:
                t = next((s for s in bundle if s['code'].endswith('L')), bundle[0])
                p = next((s for s in bundle if s['code'].endswith('P')), bundle[1])
                self.prio_listbox.insert(tk.END,
                    f"  📦 {t['code']}+{p['code']} — {t['name']}  ({t['professor']})")

        bp = tk.Frame(lf, bg=self.bg)
        bp.pack(side="right", fill="y")
        self.btn(bp, "▲ Up",   self.move_bundle_up,   "muted").pack(fill="x", pady=2)
        self.btn(bp, "▼ Down", self.move_bundle_down, "muted").pack(fill="x", pady=2)

        self.btn(self.left_panel, "💾 Save Combination",
                 self.save_wizard_combo, "success").pack(fill="x", pady=14)

    def _build_selection_bundles(self, selections):
        codes  = [s["code"] for s in selections]
        bundles, skip = [], set()
        for s in selections:
            if s["code"] in skip: continue
            lab = get_lab_code(s["code"])
            if lab and lab in codes:
                lab_sec = next(x for x in selections if x["code"] == lab)
                bundles.append([s, lab_sec]); skip.add(lab)
            else:
                theory = get_theory_code(s["code"])
                if theory and theory in codes:
                    skip.add(s["code"])
                else:
                    bundles.append([s])
        return bundles

    def move_bundle_up(self):
        pos = self.prio_listbox.curselection()
        if not pos or pos[0] == 0: return
        i = pos[0]
        self.prio_bundles[i], self.prio_bundles[i-1] = self.prio_bundles[i-1], self.prio_bundles[i]
        t, p = self.prio_listbox.get(i), self.prio_listbox.get(i-1)
        self.prio_listbox.delete(i);   self.prio_listbox.insert(i, p)
        self.prio_listbox.delete(i-1); self.prio_listbox.insert(i-1, t)
        self.prio_listbox.selection_set(i-1)
        self.wizard_selections = [s for b in self.prio_bundles for s in b]

    def move_bundle_down(self):
        pos = self.prio_listbox.curselection()
        if not pos or pos[0] == self.prio_listbox.size()-1: return
        i = pos[0]
        self.prio_bundles[i], self.prio_bundles[i+1] = self.prio_bundles[i+1], self.prio_bundles[i]
        t, n = self.prio_listbox.get(i), self.prio_listbox.get(i+1)
        self.prio_listbox.delete(i+1); self.prio_listbox.insert(i+1, t)
        self.prio_listbox.delete(i);   self.prio_listbox.insert(i, n)
        self.prio_listbox.selection_set(i+1)
        self.wizard_selections = [s for b in self.prio_bundles for s in b]

    def save_wizard_combo(self):
        if not self.wizard_selections:
            messagebox.showwarning("Empty", "Pick at least one course first.")
            return
        new_id = max([c["id"] for c in self.plans["combos"]], default=0) + 1
        new_combo = {"id": new_id,
                     "sections": self.wizard_selections,
                     "picking_order": [s["code"] for s in self.wizard_selections]}
        cur_sig = {s["code"]: s["slots"]+"||"+s["professor"] for s in self.wizard_selections}
        for ex in self.plans["combos"]:
            if cur_sig == {s["code"]: s["slots"]+"||"+s["professor"] for s in ex["sections"]}:
                messagebox.showwarning("Duplicate", f"Identical plan already exists (ID {ex['id']}).")
                return
        self.plans["combos"].append(new_combo)
        save_plans(self.plans)
        messagebox.showinfo("Saved", "Combination saved successfully!")
        self.notebook.select(0)

    # =========================================================================
    # TAB 3 – LIVE TRACKER
    # =========================================================================
    def setup_live_tab(self):
        hdr = tk.Frame(self.tab_live, bg=self.surface,
                       highlightbackground=self.border, highlightthickness=1)
        hdr.pack(fill="x")

        tk.Label(hdr, text="⚡ Live Counseling Tracker",
                 font=("Helvetica", 15, "bold"), fg=self.text, bg=self.surface
                 ).pack(side="left", padx=16, pady=10)
        self.live_status_lbl = tk.Label(hdr, text="",
                                         font=("Helvetica", 12, "bold"),
                                         fg=self.success, bg=self.surface)
        self.live_status_lbl.pack(side="right", padx=16)

        body = tk.Frame(self.tab_live, bg=self.bg)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # locked chain
        prog_frame = tk.LabelFrame(body, text="  Locked Selections  ",
                                    font=("Helvetica", 12, "bold"),
                                    fg=self.text, bg=self.bg,
                                    relief="flat",
                                    highlightbackground=self.border,
                                    highlightthickness=1)
        prog_frame.pack(fill="x", pady=(0,8))
        self.live_progress_frame = tk.Frame(prog_frame, bg=self.bg)
        self.live_progress_frame.pack(fill="x", padx=10, pady=8)

        # next options
        choices_frame = tk.LabelFrame(body, text="  Next Options  ",
                                       font=("Helvetica", 12, "bold"),
                                       fg=self.text, bg=self.bg,
                                       relief="flat",
                                       highlightbackground=self.border,
                                       highlightthickness=1)
        choices_frame.pack(fill="both", expand=True)

        self.live_canvas = tk.Canvas(choices_frame, bg=self.bg, highlightthickness=0)
        live_sb = ttk.Scrollbar(choices_frame, orient="vertical", command=self.live_canvas.yview)
        self.live_scroll_frame = tk.Frame(self.live_canvas, bg=self.bg)
        self.live_scroll_frame.bind("<Configure>",
            lambda e: self.live_canvas.configure(scrollregion=self.live_canvas.bbox("all")))
        self.live_canvas.create_window((0,0), window=self.live_scroll_frame, anchor="nw")
        self.live_canvas.configure(yscrollcommand=live_sb.set)
        self.live_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        live_sb.pack(side="right", fill="y")

        foot = tk.Frame(self.tab_live, bg=self.surface,
                        highlightbackground=self.border, highlightthickness=1)
        foot.pack(fill="x", side="bottom")
        self.btn(foot, "↩ Undo Last", self.live_handle_back,   "danger" ).pack(side="left",  padx=10, pady=8)
        self.btn(foot, "🔄 Reset",    self.initialize_live_mode, "muted").pack(side="right", padx=10, pady=8)

    def initialize_live_mode(self):
        self.plans = load_plans("plans.json")
        self.live_locked_sections = []
        self.refresh_live_decision_tree()

    def refresh_live_decision_tree(self):
        for w in self.live_scroll_frame.winfo_children():  w.destroy()
        for w in self.live_progress_frame.winfo_children(): w.destroy()

        N = len(self.live_locked_sections)
        self.live_active_combos = []

        for combo in self.plans["combos"]:
            if len(combo["picking_order"]) < N:
                continue
            ok = True
            for i in range(N):
                ls = self.live_locked_sections[i]
                ec = combo["picking_order"][i]
                if ls["code"] != ec:
                    ok = False; break
                cs = next(s for s in combo["sections"] if s["code"] == ec)
                if cs["slots"] != ls["slots"] or cs["professor"] != ls["professor"]:
                    ok = False; break
            if ok:
                self.live_active_combos.append(combo)

        if not self.live_active_combos and N > 0:
            tk.Label(self.live_scroll_frame,
                     text="❌  No surviving plan paths match your selections.",
                     font=("Helvetica", 13, "bold"), fg=self.danger, bg=self.bg
                     ).pack(pady=40)
            self.live_status_lbl.config(text="Paths remaining: 0")
            return

        if not self.live_locked_sections:
            tk.Label(self.live_progress_frame,
                     text="No selections yet. Choose a course below to begin.",
                     font=("Helvetica", 11, "italic"), fg=self.text2, bg=self.bg
                     ).pack(anchor="w")
        else:
            for i, sec in enumerate(self.live_locked_sections, 1):
                timings = get_timings_for_slots(sec['slots'], self.slot_timing_map)
                row = tk.Frame(self.live_progress_frame, bg=self.success_bg,
                               highlightbackground=self.success, highlightthickness=1)
                row.pack(fill="x", pady=2, padx=2)
                tk.Label(row,
                         text=f"✅ {i}. {sec['code']} — {sec['name']}   |   👤 {sec['professor']}   🗓 {sec['slots']}   📋 {sec['tt_code']}",
                         font=("Helvetica", 11, "bold"), fg=self.success, bg=self.success_bg,
                         anchor="w").pack(anchor="w", padx=8, pady=(4,0))
                tk.Label(row, text=f"🕐 {timings}",
                         font=("Helvetica", 10), fg=self.success, bg=self.success_bg,
                         anchor="w").pack(anchor="w", padx=8, pady=(0,4))

        # compute next options
        next_opts, seen, weights = [], set(), {}
        for combo in self.live_active_combos:
            if len(combo["picking_order"]) > N:
                nc  = combo["picking_order"][N]
                sec = next(s for s in combo["sections"] if s["code"] == nc)
                key = (sec["code"], sec["slots"], sec["professor"])
                weights[key] = weights.get(key, 0) + 1
                if key not in seen:
                    seen.add(key); next_opts.append(sec)

        self.live_status_lbl.config(text=f"Surviving plans: {len(self.live_active_combos)}")

        if not next_opts:
            if self.live_active_combos:
                tk.Label(self.live_scroll_frame,
                         text="🎉 All done! Your selections match your saved plans perfectly.",
                         font=("Helvetica", 14, "bold"), fg=self.success, bg=self.bg,
                         justify="center").pack(pady=50)
            else:
                tk.Label(self.live_scroll_frame,
                         text="No combinations available.",
                         font=("Helvetica", 12, "italic"), fg=self.text2, bg=self.bg
                         ).pack(pady=40)
            return

        for opt in next_opts:
            key    = (opt["code"], opt["slots"], opt["professor"])
            weight = weights.get(key, 0)
            timings = get_timings_for_slots(opt['slots'], self.slot_timing_map)

            card = self.card_frame(self.live_scroll_frame)
            card.pack(fill="x", pady=4, padx=8)

            info = tk.Frame(card, bg=self.surface)
            info.pack(side="left", fill="both", expand=True, padx=12, pady=10)

            tk.Label(info, text=f"{opt['code']} — {opt['name']}",
                     font=("Helvetica", 12, "bold"), fg=self.text, bg=self.surface,
                     anchor="w").pack(anchor="w")
            tk.Label(info, text=f"👤 {opt['professor']}   🗓 {opt['slots']}   📋 {opt['tt_code']}",
                     font=("Helvetica", 11), fg=self.text2, bg=self.surface,
                     anchor="w").pack(anchor="w")
            tk.Label(info, text=f"🕐 {timings}",
                     font=("Helvetica", 11), fg=self.accent, bg=self.surface,
                     anchor="w", wraplength=650).pack(anchor="w", pady=(2,0))

            right_col = tk.Frame(card, bg=self.surface)
            right_col.pack(side="right", padx=12, pady=10)
            self.badge(right_col, f"{weight} plan{'s' if weight!=1 else ''}", "info").pack(pady=(0,6))
            self.btn(right_col, "Secure ✓",
                     lambda t=opt: self.live_handle_select(t),
                     "success").pack()

    def live_handle_select(self, sec):
        self.live_locked_sections.append(sec)
        self.refresh_live_decision_tree()

    def live_handle_back(self):
        if not self.live_locked_sections: return
        self.live_locked_sections.pop()
        self.refresh_live_decision_tree()


if __name__ == "__main__":
    root = tk.Tk()
    app  = MasterCounsellingApp(root)
    root.mainloop()
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
        "MON": ["A1", "F1", "D1", "TB1", "TG1", "A2", "F2", "D2", "TB2", "TG2", "V3"],
        "TUE": ["B1", "G1", "E1", "TC1", "TAA1", "B2", "G2", "E2", "TC2", "TAA2", "V4"],
        "WED": ["C1", "A1", "F1", "V1", "V2", "C2", "A2", "F2", "TD2", "TBB2", "V5"],
        "THU": ["D1", "B1", "G1", "TE1", "TCC1", "D2", "B2", "G2", "TE2", "TCC2", "V6"],
        "FRI": ["E1", "C1", "TA1", "TF1", "TD1", "E2", "C2", "TA2", "TF2", "TDD2", "V7"]
    }
    lab_headers = [
        "08:00 AM - 08:50 AM", "08:51 AM - 09:40 AM", "09:51 AM - 10:40 AM", 
        "10:41 AM - 11:30 AM", "11:40 AM - 12:30 PM", "12:31 PM - 1:20 PM", 
        "2:00 PM - 2:50 PM", "2:51 PM - 3:40 PM", "3:51 PM - 4:40 PM", 
        "4:41 PM - 5:30 PM", "5:40 PM - 6:30 PM", "6:31 PM - 7:20 PM"
    ]
    lab_grid = {
        "MON": ["L1", "L2", "L3", "L4", "L5", "L6", "L31", "L32", "L33", "L34", "L35", "L36"],
        "TUE": ["L7", "L8", "L9", "L10", "L11", "L12", "L37", "L38", "L39", "L40", "L41", "L42"],
        "WED": ["L13", "L14", "L15", "L16", "L17", "L18", "L43", "L44", "L45", "L46", "L47", "L48"],
        "THU": ["L19", "L20", "L21", "L22", "L23", "L24", "L49", "L50", "L51", "L52", "L53", "L54"],
        "FRI": ["L25", "L26", "L27", "L28", "L29", "L30", "L55", "L56", "L57", "L58", "L59", "L60"]
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
    """Returns a mapping from slot name -> human-readable timing string."""
    t_headers, t_grid, l_headers, l_grid = get_timetable_data()
    slot_timing = {}
    for day, slots in t_grid.items():
        for idx, slot in enumerate(slots):
            if slot and slot != "—" and slot not in slot_timing:
                slot_timing[slot] = t_headers[idx]
    for day, slots in l_grid.items():
        for idx, slot in enumerate(slots):
            if slot and slot not in slot_timing:
                slot_timing[slot] = l_headers[idx]
    return slot_timing

def get_timings_for_slots(raw_slots, slot_timing_map):
    """Given a raw slot string like 'A1+TA2', return a display string of timings."""
    parts = [s.strip() for s in raw_slots.split('+')]
    timings = []
    for slot in parts:
        if slot in slot_timing_map:
            timings.append(f"{slot}: {slot_timing_map[slot]}")
        else:
            timings.append(slot)
    return " | ".join(timings)

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

def is_theory_lab_pair(code1, code2):
    """Returns True if code1 and code2 are theory/lab pairs."""
    if code1.endswith('L') and code2.endswith('P'):
        return code1[:-1] == code2[:-1]
    if code1.endswith('P') and code2.endswith('L'):
        return code1[:-1] == code2[:-1]
    return False


# ==============================================================================
# 2. MAIN APPLICATION GUI CLASS
# ==============================================================================

class MasterCounsellingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Master Course Counseling Suite")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1e1e2e")
        
        # Load Baseline Datasets
        self.courses_dict = load_courses_from_csv("CourseList.csv")
        self.plans = load_plans("plans.json")
        self.slot_timing_map = generate_slot_timing_map()
        
        if not self.courses_dict:
            messagebox.showerror("Missing Data", "CourseList.csv not found or empty! Please populate it first.")
            self.root.destroy()
            return

        # UI Color Profiles
        self.bg_color = "#1e1e2e"
        self.card_color = "#252538"
        self.accent_color = "#89b4fa"
        self.text_color = "#cdd6f4"
        self.muted_text = "#7f849c"
        self.success_color = "#a6e3a1"
        self.alert_color = "#f38ba8"

        # Apply Global styles to UI Tabs
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.card_color, foreground=self.text_color, padding=[15, 5], font=("Helvetica", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.accent_color)], foreground=[("selected", "#11111b")])

        # Create Core Notebook Layout Tab Navigation Framework
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_view = tk.Frame(self.notebook, bg=self.bg_color)
        self.tab_build = tk.Frame(self.notebook, bg=self.bg_color)
        self.tab_live = tk.Frame(self.notebook, bg=self.bg_color)

        self.notebook.add(self.tab_view, text=" 📂 Saved Combinations ")
        self.notebook.add(self.tab_build, text=" 🔨 Create New Plan Wizard ")
        self.notebook.add(self.tab_live, text=" ⚡ Live Assistant Tree Mode ")

        # Bind tab change event to refresh datasets safely
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Setup individual structures
        self.setup_view_tab()
        self.setup_build_tab()
        self.setup_live_tab()

    def on_tab_changed(self, event):
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            self.refresh_view_tab()
        elif current_tab == 1:
            self.reset_builder_wizard()
        elif current_tab == 2:
            self.initialize_live_mode()

    def format_course_display(self, sec):
        """Returns a multi-line display string for a course section including timings."""
        if sec.get("is_blank"):
            return f"Course: {sec['code']} | {sec.get('name', '')}\n[ BLANK SLOT ] — Free for timing adjustments"
        timings = get_timings_for_slots(sec['slots'], self.slot_timing_map)
        return (
            f"Course: {sec['code']} — {sec.get('name', '')}\n"
            f"Slots: {sec['slots']}  |  Prof: {sec['professor']}\n"
            f"Timings: {timings}\n"
            f"TT Code: {sec['tt_code']}"
        )

    # ==========================================================================
    # TAB 1: VIEW & MANAGE REPOSITORY LOGIC
    # ==========================================================================
    def setup_view_tab(self):
        header = tk.Frame(self.tab_view, bg=self.card_color, height=50)
        header.pack(fill="x", side="top")
        tk.Label(header, text="SAVED BLUEPRINT DATABASE REPOSITORY", font=("Helvetica", 12, "bold"), bg=self.card_color, fg=self.text_color).pack(pady=10, padx=15, side="left")
        
        container = tk.Frame(self.tab_view, bg=self.bg_color)
        container.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.view_canvas = tk.Canvas(container, bg=self.bg_color, highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=self.view_canvas.yview)
        self.view_scroll_frame = tk.Frame(self.view_canvas, bg=self.bg_color)
        
        self.view_scroll_frame.bind("<Configure>", lambda e: self.view_canvas.configure(scrollregion=self.view_canvas.bbox("all")))
        self.view_canvas.create_window((0, 0), window=self.view_scroll_frame, anchor="nw")
        self.view_canvas.configure(yscrollcommand=v_scroll.set)
        
        self.view_canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

    def refresh_view_tab(self):
        for w in self.view_scroll_frame.winfo_children():
            w.destroy()
            
        self.plans = load_plans("plans.json")
        if not self.plans["combos"]:
            tk.Label(self.view_scroll_frame, text="No combinations saved yet. Go to the 'Create New Plan Wizard' tab to construct one!", font=("Helvetica", 11, "italic"), fg=self.muted_text, bg=self.bg_color).pack(pady=50, padx=50)
            return

        for idx, combo in enumerate(self.plans["combos"], 1):
            card = tk.Frame(self.view_scroll_frame, bg=self.card_color, bd=1, relief="solid", highlightbackground="#45475a")
            card.pack(fill="x", expand=True, pady=8, padx=10)
            
            lbl_title = tk.Label(card, text=f"Combination #{idx} (System ID: {combo['id']})", font=("Helvetica", 11, "bold"), fg=self.accent_color, bg=self.card_color)
            lbl_title.pack(anchor="w", padx=15, pady=(10, 5))
            
            for code in combo["picking_order"]:
                sec = next(s for s in combo["sections"] if s["code"] == code)
                timings = get_timings_for_slots(sec['slots'], self.slot_timing_map) if not sec.get("is_blank") else "—"
                sec_text = (
                    f" • {sec['code']:<8} | {sec.get('name',''):<30} | Slots: {sec['slots']:<12} | "
                    f"Prof: {sec['professor']}\n"
                    f"   {'':8}   Timings: {timings}"
                )
                tk.Label(card, text=sec_text, font=("Courier", 9, "bold"), fg=self.text_color, bg=self.card_color, justify="left", anchor="w").pack(anchor="w", padx=25)
                
            # Control Configuration Button Pack Stack
            del_btn = tk.Button(card, text="Delete Plan", font=("Helvetica", 9, "bold"), bg=self.alert_color, fg="#11111b", relief="flat", command=lambda cid=combo['id']: self.delete_combo(cid))
            del_btn.pack(side="right", padx=(5, 15), pady=10)

            mod_btn = tk.Button(card, text="Modify Plan", font=("Helvetica", 9, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=lambda cid=combo['id']: self.open_modify_dialog(cid))
            mod_btn.pack(side="right", padx=5, pady=10)

            branch_btn = tk.Button(card, text="Branch Plan", font=("Helvetica", 9, "bold"), bg=self.success_color, fg="#11111b", relief="flat", command=lambda cid=combo['id']: self.branch_combo(cid))
            branch_btn.pack(side="right", padx=5, pady=10)

    def delete_combo(self, combo_id):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to remove this schedule combination from your system?"):
            self.plans["combos"] = [c for c in self.plans["combos"] if c["id"] != combo_id]
            save_plans(self.plans)
            self.refresh_view_tab()

    # ==========================================================================
    # BRANCH & MODIFY SUB-ROUTINE MODAL GUI ENGINE
    # ==========================================================================
    def branch_combo(self, combo_id):
        base_combo = next(c for c in self.plans["combos"] if c["id"] == combo_id)
        cloned_sections = copy.deepcopy(base_combo["sections"])
        cloned_order = copy.deepcopy(base_combo["picking_order"])
        
        new_id = max([c["id"] for c in self.plans["combos"]], default=0) + 1
        branched_combo = {
            "id": new_id,
            "sections": cloned_sections,
            "picking_order": cloned_order
        }
        
        self.plans["combos"].append(branched_combo)
        save_plans(self.plans)
        self.refresh_view_tab()
        
        messagebox.showinfo("Branched Successfully", f"Plan cloned successfully as Blueprint Clone ID: {new_id}.\nOpening modification console panel next...")
        self.open_modify_dialog(new_id)

    def open_modify_dialog(self, combo_id):
        combo = next(c for c in self.plans["combos"] if c["id"] == combo_id)
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Modify Plan Workspace — Blueprint ID: {combo_id}")
        dialog.geometry("1050x700")
        dialog.configure(bg=self.bg_color)
        dialog.grab_set()
        
        dialog.working_combo = copy.deepcopy(combo)
        self.render_modify_main_view(dialog, combo_id)

    def render_modify_main_view(self, dialog, combo_id):
        for w in dialog.winfo_children(): w.destroy()
            
        main_container = tk.Frame(dialog, bg=self.bg_color)
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        left_frame = tk.LabelFrame(main_container, text=" Course Sections Configuration ", font=("Helvetica", 10, "bold"), bg=self.bg_color, fg=self.accent_color, bd=2)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_frame = tk.LabelFrame(main_container, text=" Adjust Step Picking Sequence Priority ", font=("Helvetica", 10, "bold"), bg=self.bg_color, fg=self.accent_color, bd=2)
        right_frame.pack(side="right", fill="both", padx=(10, 0))
        
        # Populate Left View (Scrollable List of Current Track Elements)
        canvas = tk.Canvas(left_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=self.bg_color)
        scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        for code in dialog.working_combo["picking_order"]:
            sec = next(s for s in dialog.working_combo["sections"] if s["code"] == code)
            card = tk.Frame(scroll_content, bg=self.card_color, bd=1, relief="solid", highlightbackground="#45475a")
            card.pack(fill="x", expand=True, pady=5, padx=5)
            
            desc = self.format_course_display(sec)
            tk.Label(card, text=desc, font=("Courier", 9, "bold"), bg=self.card_color,
                     fg=self.muted_text if sec.get("is_blank") else self.text_color,
                     justify="left", anchor="w").pack(side="left", padx=10, pady=8)
            
            btn_subframe = tk.Frame(card, bg=self.card_color)
            btn_subframe.pack(side="right", padx=10, pady=8)
            
            rep_btn = tk.Button(btn_subframe, text="Change Section", font=("Helvetica", 9, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=lambda tc=code: self.render_replace_section_view(dialog, combo_id, tc))
            rep_btn.pack(side="top", fill="x", pady=2)
            
            if not sec.get("is_blank"):
                blank_btn = tk.Button(btn_subframe, text="Make Blank", font=("Helvetica", 9, "bold"), bg=self.muted_text, fg="#11111b", relief="flat", command=lambda tc=code: self.apply_blank_slot(dialog, combo_id, tc))
                blank_btn.pack(side="top", fill="x", pady=2)
        
        # Populate Right View: bundle-aware sorting
        # Build bundles for picking order display
        bundles = self._build_order_bundles(dialog.working_combo)
        
        prio_listbox = tk.Listbox(right_frame, font=("Helvetica", 10, "bold"), bg=self.card_color, fg=self.text_color,
                                   selectbackground=self.accent_color, selectforeground="#11111b", highlightthickness=0, bd=1)
        prio_listbox.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        for bundle in bundles:
            if len(bundle) == 1:
                code = bundle[0]
                sec = next(s for s in dialog.working_combo["sections"] if s["code"] == code)
                prof_lbl = "BLANK" if sec.get("is_blank") else sec["professor"]
                prio_listbox.insert(tk.END, f" {sec['code']} ({prof_lbl})")
            else:
                # Theory+Lab bundle
                theory_code = next((c for c in bundle if c.endswith('L')), bundle[0])
                lab_code = next((c for c in bundle if c.endswith('P')), bundle[1])
                theory_sec = next(s for s in dialog.working_combo["sections"] if s["code"] == theory_code)
                prio_listbox.insert(tk.END, f" 📦 {theory_code}+{lab_code} ({theory_sec['professor']})")
            
        btn_pane = tk.Frame(right_frame, bg=self.bg_color)
        btn_pane.pack(side="right", fill="y", pady=10, padx=(0, 10))
        tk.Button(btn_pane, text="▲ Move Up", font=("Helvetica", 9, "bold"), bg=self.card_color, fg=self.text_color,
                  command=lambda: self.dialog_move_bundle_up(prio_listbox, dialog, bundles)).pack(fill="x", pady=2)
        tk.Button(btn_pane, text="▼ Move Down", font=("Helvetica", 9, "bold"), bg=self.card_color, fg=self.text_color,
                  command=lambda: self.dialog_move_bundle_down(prio_listbox, dialog, bundles)).pack(fill="x", pady=2)
        
        # Dialog Control Bottom Command Bar
        footer = tk.Frame(dialog, bg=self.bg_color)
        footer.pack(fill="x", side="bottom", padx=15, pady=10)
        
        save_btn = tk.Button(footer, text="💾 Save Changes", font=("Helvetica", 10, "bold"), bg=self.success_color, fg="#11111b", relief="flat", command=lambda: self.save_dialog_modifications(dialog, combo_id))
        save_btn.pack(side="right", padx=5)
        
        cancel_btn = tk.Button(footer, text="Discard & Cancel", font=("Helvetica", 10, "bold"), bg=self.alert_color, fg="#11111b", relief="flat", command=dialog.destroy)
        cancel_btn.pack(side="right", padx=5)

    def _build_order_bundles(self, working_combo):
        """Group picking_order into bundles: theory+lab pairs stay together, others are solo."""
        order = working_combo["picking_order"]
        bundles = []
        skip = set()
        for i, code in enumerate(order):
            if code in skip:
                continue
            lab_code = get_lab_code(code)
            if lab_code and lab_code in order:
                bundles.append([code, lab_code])
                skip.add(lab_code)
            else:
                theory_code = get_theory_code(code)
                if theory_code and theory_code in order:
                    # This is a lab course whose theory is already processed
                    skip.add(code)
                else:
                    bundles.append([code])
        return bundles

    def _bundles_to_order(self, bundles):
        """Flatten bundles back to a flat picking order list."""
        order = []
        for bundle in bundles:
            order.extend(bundle)
        return order

    def dialog_move_bundle_up(self, listbox, dialog, bundles):
        pos = listbox.curselection()
        if not pos or pos[0] == 0: return
        idx = pos[0]
        bundles[idx], bundles[idx-1] = bundles[idx-1], bundles[idx]
        dialog.working_combo["picking_order"] = self._bundles_to_order(bundles)
        # Refresh listbox
        text = listbox.get(idx)
        prev_text = listbox.get(idx-1)
        listbox.delete(idx)
        listbox.insert(idx, prev_text)
        listbox.delete(idx-1)
        listbox.insert(idx-1, text)
        listbox.selection_set(idx-1)

    def dialog_move_bundle_down(self, listbox, dialog, bundles):
        pos = listbox.curselection()
        if not pos or pos[0] == listbox.size() - 1: return
        idx = pos[0]
        bundles[idx], bundles[idx+1] = bundles[idx+1], bundles[idx]
        dialog.working_combo["picking_order"] = self._bundles_to_order(bundles)
        text = listbox.get(idx)
        next_text = listbox.get(idx+1)
        listbox.delete(idx+1)
        listbox.insert(idx+1, text)
        listbox.delete(idx)
        listbox.insert(idx, next_text)
        listbox.selection_set(idx+1)

    def apply_blank_slot(self, dialog, combo_id, target_code):
        sec_idx = next(i for i, s in enumerate(dialog.working_combo["sections"]) if s["code"] == target_code)
        dialog.working_combo["sections"][sec_idx] = {
            "code": target_code,
            "name": self.courses_dict[target_code][0]["name"] if target_code in self.courses_dict else target_code,
            "slots": "—", "tt_code": "—", "professor": "—", "type": "—",
            "minute_blocks": [],
            "is_blank": True
        }
        self.render_modify_main_view(dialog, combo_id)

    def render_replace_section_view(self, dialog, combo_id, target_code):
        for w in dialog.winfo_children(): w.destroy()
            
        container = tk.Frame(dialog, bg=self.bg_color)
        container.pack(fill="both", expand=True, padx=15, pady=15)
        
        course_name = self.courses_dict[target_code][0]["name"] if target_code in self.courses_dict else target_code
        
        dk_header = tk.Frame(container, bg=self.bg_color)
        dk_header.pack(fill="x", pady=(0,15))
        tk.Label(dk_header, text="Modify target context focus course branch: ", font=("Helvetica", 10), fg=self.text_color, bg=self.bg_color).pack(side="left")
        
        # Show course code + name in modify dropdown
        order_codes = dialog.working_combo["picking_order"]
        dropdown_display = []
        for c in order_codes:
            cname = self.courses_dict[c][0]["name"] if c in self.courses_dict else c
            dropdown_display.append(f"{c} — {cname}")
        
        target_display = f"{target_code} — {course_name}"
        mod_dropdown = ttk.Combobox(dk_header, values=dropdown_display, state="readonly", font=("Helvetica", 10, "bold"), width=30)
        mod_dropdown.set(target_display)
        mod_dropdown.pack(side="left", padx=5)
        
        def on_dropdown_select(event):
            selected = mod_dropdown.get()
            code_part = selected.split(" — ")[0].strip()
            self.render_replace_section_view(dialog, combo_id, code_part)
        
        mod_dropdown.bind("<<ComboboxSelected>>", on_dropdown_select)

        tk.Label(container, text=f"Replace Section Sequence for: {target_code} — {course_name}", font=("Helvetica", 12, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w", pady=(0, 15))
        
        sec_idx_in_combo = next(i for i, s in enumerate(dialog.working_combo["sections"]) if s["code"] == target_code)
        
        occupied_minutes = set()
        for i, sec in enumerate(dialog.working_combo["sections"]):
            if i != sec_idx_in_combo and not sec.get("is_blank"):
                occupied_minutes.update(tuple(x) for x in sec["minute_blocks"])
        
        # Determine if target is a lab course — if so, filter by matching theory professor
        lab_prof_filter = None
        theory_code_for_lab = get_theory_code(target_code)  # returns *L code if target ends with P
        if theory_code_for_lab and theory_code_for_lab in [s["code"] for s in dialog.working_combo["sections"]]:
            theory_sec = next((s for s in dialog.working_combo["sections"] if s["code"] == theory_code_for_lab), None)
            if theory_sec and not theory_sec.get("is_blank"):
                lab_prof_filter = theory_sec["professor"]
                
        all_sections = self.courses_dict.get(target_code, [])
        valid_options = []
        for sec in all_sections:
            if lab_prof_filter and sec["professor"] != lab_prof_filter:
                continue
            sec_min = set(tuple(x) for x in sec["minute_blocks"])
            if occupied_minutes.isdisjoint(sec_min):
                valid_options.append(sec)
                
        if not valid_options:
            msg = "⚠️ CRITICAL LAYOUT CONFLICT: No available clash-free slots exist for this item\nwithout shifting early anchor positions or marking other components blank first."
            if lab_prof_filter:
                msg += f"\n\n(Lab filtered to professor: {lab_prof_filter})"
            tk.Label(container, text=msg, font=("Helvetica", 11, "bold"), fg=self.alert_color, bg=self.bg_color, justify="left").pack(pady=30)
            tk.Button(container, text="↩ Back to Blueprint Panel", font=("Helvetica", 10, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=lambda: self.render_modify_main_view(dialog, combo_id)).pack(pady=5)
            return

        if lab_prof_filter:
            tk.Label(container, text=f"🔒 Lab sections filtered to professor: {lab_prof_filter}", font=("Helvetica", 9, "italic"), fg="#cba6f7", bg=self.bg_color).pack(anchor="w", pady=(0, 8))

        scroll_frame_container = tk.Frame(container, bg=self.bg_color)
        scroll_frame_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(scroll_frame_container, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_frame_container, orient="vertical", command=canvas.yview)
        list_frame = tk.Frame(canvas, bg=self.bg_color)
        
        list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for opt in valid_options:
            btn_card = tk.Frame(list_frame, bg=self.card_color, bd=1, relief="solid", highlightbackground="#45475a")
            btn_card.pack(fill="x", expand=True, pady=4, padx=5)
            
            timings = get_timings_for_slots(opt['slots'], self.slot_timing_map)
            desc = (f"Slots: {opt['slots']:<12} | Professor: {opt['professor']:<25}\n"
                    f"Timings: {timings}\n"
                    f"TT Code: {opt['tt_code']}")
            tk.Label(btn_card, text=desc, font=("Courier", 9, "bold"), bg=self.card_color, fg=self.text_color, justify="left", anchor="w").pack(side="left", padx=10, pady=8)
            
            sel_btn = tk.Button(btn_card, text="Select Section", font=("Helvetica", 9, "bold"), bg=self.success_color, fg="#11111b", relief="flat", command=lambda choice_sec=opt: self.apply_section_replacement(dialog, combo_id, sec_idx_in_combo, choice_sec))
            sel_btn.pack(side="right", padx=10, pady=8)
            
        tk.Button(container, text="↩ Cancel / Return Back", font=("Helvetica", 10, "bold"), bg=self.alert_color, fg="#11111b", relief="flat", command=lambda: self.render_modify_main_view(dialog, combo_id)).pack(anchor="w", pady=(15, 0))

    def apply_section_replacement(self, dialog, combo_id, sec_idx, choice_sec):
        new_sec = copy.deepcopy(choice_sec)
        new_sec["is_blank"] = False
        dialog.working_combo["sections"][sec_idx] = new_sec
        self.render_modify_main_view(dialog, combo_id)

    def save_dialog_modifications(self, dialog, combo_id):
        for sec in dialog.working_combo["sections"]:
            if sec.get("is_blank"):
                messagebox.showerror("Validation Failed", f"Cannot commit configuration plan updates! Course code '{sec['code']}' is currently set as a Blank Slot. Please assign a valid timing section first.")
                return

        current_sig = {s["code"]: s["slots"] + "||" + s["professor"] for s in dialog.working_combo["sections"]}
        
        for existing in self.plans["combos"]:
            if existing["id"] == combo_id: continue
            ex_sig = {s["code"]: s["slots"] + "||" + s["professor"] for s in existing["sections"]}
            if current_sig == ex_sig:
                messagebox.showwarning("Duplicate Layout Found", f"Clash error! This modified setup profile configuration matches an existing blueprint entry (System ID {existing['id']}).")
                return
                
        idx_to_update = next(i for i, c in enumerate(self.plans["combos"]) if c["id"] == combo_id)
        self.plans["combos"][idx_to_update] = dialog.working_combo
        save_plans(self.plans)
        
        messagebox.showinfo("Success", "Combination configuration successfully modified and tracked to core records!")
        dialog.destroy()
        self.refresh_view_tab()


    # ==========================================================================
    # TAB 2: INTERACTIVE PLAN BUILDER WIZARD LOGIC
    # ==========================================================================
    def setup_build_tab(self):
        self.left_panel = tk.Frame(self.tab_build, bg=self.bg_color, width=450)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        
        self.right_panel = tk.LabelFrame(self.tab_build, text=" Selection Configuration Matrix Stack Summary ", font=("Helvetica", 10, "bold"), bg=self.bg_color, fg=self.accent_color, bd=2)
        self.right_panel.pack(side="right", fill="both", padx=15, pady=15)
        
        self.builder_course_codes = list(self.courses_dict.keys())
        self.reset_builder_wizard()

    def reset_builder_wizard(self):
        self.wizard_step = 0
        self.wizard_selections = []
        self.wizard_occupied_minutes = set()
        self.render_builder_step()

    def render_builder_step(self):
        for w in self.left_panel.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        tk.Label(self.right_panel, text="Current Step Selections Footprint:", font=("Helvetica", 10, "bold"), bg=self.bg_color, fg=self.text_color).pack(anchor="w", padx=10, pady=5)
        for s in self.wizard_selections:
            timings = get_timings_for_slots(s['slots'], self.slot_timing_map)
            tk.Label(self.right_panel,
                     text=f"✔ {s['code']} — {s['name']}\n   {s['slots']} | {s['professor']}\n   {timings}",
                     font=("Helvetica", 9), fg=self.success_color, bg=self.bg_color, justify="left").pack(anchor="w", padx=20, pady=2)

        selected_codes = [s["code"] for s in self.wizard_selections]
        remaining_codes = [c for c in self.builder_course_codes if c not in selected_codes]

        # Determine if next selection should be a locked lab (paired to last theory)
        locked_lab_code = None
        locked_lab_prof = None
        if self.wizard_selections:
            last_sel = self.wizard_selections[-1]
            lab_code = get_lab_code(last_sel["code"])
            if lab_code and lab_code in self.courses_dict and lab_code not in selected_codes:
                locked_lab_code = lab_code
                locked_lab_prof = last_sel["professor"]

        if remaining_codes or locked_lab_code:
            header_row = tk.Frame(self.left_panel, bg=self.bg_color)
            header_row.pack(fill="x", pady=(0, 10))

            if locked_lab_code:
                # Force-select lab course next
                tk.Label(header_row,
                         text=f"🔒 Next: Lab for {locked_lab_code} (locked to Prof: {locked_lab_prof})",
                         font=("Helvetica", 10, "bold"), fg="#cba6f7", bg=self.bg_color).pack(side="left")
                current_code = locked_lab_code
            else:
                tk.Label(header_row, text="Choose Course: ", font=("Helvetica", 10), fg=self.muted_text, bg=self.bg_color).pack(side="left")

                # Build dropdown showing "CODE — Name"
                display_values = []
                for c in remaining_codes:
                    cname = self.courses_dict[c][0]["name"] if c in self.courses_dict else c
                    display_values.append(f"{c} — {cname}")

                course_cb = ttk.Combobox(header_row, values=display_values, state="readonly", font=("Helvetica", 10, "bold"), width=32)
                course_cb.pack(side="left", padx=5)
                course_cb.set(display_values[0])
                current_code = remaining_codes[0]

                def change_focus_course(event):
                    selected_display = course_cb.get()
                    code_part = selected_display.split(" — ")[0].strip()
                    self.render_sections_for_selected_course(code_part, prof_filter=None)

                course_cb.bind("<<ComboboxSelected>>", change_focus_course)

            # "Save Combo" button — allows stopping selection at any point
            if self.wizard_selections:
                save_now_btn = tk.Button(header_row, text="💾 Save Combo & Set Order",
                                         font=("Helvetica", 9, "bold"), bg=self.success_color, fg="#11111b",
                                         relief="flat", command=self.render_priority_sorting_interface)
                save_now_btn.pack(side="right", padx=10)

            self.builder_sections_container = tk.Frame(self.left_panel, bg=self.bg_color)
            self.builder_sections_container.pack(fill="both", expand=True)

            prof_filter = locked_lab_prof if locked_lab_code else None
            self.render_sections_for_selected_course(current_code if locked_lab_code else remaining_codes[0], prof_filter=prof_filter)

            if locked_lab_code:
                # Bind the combobox for the locked lab scenario (no dropdown, just render)
                pass
        else:
            self.render_priority_sorting_interface()

    def render_sections_for_selected_course(self, current_code, prof_filter=None):
        for w in self.builder_sections_container.winfo_children(): w.destroy()
            
        course_name = self.courses_dict[current_code][0]["name"] if current_code in self.courses_dict else current_code
        title_text = f"{current_code} — {course_name}"
        if prof_filter:
            title_text += f"  🔒 (Prof locked: {prof_filter})"
        title = tk.Label(self.builder_sections_container, text=title_text, font=("Helvetica", 14, "bold"), fg=self.accent_color, bg=self.bg_color)
        title.pack(anchor="w", pady=(5, 15))
        
        all_sections = self.courses_dict.get(current_code, [])
        valid_options = []
        for sec in all_sections:
            if prof_filter and sec["professor"] != prof_filter:
                continue
            sec_blocks = set(tuple(x) for x in sec["minute_blocks"])
            if self.wizard_occupied_minutes.isdisjoint(sec_blocks):
                valid_options.append(sec)
                
        if not valid_options:
            msg = "⚠️ CRITICAL ERROR: Class Overlap Conflict!\nNo available slots remain open for this course given earlier choices."
            if prof_filter:
                msg += f"\n(Filtered to professor: {prof_filter})"
            tk.Label(self.builder_sections_container, text=msg, font=("Helvetica", 11, "bold"), fg=self.alert_color, bg=self.bg_color, justify="left").pack(pady=20)
            tk.Button(self.builder_sections_container, text="↩ Restart Wizard from Beginning", font=("Helvetica", 10, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=self.reset_builder_wizard).pack(pady=10)
            return
            
        scroll_frame_container = tk.Frame(self.builder_sections_container, bg=self.bg_color)
        scroll_frame_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(scroll_frame_container, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_frame_container, orient="vertical", command=canvas.yview)
        list_frame = tk.Frame(canvas, bg=self.bg_color)
        
        list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for opt in valid_options:
            btn_card = tk.Frame(list_frame, bg=self.card_color, bd=1, relief="solid", highlightbackground="#45475a")
            btn_card.pack(fill="x", expand=True, pady=4, padx=5)
            
            timings = get_timings_for_slots(opt['slots'], self.slot_timing_map)
            desc = (f"Slots: {opt['slots']:<12} | Professor: {opt['professor']:<25}\n"
                    f"Timings: {timings}\n"
                    f"TT Code: {opt['tt_code']}")
            tk.Label(btn_card, text=desc, font=("Courier", 9, "bold"), bg=self.card_color, fg=self.text_color, justify="left", anchor="w").pack(side="left", padx=10, pady=8)
            
            sel_btn = tk.Button(btn_card, text="Pick Section", font=("Helvetica", 9, "bold"), bg=self.success_color, fg="#11111b", relief="flat", command=lambda choice_sec=opt: self.advance_builder_step(choice_sec))
            sel_btn.pack(side="right", padx=10, pady=8)

    def advance_builder_step(self, chosen_section):
        self.wizard_selections.append(chosen_section)
        self.wizard_occupied_minutes.update(tuple(x) for x in chosen_section["minute_blocks"])
        self.wizard_step += 1
        self.render_builder_step()

    def render_priority_sorting_interface(self):
        for w in self.left_panel.winfo_children(): w.destroy()

        lbl_prio = tk.Label(self.left_panel, text="🏁 Configure Picking Order Priority Sequence", font=("Helvetica", 13, "bold"), fg=self.success_color, bg=self.bg_color)
        lbl_prio.pack(anchor="w", pady=(0, 5))
        tk.Label(self.left_panel, text="Sort selections from top to bottom based on registration risk priority levels.\n📦 Theory+Lab pairs move together as a bundle.", font=("Helvetica", 9, "italic"), fg=self.muted_text, bg=self.bg_color).pack(anchor="w", pady=(0, 15))
        
        listbox_frame = tk.Frame(self.left_panel, bg=self.bg_color)
        listbox_frame.pack(fill="both", expand=True)
        
        self.prio_listbox = tk.Listbox(listbox_frame, font=("Helvetica", 10, "bold"), bg=self.card_color, fg=self.text_color,
                                        selectbackground=self.accent_color, selectforeground="#11111b", highlightthickness=0, bd=1)
        self.prio_listbox.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Build bundles from current selections
        self.prio_bundles = self._build_selection_bundles(self.wizard_selections)
        
        for bundle in self.prio_bundles:
            if len(bundle) == 1:
                s = bundle[0]
                self.prio_listbox.insert(tk.END, f"{s['code']} — {s['name']} ({s['professor']})")
            else:
                theory = next((s for s in bundle if s['code'].endswith('L')), bundle[0])
                lab = next((s for s in bundle if s['code'].endswith('P')), bundle[1])
                self.prio_listbox.insert(tk.END, f"📦 {theory['code']}+{lab['code']} — {theory['name']} ({theory['professor']})")
            
        btn_pane = tk.Frame(listbox_frame, bg=self.bg_color)
        btn_pane.pack(side="right", fill="y")
        
        tk.Button(btn_pane, text="▲ Move Up", font=("Helvetica", 9, "bold"), bg=self.card_color, fg=self.text_color, command=self.move_bundle_up).pack(fill="x", pady=2)
        tk.Button(btn_pane, text="▼ Move Down", font=("Helvetica", 9, "bold"), bg=self.card_color, fg=self.text_color, command=self.move_bundle_down).pack(fill="x", pady=2)
        
        save_btn = tk.Button(self.left_panel, text="💾 Commit Plan to Database File", font=("Helvetica", 11, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=self.save_wizard_combo)
        save_btn.pack(fill="x", pady=20)

    def _build_selection_bundles(self, selections):
        """Group wizard_selections into bundles of theory+lab pairs or solo."""
        codes = [s["code"] for s in selections]
        bundles = []
        skip = set()
        for s in selections:
            if s["code"] in skip:
                continue
            lab_code = get_lab_code(s["code"])
            if lab_code and lab_code in codes:
                lab_sec = next(x for x in selections if x["code"] == lab_code)
                bundles.append([s, lab_sec])
                skip.add(lab_code)
            else:
                theory_code = get_theory_code(s["code"])
                if theory_code and theory_code in codes:
                    skip.add(s["code"])
                else:
                    bundles.append([s])
        return bundles

    def move_bundle_up(self):
        pos = self.prio_listbox.curselection()
        if not pos or pos[0] == 0: return
        idx = pos[0]
        self.prio_bundles[idx], self.prio_bundles[idx-1] = self.prio_bundles[idx-1], self.prio_bundles[idx]
        # Rebuild listbox
        text = self.prio_listbox.get(idx)
        prev_text = self.prio_listbox.get(idx-1)
        self.prio_listbox.delete(idx)
        self.prio_listbox.insert(idx, prev_text)
        self.prio_listbox.delete(idx-1)
        self.prio_listbox.insert(idx-1, text)
        self.prio_listbox.selection_set(idx-1)
        # Sync wizard_selections order
        self.wizard_selections = [s for bundle in self.prio_bundles for s in bundle]

    def move_bundle_down(self):
        pos = self.prio_listbox.curselection()
        if not pos or pos[0] == self.prio_listbox.size() - 1: return
        idx = pos[0]
        self.prio_bundles[idx], self.prio_bundles[idx+1] = self.prio_bundles[idx+1], self.prio_bundles[idx]
        text = self.prio_listbox.get(idx)
        next_text = self.prio_listbox.get(idx+1)
        self.prio_listbox.delete(idx+1)
        self.prio_listbox.insert(idx+1, text)
        self.prio_listbox.delete(idx)
        self.prio_listbox.insert(idx, next_text)
        self.prio_listbox.selection_set(idx+1)
        self.wizard_selections = [s for bundle in self.prio_bundles for s in bundle]

    def save_wizard_combo(self):
        if not self.wizard_selections:
            messagebox.showwarning("Empty Plan", "No courses selected! Please select at least one course before saving.")
            return

        ordered_codes = [s["code"] for s in self.wizard_selections]
        
        new_id = max([c["id"] for c in self.plans["combos"]], default=0) + 1
        new_combo = {
            "id": new_id,
            "sections": self.wizard_selections,
            "picking_order": ordered_codes
        }
        
        current_sig = {s["code"]: s["slots"] + "||" + s["professor"] for s in self.wizard_selections}
        for existing in self.plans["combos"]:
            ex_sig = {s["code"]: s["slots"] + "||" + s["professor"] for s in existing["sections"]}
            if current_sig == ex_sig:
                messagebox.showwarning("Duplicate Layout Found", f"This exact setup profile configuration already exists as ID {existing['id']}.")
                return
                
        self.plans["combos"].append(new_combo)
        save_plans(self.plans)
        messagebox.showinfo("Success", "Combination configuration successfully tracked and saved to database profiles!")
        self.notebook.select(0)


    # ==========================================================================
    # TAB 3: LIVE COUNSELING TRACKER SYSTEM (STRICT PREFIX DECISION TREE)
    # ==========================================================================
    def setup_live_tab(self):
        self.live_header = tk.Frame(self.tab_live, bg="#252538", height=60)
        self.live_header.pack(fill="x", side="top")
        
        self.live_title_lbl = tk.Label(self.live_header, text="⚡ LIVE COUNSELING MODE ASSISTANT TREE", font=("Helvetica", 11, "bold"), fg=self.text_color, bg="#252538")
        self.live_title_lbl.pack(pady=15, padx=15, side="left")
        
        self.live_status_lbl = tk.Label(self.live_header, text="", font=("Helvetica", 10, "bold"), fg=self.success_color, bg="#252538")
        self.live_status_lbl.pack(pady=15, padx=15, side="right")

        main_view_split = tk.Frame(self.tab_live, bg=self.bg_color)
        main_view_split.pack(fill="both", expand=True, padx=15, pady=10)
        
        progress_box = tk.LabelFrame(main_view_split, text=" Secured Track Footprint Chain (Locked Parameters Path) ", font=("Helvetica", 10, "bold"), fg=self.accent_color, bg=self.bg_color, bd=2)
        progress_box.pack(fill="x", pady=(0, 10))
        
        self.live_progress_frame = tk.Frame(progress_box, bg=self.bg_color)
        self.live_progress_frame.pack(fill="x", padx=10, pady=10)

        choices_box = tk.LabelFrame(main_view_split, text=" Active Decision Alternatives (Choose Next Section Locked Successfully) ", font=("Helvetica", 10, "bold"), fg="#fab387", bg=self.bg_color, bd=2)
        choices_box.pack(fill="both", expand=True)
        
        self.live_canvas = tk.Canvas(choices_box, bg=self.bg_color, highlightthickness=0)
        live_scrollbar = ttk.Scrollbar(choices_box, orient="vertical", command=self.live_canvas.yview)
        self.live_scroll_frame = tk.Frame(self.live_canvas, bg=self.bg_color)
        
        self.live_scroll_frame.bind("<Configure>", lambda e: self.live_canvas.configure(scrollregion=self.live_canvas.bbox("all")))
        self.live_canvas.create_window((0, 0), window=self.live_scroll_frame, anchor="nw")
        self.live_canvas.configure(yscrollcommand=live_scrollbar.set)
        
        self.live_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        live_scrollbar.pack(side="right", fill="y")

        footer = tk.Frame(self.tab_live, bg=self.bg_color)
        footer.pack(fill="x", side="bottom", padx=15, pady=10)
        
        tk.Button(footer, text="↩ Back (Undo Last Selection)", font=("Helvetica", 10, "bold"), bg=self.alert_color, fg="#11111b", relief="flat", command=self.live_handle_back, padx=10, pady=5).pack(side="left")
        tk.Button(footer, text="🔄 Reset Tracker", font=("Helvetica", 10, "bold"), bg=self.muted_text, fg="#11111b", relief="flat", command=self.initialize_live_mode, padx=10, pady=5).pack(side="right")

    def initialize_live_mode(self):
        self.plans = load_plans("plans.json")
        self.live_locked_sections = []  
        self.refresh_live_decision_tree()

    def refresh_live_decision_tree(self):
        for w in self.live_scroll_frame.winfo_children(): w.destroy()
        for w in self.live_progress_frame.winfo_children(): w.destroy()

        N = len(self.live_locked_sections)
        self.live_active_combos = []
        
        for combo in self.plans["combos"]:
            match = True
            if len(combo["picking_order"]) < N:
                match = False
            else:
                for i in range(N):
                    locked_sec = self.live_locked_sections[i]
                    expected_code = combo["picking_order"][i]
                    
                    if locked_sec["code"] != expected_code:
                        match = False
                        break
                        
                    combo_sec = next(s for s in combo["sections"] if s["code"] == expected_code)
                    if (combo_sec["slots"] != locked_sec["slots"] or 
                        combo_sec["professor"] != locked_sec["professor"]):
                        match = False
                        break
            if match:
                self.live_active_combos.append(combo)

        if not self.live_active_combos and N > 0:
            tk.Label(self.live_scroll_frame, text="❌ Error: Out of viable master blueprints!\nYour selections have broken off all preconfigured backup branches.", font=("Helvetica", 12, "bold"), fg=self.alert_color, bg=self.bg_color).pack(pady=40)
            self.live_status_lbl.config(text="Surviving Paths: 0  ")
            return

        if not self.live_locked_sections:
            tk.Label(self.live_progress_frame, text="No selections confirmed yet. Select options below to begin convergence.", font=("Helvetica", 10, "italic"), fg=self.muted_text, bg=self.bg_color).pack(anchor="w")
        else:
            for idx, sec in enumerate(self.live_locked_sections, 1):
                timings = get_timings_for_slots(sec['slots'], self.slot_timing_map)
                t = (f"✅ Step {idx}: {sec['code']} ({sec['name']}) — Slots: {sec['slots']} | "
                     f"Professor: {sec['professor']} | [{sec['tt_code']}]\n"
                     f"   Timings: {timings}")
                tk.Label(self.live_progress_frame, text=t, font=("Helvetica", 9, "bold"), fg=self.success_color, bg=self.bg_color, justify="left").pack(anchor="w", pady=1)

        next_options = []
        seen_keys = set()
        option_weights = {}

        for combo in self.live_active_combos:
            if len(combo["picking_order"]) > N:
                next_code = combo["picking_order"][N]
                sec = next(s for s in combo["sections"] if s["code"] == next_code)
                key = (sec["code"], sec["slots"], sec["professor"])
                
                option_weights[key] = option_weights.get(key, 0) + 1
                if key not in seen_keys:
                    seen_keys.add(key)
                    next_options.append(sec)

        self.live_status_lbl.config(text=f"Surviving Matrix Blueprints: {len(self.live_active_combos)}  ")

        if not next_options and len(self.plans["combos"]) > 0:
            if len(self.live_active_combos) > 0:
                success_lbl = tk.Label(self.live_scroll_frame, text="🎉 TIMETABLE CONVERGENCE SECURED COMPLETELY!\nAll chosen targets match your planned configurations flawlessly.", font=("Helvetica", 12, "bold"), fg=self.success_color, bg=self.bg_color, justify="center")
                success_lbl.pack(pady=40, padx=20)
                return
            else:
                tk.Label(self.live_scroll_frame, text="No active combinations available.", font=("Helvetica", 10, "italic"), fg=self.muted_text, bg=self.bg_color).pack(pady=40)
                return

        for opt in next_options:
            key = (opt["code"], opt["slots"], opt["professor"])
            weight = option_weights.get(key, 0)
            
            card = tk.Frame(self.live_scroll_frame, bg=self.card_color, bd=1, relief="solid", highlightbackground="#45475a")
            card.pack(fill="x", expand=True, pady=4, padx=10)
            
            timings = get_timings_for_slots(opt['slots'], self.slot_timing_map)
            desc_str = (f"Course: {opt['code']} — {opt['name']}\n"
                        f"Slots: {opt['slots']:<12} | Professor: {opt['professor']}\n"
                        f"Timings: {timings}")
            tk.Label(card, text=desc_str, font=("Helvetica", 10, "bold"), bg=self.card_color, fg=self.text_color, justify="left", anchor="w").pack(side="left", padx=15, pady=10)
            
            tk.Label(card, text=f"{weight} paths protect this", font=("Helvetica", 9, "italic"), bg=self.card_color, fg="#cba6f7").pack(side="right", padx=(0, 15))
            
            sec_btn = tk.Button(card, text="SECURE", font=("Helvetica", 9, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=lambda target_sec=opt: self.live_handle_select(target_sec), padx=10)
            sec_btn.pack(side="right", padx=10, pady=10)

    def live_handle_select(self, chosen_sec):
        self.live_locked_sections.append(chosen_sec)
        self.refresh_live_decision_tree()

    def live_handle_back(self):
        if not self.live_locked_sections: return
        self.live_locked_sections.pop()
        self.refresh_live_decision_tree()

if __name__ == "__main__":
    root = tk.Tk()
    app = MasterCounsellingApp(root)
    root.mainloop()
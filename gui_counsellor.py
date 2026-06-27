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

def get_readable_timings(raw_slots_str):
    """Translates slot strings like 'A1+TA1' into combined human-readable text."""
    if not raw_slots_str or raw_slots_str == "—":
        return "—"
    t_headers, t_grid, l_headers, l_grid = get_timetable_data()
    slots = [s.strip() for s in raw_slots_str.split('+')]
    result_pieces = []
    
    for slot in slots:
        found = False
        for day, s_list in t_grid.items():
            if slot in s_list:
                idx = s_list.index(slot)
                result_pieces.append(f"{day} {t_headers[idx]}")
                found = True
                break
        if not found:
            for day, s_list in l_grid.items():
                if slot in s_list:
                    idx = s_list.index(slot)
                    result_pieces.append(f"{day} {l_headers[idx]}")
                    break
                    
    return ", ".join(result_pieces) if result_pieces else raw_slots_str

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


# ==============================================================================
# 2. MAIN APPLICATION GUI CLASS
# ==============================================================================

class MasterCounsellingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Master Course Counseling Suite")
        self.root.geometry("1100x750")
        self.root.configure(bg="#1e1e2e")
        
        # Load Baseline Datasets
        self.courses_dict = load_courses_from_csv("CourseList.csv")
        self.plans = load_plans("plans.json")
        
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

    def bundle_picking_order(self, sections, order):
        """Helper to force matching lab courses (ending in 'P') to stay bundled immediately below their theory counterparts."""
        new_order = []
        visited = set()
        
        # Primary pass for theory elements or items without explicit links
        for code in order:
            if code in visited: continue
            new_order.append(code)
            visited.add(code)
            
            if code.endswith("L"):
                lab_counterpart = code[:-1] + "P"
                if lab_counterpart in order and lab_counterpart not in visited:
                    new_order.append(lab_counterpart)
                    visited.add(lab_counterpart)
                    
        # Catch-all safety pass
        for code in order:
            if code not in visited:
                new_order.append(code)
        return new_order

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
                sec = next((s for s in combo["sections"] if s["code"] == code), None)
                if not sec: continue
                timings = get_readable_timings(sec['slots'])
                sec_text = f" • {sec['code']:<8} | {sec['name']:<25} | Slots: {sec['slots']:<10} | Timing: {timings:<35} | Prof: {sec['professor']}"
                tk.Label(card, text=sec_text, font=("Courier", 9, "bold"), fg=self.text_color, bg=self.card_color, justify="left", anchor="w").pack(anchor="w", padx=25)
                
            # Control Configuration Button Pack Stack (Packed Right to Left)
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
        dialog.geometry("1050x650")
        dialog.configure(bg=self.bg_color)
        dialog.grab_set()  # Enforce structural focus modality
        
        # Keep tracking of working copy data configurations directly on the component structure
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
            
            timings = get_readable_timings(sec.get('slots', '—'))
            if sec.get("is_blank"):
                desc = f"Course: {sec['code']}\n[ BLANK SLOT ]\nFree for timing adjustments"
                tk.Label(card, text=desc, font=("Courier", 9, "bold"), bg=self.card_color, fg=self.muted_text, justify="left", anchor="w").pack(side="left", padx=10, pady=8)
            else:
                desc = f"Course: {sec['code']}\nSlots: {sec['slots']:<12}\nTiming: {timings}\nProf: {sec['professor']}\nCode: {sec['tt_code']}"
                tk.Label(card, text=desc, font=("Courier", 9, "bold"), bg=self.card_color, fg=self.text_color, justify="left", anchor="w").pack(side="left", padx=10, pady=8)
            
            # Action button holder
            btn_subframe = tk.Frame(card, bg=self.card_color)
            btn_subframe.pack(side="right", padx=10, pady=8)
            
            rep_btn = tk.Button(btn_subframe, text="Change Section", font=("Helvetica", 9, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=lambda tc=code: self.render_replace_section_view(dialog, combo_id, tc))
            rep_btn.pack(side="top", fill="x", pady=2)
            
            if not sec.get("is_blank"):
                blank_btn = tk.Button(btn_subframe, text="Make Blank", font=("Helvetica", 9, "bold"), bg=self.muted_text, fg="#11111b", relief="flat", command=lambda tc=code: self.apply_blank_slot(dialog, combo_id, tc))
                blank_btn.pack(side="top", fill="x", pady=2)
                
            rem_btn = tk.Button(btn_subframe, text="Remove Entirely", font=("Helvetica", 9, "bold"), bg=self.alert_color, fg="#11111b", relief="flat", command=lambda tc=code: self.remove_course_from_modify(dialog, combo_id, tc))
            rem_btn.pack(side="top", fill="x", pady=2)
            
        # Populate Right View (Sorting Track Priority Sequences)
        prio_listbox = tk.Listbox(right_frame, font=("Helvetica", 10, "bold"), bg=self.card_color, fg=self.text_color, selectbackground=self.accent_color, selectforeground="#11111b", highlightthickness=0, bd=1)
        prio_listbox.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        for code in dialog.working_combo["picking_order"]:
            sec = next(s for s in dialog.working_combo["sections"] if s["code"] == code)
            prof_lbl = "BLANK" if sec.get("is_blank") else sec["professor"]
            prio_listbox.insert(tk.END, f" {sec['code']} ({prof_lbl})")
            
        btn_pane = tk.Frame(right_frame, bg=self.bg_color)
        btn_pane.pack(side="right", fill="y", pady=10, padx=(0, 10))
        tk.Button(btn_pane, text="▲ Move Up", font=("Helvetica", 9, "bold"), bg=self.card_color, fg=self.text_color, command=lambda: self.dialog_move_prio_up(prio_listbox, dialog)).pack(fill="x", pady=2)
        tk.Button(btn_pane, text="▼ Move Down", font=("Helvetica", 9, "bold"), bg=self.card_color, fg=self.text_color, command=lambda: self.dialog_move_prio_down(prio_listbox, dialog)).pack(fill="x", pady=2)
        
        # Dialog Control Bottom Command Bar
        footer = tk.Frame(dialog, bg=self.bg_color)
        footer.pack(fill="x", side="bottom", padx=15, pady=10)
        
        save_btn = tk.Button(footer, text="💾 Save Changes", font=("Helvetica", 10, "bold"), bg=self.success_color, fg="#11111b", relief="flat", command=lambda: self.save_dialog_modifications(dialog, combo_id))
        save_btn.pack(side="right", padx=5)
        
        cancel_btn = tk.Button(footer, text="Discard & Cancel", font=("Helvetica", 10, "bold"), bg=self.alert_color, fg="#11111b", relief="flat", command=dialog.destroy)
        cancel_btn.pack(side="right", padx=5)

    def remove_course_from_modify(self, dialog, combo_id, target_code):
        dialog.working_combo["sections"] = [s for s in dialog.working_combo["sections"] if s["code"] != target_code]
        dialog.working_combo["picking_order"] = [c for c in dialog.working_combo["picking_order"] if c != target_code]
        self.render_modify_main_view(dialog, combo_id)

    def apply_blank_slot(self, dialog, combo_id, target_code):
        sec_idx = next(i for i, s in enumerate(dialog.working_combo["sections"]) if s["code"] == target_code)
        dialog.working_combo["sections"][sec_idx] = {
            "code": target_code,
            "name": self.courses_dict[target_code][0]["name"],
            "slots": "—", "tt_code": "—", "professor": "—", "type": "—",
            "minute_blocks": [],
            "is_blank": True
        }
        self.render_modify_main_view(dialog, combo_id)

    def dialog_move_prio_up(self, listbox, dialog):
        pos = listbox.curselection()
        if not pos or pos[0] == 0: return
        idx = pos[0]
        text = listbox.get(idx)
        listbox.delete(idx)
        listbox.insert(idx - 1, text)
        listbox.selection_set(idx - 1)
        dialog.working_combo["picking_order"][idx], dialog.working_combo["picking_order"][idx-1] = dialog.working_combo["picking_order"][idx-1], dialog.working_combo["picking_order"][idx]
        dialog.working_combo["picking_order"] = self.bundle_picking_order(dialog.working_combo["sections"], dialog.working_combo["picking_order"])
        self.render_modify_main_view(dialog, dialog.working_combo["id"])

    def dialog_move_prio_down(self, listbox, dialog):
        pos = listbox.curselection()
        if not pos or pos[0] == listbox.size() - 1: return
        idx = pos[0]
        text = listbox.get(idx)
        listbox.delete(idx)
        listbox.insert(idx + 1, text)
        listbox.selection_set(idx + 1)
        dialog.working_combo["picking_order"][idx], dialog.working_combo["picking_order"][idx+1] = dialog.working_combo["picking_order"][idx+1], dialog.working_combo["picking_order"][idx]
        dialog.working_combo["picking_order"] = self.bundle_picking_order(dialog.working_combo["sections"], dialog.working_combo["picking_order"])
        self.render_modify_main_view(dialog, dialog.working_combo["id"])

    def render_replace_section_view(self, dialog, combo_id, target_code):
        for w in dialog.winfo_children(): w.destroy()
            
        container = tk.Frame(dialog, bg=self.bg_color)
        container.pack(fill="both", expand=True, padx=15, pady=15)
        
        course_name = self.courses_dict[target_code][0]["name"]
        
        # Course Select Dropdown UI logic embedded during Modification state
        dk_header = tk.Frame(container, bg=self.bg_color)
        dk_header.pack(fill="x", pady=(0,15))
        tk.Label(dk_header, text="Modify target context focus course branch: ", font=("Helvetica", 10), fg=self.text_color, bg=self.bg_color).pack(side="left")
        
        mod_dropdown = ttk.Combobox(dk_header, values=dialog.working_combo["picking_order"], state="readonly", font=("Helvetica", 10, "bold"), width=12)
        mod_dropdown.set(target_code)
        mod_dropdown.pack(side="left", padx=5)
        mod_dropdown.bind("<<ComboboxSelected>>", lambda e: self.render_replace_section_view(dialog, combo_id, mod_dropdown.get()))

        tk.Label(container, text=f"Replace Section Sequence for: {target_code} — {course_name}", font=("Helvetica", 12, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w", pady=(0, 15))
        
        # Isolate the index inside current sections structure array mapping footprint
        sec_idx_in_combo = next(i for i, s in enumerate(dialog.working_combo["sections"]) if s["code"] == target_code)
        
        # Calculate timeblocks locked down by OTHER courses in this exact setup configuration
        occupied_minutes = set()
        for i, sec in enumerate(dialog.working_combo["sections"]):
            if i != sec_idx_in_combo and not sec.get("is_blank"):
                occupied_minutes.update(tuple(x) for x in sec["minute_blocks"])
                
        # Theory-Lab Professor Constraint Check
        required_prof = None
        if target_code.endswith("P"):
            theory_code = target_code[:-1] + "L"
            t_sec = next((s for s in dialog.working_combo["sections"] if s["code"] == theory_code), None)
            if t_sec and not t_sec.get("is_blank"):
                required_prof = t_sec["professor"]
        elif target_code.endswith("L"):
            lab_code = target_code[:-1] + "P"
            l_sec = next((s for s in dialog.working_combo["sections"] if s["code"] == lab_code), None)
            if l_sec and not l_sec.get("is_blank"):
                required_prof = l_sec["professor"]

        all_sections = self.courses_dict[target_code]
        valid_options = []
        for sec in all_sections:
            if required_prof and sec["professor"] != required_prof:
                continue
            sec_min = set(tuple(x) for x in sec["minute_blocks"])
            if occupied_minutes.isdisjoint(sec_min):
                valid_options.append(sec)
                
        if not valid_options:
            tk.Label(container, text="⚠️ CRITICAL LAYOUT CONFLICT: No available clash-free slots exist for this item\nwithout shifting early anchor positions or marking other components blank first.", font=("Helvetica", 11, "bold"), fg=self.alert_color, bg=self.bg_color, justify="left").pack(pady=30)
            tk.Button(container, text="↩ Back to Blueprint Panel", font=("Helvetica", 10, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=lambda: self.render_modify_main_view(dialog, combo_id)).pack(pady=5)
            return

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
            
            timings = get_readable_timings(opt['slots'])
            desc = f"Slots: {opt['slots']:<10} | Timing: {timings:<35} | Professor: {opt['professor']:<25}\nCode: {opt['tt_code']}"
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
        # Strict validation ensuring no entries remain blank upon storage action execution triggers
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
                
        # Commit back to master structure file dataset
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
        self.force_priority_ordering = False
        self.render_builder_step()

    def render_builder_step(self):
        for w in self.left_panel.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        tk.Label(self.right_panel, text="Current Step Selections Footprint:", font=("Helvetica", 10, "bold"), bg=self.bg_color, fg=self.text_color).pack(anchor="w", padx=10, pady=5)
        for s in self.wizard_selections:
            timings = get_readable_timings(s['slots'])
            tk.Label(self.right_panel, text=f"✔ {s['code']} -> {s['slots']} ({timings}) [{s['professor']}]", font=("Helvetica", 9), fg=self.success_color, bg=self.bg_color).pack(anchor="w", padx=20)

        # Non-compulsory structure: Allow finalizing early via the manual force trigger flag rule
        selected_codes = [s["code"] for s in self.wizard_selections]
        remaining_codes = [c for c in self.builder_course_codes if c not in selected_codes]

        if remaining_codes and not self.force_priority_ordering:
            # Formulate selection framework header controls row
            header_row = tk.Frame(self.left_panel, bg=self.bg_color)
            header_row.pack(fill="x", pady=(0, 10))
            
            tk.Label(header_row, text="Choose Course Focus -> ", font=("Helvetica", 10), fg=self.muted_text, bg=self.bg_color).pack(side="left")
            
            # Show course code AND name in the dropdown values tracking footprint array mappings
            dropdown_labels = [f"{c} - {self.courses_dict[c][0]['name']}" for c in remaining_codes]
            
            course_cb = ttk.Combobox(header_row, values=dropdown_labels, state="readonly", font=("Helvetica", 10, "bold"), width=35)
            course_cb.pack(side="left", padx=5)
            course_cb.set(dropdown_labels[0])
            
            # Reactive UI trigger framework attachment logic
            def change_focus_course(event):
                raw_code = course_cb.get().split(" - ")[0]
                self.render_sections_for_selected_course(raw_code)
                
            course_cb.bind("<<ComboboxSelected>>", change_focus_course)
            
            if self.wizard_selections:
                finish_btn = tk.Button(header_row, text="🏁 Finish & Save Combo", font=("Helvetica", 9, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=self.force_wizard_completion)
                finish_btn.pack(side="right", padx=5)
            
            # Content target container pane
            self.builder_sections_container = tk.Frame(self.left_panel, bg=self.bg_color)
            self.builder_sections_container.pack(fill="both", expand=True)
            
            # Run initialization execution loop mapping track footprint
            self.render_sections_for_selected_course(course_cb.get().split(" - ")[0])
        else:
            self.render_priority_sorting_interface()

    def force_wizard_completion(self):
        self.force_priority_ordering = True
        self.render_builder_step()

    def render_sections_for_selected_course(self, current_code):
        for w in self.builder_sections_container.winfo_children(): w.destroy()
            
        course_name = self.courses_dict[current_code][0]["name"]
        title = tk.Label(self.builder_sections_container, text=f"{current_code} — {course_name}", font=("Helvetica", 14, "bold"), fg=self.accent_color, bg=self.bg_color)
        title.pack(anchor="w", pady=(5, 15))
        
        # Check if theory or lab constraint professor filter is active based on code footprint tracking rules
        required_prof = None
        if current_code.endswith("P"):
            theory_code = current_code[:-1] + "L"
            t_match = next((s for s in self.wizard_selections if s["code"] == theory_code), None)
            if t_match: required_prof = t_match["professor"]
        elif current_code.endswith("L"):
            lab_code = current_code[:-1] + "P"
            l_match = next((s for s in self.wizard_selections if s["code"] == lab_code), None)
            if l_match: required_prof = l_match["professor"]

        all_sections = self.courses_dict[current_code]
        valid_options = []
        for sec in all_sections:
            if required_prof and sec["professor"] != required_prof:
                continue
            sec_blocks = set(tuple(x) for x in sec["minute_blocks"])
            if self.wizard_occupied_minutes.isdisjoint(sec_blocks):
                valid_options.append(sec)
                
        if not valid_options:
            tk.Label(self.builder_sections_container, text="⚠️ CRITICAL ERROR: Class Overlap or Professor Co-requisite Mismatch!\nNo available slots remain open for this course given earlier choices.", font=("Helvetica", 11, "bold"), fg=self.alert_color, bg=self.bg_color, justify="left").pack(pady=20)
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
            
            timings = get_readable_timings(opt['slots'])
            desc = f"Slots: {opt['slots']:<10} | Timing: {timings:<35} | Professor: {opt['professor']:<25}\nCode: {opt['tt_code']}"
            tk.Label(btn_card, text=desc, font=("Courier", 9, "bold"), bg=self.card_color, fg=self.text_color, justify="left", anchor="w").pack(side="left", padx=10, pady=8)
            
            sel_btn = tk.Button(btn_card, text="Pick Section", font=("Helvetica", 9, "bold"), bg=self.success_color, fg="#11111b", relief="flat", command=lambda choice_sec=opt: self.advance_builder_step(choice_sec))
            sel_btn.pack(side="right", padx=10, pady=8)

    def advance_builder_step(self, chosen_section):
        self.wizard_selections.append(chosen_section)
        self.wizard_occupied_minutes.update(tuple(x) for x in chosen_section["minute_blocks"])
        self.wizard_step += 1
        self.render_builder_step()

    def render_priority_sorting_interface(self):
        # Clear out any existing widgets on the left panel first to prevent duplication upon refresh
        for w in self.left_panel.winfo_children(): 
            w.destroy()

        lbl_prio = tk.Label(self.left_panel, text="🏁 Configure Picking Order Priority Sequence", font=("Helvetica", 13, "bold"), fg=self.success_color, bg=self.bg_color)
        lbl_prio.pack(anchor="w", pady=(0, 5))
        tk.Label(self.left_panel, text="Sort selections from top to bottom based on registration risk priority levels (Labs remain bundled to Theory):", font=("Helvetica", 9, "italic"), fg=self.muted_text, bg=self.bg_color).pack(anchor="w", pady=(0, 15))
        
        listbox_frame = tk.Frame(self.left_panel, bg=self.bg_color)
        listbox_frame.pack(fill="both", expand=True)
        
        self.prio_listbox = tk.Listbox(listbox_frame, font=("Helvetica", 10, "bold"), bg=self.card_color, fg=self.text_color, selectbackground=self.accent_color, selectforeground="#11111b", highlightthickness=0, bd=1)
        self.prio_listbox.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Enforce initial tracking rule parameters for automatic co-requisite bundle sorting patterns
        current_codes = [s["code"] for s in self.wizard_selections]
        bundled_codes = self.bundle_picking_order(self.wizard_selections, current_codes)
        
        reordered_selections = []
        for code in bundled_codes:
            match_sec = next(s for s in self.wizard_selections if s["code"] == code)
            reordered_selections.append(match_sec)
        self.wizard_selections = reordered_selections

        for s in self.wizard_selections:
            self.prio_listbox.insert(tk.END, f"{s['code']} — {s['name']} ({s['professor']})")
            
        btn_pane = tk.Frame(listbox_frame, bg=self.bg_color)
        btn_pane.pack(side="right", fill="y")
        
        tk.Button(btn_pane, text="▲ Move Up", font=("Helvetica", 9, "bold"), bg=self.card_color, fg=self.text_color, command=self.move_prio_up).pack(fill="x", pady=2)
        tk.Button(btn_pane, text="▼ Move Down", font=("Helvetica", 9, "bold"), bg=self.card_color, fg=self.text_color, command=self.move_prio_down).pack(fill="x", pady=2)
        
        save_btn = tk.Button(self.left_panel, text="💾 Commit Plan to Database File", font=("Helvetica", 11, "bold"), bg=self.accent_color, fg="#11111b", relief="flat", command=self.save_wizard_combo)
        save_btn.pack(fill="x", pady=20)

    def move_prio_up(self):
        pos = self.prio_listbox.curselection()
        if not pos or pos[0] == 0: return
        idx = pos[0]
        
        # Swap the items
        self.wizard_selections[idx], self.wizard_selections[idx-1] = self.wizard_selections[idx-1], self.wizard_selections[idx]
        
        # Refresh screen to update the layout and enforce bundling logic rules
        self.render_priority_sorting_interface()
        
        # Keep the active selection visual indicator stable
        new_idx = idx - 1 if idx > 0 else 0
        self.prio_listbox.selection_set(new_idx)

    def move_prio_down(self):
        pos = self.prio_listbox.curselection()
        if not pos or pos[0] == self.prio_listbox.size() - 1: return
        idx = pos[0]
        
        # Swap the items
        self.wizard_selections[idx], self.wizard_selections[idx+1] = self.wizard_selections[idx+1], self.wizard_selections[idx]
        
        # Refresh screen to update the layout and enforce bundling logic rules
        self.render_priority_sorting_interface()
        
        # Keep the active selection visual indicator stable
        new_idx = idx + 1 if idx < self.prio_listbox.size() - 1 else self.prio_listbox.size() - 1
        self.prio_listbox.selection_set(new_idx)

    def save_wizard_combo(self):
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
                timings = get_readable_timings(sec['slots'])
                t = f"✅ Step {idx}: {sec['code']} ({sec['name']}) — Slots: {sec['slots']} | Timings: {timings} | Professor: {sec['professor']} | [{sec['tt_code']}]"
                tk.Label(self.live_progress_frame, text=t, font=("Helvetica", 9, "bold"), fg=self.success_color, bg=self.bg_color).pack(anchor="w", pady=1)

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
            
            timings = get_readable_timings(opt['slots'])
            desc_str = f"Course: {opt['code']} — {opt['name']}\nSlots: {opt['slots']:<10} | Timing: {timings}\nProfessor: {opt['professor']}"
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
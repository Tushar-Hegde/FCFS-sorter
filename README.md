# Prerequisites and Setup
Python 3.x with: csv, os, json, tkinter, copy, shutil (all standard library).

Keep `CourseList.csv` in the same directory as the script. Columns, in order: Course Name, Course Code, Raw Slots (e.g. A1+TA1), Timetable Code, Professor Name, Course Type.

Run from that directory:

```python3 gui_counsellor.py```

Plans are stored in `plans_optimized.json` as a compact graph: every distinct section is written once, and any two paths whose NEXT STAGE is identical (for example two professors teaching the same time slot) point to one shared next stage. A 42,000-plan tree takes about 45 KB. The same structure is used in memory, so Secure / Back / reorder are instant. Changes are saved automatically a couple of seconds after you pause (and when you close the window). Older files are upgraded automatically on first run; the original is kept as `plans_optimized.json.v1.bak` / `.v2.bak`.

# 1. Live Tracker (first tab, opens by default)
Your working tree. Everything (choosing, adding, branching, deleting, reordering) happens here. Identical plans are merged automatically, so there is no Remove Duplicates button any more. Mouse wheel / trackpad scrolls every list.

- **Locked Path + Weekly Timetable:** each locked course is drawn on a Mon-Fri timetable (one colour per course).
- **Next Available Options:** click an option card to highlight it; its slots appear on the timetable as a dashed preview. Click again to un-highlight.
- **Plan counts:** each option shows how many saved plans still survive if you pick it.
- **Secure:** lock the option and go one level deeper. **< Go Back** undoes the last lock, **Reset Tracker** starts over.
- **^ / v:** reorder the options at this node. The order of the options at each node *is* the saved preference order. Because identical next stages are shared, reordering (or deleting) an option there applies to every path that leads to that same next stage. The confirmation for Delete Branch shows the exact number of plans removed.
- **Add New Option / Create New Plan:** these only affect the path you are on (the shared stages are copied for that path), so a new option can never clash with another path's slots.
- **Add New Option:** add a course (specific section or blank) after the current path.
- **Branch:** swap a course (and its lab) across all plans sharing that layer. Opens on the plans of your current path.
- **Delete Branch:** delete every plan below an option (two confirmations).

# 2. Create New Plan
Unchanged: builds a plan of blank slots that you can fill in from the Live Tracker.

# 3. Flow Planning
Build the order you want to pick things in as a list of **stages**. A stage is either:

- **a single course** (`+ Add as Single Stage`), or
- **a group of 2 or more courses** (`+ Add Group (pick one)...`) - in that stage you pick exactly ONE of them. Courses inside a group may clash with each other (e.g. they share a time slot); only the one you actually choose has to fit with everything else.

Example: VLSI -> Choose between DCS / Subject 3 / Subject 4 -> ...

**Labs are automatic.** If the CSV has a lab for a course (either `XXXXL` + `XXXXP` rows, or lab rows with type `LO` under the same code), the lab is joined to it: it is picked immediately after the course, with the same professor. In a group, the lab you get is the lab of whichever course you chose. A course with no lab in the CSV is treated as a single item; nothing is added that is not in the CSV.

- **Preview Tree Size:** shows how many complete plans the flow produces, how many dead-end paths were removed, and how many valid paths remain after each stage.
- **Create Full Tree:** generates EVERY plan for that flow and **overwrites** all existing plans and saved option orderings. It asks for confirmation twice and first saves `plans_optimized.backup.json`.

Rules used: no time-slot clashes among the finally chosen courses and labs; a lab must be taught by the same professor as its course; paths with no valid section left are removed, so every plan contains one course from every stage (plus its lab).

# Troubleshooting lag
Set `DEBUG_TIMING = True` near the top of `gui_counsellor.py` and run from a terminal. Any redraw, save snapshot, or garbage collection slower than ~150 ms (30 ms for GC) is printed with its duration.

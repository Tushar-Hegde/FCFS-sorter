# Prerequisites and Setup
Python 3.x with: csv, os, json, tkinter, copy, shutil (all standard library).

Keep `CourseList.csv` in the same directory as the script. Columns, in order: Course Name, Course Code, Raw Slots (e.g. A1+TA1), Timetable Code, Professor Name, Course Type.

Run from that directory:

```python3 gui_counsellor.py```

Plans are stored in `plans_optimized.json` as a compact tree (shared prefixes and sections are stored once, so even a 40,000-plan tree is well under 1 MB). An older flat-format file is upgraded automatically on first run, and the original is kept as `plans_optimized.json.v1.bak`. Your per-node option ordering (the ^ / v choices) is stored separately in the small `live_orders.json`, so reordering is instant even with a huge tree (old orderings are migrated automatically on first run). The app opens on the **Live Tracker** tab.

# 1. Live Tracker (first tab, opens by default)
Your working tree. Everything (choosing, adding, branching, deleting, reordering) happens here. Mouse wheel / trackpad scrolls every list.

- **Locked Path + Weekly Timetable:** each locked course is drawn on a Mon-Fri timetable (one colour per course).
- **Next Available Options:** click an option card to highlight it; its slots appear on the timetable as a dashed preview. Click again to un-highlight.
- **Plan counts:** each option shows how many saved plans still survive if you pick it.
- **Secure:** lock the option and go one level deeper. **< Go Back** undoes the last lock, **Reset Tracker** starts over.
- **^ / v:** reorder the options at this node (remembered per path).
- **Add New Option:** add a course (specific section or blank) after the current path.
- **Branch:** swap a course (and its lab) across all plans sharing that layer. Opens on the plans of your current path.
- **Delete Branch:** delete every plan below an option (two confirmations).
- **Remove Duplicates:** drop identical plans.

# 2. Create New Plan
Unchanged: builds a plan of blank slots that you can fill in from the Live Tracker.

# 3. Flow Planning
Type the order you want to pick courses in (e.g. VLSI -> VLSI Lab -> Digital Communication Systems -> ...). Ticking "also add its lab right after" adds a theory course's lab automatically.

- **Preview Tree Size:** shows how many complete plans the order produces, how many dead-end paths were removed, and how many valid paths remain after each pick.
- **Create Full Tree:** generates EVERY plan for that order and **overwrites** all existing plans and saved option orderings. It asks for confirmation twice and first saves `plans_optimized.backup.json`.

Rules used: no time-slot clashes; a lab must be taught by the same professor as its theory course (in either pick order); paths where a course has no valid section left are removed, so every plan contains every course in the flow.

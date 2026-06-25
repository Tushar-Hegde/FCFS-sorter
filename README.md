# Prerequisites and Setup
Ensure Python 3.x is installed on your system, with all these libraries - csv,os,json,tkinter,copy

Verify that the file CourseList.csv is present in the same directory as the script. The CSV must contain the following columns in order: Course Name, Course Code, Raw Slots (e.g., A1+TA1), Timetable Code, Professor Name, and Course Type.

View the CSV file provided to see the required layout.

Run the script using the following command in your terminal (bash) : 

```python gui_counsellor.py```
or 
```python3 gui_counsellor.py```

# 1. Saved Combinations Tab
This tab acts as the centralized repository for all schedule layouts that have been created or modified.

Viewing Blueprints: Each entry shows a unique System ID, its specific registration priority sequence, and details for every course slot (including human-readable timings and professor assignments).

Branching Plans: Click the "Branch Plan" button next to any blueprint. This duplicates the chosen combination under a new unique System ID and automatically opens the Modification Workspace, allowing you to create a secondary backup path without altering the original.

Deleting Plans: Use the "Delete Plan" button to permanently remove a schedule layout from the tracking system.

# 2. Create New Plan Wizard Tab
Use this tab to build a customized course schedule from scratch while ensuring no immediate timing overlaps occur.

Dynamic Course Selection: At each step of the creation process, a dropdown menu presents all remaining unselected course codes. This allows you to pick courses in any arbitrary order instead of a predefined sequence.

Clash Prevention: Once a course focus is selected via the dropdown, the interface evaluates your previous selections and displays only the section options that are entirely free of timing conflicts.

Priority Ranking: After selecting sections for all courses, a sorting panel appears. Select a course in the listbox and use the "Move Up" and "Move Down" buttons to order them according to your registration registration risk (e.g., placing highly competitive or low-seat courses at the top).

Saving: Click "Commit Plan to Database File" to save your schedule. The wizard will automatically alert you if an identical combination already exists in your file.

# 3. Modifying an Existing Plan
Clicking "Modify Plan" on an entry in the Saved Combinations tab opens a modal workspace dialog to adjust or swap an existing schedule.

Using Blank Slots: To swap the timings of two courses or resolve an intermediate clash while modifying, use the "Make Blank" button on a course entry. This marks it as a "[ BLANK SLOT ]" and temporarily releases its locked time minutes.

Replacing Sections: Click "Change Section" on any course to open its specific replacement view. You can also switch your course context inside this view using the top dropdown menu. The interface displays only the options that do not conflict with the non-blank sections currently in the workspace.

Saving Restrictions: You can freely arrange and hold blank slots during your editing session. However, the system enforces a strict validation routine upon saving: you will be blocked from saving if any slots remain blank or if the final layout exactly duplicates another existing system blueprint.

# 4. Live Assistant Tree Mode Tab
This tab serves as a real-time tracking companion during the actual counseling session to maintain a valid path as classes fill up.

Tracking Progress: The upper frame displays your secured track footprint chain as you lock in choices step-by-step.

Filtering Branches: The system looks at your current state and filters down your saved blueprints. The lower frame presents only the active decision alternatives that match your exact history and order.

Path Convergence Indicators: Next to each available section button, a text indicator displays how many remaining "surviving matrix blueprints" utilize that choice. This helps you select sections that keep the maximum number of backup paths viable.

Correction and Resilience: If a selection fails or a seat is lost unexpectedly, use the "Back (Undo Last Selection)" button to step backward down the decision tree, or click "Reset Tracker" to clear the live memory and restart from the top.

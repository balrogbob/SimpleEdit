#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rAthena Tools Integration for SimpleEdit

Provides menu items and dialogs for creating and editing rAthena scripts
using the rathena_script_gen and rathena_script_ui modules.
"""

from tkinter import *
from tkinter import messagebox, filedialog, simpledialog
from tkinter import ttk
import os
import sys

# Ensure rathena-tools package is in path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_rathena_path = os.path.join(_current_dir, 'rathena-tools')
if _rathena_path not in sys.path:
    sys.path.insert(0, _rathena_path)

try:
    from rathena_script_gen import ScriptGenerator, ScriptNPC, ScriptFunction
    from rathena_script_ui import DialogBuilder, NPCWizard, ScriptValidator, NPCTypeEnum
    _RATHENA_TOOLS_AVAILABLE = True
except ImportError as e:
    _RATHENA_TOOLS_AVAILABLE = False
    print(f"[DEBUG] Failed to import rAthena tools: {e}")


def _launch_wizard_dialog(root, wizard):
    """Helper to launch a wizard dialog step-by-step."""
    dlg = Toplevel(root)
    dlg.title(f"rAthena {wizard.get_step_title()}")
    dlg.transient(root)
    dlg.grab_set()
    dlg.geometry("600x450")

    frame = ttk.Frame(dlg, padding=12)
    frame.pack(fill=BOTH, expand=True)

    # Title and description
    title_label = ttk.Label(
        frame,
        text=wizard.get_step_title(),
        font=("Arial", 12, "bold")
    )
    title_label.pack(anchor='w', pady=(0, 6))

    desc_label = ttk.Label(
        frame,
        text=wizard.get_step_description(),
        wraplength=520,
        justify='left'
    )
    desc_label.pack(anchor='w', pady=(0, 12))

    # Dynamic content area
    content_frame = ttk.Frame(frame)
    content_frame.pack(fill=BOTH, expand=True, pady=(0, 12))

    # Step indicator
    step_label = ttk.Label(
        frame,
        text=f"Step {wizard.get_current_step() + 1} of {wizard.get_step_count()}"
    )
    step_label.pack(anchor='w', pady=(6, 6))

    # Buttons
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill=X, side=BOTTOM)

    # State widgets per step
    state_widgets = {}

    sprites_dir = os.path.join(_current_dir, 'rathena-tools', 'sprites')

    def find_sprite_file(sprite_id: int):
        """Return filepath for sprite if exists in sprites_dir"""
        exts = ['.png', '.gif', '.bmp', '.jpg', '.jpeg', '.act', '.scr']
        for ext in exts:
            candidate = os.path.join(sprites_dir, f"{sprite_id}{ext}")
            if os.path.exists(candidate):
                return candidate
        return None

    def render_step():
        # clear
        for w in content_frame.winfo_children():
            w.destroy()

        step = wizard.get_current_step()
        title_label.config(text=wizard.get_step_title())
        desc_label.config(text=wizard.get_step_description())
        step_label.config(text=f"Step {step + 1} of {wizard.get_step_count()}")

        # Step-specific widgets
        if step == 0:
            # NPC name and location
            ttk.Label(content_frame, text="NPC Name:").grid(row=0, column=0, sticky='w')
            name_var = StringVar(value=wizard.npc_data.get('name', ''))
            name_entry = ttk.Entry(content_frame, textvariable=name_var, width=40)
            name_entry.grid(row=0, column=1, sticky='w', padx=(6, 0))

            ttk.Label(content_frame, text="Map:").grid(row=1, column=0, sticky='w')
            map_var = StringVar(value=wizard.npc_data.get('map', 'prontera'))
            map_entry = ttk.Entry(content_frame, textvariable=map_var, width=30)
            map_entry.grid(row=1, column=1, sticky='w', padx=(6, 0))

            ttk.Label(content_frame, text="X:").grid(row=2, column=0, sticky='w')
            x_var = StringVar(value=str(wizard.npc_data.get('x', 150)))
            x_entry = ttk.Entry(content_frame, textvariable=x_var, width=10)
            x_entry.grid(row=2, column=1, sticky='w', padx=(6, 0))

            ttk.Label(content_frame, text="Y:").grid(row=3, column=0, sticky='w')
            y_var = StringVar(value=str(wizard.npc_data.get('y', 150)))
            y_entry = ttk.Entry(content_frame, textvariable=y_var, width=10)
            y_entry.grid(row=3, column=1, sticky='w', padx=(6, 0))

            ttk.Label(content_frame, text="Direction (0-7):").grid(row=4, column=0, sticky='w')
            facing_var = StringVar(value=str(wizard.npc_data.get('facing', 4)))
            facing_entry = ttk.Entry(content_frame, textvariable=facing_var, width=10)
            facing_entry.grid(row=4, column=1, sticky='w', padx=(6, 0))

            state_widgets.update({
                'name': name_var, 'map': map_var, 'x': x_var, 'y': y_var, 'facing': facing_var
            })

        elif step == 1:
            # Sprite selection and preview
            ttk.Label(content_frame, text="Sprite ID:").grid(row=0, column=0, sticky='w')
            # Collect common sprite IDs from generator enum if available
            try:
                from rathena_script_gen import NPCSprite
                sprite_options = [str(m.value) for m in NPCSprite]
            except Exception:
                sprite_options = [str(wizard.npc_data.get('sprite', 120))]

            sprite_var = StringVar(value=str(wizard.npc_data.get('sprite', 120)))
            sprite_cb = ttk.Combobox(content_frame, textvariable=sprite_var, values=sprite_options, width=20)
            sprite_cb.grid(row=0, column=1, sticky='w', padx=(6, 0))

            # Preview frame with fixed size
            preview_frame = ttk.Frame(content_frame, height=200)
            preview_frame.grid(row=1, column=0, columnspan=2, pady=(12, 0), sticky='nsew')
            preview_frame.grid_propagate(False)
            
            preview_label = ttk.Label(preview_frame, text="Preview not available")
            preview_label.pack(expand=True)

            def update_preview(*args):
                sid = sprite_var.get()
                try:
                    sid_int = int(sid)
                except Exception:
                    preview_label.config(text="Invalid sprite id")
                    return
                fp = find_sprite_file(sid_int)
                if not fp:
                    preview_label.config(text=f"No sprite file for {sid_int}")
                    preview_label.image = None
                    return
                ext = os.path.splitext(fp)[1].lower()
                if ext in ('.png', '.gif'):
                    try:
                        img = PhotoImage(file=fp)
                        # Limit image size to avoid squishing buttons
                        if img.width() > 150 or img.height() > 150:
                            # Subsample if too large
                            scale = max(img.width() // 150, img.height() // 150, 1)
                            img = img.subsample(scale, scale)
                        preview_label.config(image=img, text='')
                        preview_label.image = img
                    except Exception:
                        preview_label.config(text=os.path.basename(fp))
                        preview_label.image = None
                else:
                    preview_label.config(text=os.path.basename(fp))
                    preview_label.image = None

            sprite_var.trace_add('write', update_preview)
            # initial preview
            update_preview()
            state_widgets['sprite'] = sprite_var

        elif step == 2:
            # NPC Type selection
            ttk.Label(content_frame, text="NPC Type:").grid(row=0, column=0, sticky='w')
            try:
                from rathena_script_ui import NPCTypeEnum
                type_options = [t.value for t in NPCTypeEnum]
            except Exception:
                type_options = ["Dialog NPC"]

            t = wizard.npc_data.get('type')
            try:
                val = t.value if isinstance(t, NPCTypeEnum) else str(t)
            except Exception:
                val = str(t)
            type_var = StringVar(value=val)
            type_cb = ttk.Combobox(content_frame, textvariable=type_var, values=type_options, width=30)
            type_cb.grid(row=0, column=1, sticky='w', padx=(6, 0))
            state_widgets['type'] = type_var

        elif step == 3:
            # Interactive dialog editor with advanced options
            from rathena_script_ui import DialogAction, DialogActionEnum
            
            ttk.Label(content_frame, text="Build Dialog Sequence:", font=("Arial", 9, "bold")).pack(anchor='w')
            
            # Dialog actions list
            existing_actions = wizard.npc_data.get('dialog_actions', [])
            
            # Listbox for actions
            list_frame = ttk.Frame(content_frame)
            list_frame.pack(fill=BOTH, expand=True, pady=(6, 6))
            
            actions_listbox = Listbox(list_frame, height=8)
            actions_listbox.pack(side=LEFT, fill=BOTH, expand=True)
            
            list_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=actions_listbox.yview)
            list_scrollbar.pack(side=RIGHT, fill=Y)
            actions_listbox.config(yscrollcommand=list_scrollbar.set)
            
            # Populate existing actions
            for action in existing_actions:
                atype = action.action_type
                if atype == DialogActionEnum.MESSAGE:
                    actions_listbox.insert(END, f"Message: {action.parameters.get('message', '')[:40]}...")
                elif atype == DialogActionEnum.NEXT_BUTTON:
                    actions_listbox.insert(END, "Next Button")
                elif atype == DialogActionEnum.CLOSE_BUTTON:
                    actions_listbox.insert(END, "Close Button")
                elif atype == DialogActionEnum.MENU:
                    opts = action.parameters.get('options', [])
                    actions_listbox.insert(END, f"Menu: {', '.join(opts[:3])}...")
                elif atype == DialogActionEnum.WARP:
                    m = action.parameters.get('map', '')
                    x = action.parameters.get('x', 0)
                    y = action.parameters.get('y', 0)
                    actions_listbox.insert(END, f"Warp: {m} ({x},{y})")
                elif atype == DialogActionEnum.ITEM_CHECK:
                    actions_listbox.insert(END, f"Check: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('count', 1)}")
                elif atype == DialogActionEnum.ITEM_GIVE:
                    actions_listbox.insert(END, f"Give: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('amount', 1)}")
                elif atype == DialogActionEnum.ITEM_REMOVE:
                    actions_listbox.insert(END, f"Remove: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('amount', 1)}")
            
            # Action buttons - Basic
            action_btn_frame = ttk.Frame(content_frame)
            action_btn_frame.pack(fill=X, pady=(0, 6))
            
            def refresh_list():
                actions_listbox.delete(0, END)
                for action in existing_actions:
                    atype = action.action_type
                    if atype == DialogActionEnum.MESSAGE:
                        actions_listbox.insert(END, f"Message: {action.parameters.get('message', '')[:40]}...")
                    elif atype == DialogActionEnum.NEXT_BUTTON:
                        actions_listbox.insert(END, "Next Button")
                    elif atype == DialogActionEnum.CLOSE_BUTTON:
                        actions_listbox.insert(END, "Close Button")
                    elif atype == DialogActionEnum.MENU:
                        opts = action.parameters.get('options', [])
                        branches = action.parameters.get('branches', {})
                        branch_info = f" [{len(branches)} branches]" if branches else ""
                        actions_listbox.insert(END, f"Menu: {', '.join(opts[:3])}...{branch_info}")
                    elif atype == DialogActionEnum.WARP:
                        m = action.parameters.get('map', '')
                        x = action.parameters.get('x', 0)
                        y = action.parameters.get('y', 0)
                        actions_listbox.insert(END, f"Warp: {m} ({x},{y})")
                    elif atype == DialogActionEnum.ITEM_CHECK:
                        actions_listbox.insert(END, f"Check: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('count', 1)}")
                    elif atype == DialogActionEnum.ITEM_GIVE:
                        actions_listbox.insert(END, f"Give: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('amount', 1)}")
                    elif atype == DialogActionEnum.ITEM_REMOVE:
                        actions_listbox.insert(END, f"Remove: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('amount', 1)}")
            
            def add_msg():
                msg = simpledialog.askstring("Add Message", "Enter message text:", parent=dlg)
                if msg:
                    existing_actions.append(DialogAction(DialogActionEnum.MESSAGE, {'message': msg}))
                    refresh_list()
            
            def add_nxt():
                existing_actions.append(DialogAction(DialogActionEnum.NEXT_BUTTON, {}))
                refresh_list()
            
            def add_cls():
                existing_actions.append(DialogAction(DialogActionEnum.CLOSE_BUTTON, {}))
                refresh_list()
            
            def add_mnu():
                opts_str = simpledialog.askstring("Add Menu", "Enter options (separated by |):", parent=dlg)
                if opts_str:
                    options = [o.strip() for o in opts_str.split('|')]
                    
                    # Ask if user wants to define branches now
                    if messagebox.askyesno("Menu Branches", "Do you want to define dialog branches for each menu option?"):
                        branches = {}
                        for opt in options:
                            # Full dialog builder for each branch
                            branch_dlg = Toplevel(dlg)
                            branch_dlg.title(f"Branch: {opt}")
                            branch_dlg.transient(dlg)
                            branch_dlg.grab_set()
                            branch_dlg.geometry("700x500")
                            
                            main_frame = ttk.Frame(branch_dlg, padding=12)
                            main_frame.pack(fill=BOTH, expand=True)
                            
                            ttk.Label(main_frame, text=f"Dialog Actions for '{opt}':", font=("Arial", 10, "bold")).pack(anchor='w')
                            
                            # Branch actions list
                            branch_actions = []
                            
                            # Listbox
                            list_frame = ttk.Frame(main_frame)
                            list_frame.pack(fill=BOTH, expand=True, pady=(6, 6))
                            
                            branch_listbox = Listbox(list_frame, height=10)
                            branch_listbox.pack(side=LEFT, fill=BOTH, expand=True)
                            
                            branch_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=branch_listbox.yview)
                            branch_scrollbar.pack(side=RIGHT, fill=Y)
                            branch_listbox.config(yscrollcommand=branch_scrollbar.set)
                            
                            def refresh_branch_list():
                                branch_listbox.delete(0, END)
                                for action in branch_actions:
                                    atype = action.action_type
                                    if atype == DialogActionEnum.MESSAGE:
                                        msg = action.parameters.get('message', '')
                                        if msg.startswith('{SCRIPT}'):
                                            branch_listbox.insert(END, f"Script: {msg[8:][:30]}...")
                                        else:
                                            branch_listbox.insert(END, f"Message: {msg[:35]}...")
                                    elif atype == DialogActionEnum.NEXT_BUTTON:
                                        branch_listbox.insert(END, "Next Button")
                                    elif atype == DialogActionEnum.CLOSE_BUTTON:
                                        branch_listbox.insert(END, "Close Button")
                            
                            def add_branch_msg():
                                msg = simpledialog.askstring("Add Message", "Enter message text:", parent=branch_dlg)
                                if msg:
                                    branch_actions.append(DialogAction(DialogActionEnum.MESSAGE, {'message': msg}))
                                    refresh_branch_list()
                            
                            def add_branch_next():
                                branch_actions.append(DialogAction(DialogActionEnum.NEXT_BUTTON, {}))
                                refresh_branch_list()
                            
                            def add_branch_close():
                                branch_actions.append(DialogAction(DialogActionEnum.CLOSE_BUTTON, {}))
                                refresh_branch_list()
                            
                            def add_branch_script():
                                cmd_str = simpledialog.askstring("Script Command", "Enter command (e.g., set Zeny, Zeny - 100):", parent=branch_dlg)
                                if cmd_str:
                                    branch_actions.append(DialogAction(DialogActionEnum.MESSAGE, {'message': f"{{SCRIPT}}{cmd_str}"}))
                                    refresh_branch_list()
                            
                            def remove_branch_act():
                                sel = branch_listbox.curselection()
                                if sel:
                                    del branch_actions[sel[0]]
                                    refresh_branch_list()
                            
                            def move_branch_up():
                                sel = branch_listbox.curselection()
                                if sel and sel[0] > 0:
                                    idx = sel[0]
                                    branch_actions[idx], branch_actions[idx-1] = branch_actions[idx-1], branch_actions[idx]
                                    refresh_branch_list()
                                    branch_listbox.selection_set(idx-1)
                            
                            def move_branch_down():
                                sel = branch_listbox.curselection()
                                if sel and sel[0] < len(branch_actions) - 1:
                                    idx = sel[0]
                                    branch_actions[idx], branch_actions[idx+1] = branch_actions[idx+1], branch_actions[idx]
                                    refresh_branch_list()
                                    branch_listbox.selection_set(idx+1)
                            
                            # Action buttons
                            action_frame = ttk.Frame(main_frame)
                            action_frame.pack(fill=X, pady=(0, 6))
                            
                            ttk.Label(action_frame, text="Add:").pack(side=LEFT, padx=(0, 6))
                            ttk.Button(action_frame, text="Message", command=add_branch_msg, width=9).pack(side=LEFT, padx=2)
                            ttk.Button(action_frame, text="Next", command=add_branch_next, width=6).pack(side=LEFT, padx=2)
                            ttk.Button(action_frame, text="Close", command=add_branch_close, width=6).pack(side=LEFT, padx=2)
                            ttk.Button(action_frame, text="Script", command=add_branch_script, width=7).pack(side=LEFT, padx=2)
                            
                            # Reorder buttons
                            order_frame = ttk.Frame(main_frame)
                            order_frame.pack(fill=X, pady=(0, 6))
                            
                            ttk.Label(order_frame, text="Reorder:").pack(side=LEFT, padx=(0, 6))
                            ttk.Button(order_frame, text="↑", command=move_branch_up, width=4).pack(side=LEFT, padx=2)
                            ttk.Button(order_frame, text="↓", command=move_branch_down, width=4).pack(side=LEFT, padx=2)
                            ttk.Button(order_frame, text="✕ Remove", command=remove_branch_act, width=10).pack(side=LEFT, padx=2)
                            
                            # Bottom buttons
                            branch_saved = [False]
                            
                            def save_branch():
                                if branch_actions:
                                    # Convert actions to text format for storage
                                    lines = []
                                    for action in branch_actions:
                                        cmd = action.to_script_command()
                                        # Simple format: one command per line
                                        if action.action_type == DialogActionEnum.MESSAGE:
                                            msg = action.parameters.get('message', '')
                                            if msg.startswith('{SCRIPT}'):
                                                lines.append(msg[8:])
                                            else:
                                                lines.append(msg)
                                        elif action.action_type == DialogActionEnum.NEXT_BUTTON:
                                            lines.append('next')
                                        elif action.action_type == DialogActionEnum.CLOSE_BUTTON:
                                            lines.append('close')
                                    branches[opt] = '\n'.join(lines)
                                branch_saved[0] = True
                                branch_dlg.destroy()
                            
                            btn_frame = ttk.Frame(main_frame)
                            btn_frame.pack(fill=X, pady=(6, 0))
                            ttk.Button(btn_frame, text="Save Branch", command=save_branch).pack(side=RIGHT, padx=4)
                            ttk.Button(btn_frame, text="Skip", command=branch_dlg.destroy).pack(side=RIGHT, padx=4)
                            
                            branch_dlg.wait_window()
                        
                        existing_actions.append(DialogAction(DialogActionEnum.MENU, {'options': options, 'branches': branches}))
                    else:
                        existing_actions.append(DialogAction(DialogActionEnum.MENU, {'options': options}))
                    
                    refresh_list()
            
            def add_script_cmd():
                # Common script commands dropdown
                cmd_dlg = Toplevel(dlg)
                cmd_dlg.title("Insert Script Command")
                cmd_dlg.transient(dlg)
                cmd_dlg.grab_set()
                cmd_dlg.geometry("400x200")
                
                cmd_frame = ttk.Frame(cmd_dlg, padding=12)
                cmd_frame.pack(fill=BOTH, expand=True)
                
                ttk.Label(cmd_frame, text="Select Command:").pack(anchor='w')
                
                commands = [
                    "getitem <id>, <amount>",
                    "delitem <id>, <amount>",
                    "set <variable>, <value>",
                    "if (<condition>) {",
                    "warp \"<map>\", <x>, <y>",
                    "heal <hp>, <sp>",
                    "input <variable>",
                    "setarray <array>, <values>",
                    "getarg(<index>)",
                    "callfunc(\"<function>\")",
                    "callsub <label>",
                    "announce \"<text>\", <flag>",
                ]
                
                cmd_var = StringVar()
                cmd_combo = ttk.Combobox(cmd_frame, textvariable=cmd_var, values=commands, width=40)
                cmd_combo.pack(fill=X, pady=(6, 6))
                cmd_combo.current(0)
                
                ttk.Label(cmd_frame, text="Custom command:").pack(anchor='w', pady=(12, 0))
                custom_entry = ttk.Entry(cmd_frame, width=40)
                custom_entry.pack(fill=X, pady=(6, 6))
                
                def insert_cmd():
                    cmd = custom_entry.get().strip() or cmd_var.get()
                    if cmd:
                        existing_actions.append(DialogAction(DialogActionEnum.MESSAGE, {'message': f"{{SCRIPT}}{cmd}"}))
                        refresh_list()
                    cmd_dlg.destroy()
                
                btn_frame = ttk.Frame(cmd_frame)
                btn_frame.pack(fill=X, pady=(12, 0))
                ttk.Button(btn_frame, text="Insert", command=insert_cmd).pack(side=RIGHT, padx=4)
                ttk.Button(btn_frame, text="Cancel", command=cmd_dlg.destroy).pack(side=RIGHT, padx=4)
            
            def add_warp():
                map_name = simpledialog.askstring("Warp", "Map name:", parent=dlg)
                if map_name:
                    x = simpledialog.askinteger("Warp", "X coordinate:", parent=dlg, initialvalue=150)
                    y = simpledialog.askinteger("Warp", "Y coordinate:", parent=dlg, initialvalue=150)
                    if x is not None and y is not None:
                        existing_actions.append(DialogAction(DialogActionEnum.WARP, {'map': map_name, 'x': x, 'y': y}))
                        refresh_list()
            
            def add_item_check():
                item_id = simpledialog.askinteger("Item Check", "Item ID:", parent=dlg)
                if item_id:
                    count = simpledialog.askinteger("Item Check", "Required count:", parent=dlg, initialvalue=1)
                    if count:
                        existing_actions.append(DialogAction(DialogActionEnum.ITEM_CHECK, {'item_id': item_id, 'count': count}))
                        refresh_list()
            
            def add_item_give():
                item_id = simpledialog.askinteger("Give Item", "Item ID:", parent=dlg)
                if item_id:
                    amount = simpledialog.askinteger("Give Item", "Amount:", parent=dlg, initialvalue=1)
                    if amount:
                        existing_actions.append(DialogAction(DialogActionEnum.ITEM_GIVE, {'item_id': item_id, 'amount': amount}))
                        refresh_list()
            
            def add_item_remove():
                item_id = simpledialog.askinteger("Remove Item", "Item ID:", parent=dlg)
                if item_id:
                    amount = simpledialog.askinteger("Remove Item", "Amount:", parent=dlg, initialvalue=1)
                    if amount:
                        existing_actions.append(DialogAction(DialogActionEnum.ITEM_REMOVE, {'item_id': item_id, 'amount': amount}))
                        refresh_list()
            
            def remove_act():
                sel = actions_listbox.curselection()
                if sel:
                    del existing_actions[sel[0]]
                    refresh_list()
            
            def move_up_act():
                sel = actions_listbox.curselection()
                if sel and sel[0] > 0:
                    idx = sel[0]
                    existing_actions[idx], existing_actions[idx-1] = existing_actions[idx-1], existing_actions[idx]
                    refresh_list()
                    actions_listbox.selection_set(idx-1)
            
            def move_down_act():
                sel = actions_listbox.curselection()
                if sel and sel[0] < len(existing_actions) - 1:
                    idx = sel[0]
                    existing_actions[idx], existing_actions[idx+1] = existing_actions[idx+1], existing_actions[idx]
                    refresh_list()
                    actions_listbox.selection_set(idx+1)
            
            ttk.Label(action_btn_frame, text="Add:").pack(side=LEFT, padx=(0, 6))
            ttk.Button(action_btn_frame, text="Message", command=add_msg, width=9).pack(side=LEFT, padx=2)
            ttk.Button(action_btn_frame, text="Next", command=add_nxt, width=6).pack(side=LEFT, padx=2)
            ttk.Button(action_btn_frame, text="Close", command=add_cls, width=6).pack(side=LEFT, padx=2)
            ttk.Button(action_btn_frame, text="Menu", command=add_mnu, width=6).pack(side=LEFT, padx=2)
            ttk.Button(action_btn_frame, text="Script", command=add_script_cmd, width=7).pack(side=LEFT, padx=2)
            
            # Advanced actions
            action_btn_frame2 = ttk.Frame(content_frame)
            action_btn_frame2.pack(fill=X, pady=(0, 6))
            
            ttk.Label(action_btn_frame2, text="Advanced:").pack(side=LEFT, padx=(0, 6))
            ttk.Button(action_btn_frame2, text="Warp", command=add_warp, width=8).pack(side=LEFT, padx=2)
            ttk.Button(action_btn_frame2, text="Check Item", command=add_item_check, width=10).pack(side=LEFT, padx=2)
            ttk.Button(action_btn_frame2, text="Give Item", command=add_item_give, width=10).pack(side=LEFT, padx=2)
            ttk.Button(action_btn_frame2, text="Remove Item", command=add_item_remove, width=12).pack(side=LEFT, padx=2)
            
            # Reorder
            order_frame = ttk.Frame(content_frame)
            order_frame.pack(fill=X)
            
            ttk.Label(order_frame, text="Reorder:").pack(side=LEFT, padx=(0, 6))
            ttk.Button(order_frame, text="↑", command=move_up_act, width=4).pack(side=LEFT, padx=2)
            ttk.Button(order_frame, text="↓", command=move_down_act, width=4).pack(side=LEFT, padx=2)
            ttk.Button(order_frame, text="✕ Remove", command=remove_act, width=10).pack(side=LEFT, padx=2)
            
            state_widgets['dialog_actions'] = existing_actions

        elif step == 4:
            # Summary and preview
            summary = wizard.get_summary()
            ttk.Label(content_frame, text="Summary:").pack(anchor='w')
            summary_box = Text(content_frame, height=6, wrap=WORD)
            summary_box.pack(fill=X, expand=False, pady=(6, 6))
            summary_box.insert('1.0', summary)
            summary_box.config(state=DISABLED)

            ttk.Label(content_frame, text="Preview Script:").pack(anchor='w')
            preview_box = Text(content_frame, height=8, wrap=WORD)
            preview_box.pack(fill=BOTH, expand=True)

            # Build preview NPC and script
            try:
                sd = wizard.npc_data
                preview_npc = ScriptNPC(sd.get('name', ''), sd.get('map', 'prontera'), sd.get('x', 150), sd.get('y', 150), facing=sd.get('facing', 4), sprite_id=sd.get('sprite', 120))
                for act in sd.get('dialog_actions', []):
                    if hasattr(act, 'to_script_command'):
                        preview_npc.add_command(act.to_script_command())
                gen = ScriptGenerator()
                gen.add_npc(preview_npc)
                preview_script = gen.generate_script()
                preview_box.insert('1.0', preview_script)
            except Exception as e:
                preview_box.insert('1.0', f"Failed to build preview: {e}")

            state_widgets['preview_box'] = preview_box

    def save_current_step():
        # Persist current step values into wizard.npc_data
        step = wizard.get_current_step()
        try:
            if step == 0:
                name = state_widgets['name'].get().strip()
                mapn = state_widgets['map'].get().strip()
                x = int(state_widgets['x'].get())
                y = int(state_widgets['y'].get())
                facing = int(state_widgets['facing'].get())
                wizard.set_npc_basic_info(name, mapn, x, y)
                wizard.npc_data['facing'] = facing

            elif step == 1:
                sprite_id = int(state_widgets['sprite'].get())
                wizard.set_npc_appearance(sprite_id)

            elif step == 2:
                sel = state_widgets['type'].get()
                # Map selected value back to enum
                try:
                    from rathena_script_ui import NPCTypeEnum
                    for t in NPCTypeEnum:
                        if t.value == sel:
                            wizard.set_npc_type(t)
                            break
                except Exception:
                    pass

            elif step == 3:
                # Dialog actions are already in existing_actions list (passed by reference)
                # Just need to update wizard data
                dialog_actions_list = state_widgets.get('dialog_actions')
                if dialog_actions_list is not None:
                    wizard.npc_data['dialog_actions'] = dialog_actions_list
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save step data: {e}")

    def next_step():
        # Save current inputs first
        save_current_step()
        try:
            if wizard.next_step():
                dlg.destroy()
                _launch_wizard_dialog(root, wizard)
            else:
                # wizard._finish() called internally
                dlg.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Wizard error: {e}")

    def prev_step():
        try:
            if wizard.previous_step():
                dlg.destroy()
                _launch_wizard_dialog(root, wizard)
        except Exception as e:
            messagebox.showerror("Error", f"Wizard error: {e}")

    ttk.Button(btn_frame, text="Back", command=prev_step).pack(side=LEFT, padx=4)
    ttk.Button(btn_frame, text="Next", command=next_step).pack(side=RIGHT, padx=4)
    ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=RIGHT, padx=4)

    # Initial render
    try:
        render_step()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to render wizard step: {e}")


def create_rathena_menu(root, menuBar, textArea):
    """Create the rAthena Tools menu and add it to the menu bar."""
    if not _RATHENA_TOOLS_AVAILABLE:
        return None
    
    rathenaMenu = Menu(menuBar, tearoff=False)
    menuBar.add_cascade(label="rAthena Tools", menu=rathenaMenu)
    
    def get_textarea():
        """Get the current text area widget from root"""
        try:
            import sys
            main_module = sys.modules['__main__']
            if hasattr(main_module, 'textArea'):
                return main_module.textArea
        except:
            pass
        return None
    
    rathenaMenu.add_command(
        label="New NPC Script",
        command=lambda: launch_npc_wizard(root, get_textarea)
    )
    rathenaMenu.add_command(
        label="New Function",
        command=lambda: launch_function_creator(root, get_textarea)
    )
    rathenaMenu.add_separator()
    rathenaMenu.add_command(
        label="NPC Wizard...",
        command=lambda: launch_npc_wizard(root, get_textarea)
    )
    rathenaMenu.add_command(
        label="Dialog Builder...",
        command=lambda: launch_dialog_builder(root, get_textarea)
    )
    rathenaMenu.add_separator()
    rathenaMenu.add_command(
        label="Validate Script",
        command=lambda: validate_current_script(root, get_textarea)
    )
    rathenaMenu.add_command(
        label="Insert Quick NPC",
        command=lambda: insert_quick_npc(root, get_textarea)
    )
    
    return rathenaMenu


def launch_npc_wizard(root, get_textarea):
    """Launch the NPC Wizard dialog."""
    if not _RATHENA_TOOLS_AVAILABLE:
        messagebox.showerror(
            "Not Available",
            "rAthena Tools are not available. Ensure rathena_script_gen.py and rathena_script_ui.py are installed."
        )
        return
    
    try:
        # Get the textArea (could be callable or direct reference)
        if callable(get_textarea):
            textArea = get_textarea()
        else:
            textArea = get_textarea
        
        if textArea is None:
            messagebox.showerror("Error", "No text editor found")
            return
        
        # Create callback for when wizard completes
        def on_npc_complete(npc):
            """Called when NPC wizard is complete"""
            try:
                # Generate script from the created NPC
                gen = ScriptGenerator()
                gen.add_npc(npc)
                script_text = gen.generate_script()
                
                # Insert into text area
                textArea.insert('end', '\n' + script_text)
                messagebox.showinfo("Success", f"NPC '{npc.name}' inserted successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to insert script: {e}")
        
        # Create wizard with callback
        wizard = NPCWizard(on_npc_complete)
        
        # Launch wizard in a dialog
        _launch_wizard_dialog(root, wizard)
        
    except Exception as e:
        messagebox.showerror("Error", f"NPC Wizard error: {e}")


def launch_function_creator(root, get_textarea):
    """Launch a simple function creator dialog."""
    if not _RATHENA_TOOLS_AVAILABLE:
        messagebox.showerror(
            "Not Available",
            "rAthena Tools are not available."
        )
        return
    
    # Get the textArea
    if callable(get_textarea):
        textArea = get_textarea()
    else:
        textArea = get_textarea
    
    if textArea is None:
        messagebox.showerror("Error", "No text editor found")
        return
    
    dlg = Toplevel(root)
    dlg.title("Create rAthena Function")
    dlg.transient(root)
    dlg.grab_set()
    dlg.geometry("500x400")
    
    frame = ttk.Frame(dlg, padding=12)
    frame.pack(fill=BOTH, expand=True)
    
    # Function name
    ttk.Label(frame, text="Function Name:").grid(row=0, column=0, sticky='w')
    func_name = ttk.Entry(frame, width=30)
    func_name.grid(row=0, column=1, sticky='ew', padx=(6, 0))
    
    # Parameters
    ttk.Label(frame, text="Parameters (comma-separated):").grid(row=1, column=0, sticky='w')
    params = ttk.Entry(frame, width=30)
    params.grid(row=1, column=1, sticky='ew', padx=(6, 0))
    
    # Function body
    ttk.Label(frame, text="Function Body:").grid(row=2, column=0, sticky='nw')
    body = Text(frame, width=40, height=15, wrap=WORD)
    body.grid(row=2, column=1, sticky='nsew', padx=(6, 0))
    
    # Scrollbar for body
    scrollbar = ttk.Scrollbar(frame, orient='vertical', command=body.yview)
    scrollbar.grid(row=2, column=2, sticky='ns')
    body.config(yscrollcommand=scrollbar.set)
    
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(2, weight=1)
    
    def save_function():
        try:
            name = func_name.get().strip()
            params_str = params.get().strip()
            body_str = body.get('1.0', 'end').strip()
            
            if not name:
                messagebox.showwarning("Input Error", "Function name is required.")
                return
            
            # Create script function
            param_list = [p.strip() for p in params_str.split(',')] if params_str else []
            func = ScriptFunction(name, param_list)
            for line in body_str.split('\n'):
                if line.strip():
                    func.add_command(line)
            
            # Generate and insert
            gen = ScriptGenerator()
            gen.add_function(func)
            script_text = gen.generate_script()
            
            textArea.insert('end', '\n' + script_text)
            messagebox.showinfo("Success", "Function inserted successfully!")
            dlg.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create function: {e}")
    
    # Buttons
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=3, column=0, columnspan=3, sticky='e', pady=(12, 0))
    
    ttk.Button(btn_frame, text="Insert", command=save_function).pack(side=RIGHT, padx=4)
    ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=RIGHT, padx=4)







def launch_dialog_builder(root, get_textarea):
    """Launch the interactive Dialog Builder."""
    if not _RATHENA_TOOLS_AVAILABLE:
        messagebox.showerror(
            "Not Available",
            "rAthena Tools are not available."
        )
        return
        
    # Get the textArea
    if callable(get_textarea):
        textArea = get_textarea()
    else:
        textArea = get_textarea
        
    if textArea is None:
        messagebox.showerror("Error", "No text editor found")
        return
        
    try:
        from rathena_script_ui import DialogAction, DialogActionEnum
            
        dlg = Toplevel(root)
        dlg.title("Dialog Builder")
        dlg.transient(root)
        dlg.grab_set()
        dlg.geometry("800x600")
            
        main_frame = ttk.Frame(dlg, padding=12)
        main_frame.pack(fill=BOTH, expand=True)
            
        # Split into left (tools) and right (preview)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 6))
            
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(6, 0))
            
        # Dialog actions list
        dialog_actions = []
            
        # LEFT: Action builder
        ttk.Label(left_frame, text="Dialog Actions:", font=("Arial", 10, "bold")).pack(anchor='w')
            
        # Listbox for actions
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=BOTH, expand=True, pady=(6, 6))
            
        actions_listbox = Listbox(list_frame, height=15)
        actions_listbox.pack(side=LEFT, fill=BOTH, expand=True)
            
        list_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=actions_listbox.yview)
        list_scrollbar.pack(side=RIGHT, fill=Y)
        actions_listbox.config(yscrollcommand=list_scrollbar.set)
            
        # Action buttons
        action_btn_frame = ttk.Frame(left_frame)
        action_btn_frame.pack(fill=X, pady=(0, 6))
            
        ttk.Label(action_btn_frame, text="Add Action:").pack(side=LEFT, padx=(0, 6))
            
        def add_message():
            msg = simpledialog.askstring("Add Message", "Enter message text:", parent=dlg)
            if msg:
                action = DialogAction(DialogActionEnum.MESSAGE, {'message': msg})
                dialog_actions.append(action)
                actions_listbox.insert(END, f"Message: {msg[:40]}...")
                update_preview()
            
        def add_next():
            action = DialogAction(DialogActionEnum.NEXT_BUTTON, {})
            dialog_actions.append(action)
            actions_listbox.insert(END, "Next Button")
            update_preview()
            
        def add_close():
            action = DialogAction(DialogActionEnum.CLOSE_BUTTON, {})
            dialog_actions.append(action)
            actions_listbox.insert(END, "Close Button")
            update_preview()
            
        def add_menu():
            opts_str = simpledialog.askstring("Add Menu", "Enter menu options (separated by |):", parent=dlg)
            if opts_str:
                options = [o.strip() for o in opts_str.split('|')]
                
                # Ask if user wants to define branches now
                if messagebox.askyesno("Menu Branches", "Do you want to define dialog branches for each menu option?"):
                    branches = {}
                    for opt in options:
                        # Full dialog builder for each branch
                        branch_dlg = Toplevel(dlg)
                        branch_dlg.title(f"Branch: {opt}")
                        branch_dlg.transient(dlg)
                        branch_dlg.grab_set()
                        branch_dlg.geometry("700x500")
                        
                        main_frame = ttk.Frame(branch_dlg, padding=12)
                        main_frame.pack(fill=BOTH, expand=True)
                        
                        ttk.Label(main_frame, text=f"Dialog Actions for '{opt}':", font=("Arial", 10, "bold")).pack(anchor='w')
                        
                        # Branch actions list
                        branch_actions = []
                        
                        # Listbox
                        list_frame = ttk.Frame(main_frame)
                        list_frame.pack(fill=BOTH, expand=True, pady=(6, 6))
                        
                        branch_listbox = Listbox(list_frame, height=10)
                        branch_listbox.pack(side=LEFT, fill=BOTH, expand=True)
                        
                        branch_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=branch_listbox.yview)
                        branch_scrollbar.pack(side=RIGHT, fill=Y)
                        branch_listbox.config(yscrollcommand=branch_scrollbar.set)
                        
                        def refresh_branch_list():
                            branch_listbox.delete(0, END)
                            for action in branch_actions:
                                atype = action.action_type
                                if atype == DialogActionEnum.MESSAGE:
                                    msg = action.parameters.get('message', '')
                                    if msg.startswith('{SCRIPT}'):
                                        branch_listbox.insert(END, f"Script: {msg[8:][:30]}...")
                                    else:
                                        branch_listbox.insert(END, f"Message: {msg[:35]}...")
                                elif atype == DialogActionEnum.NEXT_BUTTON:
                                    branch_listbox.insert(END, "Next Button")
                                elif atype == DialogActionEnum.CLOSE_BUTTON:
                                    branch_listbox.insert(END, "Close Button")
                        
                        def add_branch_msg():
                            msg = simpledialog.askstring("Add Message", "Enter message text:", parent=branch_dlg)
                            if msg:
                                branch_actions.append(DialogAction(DialogActionEnum.MESSAGE, {'message': msg}))
                                refresh_branch_list()
                        
                        def add_branch_next():
                            branch_actions.append(DialogAction(DialogActionEnum.NEXT_BUTTON, {}))
                            refresh_branch_list()
                        
                        def add_branch_close():
                            branch_actions.append(DialogAction(DialogActionEnum.CLOSE_BUTTON, {}))
                            refresh_branch_list()
                        
                        def add_branch_script():
                            cmd_str = simpledialog.askstring("Script Command", "Enter command (e.g., set Zeny, Zeny - 100):", parent=branch_dlg)
                            if cmd_str:
                                branch_actions.append(DialogAction(DialogActionEnum.MESSAGE, {'message': f"{{SCRIPT}}{cmd_str}"}))
                                refresh_branch_list()
                        
                        def remove_branch_act():
                            sel = branch_listbox.curselection()
                            if sel:
                                del branch_actions[sel[0]]
                                refresh_branch_list()
                        
                        def move_branch_up():
                            sel = branch_listbox.curselection()
                            if sel and sel[0] > 0:
                                idx = sel[0]
                                branch_actions[idx], branch_actions[idx-1] = branch_actions[idx-1], branch_actions[idx]
                                refresh_branch_list()
                                branch_listbox.selection_set(idx-1)
                        
                        def move_branch_down():
                            sel = branch_listbox.curselection()
                            if sel and sel[0] < len(branch_actions) - 1:
                                idx = sel[0]
                                branch_actions[idx], branch_actions[idx+1] = branch_actions[idx+1], branch_actions[idx]
                                refresh_branch_list()
                                branch_listbox.selection_set(idx+1)
                        
                        # Action buttons
                        action_frame = ttk.Frame(main_frame)
                        action_frame.pack(fill=X, pady=(0, 6))
                        
                        ttk.Label(action_frame, text="Add:").pack(side=LEFT, padx=(0, 6))
                        ttk.Button(action_frame, text="Message", command=add_branch_msg, width=9).pack(side=LEFT, padx=2)
                        ttk.Button(action_frame, text="Next", command=add_branch_next, width=6).pack(side=LEFT, padx=2)
                        ttk.Button(action_frame, text="Close", command=add_branch_close, width=6).pack(side=LEFT, padx=2)
                        ttk.Button(action_frame, text="Script", command=add_branch_script, width=7).pack(side=LEFT, padx=2)
                        
                        # Reorder buttons
                        order_frame = ttk.Frame(main_frame)
                        order_frame.pack(fill=X, pady=(0, 6))
                        
                        ttk.Label(order_frame, text="Reorder:").pack(side=LEFT, padx=(0, 6))
                        ttk.Button(order_frame, text="↑", command=move_branch_up, width=4).pack(side=LEFT, padx=2)
                        ttk.Button(order_frame, text="↓", command=move_branch_down, width=4).pack(side=LEFT, padx=2)
                        ttk.Button(order_frame, text="✕ Remove", command=remove_branch_act, width=10).pack(side=LEFT, padx=2)
                        
                        # Bottom buttons
                        branch_saved = [False]
                        
                        def save_branch():
                            if branch_actions:
                                # Convert actions to text format for storage
                                lines = []
                                for action in branch_actions:
                                    if action.action_type == DialogActionEnum.MESSAGE:
                                        msg = action.parameters.get('message', '')
                                        if msg.startswith('{SCRIPT}'):
                                            lines.append(msg[8:])
                                        else:
                                            lines.append(msg)
                                    elif action.action_type == DialogActionEnum.NEXT_BUTTON:
                                        lines.append('next')
                                    elif action.action_type == DialogActionEnum.CLOSE_BUTTON:
                                        lines.append('close')
                                branches[opt] = '\n'.join(lines)
                            branch_saved[0] = True
                            branch_dlg.destroy()
                        
                        btn_frame_br = ttk.Frame(main_frame)
                        btn_frame_br.pack(fill=X, pady=(6, 0))
                        ttk.Button(btn_frame_br, text="Save Branch", command=save_branch).pack(side=RIGHT, padx=4)
                        ttk.Button(btn_frame_br, text="Skip", command=branch_dlg.destroy).pack(side=RIGHT, padx=4)
                        
                        branch_dlg.wait_window()
                    
                    action = DialogAction(DialogActionEnum.MENU, {'options': options, 'branches': branches})
                    dialog_actions.append(action)
                    branches_info = f" [{len(branches)} branches]" if branches else ""
                    actions_listbox.insert(END, f"Menu: {', '.join(options[:3])}...{branches_info}")
                else:
                    action = DialogAction(DialogActionEnum.MENU, {'options': options})
                    dialog_actions.append(action)
                    actions_listbox.insert(END, f"Menu: {', '.join(options[:3])}...")
                
                update_preview()
            
        def add_warp():
            map_name = simpledialog.askstring("Warp", "Map name:", parent=dlg)
            if map_name:
                x = simpledialog.askinteger("Warp", "X coordinate:", parent=dlg, initialvalue=150)
                y = simpledialog.askinteger("Warp", "Y coordinate:", parent=dlg, initialvalue=150)
                if x is not None and y is not None:
                    action = DialogAction(DialogActionEnum.WARP, {'map': map_name, 'x': x, 'y': y})
                    dialog_actions.append(action)
                    actions_listbox.insert(END, f"Warp: {map_name} ({x},{y})")
                    update_preview()
            
        def add_item_check():
            item_id = simpledialog.askinteger("Item Check", "Item ID:", parent=dlg)
            if item_id:
                count = simpledialog.askinteger("Item Check", "Required count:", parent=dlg, initialvalue=1)
                if count:
                    action = DialogAction(DialogActionEnum.ITEM_CHECK, {'item_id': item_id, 'count': count})
                    dialog_actions.append(action)
                    actions_listbox.insert(END, f"Check: Item {item_id} x{count}")
                    update_preview()
            
        def add_item_give():
            item_id = simpledialog.askinteger("Give Item", "Item ID:", parent=dlg)
            if item_id:
                amount = simpledialog.askinteger("Give Item", "Amount:", parent=dlg, initialvalue=1)
                if amount:
                    action = DialogAction(DialogActionEnum.ITEM_GIVE, {'item_id': item_id, 'amount': amount})
                    dialog_actions.append(action)
                    actions_listbox.insert(END, f"Give: Item {item_id} x{amount}")
                    update_preview()
            
        def add_item_remove():
            item_id = simpledialog.askinteger("Remove Item", "Item ID:", parent=dlg)
            if item_id:
                amount = simpledialog.askinteger("Remove Item", "Amount:", parent=dlg, initialvalue=1)
                if amount:
                    action = DialogAction(DialogActionEnum.ITEM_REMOVE, {'item_id': item_id, 'amount': amount})
                    dialog_actions.append(action)
                    actions_listbox.insert(END, f"Remove: Item {item_id} x{amount}")
                    update_preview()
            
        def move_up():
            sel = actions_listbox.curselection()
            if sel and sel[0] > 0:
                idx = sel[0]
                dialog_actions[idx], dialog_actions[idx-1] = dialog_actions[idx-1], dialog_actions[idx]
                refresh_list()
                actions_listbox.selection_set(idx-1)
                update_preview()
            
        def move_down():
            sel = actions_listbox.curselection()
            if sel and sel[0] < len(dialog_actions) - 1:
                idx = sel[0]
                dialog_actions[idx], dialog_actions[idx+1] = dialog_actions[idx+1], dialog_actions[idx]
                refresh_list()
                actions_listbox.selection_set(idx+1)
                update_preview()
            
        def remove_action():
            sel = actions_listbox.curselection()
            if sel:
                idx = sel[0]
                del dialog_actions[idx]
                refresh_list()
                update_preview()
            
        def refresh_list():
            actions_listbox.delete(0, END)
            for action in dialog_actions:
                atype = action.action_type
                if atype == DialogActionEnum.MESSAGE:
                    msg = action.parameters.get('message', '')
                    if msg.startswith('{SCRIPT}'):
                        actions_listbox.insert(END, f"Script: {msg[8:][:35]}...")
                    else:
                        actions_listbox.insert(END, f"Message: {msg[:40]}...")
                elif atype == DialogActionEnum.NEXT_BUTTON:
                    actions_listbox.insert(END, "Next Button")
                elif atype == DialogActionEnum.CLOSE_BUTTON:
                    actions_listbox.insert(END, "Close Button")
                elif atype == DialogActionEnum.MENU:
                    opts = action.parameters.get('options', [])
                    branches = action.parameters.get('branches', {})
                    branch_info = f" [{len(branches)} branches]" if branches else ""
                    actions_listbox.insert(END, f"Menu: {', '.join(opts[:3])}...{branch_info}")
                elif atype == DialogActionEnum.WARP:
                    m = action.parameters.get('map', '')
                    x = action.parameters.get('x', 0)
                    y = action.parameters.get('y', 0)
                    actions_listbox.insert(END, f"Warp: {m} ({x},{y})")
                elif atype == DialogActionEnum.ITEM_CHECK:
                    actions_listbox.insert(END, f"Check: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('count', 1)}")
                elif atype == DialogActionEnum.ITEM_GIVE:
                    actions_listbox.insert(END, f"Give: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('amount', 1)}")
                elif atype == DialogActionEnum.ITEM_REMOVE:
                    actions_listbox.insert(END, f"Remove: Item {action.parameters.get('item_id', 0)} x{action.parameters.get('amount', 1)}")
            
        def add_script_cmd():
            # Common script commands dropdown
            cmd_dlg = Toplevel(dlg)
            cmd_dlg.title("Insert Script Command")
            cmd_dlg.transient(dlg)
            cmd_dlg.grab_set()
            cmd_dlg.geometry("400x200")
            
            cmd_frame = ttk.Frame(cmd_dlg, padding=12)
            cmd_frame.pack(fill=BOTH, expand=True)
            
            ttk.Label(cmd_frame, text="Select Command:").pack(anchor='w')
            
            commands = [
                "getitem <id>, <amount>",
                "delitem <id>, <amount>",
                "set <variable>, <value>",
                "if (<condition>) {",
                "warp \"<map>\", <x>, <y>",
                "heal <hp>, <sp>",
                "input <variable>",
                "setarray <array>, <values>",
                "getarg(<index>)",
                "callfunc(\"<function>\")",
                "callsub <label>",
                "announce \"<text>\", <flag>",
            ]
            
            cmd_var = StringVar()
            cmd_combo = ttk.Combobox(cmd_frame, textvariable=cmd_var, values=commands, width=40)
            cmd_combo.pack(fill=X, pady=(6, 6))
            cmd_combo.current(0)
            
            ttk.Label(cmd_frame, text="Custom command:").pack(anchor='w', pady=(12, 0))
            custom_entry = ttk.Entry(cmd_frame, width=40)
            custom_entry.pack(fill=X, pady=(6, 6))
            
            def insert_cmd():
                cmd = custom_entry.get().strip() or cmd_var.get()
                if cmd:
                    action = DialogAction(DialogActionEnum.MESSAGE, {'message': f"{{SCRIPT}}{cmd}"})
                    dialog_actions.append(action)
                    actions_listbox.insert(END, f"Script: {cmd[:35]}...")
                    update_preview()
                cmd_dlg.destroy()
            
            btn_frame_cmd = ttk.Frame(cmd_frame)
            btn_frame_cmd.pack(fill=X, pady=(12, 0))
            ttk.Button(btn_frame_cmd, text="Insert", command=insert_cmd).pack(side=RIGHT, padx=4)
            ttk.Button(btn_frame_cmd, text="Cancel", command=cmd_dlg.destroy).pack(side=RIGHT, padx=4)
        
        ttk.Button(action_btn_frame, text="Message", command=add_message, width=10).pack(side=LEFT, padx=2)
        ttk.Button(action_btn_frame, text="Next", command=add_next, width=8).pack(side=LEFT, padx=2)
        ttk.Button(action_btn_frame, text="Close", command=add_close, width=8).pack(side=LEFT, padx=2)
        ttk.Button(action_btn_frame, text="Menu", command=add_menu, width=8).pack(side=LEFT, padx=2)
        ttk.Button(action_btn_frame, text="Script", command=add_script_cmd, width=8).pack(side=LEFT, padx=2)
            
        action_btn_frame2 = ttk.Frame(left_frame)
        action_btn_frame2.pack(fill=X, pady=(0, 6))
            
        ttk.Label(action_btn_frame2, text="Advanced:").pack(side=LEFT, padx=(0, 6))
        ttk.Button(action_btn_frame2, text="Warp", command=add_warp, width=8).pack(side=LEFT, padx=2)
        ttk.Button(action_btn_frame2, text="Check Item", command=add_item_check, width=10).pack(side=LEFT, padx=2)
        ttk.Button(action_btn_frame2, text="Give Item", command=add_item_give, width=10).pack(side=LEFT, padx=2)
        ttk.Button(action_btn_frame2, text="Remove Item", command=add_item_remove, width=12).pack(side=LEFT, padx=2)
            
        # Reorder/remove buttons
        order_frame = ttk.Frame(left_frame)
        order_frame.pack(fill=X, pady=(0, 6))
            
        ttk.Label(order_frame, text="Reorder:").pack(side=LEFT, padx=(0, 6))
        ttk.Button(order_frame, text="↑ Up", command=move_up, width=8).pack(side=LEFT, padx=2)
        ttk.Button(order_frame, text="↓ Down", command=move_down, width=8).pack(side=LEFT, padx=2)
        ttk.Button(order_frame, text="✕ Remove", command=remove_action, width=10).pack(side=LEFT, padx=2)
            
        # RIGHT: Preview
        ttk.Label(right_frame, text="Preview:", font=("Arial", 10, "bold")).pack(anchor='w')
        
        preview_text_frame = ttk.Frame(right_frame)
        preview_text_frame.pack(fill=BOTH, expand=True, pady=(6, 0))
        
        preview_text = Text(preview_text_frame, wrap=WORD, height=20)
        preview_text.pack(side=LEFT, fill=BOTH, expand=True)
        
        preview_scrollbar = ttk.Scrollbar(preview_text_frame, orient='vertical', command=preview_text.yview)
        preview_scrollbar.pack(side=RIGHT, fill=Y)
        preview_text.config(yscrollcommand=preview_scrollbar.set)
        
        def update_preview():
            preview_text.delete('1.0', END)
            if not dialog_actions:
                preview_text.insert('1.0', "// No actions added yet")
                return
            
            commands = [action.to_script_command() for action in dialog_actions]
            preview_text.insert('1.0', '\n'.join(commands))
        
        # Insert button below preview
        preview_btn_frame = ttk.Frame(right_frame)
        preview_btn_frame.pack(fill=X, pady=(6, 0))
        
        def insert_preview():
            """Insert preview content directly into editor"""
            if not dialog_actions:
                messagebox.showwarning("Empty", "No dialog actions to insert.")
                return
            
            try:
                commands = [action.to_script_command() for action in dialog_actions]
                output = '\n'.join(commands)
                textArea.insert('end', '\n' + output + '\n')
                messagebox.showinfo("Success", "Dialog commands inserted into editor!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to insert: {e}")
        
        ttk.Button(preview_btn_frame, text="Insert into Editor", command=insert_preview).pack(side=LEFT, padx=4)
            
        # Bottom buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(12, 0), side=BOTTOM)
            
        def insert_dialog():
            if not dialog_actions:
                messagebox.showwarning("Empty", "No dialog actions to insert.")
                return
                
            try:
                commands = [action.to_script_command() for action in dialog_actions]
                output = '\n'.join(commands)
                textArea.insert('end', '\n' + output + '\n')
                messagebox.showinfo("Success", "Dialog commands inserted!")
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to insert dialog: {e}")
            
        ttk.Button(btn_frame, text="Insert into Script", command=insert_dialog).pack(side=RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=RIGHT, padx=4)
            
        # Initial preview
        update_preview()
            
    except Exception as e:
        messagebox.showerror("Error", f"Dialog Builder error: {e}")


def validate_current_script(root, get_textarea):
    """Validate the current script in the text area."""
    if not _RATHENA_TOOLS_AVAILABLE:
        messagebox.showerror(
            "Not Available",
            "rAthena Tools are not available."
        )
        return
    
    # Get the textArea
    if callable(get_textarea):
        textArea = get_textarea()
    else:
        textArea = get_textarea
    
    if textArea is None:
        messagebox.showerror("Error", "No text editor found")
        return
    
    try:
        script_text = textArea.get('1.0', 'end')
        
        # Basic validation checks
        if len(script_text.strip()) < 10:
            messagebox.showwarning("Validation", "Script is too short or empty.")
            return
        
        # Check for common elements
        has_npc = 'script' in script_text.lower() or 'prontera' in script_text.lower()
        has_commands = 'mes' in script_text.lower() or 'close' in script_text.lower()
        
        if has_npc and has_commands:
            messagebox.showinfo("Validation", "Script looks valid! ✓\n\nContains NPC definition and commands.")
        elif script_text.strip():
            messagebox.showwarning(
                "Validation Issues",
                "Script may be incomplete.\n\n"
                "Make sure to include:\n"
                "• NPC location (e.g., 'prontera')\n"
                "• NPC commands (e.g., 'mes', 'close')"
            )
        else:
            messagebox.showwarning("Validation", "Script is empty.")
    except Exception as e:
        messagebox.showerror("Error", f"Validation error: {e}")


def insert_quick_npc(root, get_textarea):
    """Insert a quick/template NPC."""
    if not _RATHENA_TOOLS_AVAILABLE:
        messagebox.showerror(
            "Not Available",
            "rAthena Tools are not available."
        )
        return
    
    # Get the textArea
    if callable(get_textarea):
        textArea = get_textarea()
    else:
        textArea = get_textarea
    
    if textArea is None:
        messagebox.showerror("Error", "No text editor found")
        return
    
    dlg = Toplevel(root)
    dlg.title("Quick NPC")
    dlg.transient(root)
    dlg.grab_set()
    dlg.geometry("400x300")
    
    frame = ttk.Frame(dlg, padding=12)
    frame.pack(fill=BOTH, expand=True)
    
    # NPC Name
    ttk.Label(frame, text="NPC Name:").grid(row=0, column=0, sticky='w')
    npc_name = ttk.Entry(frame, width=30)
    npc_name.grid(row=0, column=1, sticky='ew', padx=(6, 0))
    
    # Map
    ttk.Label(frame, text="Map:").grid(row=1, column=0, sticky='w')
    map_name = ttk.Entry(frame, width=30)
    map_name.insert(0, 'prontera')
    map_name.grid(row=1, column=1, sticky='ew', padx=(6, 0))
    
    # X, Y
    ttk.Label(frame, text="X Position:").grid(row=2, column=0, sticky='w')
    x_pos = ttk.Entry(frame, width=10)
    x_pos.insert(0, '100')
    x_pos.grid(row=2, column=1, sticky='w', padx=(6, 0))
    
    ttk.Label(frame, text="Y Position:").grid(row=3, column=0, sticky='w')
    y_pos = ttk.Entry(frame, width=10)
    y_pos.insert(0, '100')
    y_pos.grid(row=3, column=1, sticky='w', padx=(6, 0))
    
    # Sprite ID
    ttk.Label(frame, text="Sprite ID:").grid(row=4, column=0, sticky='w')
    sprite_id = ttk.Entry(frame, width=10)
    sprite_id.insert(0, '111')
    sprite_id.grid(row=4, column=1, sticky='w', padx=(6, 0))
    
    frame.columnconfigure(1, weight=1)
    
    def create_npc():
        try:
            name = npc_name.get().strip()
            if not name:
                messagebox.showwarning("Input Error", "NPC name is required.")
                return
            
            # Create NPC
            npc = ScriptNPC(
                name,
                map_name.get().strip(),
                int(x_pos.get()),
                int(y_pos.get()),
                int(sprite_id.get())
            )
            
            npc.add_command('mes "[' + name + ']";')
            npc.add_command('mes "Hello there!";')
            npc.add_command('close;')
            
            # Generate and insert
            gen = ScriptGenerator()
            gen.add_npc(npc)
            script_text = gen.generate_script()
            
            textArea.insert('end', '\n' + script_text)
            messagebox.showinfo("Success", "Quick NPC inserted successfully!")
            dlg.destroy()
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create NPC: {e}")
    
    # Buttons
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=5, column=0, columnspan=2, sticky='e', pady=(12, 0))
    
    ttk.Button(btn_frame, text="Create", command=create_npc).pack(side=RIGHT, padx=4)
    ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=RIGHT, padx=4)

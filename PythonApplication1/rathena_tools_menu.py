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
    """Launch enhanced function creator with types and templates."""
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
    dlg.geometry("750x600")
    
    main_frame = ttk.Frame(dlg, padding=12)
    main_frame.pack(fill=BOTH, expand=True)
    
    # Split into left (definition) and right (templates/preview)
    left_frame = ttk.Frame(main_frame)
    left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 6))
    
    right_frame = ttk.Frame(main_frame)
    right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(6, 0))
    
    # LEFT: Function definition
    ttk.Label(left_frame, text="Function Definition", font=("Arial", 10, "bold")).pack(anchor='w', pady=(0, 6))
    
    # Function name
    ttk.Label(left_frame, text="Function Name:").pack(anchor='w')
    func_name = ttk.Entry(left_frame, width=40)
    func_name.pack(fill=X, pady=(2, 6))
    
    # Return type
    ttk.Label(left_frame, text="Return Type:").pack(anchor='w')
    return_types = ["void (no return)", "int", "string", "array", "auto"]
    return_type_var = StringVar(value="void (no return)")
    return_type_combo = ttk.Combobox(left_frame, textvariable=return_type_var, values=return_types, width=37, state='readonly')
    return_type_combo.pack(fill=X, pady=(2, 6))
    
    # Parameters frame
    ttk.Label(left_frame, text="Parameters:", font=("Arial", 9, "bold")).pack(anchor='w', pady=(6, 2))
    
    param_frame = ttk.Frame(left_frame)
    param_frame.pack(fill=BOTH, expand=False, pady=(0, 6))
    
    # Parameter list
    param_list = []  # List of (name, type) tuples
    
    params_listbox = Listbox(param_frame, height=5)
    params_listbox.pack(side=LEFT, fill=BOTH, expand=True)
    
    params_scroll = ttk.Scrollbar(param_frame, orient='vertical', command=params_listbox.yview)
    params_scroll.pack(side=RIGHT, fill=Y)
    params_listbox.config(yscrollcommand=params_scroll.set)
    
    # Parameter buttons
    param_btn_frame = ttk.Frame(left_frame)
    param_btn_frame.pack(fill=X, pady=(0, 6))
    
    def add_parameter():
        param_dlg = Toplevel(dlg)
        param_dlg.title("Add Parameter")
        param_dlg.transient(dlg)
        param_dlg.grab_set()
        param_dlg.geometry("350x150")
        
        param_dlg_frame = ttk.Frame(param_dlg, padding=12)
        param_dlg_frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(param_dlg_frame, text="Parameter Name:").grid(row=0, column=0, sticky='w')
        param_name_entry = ttk.Entry(param_dlg_frame, width=25)
        param_name_entry.grid(row=0, column=1, sticky='ew', padx=(6, 0), pady=(0, 6))
        
        ttk.Label(param_dlg_frame, text="Parameter Type:").grid(row=1, column=0, sticky='w')
        param_types = ["int", "string", "array", "any"]
        param_type_var = StringVar(value="int")
        param_type_combo = ttk.Combobox(param_dlg_frame, textvariable=param_type_var, values=param_types, width=22, state='readonly')
        param_type_combo.grid(row=1, column=1, sticky='ew', padx=(6, 0), pady=(0, 12))
        
        param_dlg_frame.columnconfigure(1, weight=1)
        
        def save_param():
            pname = param_name_entry.get().strip()
            ptype = param_type_var.get()
            if pname:
                param_list.append((pname, ptype))
                params_listbox.insert(END, f"{pname} ({ptype})")
                param_dlg.destroy()
            else:
                messagebox.showwarning("Input Error", "Parameter name is required.", parent=param_dlg)
        
        btn_frame_p = ttk.Frame(param_dlg_frame)
        btn_frame_p.grid(row=2, column=0, columnspan=2, sticky='e')
        
        ttk.Button(btn_frame_p, text="Add", command=save_param).pack(side=RIGHT, padx=4)
        ttk.Button(btn_frame_p, text="Cancel", command=param_dlg.destroy).pack(side=RIGHT, padx=4)
        
        param_name_entry.focus()
    
    def remove_parameter():
        sel = params_listbox.curselection()
        if sel:
            idx = sel[0]
            del param_list[idx]
            params_listbox.delete(idx)
    
    ttk.Button(param_btn_frame, text="+ Add Parameter", command=add_parameter, width=15).pack(side=LEFT, padx=2)
    ttk.Button(param_btn_frame, text="✕ Remove", command=remove_parameter, width=10).pack(side=LEFT, padx=2)
    
    # Function body
    ttk.Label(left_frame, text="Function Body:", font=("Arial", 9, "bold")).pack(anchor='w', pady=(6, 2))
    
    body_frame = ttk.Frame(left_frame)
    body_frame.pack(fill=BOTH, expand=True)
    
    body = Text(body_frame, width=40, height=12, wrap=WORD)
    body.pack(side=LEFT, fill=BOTH, expand=True)
    
    body_scrollbar = ttk.Scrollbar(body_frame, orient='vertical', command=body.yview)
    body_scrollbar.pack(side=RIGHT, fill=Y)
    body.config(yscrollcommand=body_scrollbar.set)
    
    # RIGHT: Templates and preview
    ttk.Label(right_frame, text="Code Templates", font=("Arial", 10, "bold")).pack(anchor='w', pady=(0, 6))
    
    # Template selector
    templates = {
        "Empty Function": "",
        "Item Checker": """// Check if player has item
if (countitem({item_id}) < {amount}) {{
    mes "You don't have enough items!";
    return 0;
}}
return 1;""",
        "Item Giver": """// Give items to player
getitem {item_id}, {amount};
mes "You received items!";
return;""",
        "Zeny Checker": """// Check if player has enough Zeny
if (Zeny < {amount}) {{
    mes "You don't have enough Zeny!";
    return 0;
}}
return 1;""",
        "Variable Setter": """// Set quest/game variable
set {variable_name}, {value};
return;""",
        "Level Checker": """// Check player level
if (BaseLevel < {min_level}) {{
    mes "Your level is too low!";
    return 0;
}}
return 1;""",
        "Random Reward": """// Give random reward
.@rand = rand(1, 100);
if (.@rand <= 50) {{
    getitem 501, 1;  // Red Potion
}} else if (.@rand <= 80) {{
    getitem 502, 1;  // Orange Potion
}} else {{
    getitem 503, 1;  // Yellow Potion
}}
return;""",
        "Array Helper": """// Work with arrays
setarray .@items[0], 501, 502, 503;
for (.@i = 0; .@i < getarraysize(.@items); .@i++) {{
    getitem .@items[.@i], 1;
}}
return;""",
        "Time Check": """// Check if time restriction applies
.@hour = gettime(3);  // 0-23
if (.@hour >= {start_hour} && .@hour < {end_hour}) {{
    return 1;  // Within time range
}}
return 0;  // Outside time range"""
    }
    
    template_list = list(templates.keys())
    template_var = StringVar(value=template_list[0])
    template_combo = ttk.Combobox(right_frame, textvariable=template_var, values=template_list, width=30, state='readonly')
    template_combo.pack(fill=X, pady=(0, 6))
    
    # Template preview
    ttk.Label(right_frame, text="Template Preview:").pack(anchor='w')
    
    template_preview_frame = ttk.Frame(right_frame)
    template_preview_frame.pack(fill=BOTH, expand=True, pady=(2, 6))
    
    template_preview = Text(template_preview_frame, height=10, wrap=WORD, state=DISABLED)
    template_preview.pack(side=LEFT, fill=BOTH, expand=True)
    
    template_preview_scroll = ttk.Scrollbar(template_preview_frame, orient='vertical', command=template_preview.yview)
    template_preview_scroll.pack(side=RIGHT, fill=Y)
    template_preview.config(yscrollcommand=template_preview_scroll.set)
    
    def update_template_preview(*args):
        selected = template_var.get()
        template_code = templates.get(selected, "")
        template_preview.config(state=NORMAL)
        template_preview.delete('1.0', END)
        template_preview.insert('1.0', template_code)
        template_preview.config(state=DISABLED)
    
    template_var.trace_add('write', update_template_preview)
    update_template_preview()
    
    def insert_template():
        selected = template_var.get()
        template_code = templates.get(selected, "")
        if template_code:
            body.insert('end', template_code)
    
    ttk.Button(right_frame, text="Insert Template into Body", command=insert_template, width=25).pack(pady=(0, 12))
    
    # Common snippets
    ttk.Label(right_frame, text="Quick Snippets:", font=("Arial", 9, "bold")).pack(anchor='w')
    
    snippets_frame = ttk.Frame(right_frame)
    snippets_frame.pack(fill=X)
    
    def insert_snippet(snippet):
        body.insert('end', snippet + '\n')
    
    snippets = [
        ("getarg", "getarg({index})"),
        ("return", "return {value};"),
        ("if", "if ({condition}) {{\n    \n}}"),
        ("for", "for (.@i = 0; .@i < {count}; .@i++) {{\n    \n}}"),
        ("mes", "mes \"{message}\";"),
        ("close", "close;")
    ]
    
    for label, snippet in snippets:
        ttk.Button(snippets_frame, text=label, command=lambda s=snippet: insert_snippet(s), width=8).pack(side=LEFT, padx=2, pady=2)
    
    # Function preview (optional - below snippets)
    ttk.Label(right_frame, text="Preview:", font=("Arial", 9, "bold")).pack(anchor='w', pady=(12, 2))
    
    preview_frame = ttk.Frame(right_frame)
    preview_frame.pack(fill=BOTH, expand=True)
    
    preview_display = Text(preview_frame, height=6, wrap=WORD, state=DISABLED, bg='#f0f0f0')
    preview_display.pack(side=LEFT, fill=BOTH, expand=True)
    
    preview_scroll = ttk.Scrollbar(preview_frame, orient='vertical', command=preview_display.yview)
    preview_scroll.pack(side=RIGHT, fill=Y)
    preview_display.config(yscrollcommand=preview_scroll.set)
    
    def update_preview():
        """Update the function preview"""
        name = func_name.get().strip() or "MyFunction"
        return_type = return_type_var.get()
        body_str = body.get('1.0', 'end').strip()
        
        lines = []
        lines.append(f"function\t{name}\t{{")
        
        if param_list:
            for idx, (pname, ptype) in enumerate(param_list):
                lines.append(f"\t// {pname} ({ptype})")
        
        if body_str:
            for line in body_str.split('\n')[:3]:  # Show first 3 lines
                if line.strip():
                    lines.append('\t' + line[:40])
        
        if len(body_str.split('\n')) > 3:
            lines.append('\t// ...')
        
        lines.append("}")
        
        preview_display.config(state=NORMAL)
        preview_display.delete('1.0', END)
        preview_display.insert('1.0', '\n'.join(lines))
        preview_display.config(state=DISABLED)
    
    # Update preview on changes
    func_name.bind('<KeyRelease>', lambda e: update_preview())
    body.bind('<KeyRelease>', lambda e: update_preview())
    
    # Insert button below preview
    preview_btn_frame = ttk.Frame(right_frame)
    preview_btn_frame.pack(fill=X, pady=(6, 0))
    
    def insert_from_preview():
        """Insert function from preview directly into editor"""
        try:
            script_text = generate_function_code()
            
            if not script_text:
                messagebox.showwarning("Empty", "Function name is required to insert.")
                return
            
            textArea.insert('insert', '\n' + script_text + '\n')
            messagebox.showinfo("Success", "Function inserted at cursor position!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert: {e}")
    
    ttk.Button(preview_btn_frame, text="Insert into Editor", command=insert_from_preview).pack(side=LEFT, padx=4)
    
    # Bottom buttons
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill=X, pady=(12, 0), side=BOTTOM)
    
    def generate_function_code():
        """Generate the function code without inserting"""
        name = func_name.get().strip()
        return_type = return_type_var.get()
        body_str = body.get('1.0', 'end').strip()
        
        if not name:
            return None
        
        # Build function comment header
        script_lines = []
        script_lines.append(f"// Function: {name}")
        
        if param_list:
            script_lines.append("// Parameters:")
            for idx, (pname, ptype) in enumerate(param_list):
                script_lines.append(f"//   - {pname} ({ptype}) via getarg({idx})")
        
        if not return_type.startswith("void"):
            script_lines.append(f"// Returns: {return_type}")
        
        # Function definition
        script_lines.append(f"function\t{name}\t{{")
        
        # Add parameter comments in body
        if param_list:
            for idx, (pname, ptype) in enumerate(param_list):
                script_lines.append(f"\t// {pname} = getarg({idx});")
        
        # Add body
        for line in body_str.split('\n'):
            if line.strip():
                script_lines.append('\t' + line)
        
        # Add return if needed
        if not return_type.startswith("void") and "return" not in body_str.lower():
            script_lines.append("\treturn 0;  // TODO: Return appropriate value")
        
        script_lines.append("}")
        
        return '\n'.join(script_lines)
    
    def insert_function():
        """Insert function into editor and close"""
        try:
            script_text = generate_function_code()
            
            if not script_text:
                messagebox.showwarning("Input Error", "Function name is required.")
                return
            
            textArea.insert('insert', '\n' + script_text + '\n')
            messagebox.showinfo("Success", "Function inserted successfully!")
            dlg.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert function: {e}")
    
    def insert_function_keep_open():
        """Insert function into editor but keep dialog open"""
        try:
            script_text = generate_function_code()
            
            if not script_text:
                messagebox.showwarning("Input Error", "Function name is required.")
                return
            
            textArea.insert('insert', '\n' + script_text + '\n')
            messagebox.showinfo("Success", "Function inserted! Dialog remains open for more functions.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert function: {e}")
    
    ttk.Button(btn_frame, text="Insert & Close", command=insert_function).pack(side=RIGHT, padx=4)
    ttk.Button(btn_frame, text="Insert Function", command=insert_function_keep_open).pack(side=RIGHT, padx=4)
    ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=RIGHT, padx=4)
    
    # Initial preview
    update_preview()
    func_name.focus()







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
    """Validate the current script with line-by-line error highlighting."""
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
        # Create validation dialog
        dlg = Toplevel(root)
        dlg.title("Script Validator")
        dlg.transient(root)
        dlg.grab_set()
        dlg.geometry("700x600")
            
        main_frame = ttk.Frame(dlg, padding=12)
        main_frame.pack(fill=BOTH, expand=True)
            
        ttk.Label(main_frame, text="Script Validation Results", font=("Arial", 12, "bold")).pack(anchor='w', pady=(0, 12))
            
        # Results area with tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=BOTH, expand=True)
            
        # Tab 1: Errors
        errors_frame = ttk.Frame(notebook)
        notebook.add(errors_frame, text="Errors")
            
        errors_list = Text(errors_frame, height=15, wrap=WORD)
        errors_list.pack(side=LEFT, fill=BOTH, expand=True)
            
        errors_scroll = ttk.Scrollbar(errors_frame, orient='vertical', command=errors_list.yview)
        errors_scroll.pack(side=RIGHT, fill=Y)
        errors_list.config(yscrollcommand=errors_scroll.set)
            
        # Tab 2: Warnings
        warnings_frame = ttk.Frame(notebook)
        notebook.add(warnings_frame, text="Warnings")
            
        warnings_list = Text(warnings_frame, height=15, wrap=WORD)
        warnings_list.pack(side=LEFT, fill=BOTH, expand=True)
            
        warnings_scroll = ttk.Scrollbar(warnings_frame, orient='vertical', command=warnings_list.yview)
        warnings_scroll.pack(side=RIGHT, fill=Y)
        warnings_list.config(yscrollcommand=warnings_scroll.set)
            
        # Tab 3: Best Practices
        practices_frame = ttk.Frame(notebook)
        notebook.add(practices_frame, text="Best Practices")
            
        practices_list = Text(practices_frame, height=15, wrap=WORD)
        practices_list.pack(side=LEFT, fill=BOTH, expand=True)
            
        practices_scroll = ttk.Scrollbar(practices_frame, orient='vertical', command=practices_list.yview)
        practices_scroll.pack(side=RIGHT, fill=Y)
        practices_list.config(yscrollcommand=practices_scroll.set)
            
        # Summary label
        summary_label = ttk.Label(main_frame, text="", font=("Arial", 10, "bold"))
        summary_label.pack(pady=(12, 0))
            
        # Progress bar
        progress = ttk.Progressbar(main_frame, mode='indeterminate')
        progress.pack(fill=X, pady=(6, 12))
            
        # Bottom buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X)
        
        # Store fixable issues for auto-fix feature
        fixable_issues = []
            
        def clear_highlights():
            """Clear all validation-related highlights from editor"""
            try:
                textArea.tag_remove('validation_error', '1.0', 'end')
                textArea.tag_remove('validation_warning', '1.0', 'end')
                textArea.tag_remove('validation_suggestion', '1.0', 'end')
                textArea.tag_remove('validation_error_line', '1.0', 'end')
                textArea.tag_remove('validation_warning_line', '1.0', 'end')
            except Exception:
                pass
        
        def apply_all_fixes():
            """Apply all auto-fixable issues with user confirmation"""
            if not fixable_issues:
                messagebox.showinfo("No Fixes", "No auto-fixable issues found.")
                return
            
            if not messagebox.askyesno("Apply All Fixes", 
                f"Apply all {len(fixable_issues)} suggested fixes?\n\n"
                "This will modify your script automatically.\n"
                "You can undo these changes if needed."):
                return
            
            try:
                # Sort by line number in reverse order to preserve positions
                sorted_fixes = sorted(fixable_issues, key=lambda x: x['line'], reverse=True)
                
                applied_count = 0
                for fix in sorted_fixes:
                    line_num = fix['line']
                    old_text = fix['old']
                    new_text = fix['new']
                    
                    # Get current line text
                    current_line = textArea.get(f"{line_num}.0", f"{line_num}.end")
                    
                    # Verify the line still contains the old text
                    if old_text in current_line:
                        # Replace in the line
                        updated_line = current_line.replace(old_text, new_text, 1)
                        
                        # Update in editor
                        textArea.delete(f"{line_num}.0", f"{line_num}.end")
                        textArea.insert(f"{line_num}.0", updated_line)
                        applied_count += 1
                
                messagebox.showinfo("Fixes Applied", 
                    f"Successfully applied {applied_count} of {len(fixable_issues)} fixes.\n\n"
                    "Please re-validate to check for remaining issues.")
                
                # Clear and re-run validation
                fixable_issues.clear()
                clear_highlights()
                dlg.destroy()
                validate_current_script(root, get_textarea)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to apply fixes: {e}")
        
        def review_fixes():
            """Review and selectively apply fixes one by one"""
            if not fixable_issues:
                messagebox.showinfo("No Fixes", "No auto-fixable issues found.")
                return
            
            # Create review dialog
            review_dlg = Toplevel(dlg)
            review_dlg.title("Review & Apply Fixes")
            review_dlg.transient(dlg)
            review_dlg.grab_set()
            review_dlg.geometry("700x500")
            
            review_frame = ttk.Frame(review_dlg, padding=12)
            review_frame.pack(fill=BOTH, expand=True)
            
            ttk.Label(review_frame, text="Review Suggested Fixes", font=("Arial", 12, "bold")).pack(anchor='w', pady=(0, 12))
            
            # Current fix index
            current_idx = [0]
            applied_fixes = []
            
            def show_fix():
                """Display current fix"""
                if current_idx[0] >= len(fixable_issues):
                    messagebox.showinfo("Complete", 
                        f"Review complete!\n\n"
                        f"Applied {len(applied_fixes)} of {len(fixable_issues)} fixes.")
                    review_dlg.destroy()
                    if applied_fixes:
                        # Re-run validation
                        clear_highlights()
                        dlg.destroy()
                        validate_current_script(root, get_textarea)
                    return
                
                fix = fixable_issues[current_idx[0]]
                
                # Update display
                info_text.config(state=NORMAL)
                info_text.delete('1.0', END)
                info_text.insert('1.0', f"Fix {current_idx[0] + 1} of {len(fixable_issues)}\n\n", 'bold')
                info_text.insert('end', f"Line {fix['line']}: {fix['type']}\n\n", 'location')
                info_text.insert('end', "Original:\n", 'bold')
                info_text.insert('end', f"  {fix['old']}\n\n", 'old')
                info_text.insert('end', "Suggested Fix:\n", 'bold')
                info_text.insert('end', f"  {fix['new']}\n\n", 'new')
                info_text.insert('end', f"Description: {fix['description']}", 'normal')
                info_text.config(state=DISABLED)
                
                # Update progress
                progress_label.config(text=f"Progress: {current_idx[0] + 1} / {len(fixable_issues)}")
            
            # Info display
            info_frame = ttk.Frame(review_frame)
            info_frame.pack(fill=BOTH, expand=True, pady=(0, 12))
            
            info_text = Text(info_frame, height=15, wrap=WORD, state=DISABLED)
            info_text.pack(side=LEFT, fill=BOTH, expand=True)
            
            info_scroll = ttk.Scrollbar(info_frame, orient='vertical', command=info_text.yview)
            info_scroll.pack(side=RIGHT, fill=Y)
            info_text.config(yscrollcommand=info_scroll.set)
            
            # Configure tags
            info_text.tag_config('bold', font=("Arial", 9, "bold"))
            info_text.tag_config('location', foreground='#0000FF')
            info_text.tag_config('old', foreground='#FF0000', background='#FFE6E6')
            info_text.tag_config('new', foreground='#008000', background='#E6FFE6')
            info_text.tag_config('normal', foreground='#000000')
            
            # Progress label
            progress_label = ttk.Label(review_frame, text="", font=("Arial", 9))
            progress_label.pack(anchor='w')
            
            # Action buttons
            action_frame = ttk.Frame(review_frame)
            action_frame.pack(fill=X, pady=(12, 0))
            
            def apply_fix():
                """Apply current fix and move to next"""
                fix = fixable_issues[current_idx[0]]
                try:
                    line_num = fix['line']
                    old_text = fix['old']
                    new_text = fix['new']
                    
                    # Get current line
                    current_line = textArea.get(f"{line_num}.0", f"{line_num}.end")
                    
                    # Apply fix
                    if old_text in current_line:
                        updated_line = current_line.replace(old_text, new_text, 1)
                        textArea.delete(f"{line_num}.0", f"{line_num}.end")
                        textArea.insert(f"{line_num}.0", updated_line)
                        applied_fixes.append(fix)
                    
                    current_idx[0] += 1
                    show_fix()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to apply fix: {e}")
            
            def skip_fix():
                """Skip current fix and move to next"""
                current_idx[0] += 1
                show_fix()
            
            def apply_all_remaining():
                """Apply all remaining fixes without review"""
                if messagebox.askyesno("Apply All", 
                    f"Apply all {len(fixable_issues) - current_idx[0]} remaining fixes?"):
                    try:
                        remaining = fixable_issues[current_idx[0]:]
                        # Sort by line number in reverse
                        remaining_sorted = sorted(remaining, key=lambda x: x['line'], reverse=True)
                        
                        for fix in remaining_sorted:
                            line_num = fix['line']
                            old_text = fix['old']
                            new_text = fix['new']
                            
                            current_line = textArea.get(f"{line_num}.0", f"{line_num}.end")
                            if old_text in current_line:
                                updated_line = current_line.replace(old_text, new_text, 1)
                                textArea.delete(f"{line_num}.0", f"{line_num}.end")
                                textArea.insert(f"{line_num}.0", updated_line)
                                applied_fixes.append(fix)
                        
                        messagebox.showinfo("Complete", 
                            f"Applied {len(applied_fixes)} fixes total.")
                        review_dlg.destroy()
                        
                        # Re-run validation
                        clear_highlights()
                        dlg.destroy()
                        validate_current_script(root, get_textarea)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to apply fixes: {e}")
            
            ttk.Button(action_frame, text="✓ Apply Fix", command=apply_fix, width=12).pack(side=LEFT, padx=4)
            ttk.Button(action_frame, text="→ Skip", command=skip_fix, width=10).pack(side=LEFT, padx=4)
            ttk.Button(action_frame, text="Apply All Remaining", command=apply_all_remaining, width=18).pack(side=LEFT, padx=4)
            ttk.Button(action_frame, text="Cancel", command=review_dlg.destroy, width=10).pack(side=RIGHT, padx=4)
            
            # Show first fix
            show_fix()
            
        def close_dialog():
            clear_highlights()
            dlg.destroy()
            
        ttk.Button(btn_frame, text="Clear Highlights", command=clear_highlights).pack(side=LEFT, padx=4)
        ttk.Button(btn_frame, text="Review & Fix...", command=review_fixes).pack(side=LEFT, padx=4)
        ttk.Button(btn_frame, text="Apply All Fixes", command=apply_all_fixes).pack(side=LEFT, padx=4)
        ttk.Button(btn_frame, text="Close", command=close_dialog).pack(side=RIGHT, padx=4)
            
        # Configure text widget tags
        errors_list.tag_config('error', foreground='#FF0000', font=("Arial", 9, "bold"))
        errors_list.tag_config('location', foreground='#0000FF')
        warnings_list.tag_config('warning', foreground='#FFA500', font=("Arial", 9, "bold"))
        warnings_list.tag_config('location', foreground='#0000FF')
        practices_list.tag_config('suggestion', foreground='#008000', font=("Arial", 9, "bold"))
        practices_list.tag_config('location', foreground='#0000FF')
            
        # Configure editor highlighting tags
        try:
            textArea.tag_config('validation_error', foreground='#FF0000', background='#FFE6E6')
            textArea.tag_config('validation_warning', foreground='#FFA500', background='#FFF8E6')
            textArea.tag_config('validation_suggestion', foreground='#008000', background='#E6FFE6')
            textArea.tag_config('validation_error_line', background='#FFE6E6')
            textArea.tag_config('validation_warning_line', background='#FFF8E6')
        except Exception:
            pass
            
        # Start validation
        progress.start()
            
        def perform_validation():
            """Run comprehensive validation checks"""
            try:
                script_text = textArea.get('1.0', 'end-1c')
                lines = script_text.split('\n')
                    
                errors = []
                warnings = []
                suggestions = []
                
                # Load rAthena commands from syntax file
                rathena_commands = set()
                try:
                    syntax_file = os.path.join(_current_dir, 'syntax', 'rathena.ini')
                    if os.path.exists(syntax_file):
                        with open(syntax_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith('builtins.csv'):
                                    # Extract commands from builtins.csv line
                                    builtins_line = line.split('=', 1)[1].strip()
                                    commands = [cmd.strip() for cmd in builtins_line.split(',') if cmd.strip()]
                                    rathena_commands.update(commands)
                                    break
                        # Add keywords too
                        with open(syntax_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith('keywords.csv'):
                                    keywords_line = line.split('=', 1)[1].strip()
                                    keywords = [kw.strip() for kw in keywords_line.split(',') if kw.strip()]
                                    rathena_commands.update(keywords)
                                    break
                except Exception as e:
                    # Fallback to basic commands if syntax file fails
                    rathena_commands = {'mes', 'close', 'next', 'end', 'set', 'getitem', 'delitem', 'warp', 
                                       'menu', 'select', 'if', 'else', 'switch', 'case', 'break', 'goto'}
                    
                # Clear previous highlights
                clear_highlights()
                    
                # 1. Empty script check
                if not script_text.strip():
                    errors.append((0, 0, "Script is empty"))
                    errors_list.insert('end', "✗ Error: ", 'error')
                    errors_list.insert('end', "Script is empty\n")
                    return errors, warnings, suggestions
                    
                # 2. Line-by-line validation
                in_npc = False
                in_function = False
                in_block = False
                in_multiline_comment = False
                bracket_count = 0
                npc_name = None
                function_name = None
                expected_indent = 0  # Track expected indentation level
                indent_stack = [0]  # Stack to track indentation levels
                    
                for line_num, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    # Simple multi-line comment handling - just like bracket tracking
                    if '/*' in stripped:
                        in_multiline_comment = True
                    if '*/' in stripped:
                        in_multiline_comment = False
                        continue  # Skip the line with */
                    
                    # Skip everything inside multi-line comments
                    if in_multiline_comment:
                        continue
                        
                    # Skip empty lines and single-line comments
                    if not stripped or stripped.startswith('//'):
                        continue
                        
                    # Check for NPC definition
                    if '\tscript\t' in line:
                        # Format: map,x,y,dir<tab>script<tab>name<tab>sprite,{
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            in_npc = True
                            npc_name = parts[2].strip()
                                
                            # Validate NPC name
                            if not npc_name:
                                errors.append((line_num, len(line), "NPC name is empty"))
                                _highlight_line_error(textArea, line_num, 'validation_error_line')
                                errors_list.insert('end', f"✗ Line {line_num}: ", ('error', 'location'))
                                errors_list.insert('end', "NPC name is empty\n")
                            elif len(npc_name) > 24:
                                warnings.append((line_num, len(line), f"NPC name '{npc_name}' exceeds 24 characters"))
                                _highlight_line_warning(textArea, line_num, 'validation_warning_line')
                                warnings_list.insert('end', f"⚠ Line {line_num}: ", ('warning', 'location'))
                                warnings_list.insert('end', f"NPC name '{npc_name}' exceeds 24 characters\n")
                                
                            # Validate location format
                            location = parts[0].strip()
                            loc_parts = location.split(',')
                            if len(loc_parts) != 4:
                                errors.append((line_num, len(location), "Invalid NPC location format (expected: map,x,y,dir)"))
                                _highlight_error(textArea, line_num, 0, len(location), 'validation_error')
                                errors_list.insert('end', f"✗ Line {line_num}: ", ('error', 'location'))
                                errors_list.insert('end', "Invalid NPC location format\n")
                        
                    # Check for function definition
                    if 'function\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            in_function = True
                            function_name = parts[1].strip()
                                
                            # Validate function name
                            if not function_name:
                                errors.append((line_num, len(line), "Function name is empty"))
                                _highlight_line_error(textArea, line_num, 'validation_error_line')
                                errors_list.insert('end', f"✗ Line {line_num}: ", ('error', 'location'))
                                errors_list.insert('end', "Function name is empty\n")
                        
                    # Update indentation stack FIRST (for current line)
                    if '{' in stripped:
                        in_block = True
                        expected_indent += 1
                        indent_stack.append(expected_indent)
                    
                    # Track brackets
                    bracket_count += stripped.count('{') - stripped.count('}')
                    
                    # SIMPLE RULE: If we're in a block (after seeing {), validate ALL non-empty lines
                    # Skip ONLY: empty lines, pure comments, and definition lines
                    if in_block and stripped and not stripped.startswith('//'):
                        # Skip only the definition line itself
                        is_definition_line = ('function\t' in line or '\tscript\t' in line)
                        
                        if not is_definition_line:
                            # Calculate current indentation
                            current_indent = len(line) - len(line.lstrip('\t '))
                            leading_whitespace = line[:current_indent]
                            
                            # Determine line characteristics
                            opens_block = '{' in stripped
                            closes_block = '}' in stripped
                            is_else_clause = closes_block and 'else' in stripped.lower()
                            
                            # Expected indentation (use CURRENT stack state)
                            expected_tabs = indent_stack[-1] if indent_stack else 0
                            
                            # Check indentation type
                            has_spaces = ' ' in leading_whitespace
                            has_tabs = '\t' in leading_whitespace
                            
                            # Issue 1: Mixed tabs and spaces
                            if has_spaces and has_tabs:
                                warnings.append((line_num, 0, "Mixed tabs and spaces in indentation"))
                                warnings_list.insert('end', f"⚠ Line {line_num}: ", ('warning', 'location'))
                                warnings_list.insert('end', "Mixed tabs and spaces in indentation\n")
                                
                                if is_else_clause:
                                    correct_indent = '\t' * (expected_tabs - 1) if expected_tabs > 0 else ''
                                elif closes_block and not opens_block:
                                    correct_indent = '\t' * (expected_tabs - 1) if expected_tabs > 0 else ''
                                else:
                                    correct_indent = '\t' * expected_tabs
                                
                                fixable_issues.append({
                                    'line': line_num,
                                    'type': 'Indentation (Mixed)',
                                    'old': leading_whitespace,
                                    'new': correct_indent,
                                    'description': f'Replace mixed indentation with {len(correct_indent)} tab(s)'
                                })
                            
                            # Issue 2: Using spaces instead of tabs
                            elif has_spaces and not has_tabs:
                                warnings.append((line_num, 0, "Using spaces instead of tabs for indentation"))
                                warnings_list.insert('end', f"⚠ Line {line_num}: ", ('warning', 'location'))
                                warnings_list.insert('end', "Using spaces instead of tabs (rAthena standard uses tabs)\n")
                                
                                space_count = len(leading_whitespace)
                                if is_else_clause:
                                    correct_indent = '\t' * (expected_tabs - 1) if expected_tabs > 0 else ''
                                elif closes_block and not opens_block:
                                    correct_indent = '\t' * (expected_tabs - 1) if expected_tabs > 0 else ''
                                else:
                                    correct_indent = '\t' * expected_tabs
                                
                                fixable_issues.append({
                                    'line': line_num,
                                    'type': 'Indentation (Spaces)',
                                    'old': leading_whitespace,
                                    'new': correct_indent,
                                    'description': f'Convert {space_count} space(s) to {len(correct_indent)} tab(s)'
                                })
                            
                            # Issue 3: Wrong number of tabs
                            elif has_tabs and not has_spaces:
                                tab_count = leading_whitespace.count('\t')
                                
                                # Determine correct level
                                if is_else_clause:
                                    check_indent = expected_tabs - 1 if expected_tabs > 0 else 0
                                elif closes_block and not opens_block:
                                    check_indent = expected_tabs - 1 if expected_tabs > 0 else 0
                                else:
                                    check_indent = expected_tabs
                                
                                if tab_count != check_indent:
                                    warnings.append((line_num, 0, f"Incorrect indentation: found {tab_count} tab(s), expected {check_indent}"))
                                    warnings_list.insert('end', f"⚠ Line {line_num}: ", ('warning', 'location'))
                                    warnings_list.insert('end', f"Incorrect indentation: {tab_count} tab(s), expected {check_indent}\n")
                                    
                                    correct_indent = '\t' * check_indent
                                    fixable_issues.append({
                                        'line': line_num,
                                        'type': 'Indentation (Tab Count)',
                                        'old': leading_whitespace,
                                        'new': correct_indent,
                                        'description': f'Adjust indentation from {tab_count} to {check_indent} tab(s)'
                                    })
                            
                            # Issue 4: No indentation at all (0 tabs when we expect some)
                            elif not has_tabs and not has_spaces and expected_tabs > 0:
                                # Only flag if this is not a closing brace
                                if not (closes_block and not opens_block):
                                    warnings.append((line_num, 0, f"Missing indentation: found 0 tab(s), expected {expected_tabs}"))
                                    warnings_list.insert('end', f"⚠ Line {line_num}: ", ('warning', 'location'))
                                    warnings_list.insert('end', f"Missing indentation: found 0 tab(s), expected {expected_tabs}\n")
                                    
                                    correct_indent = '\t' * expected_tabs
                                    fixable_issues.append({
                                        'line': line_num,
                                        'type': 'Indentation (Missing)',
                                        'old': '',
                                        'new': correct_indent,
                                        'description': f'Add {expected_tabs} tab(s) for proper indentation'
                                    })
                    
                    # Update indentation stack AFTER validation (for closing braces)
                    if '}' in stripped and bracket_count == 0:
                        in_block = False
                        in_npc = False
                        in_function = False
                        if len(indent_stack) > 1:
                            indent_stack.pop()
                        expected_indent = indent_stack[-1] if indent_stack else 0
                        
                    if '}' in stripped:
                        if len(indent_stack) > 1:
                            indent_stack.pop()
                        expected_indent = indent_stack[-1] if indent_stack else 0
                        
                    # Check for common syntax errors
                        
                    # Missing semicolons - use comprehensive command list from syntax file
                    # Exceptions:
                    # - Lines ending with comma (,) are continuations
                    # - Case labels should end with colon (:)
                    if in_block and not stripped.endswith((';', '{', '}', ':', ',')):
                        # Check if this is a case statement (should end with :)
                        is_case_label = stripped.lower().startswith('case ') or stripped.lower().startswith('default')
                        
                        if is_case_label:
                            # Case labels need colon, not semicolon
                            warnings.append((line_num, len(line), "Case label should end with colon (:)"))
                            _highlight_warning(textArea, line_num, len(line) - 1, len(line), 'validation_warning')
                            warnings_list.insert('end', f"⚠ Line {line_num}: ", ('warning', 'location'))
                            warnings_list.insert('end', "Case label should end with colon (:)\n")
                            
                            # Add to fixable issues
                            fixable_issues.append({
                                'line': line_num,
                                'type': 'Missing Colon',
                                'old': stripped,
                                'new': stripped + ':',
                                'description': 'Add missing colon at end of case label'
                            })
                        else:
                            # Regular statements need semicolons
                            # Check if line contains any rAthena command
                            line_lower = stripped.lower()
                            has_command = any(cmd in line_lower for cmd in rathena_commands if cmd)
                            
                            # Also check for common patterns that need semicolons
                            needs_semicolon = (
                                has_command or
                                '=' in stripped or  # Variable assignment
                                stripped.startswith('.@') or  # Local variable
                                stripped.startswith('@') or   # Temp variable
                                stripped.startswith('$') or   # Global variable
                                stripped.startswith('#')      # Account variable
                            )
                            
                            if needs_semicolon:
                                warnings.append((line_num, len(line), "Missing semicolon"))
                                _highlight_warning(textArea, line_num, len(line) - 1, len(line), 'validation_warning')
                                warnings_list.insert('end', f"⚠ Line {line_num}: ", ('warning', 'location'))
                                warnings_list.insert('end', "Missing semicolon\n")
                                
                                # Add to fixable issues
                                fixable_issues.append({
                                    'line': line_num,
                                    'type': 'Missing Semicolon',
                                    'old': stripped,
                                    'new': stripped + ';',
                                    'description': 'Add missing semicolon at end of line'
                                })
                        
                    # Unclosed strings
                    quote_count = stripped.count('"')
                    if quote_count % 2 != 0:
                        errors.append((line_num, len(line), "Unclosed string"))
                        # Find position of first quote
                        quote_pos = line.find('"')
                        _highlight_error(textArea, line_num, quote_pos, len(line), 'validation_error')
                        errors_list.insert('end', f"✗ Line {line_num}: ", ('error', 'location'))
                        errors_list.insert('end', "Unclosed string\n")
                        
                    # Common command typos (using word boundaries to avoid false positives)
                    import re
                    typos = {
                        'mesage': 'mes',
                        'messge': 'mes',
                        'nxt': 'next',
                        'clos': 'close',
                        'closse': 'close',
                        'warpp': 'warp',
                        'getiitem': 'getitem',
                        'deliitem': 'delitem'
                    }
                    for typo, correct in typos.items():
                        # Match whole word followed by non-letter (punctuation, whitespace, end of string)
                        # This catches "clos;" but not "close;" or "closest"
                        pattern = r'\b' + re.escape(typo) + r'(?=[^a-zA-Z]|$)'
                        match = re.search(pattern, stripped, re.IGNORECASE)
                        if match:
                            typo_pos = line.lower().find(typo)
                            warnings.append((line_num, typo_pos, f"Possible typo: '{typo}' (did you mean '{correct}'?)"))
                            _highlight_warning(textArea, line_num, typo_pos, typo_pos + len(typo), 'validation_warning')
                            warnings_list.insert('end', f"⚠ Line {line_num}: ", ('warning', 'location'))
                            warnings_list.insert('end', f"Possible typo: '{typo}' → '{correct}'\n")
                            
                            # Add to fixable issues
                            fixable_issues.append({
                                'line': line_num,
                                'type': 'Typo',
                                'old': typo,
                                'new': correct,
                                'description': f"Replace '{typo}' with '{correct}'"
                            })
                        
                    # Best practice: Use mes for NPC dialog
                    if in_npc and '"' in stripped and 'mes' not in stripped and not stripped.startswith('//'):
                        if not any(cmd in stripped for cmd in ['select', 'input', 'set', 'if', 'switch', 'case']):
                            suggestions.append((line_num, 0, "Consider using 'mes' for NPC dialog"))
                            practices_list.insert('end', f"💡 Line {line_num}: ", ('suggestion', 'location'))
                            practices_list.insert('end', "Consider using 'mes' for NPC dialog\n")
                        
                    # Best practice: Close dialogs properly
                    if in_npc and line_num == len(lines) and 'close' not in stripped and 'end' not in stripped:
                        suggestions.append((line_num, 0, "NPC dialog should end with 'close;' or 'end;'"))
                        practices_list.insert('end', f"💡 Line {line_num}: ", ('suggestion', 'location'))
                        practices_list.insert('end', "NPC should end with 'close;' or 'end;'\n")
                    
                # 3. Check bracket balance
                if bracket_count != 0:
                    errors.append((0, 0, f"Unbalanced brackets (difference: {bracket_count})"))
                    errors_list.insert('end', "✗ Error: ", 'error')
                    errors_list.insert('end', f"Unbalanced brackets (difference: {bracket_count})\n")
                    
                # 4. Check for required elements
                has_npc = any('\tscript\t' in line for line in lines)
                has_function = any('function\t' in line for line in lines)
                    
                if not has_npc and not has_function:
                    warnings.append((0, 0, "Script contains no NPCs or functions"))
                    warnings_list.insert('end', "⚠ Warning: ", 'warning')
                    warnings_list.insert('end', "Script contains no NPCs or functions\n")
                    
                return errors, warnings, suggestions
                    
            except Exception as e:
                errors_list.insert('end', "✗ Error: ", 'error')
                errors_list.insert('end', f"Validation error: {e}\n")
                return [(0, 0, str(e))], [], []
            
        def _highlight_line_error(text_widget, line_num, tag):
            """Highlight entire line for errors"""
            try:
                start = f"{line_num}.0"
                end = f"{line_num}.end"
                text_widget.tag_add(tag, start, end)
            except Exception:
                pass
            
        def _highlight_line_warning(text_widget, line_num, tag):
            """Highlight entire line for warnings"""
            try:
                start = f"{line_num}.0"
                end = f"{line_num}.end"
                text_widget.tag_add(tag, start, end)
            except Exception:
                pass
            
        def _highlight_error(text_widget, line_num, start_col, end_col, tag):
            """Highlight specific text range for errors"""
            try:
                start = f"{line_num}.{start_col}"
                end = f"{line_num}.{end_col}"
                text_widget.tag_add(tag, start, end)
            except Exception:
                pass
            
        def _highlight_warning(text_widget, line_num, start_col, end_col, tag):
            """Highlight specific text range for warnings"""
            try:
                start = f"{line_num}.{start_col}"
                end = f"{line_num}.{end_col}"
                text_widget.tag_add(tag, start, end)
            except Exception:
                pass
            
        def finish_validation():
            """Complete validation and update UI"""
            progress.stop()
                
            errors, warnings, suggestions = perform_validation()
                
            # Update summary
            if not errors and not warnings:
                summary_label.config(text="✓ Script validation passed!", foreground='#008000')
                errors_list.insert('end', "\n✓ No errors found!\n", 'error')
            elif errors:
                summary_label.config(text=f"✗ {len(errors)} error(s) found", foreground='#FF0000')
            else:
                summary_label.config(text=f"⚠ {len(warnings)} warning(s) found", foreground='#FFA500')
                
            if not warnings:
                warnings_list.insert('end', "\n✓ No warnings!\n", 'warning')
                
            if not suggestions:
                practices_list.insert('end', "\n✓ No suggestions!\n", 'suggestion')
                
            # Disable text widgets
            errors_list.config(state=DISABLED)
            warnings_list.config(state=DISABLED)
            practices_list.config(state=DISABLED)
            
        # Run validation after dialog appears
        dlg.after(100, finish_validation)
            
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

from ast import Not
from selectors import SelectorKey
from tkinter import *
from tkinter import filedialog, messagebox
from io import StringIO
from threading import Thread
import threading
import time
import os
import sys
import re

def match_case_like_this(start, end):
    pattern = r'def\s+[\w]*\s*\('
    pattern2 = r'\s[\w]*\s*\.*'
    matches = []
    
    for line in textArea.get(start, end).split('\n'):
        if re.search(pattern, line):
            matches.append(re.search(pattern, line).group(0))

    matche = '\n'.join(matches)
    matches2 = []
    for line in matche.split('\n'):
        if re.search(pattern2, line):
            matches2.append(re.search(pattern2, line).group(0).lstrip())

    return r'\b' + '|'.join(matches2) + r'\b'

def functionNames(start, end):
    global match_string
    match_string = match_case_like_this(start, end)
def highlight_python_helper():

    start = round(float(textArea.index(CURRENT)) - 50.0, 1)     # Get index at line 1 char 0 ('END')
    end = round(float(textArea.index(CURRENT)) + 50.0, 1)    # Get index at last char
    start2 = round(float(textArea.index(CURRENT)) - 500.0, 1)     # Get index at line 1 char 0 ('END')
    end2 = round(float(textArea.index(CURRENT)) + 500.0, 1)    # Get index at last char
    textArea.tag_remove('string', start, end)
    textArea.tag_remove('keyword', start, end)
    textArea.tag_remove('comment', start, end)
    textArea.tag_remove('selfs', start, end)
    textArea.tag_remove('def', start, end)
    textArea.tag_remove('number', start, end)
    # Define regex patterns
    functionNames(start, end)
    defs = match_string
    keywords = r'\b(if|else|while|for|return|def|from|import|class)\b'
    selfs = r'\b(?:[a-z])(?:[A-Z]?[a-z])*(?:[A-Z][a-z]*)|\b(self|root)\b'
    comments = r'#[^\n]*|"""(.*?)"""'
    string = r'"[^"]*"|\'[^\']*\''
    number = r'\b(\d+(\.\d*)?|\.\d+)\b'

    def highlight_keywords():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(keywords, content)]
        for match in reversed(matches):
            textArea.tag_add("keyword", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_strings():
        content = textArea.get(start2, end2)
        matches = [m.span() for m in re.finditer(string, content)]
        for match in reversed(matches):
            textArea.tag_add("string", f"{start2} + {match[0]}c", f"{start2} + {match[1]}c")

    def highlight_comments():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(comments, content, re.DOTALL)]
        for match in reversed(matches):
            textArea.tag_add("comment", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_numbers():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(number, content)]
        for match in reversed(matches):
            textArea.tag_add("number", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_selfs():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(selfs, content)]
        for match in reversed(matches):
            textArea.tag_add("selfs", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_def():
        if not defs == r'\b\b':
            content = textArea.get(start, end)
            matches = [m.span() for m in re.finditer(defs, content)]
            for match in reversed(matches):
                textArea.tag_add("def", f"{start} + {match[0]}c", f"{start} + {match[1]}c")


    highlight_keywords()
    highlight_def()
    highlight_numbers()
    highlight_selfs()
    highlight_strings()
    highlight_comments()

def highlight_python_init():

    start = "1.0"     # Get index at line 1 char 0 ('END')
    end = END     # Get index at last char
    # Define regex patterns
    keywords = r'\b(if|else|while|for|return|def|from|import|class)\b'
    selfs = '\b(?:[a-z])(?:[A-Z]?[a-z])*(?:[A-Z][a-z]*)|\b(self|root)\b'
    comments = r'#[^\n]*|"""(.*?)"""'
    string = r'"[^"]*"|\'[^\']*\''
    number = r'\b(\d+(\.\d*)?|\.\d+)\b'
    functionNames(start, end)
    defs = match_string
    def highlight_keywords():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(keywords, content)]
        for match in reversed(matches):
            textArea.tag_add("keyword", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_strings():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(string, content)]
        for match in reversed(matches):
            textArea.tag_add("string", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_comments():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(comments, content, re.DOTALL)]
        for match in reversed(matches):
            textArea.tag_add("comment", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_numbers():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(number, content)]
        for match in reversed(matches):
            textArea.tag_add("number", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_selfs():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(selfs, content)]
        for match in reversed(matches):
            textArea.tag_add("selfs", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    def highlight_def():
        if not defs == r'\b\b':
            content = textArea.get(start, end)
            matches = [m.span() for m in re.finditer(defs, content)]
            for match in reversed(matches):
                textArea.tag_add("def", f"{start} + {match[0]}c", f"{start} + {match[1]}c")

    highlight_keywords()
    highlight_strings()
    highlight_def()
    highlight_numbers()
    highlight_selfs()
    highlight_comments()

# Create instance
root = Tk()

# Set geometry
root.geometry("800x600")

# Change the title of the window
root.title('SimpleEdit')

# Add menu bar
menuBar = Menu(root)
root.config(menu=menuBar)
root.fileName = ""

def _bind_shortcut_keys(event):
    if event.state == 4 and event.keysym == 'z': 
        textArea.edit_undo()
       
    elif event.state == 4 and event.keysym == 'y': 
        textArea.edit_redo()
        

def copyToClipboard():
    copiedText = textArea.selection_get() # get selected text
    root.clipboard_clear() # clear clipboard content
    root.clipboard_append(copiedText) # add selected text to clipboard
    
def pasteFromClipboard():
    pastedText = root.clipboard_get() # get content from clipboard
    textArea.insert('insert', pastedText) # insert that content into textarea at cursor position
    
def cutSelectedText():
    cuttedText = textArea.selection_get() # get selected text
    textArea.delete(SEL_FIRST, SEL_LAST) # delete selection
    root.clipboard_clear() # clear clipboard content
    root.clipboard_append(cuttedText) # add cutted text to clipboard
    
def saveFileAsThreaded():
    thread = Thread(target=saveFileAs)
    thread.start()
def saveFileAs():
    if stop_event.is_set():
        exit
    else:
    
        def getSizeOfTextArea():
            """Calculate the size (in bytes) of the content in text area"""
            return sum([1 for c in textArea.get('1.0', END)])   # Count number of characters excluding newlines
        if root.fileName == "":
            fileName = filedialog.asksaveasfilename(initialdir="/", title="Select file",
                                                filetypes=(("Text files", "*.txt"), ("Python Source files", "*.py"), ("All files", "*.*")))
            root.fileName = fileName

        sys.stdout = statusBar['text']
        fileName = root.fileName
        if fileName:
            try:
                total_size = getSizeOfTextArea()  # Get the estimated total size of the file 
                current_size = 0 
                with open(fileName, 'w') as f:
                    for char in textArea.get('1.0', END):
                        f.write(char)
                        current_size += 1  # This will give us an estimation but not exact byte count because of variable character sizes and line breaks
                    
                        progress = round((current_size/total_size)*100, 0)  # Calculate percentage completion rounded to 2 decimal places
                        statusBar['text'] = f"Saving... {progress}% - {fileName}"
                
                #statusBar['text'] = f"'{fileName}' saved successfully!"  # Change the status message when operation is finished
                root.fileName = fileName
            except Exception as e:
                messagebox.showerror("Error", str(e))

def saveFileAsThreaded2():
    thread = Thread(target=saveFileAs2)
    thread.start()
def saveFileAs2():
    if stop_event.is_set():
        exit
    else:
    
        def getSizeOfTextArea():
            """Calculate the size (in bytes) of the content in text area"""
            return sum([1 for c in textArea.get('1.0', END)])   # Count number of characters excluding newlines
        
        fileName2 = filedialog.asksaveasfilename(initialdir=root.fileName, title="Select file",
                                                filetypes=(("Text files", "*.txt"), ("Python Source files", "*.py"), ("All files", "*.*")))
        if root.fileName == "":
            root.fileName = fileName2

        sys.stdout = statusBar['text']
        fileName = fileName2
        if fileName:
            try:
                total_size = getSizeOfTextArea()  # Get the estimated total size of the file 
                current_size = 0 
                with open(fileName, 'w') as f:
                    for char in textArea.get('1.0', END):
                        f.write(char)
                        current_size += 1  # This will give us an estimation but not exact byte count because of variable character sizes and line breaks
                    
                        progress = round((current_size/total_size)*100, 0)  # Calculate percentage completion rounded to 2 decimal places
                        statusBar['text'] = f"Saving... {progress}% - {fileName}"
                
                #statusBar['text'] = f"'{fileName}' saved successfully!"  # Change the status message when operation is finished
                if fileName != "":
                    root.fileName = fileName
            except Exception as e:
                messagebox.showerror("Error", str(e))

def openFile():
    thread = Thread(target=openFileThreaded)
    thread.start()
def openFileThreaded():
    if root.fileName == "":
        fileName = filedialog.askopenfilename(initialdir="/", title="Select file",
                                          filetypes=(("Text files", "*.txt"), ("Python Source files", "*.py"), ("All files", "*.*")))
    else:
                fileName = filedialog.askopenfilename(initialdir=root.fileName, title="Select file",
                                          filetypes=(("Text files", "*.txt"), ("Python Source files", "*.py"), ("All files", "*.*")))
        
    if fileName:
        try:
            with open(fileName, 'r', errors='replace') as f:
                textArea.delete('1.0', END) # clear the current content of the text area
                textArea.insert('1.0', f.read()) # insert the content of the opened file at line 1 char 0 (starting point)
            statusBar['text'] = f"'{fileName}' opened successfully!"
            root.fileName = fileName
            if updateSyntaxHighlighting.get():
                Thread(target=lambda: root.after(0, highlight_python_init)).start()
        except Exception as e:
            messagebox.showerror("Error", str(e))


def newFile():
    textArea.delete('1.0', END)
    statusBar['text'] = "New Document!"

def saveFile():
    fileName = root.fileName
    statusBar['text'] = "Ready"
    if fileName:
        try:
            
            with open(fileName, 'w') as f:
                f.write(textArea.get('1.0', END)) # get everything from line 1 char 0 (starting point) to end ('END')
            statusBar['text'] = f"'{fileName}' saved successfully!"
            root.fileName = fileName
        except Exception as e:
            messagebox.showerror("Error", str(e))

def highlight_python_threaded(event):
    if updateSyntaxHighlighting.get():
        thread = Thread(target=highlight_python_helper)
        thread.start()
stop_event = threading.Event()

def update_highlights():
    if updateSyntaxHighlighting.get():
        root.after(0, highlight_python_helper)  # your function to apply highlights
    
    else:
        textArea.tag_remove('string', "1.0", END)
        textArea.tag_remove('keyword', "1.0", END)
        textArea.tag_remove('comment', "1.0", END)
        textArea.tag_remove('selfs', "1.0", END)
        textArea.tag_remove('def', "1.0", END)
        textArea.tag_remove('number', "1.0", END)
    root.after(5000, update_highlights)  # schedule next run after 1 sec

# Start updating highlights on new thread

    

root.bind('<Control-Key-s>', lambda event: saveFileAsThreaded())
# Create menu options
fileMenu = Menu(menuBar, tearoff=False)
menuBar.add_cascade(label="File", menu=fileMenu)
fileMenu.add_command(label='New', command=newFile)
fileMenu.add_command(label='Open', command=openFile)
fileMenu.add_command(label='Save', command=saveFileAsThreaded)
fileMenu.add_command(label='Save As', command=saveFileAsThreaded2)
fileMenu.add_separator()
fileMenu.add_command(label='Exit', command=lambda: root.destroy())
editMenu = Menu(menuBar, tearoff=False)
menuBar.add_cascade(label="Edit", menu=editMenu)
editMenu.add_command(label='Cut', command=cutSelectedText)
editMenu.add_command(label='Copy', command=copyToClipboard)
editMenu.add_command(label='Paste', command=pasteFromClipboard)
editMenu.add_separator()
editMenu.add_command(label='Undo', command=lambda: textArea.edit_undo(), accelerator='Ctrl+Z')
editMenu.add_command(label='Redo', command=lambda: textArea.edit_redo(), accelerator='Ctrl+Y')

# Create toolbar
toolBar = Frame(root, bg='blue')
toolBar.pack(side=TOP, fill=X)

btn1 = Button(toolBar, text='New', command=newFile)
btn1.pack(side=LEFT, padx=2, pady=2)

btn2 = Button(toolBar, text='Open', command=openFile)
btn2.pack(side=LEFT, padx=2, pady=2)

btn3 = Button(toolBar, text='Save', command=saveFileAsThreaded)
btn3.pack(side=LEFT, padx=2, pady=2)

# Create status bar
statusBar = Label(root, text="Ready", bd='1', relief=SUNKEN, anchor=W)
statusBar.pack(side=BOTTOM, fill=X)

# Create text area
textArea = Text(root)
textArea.pack(fill=BOTH, expand=True, anchor="center")
textArea['bg'] = 'black'
textArea.tag_config("keyword", foreground="red")
textArea.tag_config("number", foreground="#FDFD6A")
textArea.tag_config("selfs", foreground="#33ccff")
textArea.tag_config("def", foreground="#33ccff")
textArea.tag_config("all", foreground="#4AF626")
textArea.tag_config("string", foreground="#C9CA6B")
textArea.tag_config("comment", foreground="#75715E")
textArea.tag_config("bold", font=("consolas", 12, "bold"))
textArea['fg'] = '#4AF626'
textArea['font'] = 'consolas 12'
textArea['undo'] = True
textArea.bind('<KeyRelease>', root.after(50, highlight_python_threaded))   # Call the function on key release (i.e., after typing finishes)

updateSyntaxHighlighting = IntVar()

Thread(target=lambda: root.after(0, update_highlights)).start()

checkButton = Checkbutton(toolBar, text="Python Syntax", variable=updateSyntaxHighlighting, onvalue=True, offvalue=False, command=lambda: Thread(target=highlight_python_init).start())
checkButton.pack(side=LEFT, padx=2, pady=2)



def format_bold():
    try:
        sel_start, sel_end = textArea.tag_ranges("sel")
        # Replace 'sel' with the current selection in the text area
        textArea.tag_add("bold", sel_start, sel_end)
    except Exception as e:
        textArea.tag_add("bold", "1.0", END)

format_button1 = Button(toolBar, text='Bold', command=format_bold)
format_button1.pack(side=LEFT, padx=2, pady=2)
# Start mainloop
root.mainloop()
stop_event.set()
SystemExit()
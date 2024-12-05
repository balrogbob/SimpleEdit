#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SimpleEdit 

Got Bored, decided to start with nothing and just code whatever came into my head. 
Turns out that was a python code editor to write the code for the editor I am writing. 
Has basic syntax highlighting, save and load functionality, and you can make text bold. 
But you cant unmake it bold. Also doesnt use any non-standard libraries, a fresh 
python install is enough. Uses Tkinter for GUI, and badly written unoptimized but 
threaded code to do the saving, loading, and highlighting. 

MIT License

Copyright (c) 2024 Joshua Richards

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Built-in/Generic Imports
import os
import sys
import threading
import time
import re
import configparser
import pickle
from token import NEWLINE
import torch
import tiktoken
from model import GPTConfig, GPT
from ast import Not
from selectors import SelectorKey
from tkinter import *
from tkinter import filedialog, messagebox, colorchooser
from io import StringIO
from threading import Thread
from contextlib import nullcontext


__author__ = 'Joshua Richards'
__copyright__ = 'Copyright 2024, SimpleEdit'
__credits__ = ['Balrogbob (Joshua Richards)']
__license__ = 'MIT'
__version__ = '0.0.2'
__maintainer__ = 'Balrogbob'
__email__ = 'josh@iconofgaming.com'
__status__ = 'pre-alpha'

init_from = 'resume' # either 'resume' (from an out_dir) or a gpt2 variant (e.g. 'gpt2-xl')
out_dir = 'out' # ignored if init_from is not 'resume'
start = "\n" # or "<|endoftext|>" or etc. Can also specify a file, use as: "FILE:prompt.txt"
num_samples = 1 # number of samples to draw
max_new_tokens = 128 # number of tokens generated in each sample
temperature = 1.1 # 1.0 = no change, < 1.0 = less random, > 1.0 = more random, in predictions
top_k = 300 # retain only the top_k most likely tokens, clamp others to have 0 probability
seed = 1337
device = 'cpu' # examples: 'cpu', 'cuda', 'cuda:0', 'cuda:1', etc.
dtype = 'float16'
torch.manual_seed(seed)
device_type = 'cpu'
ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]

# model

# init from a model saved in a specific directory
ckpt_path = os.path.join(out_dir, 'ckpt.pt')
checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
gptconf = GPTConfig(**checkpoint['model_args'])
model = GPT(gptconf)
state_dict = checkpoint['model']
unwanted_prefix = '_orig_mod.'
for k,v in list(state_dict.items()):
    if k.startswith(unwanted_prefix):
        state_dict[k[len(unwanted_prefix):]] = state_dict.pop(k)
model.load_state_dict(state_dict)
model.eval()
model.to(device)
# look for the meta pickle in case it is available in the dataset folder
load_meta = False


# ok let's assume gpt-2 encodings by default
enc = tiktoken.get_encoding("gpt2")
encode = lambda s: enc.encode(s, allowed_special={"<|endoftext|>"})
decode = lambda l: enc.decode(l)
# encode the beginning of the prompt

class CursorIndicator(Canvas):
    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self.config(width=2, bg="white")  # Change the color here
config = {}
config['[Section1]'] = {'fontName': 'consolas', 'cursorColor': 'white', 'fontSize': 12, 'fontColor': '#4AF626', 'backgroundColor': 'black', 'undoSetting': True, 'aiMaxContext': 512}

ini_path = 'config.ini'  # Create the .ini file in the same directory as your Python script

# Check if file exists. If it doesn't, write it.
if not os.path.isfile(ini_path):
    with open(ini_path, "w") as f:
        for section in config.keys():
            f.write(f"{section}\n")
            for key, value in config[section].items():
                f.write(f"{key} = {value}\n")

config = configparser.ConfigParser()
config.read(ini_path)

fontName = config.get("Section1", "fontName")  # prints: consolas
fontSize = config.get("Section1", "fontSize")  # prints: 12
fontColor = config.get("Section1", "fontColor")  # prints: '#4AF626'
backgroundColor = config.get("Section1", "backgroundColor")  # prints: 'black'
undoSetting = config.getboolean("Section1", "undoSetting")  # prints: True
cursorColor = config.get("Section1", "cursorColor")  # prints: white
aiMaxContext = config.get("Section1", "aiMaxContext")  # prints: white
def pythonAIAutoComplete():
    end = ''
    try:
        start, end = textArea.tag_ranges("sel")  # Get start and end of selected text in the Text widget
        if len(textArea.get(start, end)) >= aiMaxContext:
            textArea.tag_remove("sel", '1.0', END)
            start = textArea.index(f'{start}-{aiMaxContext}c')
            statusBar['text'] = f"Reducing Selection to avoid model insanity!"
            textArea.tag_add("sel", start, end)
            bypass = True
    except Exception as e:  # If no selection exists, it raises a TclError
        if end == '':
            start = textArea.index(f'insert-{aiMaxContext}c')   # Get index at line 1 char 0 ('END')
            end = textArea.index('insert')    # Get index at last char
            statusBar['text'] = f"Selecing previous {aiMaxContext} characters as context for generation."
            root.update_idletasks
            root.after(0, textArea.tag_add("sel", start, end))
    content = textArea.get(start, end)
    maxTokens = int(len(content) / 8 + 64)
    statusBar['text'] = f"Setting max tokens to {maxTokens}."
    print(f"Setting max tokens to {maxTokens}.")
    root.update_idletasks
    root.after(200)
    #if maxTokens >= 256:
    #    maxTokens = 256
    if content == '':
        content = f'<|endoftext|>'
        statusBar['text'] = f"Empty Context!!! Good Luck!"
        root.update_idletasks
        root.after(300)
    else:
        content = f'<|endoftext|>{content}'
    statusBar['text'] = f"Encoding!"
    root.update_idletasks
    root.after(50)
    start_ids = encode(content)
    statusBar['text'] = f"Encoded!"
    root.update_idletasks
    root.after(0)

    x = (torch.tensor(start_ids, dtype=torch.long, device=device)[None, ...])
    # run generation
    with torch.no_grad():
         statusBar['text'] = f"Generating!"
         root.update_idletasks
         root.after(0)
         y = model.generate(x, maxTokens, temperature=temperature, top_k=top_k)
         statusBar['text'] = f"Generated, Populating now."
         root.update_idletasks
         root.after(0)

         textArea.mark_set('insert', f'{end}')
         textArea.delete(start, end)
         def clean_string(input_text):
            pattern = r'<\|\s*endoftext\s*\|>'
            cleaned_text = re.sub(pattern, '', input_text)
            return cleaned_text
         decoded = clean_string(str(decode(y[0].tolist())))
         textArea.insert(textArea.index(INSERT), decoded)
         textArea.tag_remove("sel", '1.0', END)
         textArea.see(INSERT)
         readyUpdate()

def createConfigWindow():
    # This function creates and displays the configuration window as a modal dialog.
    global top

    # Create new top level widget.
    top = Toplevel()
    top.grab_set() # Modal behavior.
    top.title("Settings")

    # Frame for the Text Boxes.
    text_frame = Frame(top)
    text_frame.pack()

    fontNameField = Entry(text_frame, width=20, text=config.get("Section1", "fontName"))
    fontNameField.grid(row=0, column=2)
    fontNameLabel = Label(text_frame, width=20, text="Font")
    fontNameLabel.grid(row=0, column=1)

    fontSizeField = Entry(text_frame, width=20, text=config.get("Section1", "fontSize"))
    fontSizeField.grid(row=1, column=2)
    fontSizeLabel = Label(text_frame, width=20, text="Font Size")
    fontSizeLabel.grid(row=1, column=1)


    undoCheckVar = IntVar()
    undoCheck = Checkbutton(text_frame, text="Enable undo", variable=undoCheckVar)
    undoCheck.grid(row=6, column=1)

    aiMaxContext
    aiMaxContextField = Entry(text_frame, width=20, text=config.get("Section1", "aiMaxContext"))
    aiMaxContextField.grid(row=7, column=2)
    aiMaxContextLabel = Label(text_frame, width=20, text="Max AI Context")
    aiMaxContextLabel.grid(row=7, column=1)


    backgroundColorField = Entry(text_frame, width=20)
    backgroundColorField.grid(row=2, column=2) 
    cursorColorField = Entry(text_frame, width=20)
    cursorColorField.grid(column=2, row=4)

    fontColorChoice = Entry(text_frame, width=20)
    fontColorChoice.grid(column=2, row=5)
    fontColorVar = StringVar()

    def fontColor():
        fontColor = colorchooser.askcolor(title="Font Color", initialcolor=config.get("Section1", "fontColor"))
        if fontColor:
            fontColorChoice.delete(0, END)
            fontColorChoice.insert(0, getHexColor(fontColor))

    def backgroundColor():
        backgroundColor = colorchooser.askcolor(title='Background Color', initialcolor=config.get("Section1", "backgroundColor"))
        if backgroundColor:
            backgroundColorField.delete(0, END)
            backgroundColorField.insert(0, getHexColor(backgroundColor))

    def cursorColor():
        cursorColor = colorchooser.askcolor(title="Cursor Color", initialcolor=config.get("Section1", "cursorColor"))
        if cursorColor:
            cursorColorField.delete(0, END)
            cursorColorField.insert(0, getHexColor(cursorColor))

    color_chooser_button = Button(text_frame, text='Choose Font Color', command=fontColor)
    color_chooser_button.grid(row=5, column=1)

    backgroundFocusField = Button(text_frame, text="Choose Background", command=backgroundColor) 
    backgroundFocusField.grid(row=2, column=1)

    cursorFocusField = Button(text_frame, text="Choose Cursor Color", command=cursorColor) 
    cursorFocusField.grid(row=4, column=1)


    def onClosing():
        fontName = fontNameField.get()
        fontSize = fontSizeField.get()
        fontColor = fontColorChoice.get()
        backgroundColor = backgroundColorField.get()
        undoSetting = undoCheckVar.get()
        cursorColor = cursorColorField.get()
        aiMaxContext = aiMaxContextField.get()
        
        config.set("Section1", "fontName", fontName)
        config.set("Section1", "fontSize", fontSize)
        config.set("Section1", "fontColor", fontColor)
        config.set("Section1", "backgroundColor", backgroundColor) 
        config.set("Section1", "undoSetting", str(undoSetting))
        config.set("Section1", "cursorColor", cursorColor)
        config.set("Section1", "aiMaxContext", aiMaxContext)
        

        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        fontName = config.get("Section1", "fontName")  # prints: consolas
        fontSize = config.get("Section1", "fontSize")  # prints: 12
        fontColor = config.get("Section1", "fontColor")  # prints: '#4AF626'
        backgroundColor = config.get("Section1", "backgroundColor")  # prints: 'black'
        undoSetting = config.getboolean("Section1", "undoSetting")  # prints: True
        cursorColor = config.get("Section1", "cursorColor")  # prints: white
        aiMaxContext = config.get("Section1", "aiMaxContext")  # prints: white
        textArea.config(font=(fontName, fontSize))
        textArea.config(bg=(backgroundColor))
        textArea.config(fg=(fontColor))
        textArea.config(insertbackground=(cursorColor))
        textArea.config(undo=(undoSetting))
        top.destroy()



    def refreshFromFile():
        fontNameField.delete(0, END)
        fontNameField.insert(0, config.get("Section1", "fontName"))  
        fontSizeField.delete(0, END)
        fontSizeField.insert(0, config.get("Section1", "fontSize"))
        fontColorChoice.delete(0, END)
        fontColorChoice.insert(0, config.get("Section1", "fontColor"))
        undoCheckVar.set(config.getboolean("Section1", "undoSetting"))  
        cursorColorField.delete(0, END)
        cursorColorField.insert(0, config.get("Section1", "cursorColor"))
        backgroundColorField.delete(0, END)
        backgroundColorField.insert(0, config.get("Section1", "backgroundColor"))
        aiMaxContextField.delete(0, END)
        aiMaxContextField.insert(0, config.get("Section1", "aiMaxContext"))


        # Create a color picker button that opens a color dialog.
    

        # Add the widgets.
    text_frame.pack()
    saveButton = Button(top, text="Save", command=onClosing)
    saveButton.pack()

    refreshButton = Button(top, text="Refresh from file", command=refreshFromFile)
    refreshButton.pack()
    refreshFromFile()


    def saveToFile():
        onClosing()

# Then elsewhere in your tkinter program when you want to open this window as a popup on a button click
def getHexColor(s):
    match = re.search(r'#\w+', str(s))
    if match:
        return match.group(0)

def settingModal():
    createConfigWindow()
    top.mainloop()

def matchCaseLikeThis(start, end):
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
    match_string = matchCaseLikeThis(start, end)
def highlightPythonHelper(event):
    start = round(float(textArea.index(CURRENT)) - 100.0, 1)     # Get index at line 1 char 0 ('END')
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
    def highlightKeywords():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(keywords, content)]
        for match in reversed(matches):
            textArea.tag_add("keyword", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
    def highlightStrings():
        content = textArea.get(start2, end2)
        matches = [m.span() for m in re.finditer(string, content)]
        for match in reversed(matches):
            textArea.tag_add("string", f"{start2} + {match[0]}c", f"{start2} + {match[1]}c")
    def highlightComments():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(comments, content, re.DOTALL)]
        for match in reversed(matches):
            textArea.tag_add("comment", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
    def highlightNumbers():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(number, content)]
        for match in reversed(matches):
            textArea.tag_add("number", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
    def highlightSelfs():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(selfs, content)]
        for match in reversed(matches):
            textArea.tag_add("selfs", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
    def highlightDef():
        if not defs == r'\b\b':
            content = textArea.get(start, end)
            matches = [m.span() for m in re.finditer(defs, content)]
            for match in reversed(matches):
                textArea.tag_add("def", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
    highlightKeywords()
    highlightDef()
    highlightNumbers()
    highlightSelfs()
    stringst = Thread(target=highlightStrings())
    stringst.start()
    commentst = Thread(target=highlightComments())
    commentst.start()

def highlightPythonInit():
    if updateSyntaxHighlighting.get():
        root.update_idletasks()
        statusBar['text'] = f"Processing Inital Syntax, Please wait... 0%"
    start = "1.0"     # Get index at line 1 char 0 ('END')
    end = END     # Get index at last char
    # Define regex patterns
    keywords = r'\b(if|else|while|for|return|def|from|import|class)\b'
    selfs = r'\b(?:[a-z])(?:[A-Z]?[a-z])*(?:[A-Z][a-z]*)|\b(self|root)\b'
    comments = r'#[^\n]*|"""(.*?)"""'
    string = r'"[^"]*"|\'[^\']*\''
    number = r'\b(\d+(\.\d*)?|\.\d+)\b'
    functionNames(start, end)
    if updateSyntaxHighlighting.get():
        root.update_idletasks()
        statusBar['text'] = f"Processing Inital Syntax, Please wait... 10%"
    defs = match_string
    def highlightKeywords():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(keywords, content)]
        for match in reversed(matches):
            textArea.tag_add("keyword", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
        if updateSyntaxHighlighting.get():
            root.update_idletasks()
            statusBar['text'] = f"Processing Inital Syntax, Please wait... 20%"
    def highlightStrings():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(string, content)]
        for match in reversed(matches):
            textArea.tag_add("string", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
        if updateSyntaxHighlighting.get():
            root.update_idletasks()
            statusBar['text'] = f"Processing Inital Syntax, Please wait... 30%"
    def highlightComments():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(comments, content, re.DOTALL)]
        for match in reversed(matches):
            textArea.tag_add("comment", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
        if updateSyntaxHighlighting.get():
            root.update_idletasks()
            statusBar['text'] = f"Processing Inital Syntax, Please wait... 90%"
    def highlightNumbers():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(number, content)]
        for match in reversed(matches):
            textArea.tag_add("number", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
        if updateSyntaxHighlighting.get():
            root.update_idletasks()
            statusBar['text'] = f"Processing Inital Syntax, Please wait... 50%"
    def highlightSelfs():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(selfs, content)]
        for match in reversed(matches):
            textArea.tag_add("selfs", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
        if updateSyntaxHighlighting.get():
            root.update_idletasks()
            statusBar['text'] = f"Processing Inital Syntax, Please wait... 70%"
    def highlightDef():
        content = textArea.get(start, end)
        matches = [m.span() for m in re.finditer(defs, content)]
        for match in reversed(matches):
            textArea.tag_add("def", f"{start} + {match[0]}c", f"{start} + {match[1]}c")
        if updateSyntaxHighlighting.get():
            root.update_idletasks()
            statusBar['text'] = f"Processing Inital Syntax, Please wait... 70%"
    keywordt = Thread(target=highlightKeywords())
    keywordt.start()
    stringst = Thread(target=highlightStrings())
    stringst.start()
    defst = Thread(target=highlightDef())
    defst.start()
    numberst = Thread(target=highlightNumbers())
    numberst.start()
    selfst = Thread(target=highlightSelfs())
    selfst.start()
    commentst = Thread(target=highlightComments())
    commentst.start()
    if updateSyntaxHighlighting.get():
        statusBar['text'] = f"Processing Inital Syntax, Please wait... 100%"
        root.after(300)
        statusBar['text'] = f"Ready"

def highlightPythonInitT():
    if updateSyntaxHighlighting.get():
        thread = Thread(target=highlightPythonInit)
        thread.start()
    else:
        textArea.tag_remove('string', "1.0", END)
        textArea.tag_remove('keyword', "1.0", END)
        textArea.tag_remove('comment', "1.0", END)
        textArea.tag_remove('selfs', "1.0", END)
        textArea.tag_remove('def', "1.0", END)
        textArea.tag_remove('number', "1.0", END)
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

def formatBold():
    try:
        sel_start, sel_end = textArea.tag_ranges("sel")  # Get start and end of selected text in the Text widget
    except Exception as e:  # If no selection exists, it raises a TclError
        sel_start, sel_end = "1.0", END  # Set start to first character (line 1, char 0) and end to last character (END)
    
    if textArea.tag_ranges("bold"):  # Check if the selected/all text is already underline
        textArea.tag_remove("bold", sel_start, sel_end)  # Remove underline formatting from selected/all text
    else:
        if textArea.tag_ranges("bolditalic"):  # Check if the selected/all text is already underline
            textArea.tag_remove("bolditalic", sel_start, sel_end)  # Remove underline formatting from selected/all text
            textArea.tag_add("italic", sel_start, sel_end) # leave the text just italic
        else:
            if textArea.tag_ranges("all"):  # Check if the selected/all text is already underline
                textArea.tag_remove("all", sel_start, sel_end)  # Remove all formatting from selected/all text
                textArea.tag_add("underlineitalic", sel_start, sel_end) # leave the text just bold italic
            else:
                if textArea.tag_ranges("boldunderline"):  # Check if the selected/all text is already bolded
                    textArea.tag_remove("boldunderline", sel_start, sel_end)
                    textArea.tag_add("underline", sel_start, sel_end)
                else:
                    if textArea.tag_ranges("underline"):  # Check if the selected/all text is already italic
                        textArea.tag_remove("underline", sel_start, sel_end)
                        textArea.tag_add("boldunderline", sel_start, sel_end)
                    else:
                        if textArea.tag_ranges("italic"):  # Check if the selected/all text is already bolded
                            textArea.tag_remove("italic", sel_start, sel_end)
                            textArea.tag_add("bolditalic", sel_start, sel_end)
                        else:
                            if textArea.tag_ranges("underlineitalic"):  # Check if the selected/all text is already bolded
                                textArea.tag_remove("underlineitalic", sel_start, sel_end)
                                textArea.tag_add("all", sel_start, sel_end)
                            else:
                                textArea.tag_add("bold", sel_start, sel_end)  # Add bold formatting to selected/all text

def formatItalic():
    try:
        sel_start, sel_end = textArea.tag_ranges("sel")  # Get start and end of selected text in the Text widget
    except Exception as e:  # If no selection exists, it raises an error
        sel_start, sel_end = "1.0", END  # Set start to first character (line 1, char 0) and end to last character (END)

    if textArea.tag_ranges("italic"):  # Check if the selected/all text is already underline
        textArea.tag_remove("italic", sel_start, sel_end)  # Remove underline formatting from selected/all text
    else:
        if textArea.tag_ranges("underlineitalic"):  # Check if the selected/all text is already underline
            textArea.tag_remove("underlineitalic", sel_start, sel_end)  # Remove underline formatting from selected/all text
            textArea.tag_add("underline", sel_start, sel_end) # leave the text just italic
        else:
            if textArea.tag_ranges("all"):  # Check if the selected/all text is already underline
                textArea.tag_remove("all", sel_start, sel_end)  # Remove all formatting from selected/all text
                textArea.tag_add("boldunderline", sel_start, sel_end) # leave the text just bold italic
            else:
                if textArea.tag_ranges("bolditalic"):  # Check if the selected/all text is already bolded
                     textArea.tag_remove("bolditalic", sel_start, sel_end)
                     textArea.tag_add("bold", sel_start, sel_end)
                else:
                    if textArea.tag_ranges("underline"):  # Check if the selected/all text is already italic
                        textArea.tag_remove("underline", sel_start, sel_end)
                        textArea.tag_add("underlineitalic", sel_start, sel_end)
                    else:
                        if textArea.tag_ranges("bold"):  # Check if the selected/all text is already bolded
                            textArea.tag_remove("bold", sel_start, sel_end)
                            textArea.tag_add("bolditalic", sel_start, sel_end)
                        else:
                            if textArea.tag_ranges("boldunderline"):  # Check if the selected/all text is already bolded
                                textArea.tag_remove("boldunderline", sel_start, sel_end)
                                textArea.tag_add("all", sel_start, sel_end)
                            else:
                                textArea.tag_add("italic", sel_start, sel_end)  # Add bold formatting to selected/all text

def formatUnderLine():
    try:
        sel_start, sel_end = textArea.tag_ranges("sel")  # Get start and end of selected text in the Text widget
    except Exception as e:  # If no selection exists, it raises an error
        sel_start, sel_end = "1.0", END  # Set start to first character (line 1, char 0) and end to last character (END)

    if textArea.tag_ranges("underline"):  # Check if the selected/all text is already underline
        textArea.tag_remove("underline", sel_start, sel_end)  # Remove underline formatting from selected/all text
    else:
        if textArea.tag_ranges("underlineitalic"):  # Check if the selected/all text is already underline
            textArea.tag_remove("underlineitalic", sel_start, sel_end)  # Remove underline formatting from selected/all text
            textArea.tag_add("italic", sel_start, sel_end) # leave the text just italic
        else:
            if textArea.tag_ranges("all"):  # Check if the selected/all text is already underline
                textArea.tag_remove("all", sel_start, sel_end)  # Remove all formatting from selected/all text
                textArea.tag_add("bolditalic", sel_start, sel_end) # leave the text just bold italic
            else:
                if textArea.tag_ranges("boldunderline"):  # Check if the selected/all text is already bolded
                    textArea.tag_remove("boldunderline", sel_start, sel_end)
                    textArea.tag_add("bold", sel_start, sel_end)
                else:
                    if textArea.tag_ranges("italic"):  # Check if the selected/all text is already italic
                        textArea.tag_remove("italic", sel_start, sel_end)
                        textArea.tag_add("underlineitalic", sel_start, sel_end)
                    else:
                        if textArea.tag_ranges("bold"):  # Check if the selected/all text is already bolded
                            textArea.tag_remove("bold", sel_start, sel_end)
                            textArea.tag_add("boldunderline", sel_start, sel_end)
                        else:
                            if textArea.tag_ranges("bolditalic"):  # Check if the selected/all text is already bolded
                                textArea.tag_remove("bolditalic", sel_start, sel_end)
                                textArea.tag_add("all", sel_start, sel_end)
                            else:
                                textArea.tag_add("underline", sel_start, sel_end)  # Add bold formatting to selected/all text
   
def removeAllFormatting():
    try:
        sel_start, sel_end = textArea.tag_ranges("sel")  # Get start and end of selected text in the Text widget
    except Exception as e:  # If no selection exists, it raises an error
        sel_start, sel_end = "1.0", END  # Set start to first character (line 1, char 0) and end to last character (END)
    textArea.tag_remove("underline", sel_start, sel_end)  # Remove underline formatting from selected/all text
    textArea.tag_remove("underlineitalic", sel_start, sel_end)  # Remove underline formatting from selected/all text
    textArea.tag_remove("all", sel_start, sel_end)  # Remove all formatting from selected/all text
    textArea.tag_remove("boldunderline", sel_start, sel_end)
    textArea.tag_remove("italic", sel_start, sel_end)
    textArea.tag_remove("bold", sel_start, sel_end)
    textArea.tag_remove("bolditalic", sel_start, sel_end)

def saveFileAsThreaded():
    thread = Thread(target=saveFileAs)
    thread.start()

def saveFileAs():
    if stop_event.is_set():
        exit
    else:
        def getSizeOfTextArea():
            """Calculate the size (in bytes) of the content in text area"""
            return sum([1 for c in textArea.get('1.0', END).split('\n')])   # Count number of lines
        if root.fileName == "":
            fileName = filedialog.asksaveasfilename(initialdir="/", title="Select file",
                                                filetypes=(("Text files", "*.txt"), ("Python Source files", "*.py"), ("All files", "*.*")))
            root.fileName = fileName
        sys.stdout = statusBar['text']
        fileName = root.fileName
        if fileName:
            try:
                total_size = getSizeOfTextArea()# Get the estimated total size of the file 
                current_size = 0 
                with open(fileName, 'w', errors='replace') as f:
                    for line in textArea.get('1.0', END).split('\n'):
                        f.write(line + '\n')
                        current_size += 1  
                        progress = round((current_size/total_size)*100, 2)  # Calculate percentage completion rounded to 2 decimal places
                        if progress >= 100.00:
                            progress = 100.00
                        statusBar['text'] = f"Saving... {progress}% - {fileName}"
                root.fileName = fileName
                statusBar['text'] = f"Saving... 100% - {fileName}"
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
            return sum([1 for c in textArea.get('1.0', END).split('\n')])   # Count number of lines
        fileName2 = filedialog.asksaveasfilename(initialdir=root.fileName, title="Select file",
                                                filetypes=(("Text files", "*.txt"), ("Python Source files", "*.py"), ("All files", "*.*")))
        if root.fileName == "":
            root.fileName = fileName2
        sys.stdout = statusBar['text']
        fileName = fileName2
        if fileName:
            try:
                total_size = getSizeOfTextArea()# Get the estimated total size of the file 
                current_size = 0 
                with open(fileName, 'w', errors='replace') as f:
                    for line in textArea.get('1.0', END).split('\n'):
                        f.write(line + '\n')
                        current_size += 1 
                        progress = round((current_size/total_size)*100, 2)  # Calculate percentage completion rounded to 2 decimal places
                        if progress >= 100.00:
                            progress = 100.00
                        statusBar['text'] = f"Saving... {progress}% - {fileName}"
                root.fileName = fileName
                statusBar['text'] = f"Saving... 100% - {fileName}"
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
                root.update_idletasks
                thread = Thread(target=lambda: root.after(0, highlightPythonInit))
                thread.start()
        except Exception as e:
            messagebox.showerror("Error", str(e))

def readyUpdate():
    root.after(1000)
    statusBar['text'] = "Ready"

def newFile():
    textArea.delete('1.0', END)
    statusBar['text'] = "New Document!"
    thread = Thread(target=readyUpdate)
    thread.start()

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

def highlightPythonThreaded(event):
    if updateSyntaxHighlighting.get():
        thread = Thread(target=highlightPythonHelper)
        root.after(100, thread.start())

stop_event = threading.Event()

def updateHighlights():
    if updateSyntaxHighlighting.get():
        thread = Thread(target=highlightPythonHelper(NONE))
        thread.start()  # your function to apply highlights
    else:
        textArea.tag_remove('string', "1.0", END)
        textArea.tag_remove('keyword', "1.0", END)
        textArea.tag_remove('comment', "1.0", END)
        textArea.tag_remove('selfs', "1.0", END)
        textArea.tag_remove('def', "1.0", END)
        textArea.tag_remove('number', "1.0", END)
    root.after(2000, updateHighlights)  # schedule next run after 10 sec
    root.update_idletasks()

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
formatButton1 = Button(toolBar, text='Bold', command=formatBold)
formatButton1.pack(side=LEFT, padx=2, pady=2)
formatButton2 = Button(toolBar, text='Italic', command=formatItalic)
formatButton2.pack(side=LEFT, padx=2, pady=2)
formatButton3 = Button(toolBar, text='Underline', command=formatUnderLine)
formatButton3.pack(side=LEFT, padx=2, pady=2)
formatButton4 = Button(toolBar, text='Remove Formatting', command=removeAllFormatting)
formatButton4.pack(side=LEFT, padx=2, pady=2)

# Create status bar
statusBar = Label(root, text="Ready", bd='1', relief=SUNKEN, anchor=W)
statusBar.pack(side=BOTTOM, fill=X)

# Create text area
textArea = Text(root, insertbackground=cursorColor)
textArea.pack(side=LEFT, fill=BOTH, expand=True, anchor="center")
textArea['bg'] = backgroundColor
textArea.tag_config("keyword", foreground="red")
textArea.tag_config("number", foreground="#FDFD6A")
textArea.tag_config("selfs", foreground="#33ccff")
textArea.tag_config("def", foreground="#33ccff")
textArea.tag_config("string", foreground="#C9CA6B")
textArea.tag_config("comment", foreground="#75715E")
textArea.tag_config("bold", font=(fontName, fontSize, "bold"))
textArea.tag_config("italic", font=(fontName, fontSize, "italic"))
textArea.tag_config("underline", font=(fontName, fontSize, "underline"))
textArea.tag_config("all", font=(fontName, fontSize, "bold", "italic", "underline"))
textArea.tag_config("underlineitalic", font=(fontName, fontSize, "italic", "underline"))
textArea.tag_config("boldunderline", font=(fontName, fontSize, "bold", "underline"))
textArea.tag_config("bolditalic", font=(fontName, fontSize, "bold", "italic"))
textArea['fg'] = fontColor
textArea['font'] = f'{fontName} {str(fontSize)}'
textArea['undo'] = undoSetting
scroll = Scrollbar(root, command=textArea.yview)
textArea.configure(yscrollcommand=scroll.set)

def highlightPythonHelperT(event):
    if updateSyntaxHighlighting.get():
        highlightPythonHelper(event)
    else:
        textArea.tag_remove('string', "1.0", END)
        textArea.tag_remove('keyword', "1.0", END)
        textArea.tag_remove('comment', "1.0", END)
        textArea.tag_remove('selfs', "1.0", END)
        textArea.tag_remove('def', "1.0", END)
        textArea.tag_remove('number', "1.0", END)

textArea.bind('<KeyRelease>', lambda event: Thread(target=highlightPythonHelperT(Event)).start())   # Call the function on key release (i.e., after typing finishes)
updateSyntaxHighlighting = IntVar()
Thread(target=lambda: root.after(0, updateHighlights)).start()
checkButton = Checkbutton(toolBar, text="Python Syntax", variable=updateSyntaxHighlighting, onvalue=True, offvalue=False, command=lambda: root.after(0, highlightPythonInitT))
checkButton.pack(side=LEFT, padx=2, pady=2)
formatButton5 = Button(toolBar, text='Settings', command=settingModal)
formatButton5.pack(side=RIGHT, padx=2, pady=2)
formatButton5 = Button(toolBar, text='AI Autocomplete (Experimental)', command=lambda: Thread(target=pythonAIAutoComplete).start())
formatButton5.pack(side=RIGHT, padx=2, pady=2)
scroll.pack(side=RIGHT, fill=Y)



# Define Main Loop
def main():
    root.mainloop()
    stop_event.set()
    SystemExit()

# Start mainloop with proper convention
if __name__ == '__main__':
    main()
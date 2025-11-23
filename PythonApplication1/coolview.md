<div style="background:black;color:#00ff00;font-family:consolas,monospace;white-space:pre-wrap;padding:8px;">
<strong><span style="color:#75715E">#!/usr/bin/env python3</span>
<span style="color:#75715E"># -*- coding: utf-8 -*-</span>
<span style="color:#C9CA6B">&quot;&quot;&quot;
SimpleEdit

A small Tkinter-based code editor with basic syntax highlighting, MRU,
formatting toggles and an experimental local GPT autocomplete.

License: MIT
Copyright (c) 2024 Joshua Richards
&quot;&quot;&quot;</span>

<span style="color:#75715E"># Built-in imports</span>
<span style="color:#FF0000">import</span> os
<span style="color:#FF0000">import</span> sys
<span style="color:#FF0000">import</span> threading
<span style="color:#FF0000">import</span> re
<span style="color:#FF0000">import</span> configparser
<span style="color:#FF0000">import</span> random
<span style="color:#FF0000">import</span> time
<span style="color:#FF0000">import</span> html
<span style="color:#FF0000">from</span> html.<span style="color:#8A2BE2"><span style="color:#33CCFF">parser</span></span> <span style="color:#FF0000">import</span> HTMLParser
<span style="color:#FF0000">import</span> json
<span style="color:#FF0000">import</span> base64
<span style="color:#FF0000">from</span> io <span style="color:#FF0000">import</span> StringIO
<span style="color:#FF0000">from</span> threading <span style="color:#FF0000">import</span> Thread
<span style="color:#FF0000">from</span> tkinter <span style="color:#FF0000">import</span> *
<span style="color:#FF0000">from</span> tkinter <span style="color:#FF0000">import</span> filedialog, messagebox, colorchooser, simpledialog
<span style="color:#FF0000">from</span> tkinter <span style="color:#FF0000">import</span> ttk
<span style="color:#FF0000">import</span> shutil, sys, os


<span style="color:#75715E"># Optional ML dependencies (wrapped so editor still runs without them)</span>
<span style="color:#FF0000">try</span>:
    <span style="color:#FF0000">import</span> torch
    <span style="color:#FF0000">import</span> tiktoken
    <span style="color:#FF0000">from</span> <span style="color:#8A2BE2">model</span> <span style="color:#FF0000">import</span> GPTConfig, GPT
    <span style="color:#8A2BE2">_ML_AVAILABLE</span> = <span style="color:#9CDCFE">True</span>
<span style="color:#FF0000">except</span> Exception:
    <span style="color:#8A2BE2">_ML_AVAILABLE</span> = <span style="color:#9CDCFE">False</span>
<span style="color:#8A2BE2">_AI_BUTTON_DEFAULT_TEXT</span> = <span style="color:#C9CA6B">&quot;AI Autocomplete (Experimental)&quot;</span>
<span style="color:#FFA500"><span style="color:#8A2BE2">__author__</span></span> = <span style="color:#C9CA6B">&#x27;Joshua Richards&#x27;</span>
<span style="color:#FFA500"><span style="color:#8A2BE2">__license__</span></span> = <span style="color:#C9CA6B">&#x27;MIT&#x27;</span>
<span style="color:#FFA500"><span style="color:#8A2BE2">__version__</span></span> = <span style="color:#C9CA6B">&#x27;0.0.2&#x27;</span>

<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Config / MRU initialization</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#8A2BE2"><span style="color:#FF79C6">DEFAULT_CONFIG</span></span> = {
    <span style="color:#C9CA6B">&#x27;Section1&#x27;</span>: {
        <span style="color:#C9CA6B">&#x27;fontName&#x27;</span>: <span style="color:#C9CA6B">&#x27;consolas&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;fontSize&#x27;</span>: <span style="color:#C9CA6B">&#x27;12&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;fontColor&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#4AF626&#x27;</span></span>,
        <span style="color:#C9CA6B">&#x27;backgroundColor&#x27;</span>: <span style="color:#C9CA6B">&#x27;black&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;cursorColor&#x27;</span>: <span style="color:#C9CA6B">&#x27;white&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;undoSetting&#x27;</span>: <span style="color:#C9CA6B">&#x27;True&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;aiMaxContext&#x27;</span>: <span style="color:#C9CA6B">&#x27;512&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;temperature&#x27;</span>: <span style="color:#C9CA6B">&#x27;1.1&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;top_k&#x27;</span>: <span style="color:#C9CA6B">&#x27;300&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;seed&#x27;</span>: <span style="color:#C9CA6B">&#x27;1337&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;syntaxHighlighting&#x27;</span>: <span style="color:#C9CA6B">&#x27;True&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;loadAIOnOpen&#x27;</span>: <span style="color:#C9CA6B">&#x27;False&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;loadAIOnNew&#x27;</span>: <span style="color:#C9CA6B">&#x27;False&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;saveFormattingInFile&#x27;</span>: <span style="color:#C9CA6B">&#x27;False&#x27;</span>,   <span style="color:#75715E"># new: persist whether to embed formatting header</span>
    }
}

<span style="color:#8A2BE2">_TAG_COLOR_MAP</span> = {
    <span style="color:#C9CA6B">&#x27;number&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#FDFD6A&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#FFFF00&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;variable&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#8A2BE2&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;decorator&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#66CDAA&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;class_name&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#FFB86B&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;constant&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#FF79C6&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;attribute&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#33CCFF&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#9CDCFE&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;def&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#FFA500&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#FF0000&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;string&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#C9CA6B&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;operator&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#AAAAAA&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;comment&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#75715E&#x27;</span></span>,
    <span style="color:#C9CA6B">&#x27;todo&#x27;</span>: <span style="color:#C9CA6B">&#x27;<span style="color:#75715E"><span style="color:#ffffff;background-color:#B22222">#FFFFFF&#x27;</span></span></span>,  # todo uses white text on red background - background handled specially
}
<span style="color:#75715E"># reverse map for parsing spans back to tag names (normalized to lower hex)</span>
<span style="color:#8A2BE2">_COLOR_TO_TAG</span> = {v.<span style="color:#33CCFF">lower</span>(): k <span style="color:#FF0000">for</span> k, v <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">_TAG_COLOR_MAP</span>.<span style="color:#33CCFF">items</span>()}

<span style="color:#75715E"># --- HTML parser to extract plain text and tag ranges from simple HTML fragments ---</span>
<span style="color:#FF0000">class</span> <span style="color:#FFB86B">_SimpleHTMLToTagged</span>(HTMLParser):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Parses a fragment of HTML and returns plain text plus tag ranges for
    simple tags: &lt;b&gt;/&lt;strong&gt;, &lt;i&gt;/&lt;em&gt;, &lt;u&gt;, and &lt;span style=&quot;color:...&quot;&gt;.
    Nested tags are supported and ranges are produced in absolute character offsets.
    &quot;&quot;&quot;</span>
    <span style="color:#FF0000">def</span> <span style="color:#FFA500">__init__</span>(<span style="color:#FFFF00">self</span>):
        super().<span style="color:#FFA500"><span style="color:#33CCFF">__init__</span></span>()
        <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">out</span></span> = []
        <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span> = <span style="color:#FDFD6A">0</span>
        <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span> = []  <span style="color:#75715E"># list of (internal_tag_name, start_pos)</span>
        <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">ranges</span></span> = {}  <span style="color:#75715E"># tag -&gt; [[start,end], ...]</span>
        <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">_span_color_pending</span> = <span style="color:#9CDCFE">None</span>

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">handle_starttag</span>(<span style="color:#FFFF00">self</span>, <span style="color:#8A2BE2">tag</span>, attrs):
        <span style="color:#8A2BE2">tag</span> = <span style="color:#8A2BE2">tag</span>.<span style="color:#33CCFF">lower</span>()
        <span style="color:#8A2BE2">attrd</span> = <span style="color:#9CDCFE">dict</span>(attrs)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;b&#x27;</span>, <span style="color:#C9CA6B">&#x27;strong&#x27;</span>):
            <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span>.<span style="color:#33CCFF">append</span>((<span style="color:#C9CA6B">&#x27;bold&#x27;</span>, <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span>))
        elif <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;i&#x27;</span>, <span style="color:#C9CA6B">&#x27;em&#x27;</span>):
            <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span>.<span style="color:#33CCFF">append</span>((<span style="color:#C9CA6B">&#x27;italic&#x27;</span>, <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span>))
        elif <span style="color:#8A2BE2">tag</span> == <span style="color:#C9CA6B">&#x27;u&#x27;</span>:
            <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span>.<span style="color:#33CCFF">append</span>((<span style="color:#C9CA6B">&#x27;underline&#x27;</span>, <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span>))
        elif <span style="color:#8A2BE2">tag</span> == <span style="color:#C9CA6B">&#x27;span&#x27;</span>:
            <span style="color:#8A2BE2">style</span> = <span style="color:#8A2BE2">attrd</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;style&#x27;</span>, <span style="color:#C9CA6B">&#x27;&#x27;</span>) <span style="color:#FF0000">or</span> <span style="color:#8A2BE2">attrd</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;class&#x27;</span>, <span style="color:#C9CA6B">&#x27;&#x27;</span>)
            <span style="color:#75715E"># find color in style string</span>
            <span style="color:#8A2BE2">m</span> = re.<span style="color:#33CCFF">search</span>(r<span style="color:#C9CA6B">&#x27;color\s*:\s*(<span style="color:#75715E">#[0-9A-Fa-f]{3,6}|[A-Za-z]+)&#x27;</span></span>, style)
            <span style="color:#8A2BE2">bg</span> = <span style="color:#9CDCFE">None</span>
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m</span>:
                <span style="color:#8A2BE2">color</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>).<span style="color:#33CCFF">lower</span>()
                <span style="color:#75715E"># normalize 3-digit hex to 6-digit</span>
                <span style="color:#FF0000">if</span> re.<span style="color:#FF0000"><span style="color:#33CCFF">match</span></span>(<span style="color:#C9CA6B">r&#x27;^<span style="color:#75715E">#[0-9a-f]{3}$&#x27;</span></span>, color):
                    <span style="color:#8A2BE2">color</span> = <span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#&#x27;</span></span> + <span style="color:#C9CA6B">&#x27;&#x27;</span>.join([c*2 for c in color[1:]])
                <span style="color:#75715E"># look up tag by color</span>
                <span style="color:#8A2BE2">tagname</span> = <span style="color:#8A2BE2">_COLOR_TO_TAG</span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">color</span>)
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">tagname</span>:
                    <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">tagname</span>, <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span>))
                    <span style="color:#FF0000">return</span>
            <span style="color:#75715E"><span style="color:#ffffff;background-color:#B22222"># special-check for todo</span> background (red background with white text)</span>
            <span style="color:#8A2BE2">m2</span> = re.<span style="color:#33CCFF">search</span>(r<span style="color:#C9CA6B">&#x27;background(?:-color)?\s*:\s*(<span style="color:#75715E">#[0-9A-Fa-f]{3,6}|[A-Za-z]+)&#x27;</span></span>, style)
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m2</span>:
                <span style="color:#8A2BE2">bgcol</span> = <span style="color:#8A2BE2">m2</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>).<span style="color:#33CCFF">lower</span>()
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">bgcol</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#b22222&#x27;</span></span>, <span style="color:#C9CA6B">&#x27;b22222&#x27;</span>, <span style="color:#C9CA6B">&#x27;red&#x27;</span>):
                    <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span>.<span style="color:#33CCFF">append</span>((<span style="color:#C9CA6B">&#x27;todo&#x27;</span>, <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span>))
                    <span style="color:#FF0000">return</span>
            <span style="color:#75715E"># unknown span -&gt; push a sentinel so it can be popped later without creating a tag</span>
            <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span>.<span style="color:#33CCFF">append</span>((<span style="color:#9CDCFE">None</span>, <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span>))

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">handle_endtag</span>(<span style="color:#FFFF00">self</span>, <span style="color:#8A2BE2">tag</span>):
        <span style="color:#8A2BE2">tag</span> = <span style="color:#8A2BE2">tag</span>.<span style="color:#33CCFF">lower</span>()
        <span style="color:#75715E"># pop the most recent matching type on stack (search backwards)</span>
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#75715E"># We pop the last entry, regardless of tag name, to keep things simple and robust.</span>
        <span style="color:#8A2BE2">name</span>, <span style="color:#8A2BE2">start</span> = <span style="color:#FFFF00">self</span>.<span style="color:#33CCFF">stack</span>.<span style="color:#33CCFF">pop</span>()
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">name</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#8A2BE2">end</span> = <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">end</span> &gt; <span style="color:#8A2BE2">start</span>:
            <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">ranges</span></span>.<span style="color:#33CCFF">setdefault</span>(<span style="color:#8A2BE2">name</span>, []).<span style="color:#33CCFF">append</span>([<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>])

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">handle_data</span>(<span style="color:#FFFF00">self</span>, <span style="color:#8A2BE2">data</span>):
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">data</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">out</span></span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">data</span>)
        <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">pos</span></span> += <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">data</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">get_result</span>(<span style="color:#FFFF00">self</span>):
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>.<span style="color:#33CCFF">join</span>(<span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">out</span></span>), <span style="color:#FFFF00">self</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">ranges</span></span>

<span style="color:#75715E"># --- Convert buffer to HTML fragment (used for .md and .html outputs) ---</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">_convert_buffer_to_html_fragment</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Produce an HTML fragment representing the buffer: syntax highlighting
    rendered as &lt;span style=&quot;color:...&quot;&gt; and formatting as &lt;strong&gt;/&lt;em&gt;/&lt;u&gt;.
    Fragment is safe to embed directly into Markdown (.md) as raw HTML or into
    a full HTML document (.html).
    &quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">content</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>)
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">content</span>:
            <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>

        <span style="color:#75715E"># gather all tag ranges (formatting + syntax)</span>
        <span style="color:#8A2BE2">tags_by_name</span> = <span style="color:#FFA500">_collect_all_tag_ranges</span>()  <span style="color:#75715E"># returns dict tag -&gt; [[s,e],...]</span>

        <span style="color:#75715E"># build events and walk linear segments (end events before start events)</span>
        <span style="color:#8A2BE2">events</span> = []
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">tag</span>, <span style="color:#8A2BE2">ranges</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">tags_by_name</span>.<span style="color:#33CCFF">items</span>():
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">ranges</span>:
                <span style="color:#8A2BE2">events</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#C9CA6B">&#x27;start&#x27;</span>, <span style="color:#8A2BE2">tag</span>))
                <span style="color:#8A2BE2">events</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">e</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>, <span style="color:#8A2BE2">tag</span>))
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">events</span>:
            <span style="color:#75715E"># no tags -&gt; just escape HTML and return text with newlines preserved as &lt;br&gt;</span>
            <span style="color:#FF0000">return</span> html.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">content</span>).<span style="color:#33CCFF">replace</span>(<span style="color:#C9CA6B">&#x27;\n&#x27;</span>, <span style="color:#C9CA6B">&#x27;\n&#x27;</span>)

        <span style="color:#8A2BE2">events_by_pos</span> = {}
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">pos</span>, kind, <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">events</span>:
            <span style="color:#8A2BE2">events_by_pos</span>.<span style="color:#33CCFF">setdefault</span>(<span style="color:#8A2BE2">pos</span>, []).<span style="color:#33CCFF">append</span>((kind, <span style="color:#8A2BE2">tag</span>))
        <span style="color:#75715E"># ensure start and end boundaries included</span>
        <span style="color:#8A2BE2">positions</span> = sorted(<span style="color:#9CDCFE">set</span>(<span style="color:#9CDCFE">list</span>(<span style="color:#8A2BE2">events_by_pos</span>.<span style="color:#33CCFF">keys</span>()) + [<span style="color:#FDFD6A">0</span>, <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">content</span>)]))
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">pos</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">events_by_pos</span>:
            <span style="color:#75715E"># ensure <span style="color:#C9CA6B">&#x27;end&#x27;</span> sorts before <span style="color:#C9CA6B">&#x27;start&#x27;</span></span>
            <span style="color:#8A2BE2">events_by_pos</span>[<span style="color:#8A2BE2">pos</span>].<span style="color:#33CCFF">sort</span>(key=<span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">x</span>: <span style="color:#FDFD6A">0</span> <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">x</span>[<span style="color:#FDFD6A">0</span>] == <span style="color:#C9CA6B">&#x27;end&#x27;</span> <span style="color:#FF0000">else</span> <span style="color:#FDFD6A">1</span>)

        <span style="color:#8A2BE2">out_parts</span> = []
        <span style="color:#8A2BE2">active</span> = []  <span style="color:#75715E"># maintain stack of active tags to produce nested HTML</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">positions</span>) - <span style="color:#FDFD6A">1</span>):
            <span style="color:#8A2BE2">pos</span> = <span style="color:#8A2BE2">positions</span>[<span style="color:#8A2BE2">i</span>]
            <span style="color:#FF0000">for</span> kind, <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">events_by_pos</span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">pos</span>, []):
                <span style="color:#FF0000">if</span> kind == <span style="color:#C9CA6B">&#x27;end&#x27;</span>:
                    <span style="color:#75715E"># close last occurrence of tag in active stack (search right-to-left)</span>
                    <span style="color:#FF0000">for</span> j <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">active</span>) - <span style="color:#FDFD6A">1</span>, -<span style="color:#FDFD6A">1</span>, -<span style="color:#FDFD6A">1</span>):
                        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">active</span>[j] == <span style="color:#8A2BE2">tag</span>:
                            <span style="color:#75715E"># close tags in reverse order until that tag is closed</span>
                            <span style="color:#FF0000">for</span> k <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">active</span>) - <span style="color:#FDFD6A">1</span>, j - <span style="color:#FDFD6A">1</span>, -<span style="color:#FDFD6A">1</span>):
                                <span style="color:#8A2BE2">t</span> = <span style="color:#8A2BE2">active</span>.<span style="color:#33CCFF">pop</span>()
                                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;bold&#x27;</span>, <span style="color:#C9CA6B">&#x27;italic&#x27;</span>, <span style="color:#C9CA6B">&#x27;underline&#x27;</span>):
                                    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">t</span> == <span style="color:#C9CA6B">&#x27;bold&#x27;</span>:
                                        <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;/strong&gt;&#x27;</span>)
                                    elif <span style="color:#8A2BE2">t</span> == <span style="color:#C9CA6B">&#x27;italic&#x27;</span>:
                                        <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;/em&gt;&#x27;</span>)
                                    elif <span style="color:#8A2BE2">t</span> == <span style="color:#C9CA6B">&#x27;underline&#x27;</span>:
                                        <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;/u&gt;&#x27;</span>)
                                <span style="color:#FF0000">else</span>:
                                    <span style="color:#75715E"># syntax tags: close span</span>
                                    <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;/span&gt;&#x27;</span>)
                            <span style="color:#FF0000">break</span>
                elif kind == <span style="color:#C9CA6B">&#x27;start&#x27;</span>:
                    <span style="color:#75715E"># start tag: open HTML wrapper and push to active</span>
                    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;bold&#x27;</span>, <span style="color:#C9CA6B">&#x27;italic&#x27;</span>, <span style="color:#C9CA6B">&#x27;underline&#x27;</span>):
                        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">tag</span> == <span style="color:#C9CA6B">&#x27;bold&#x27;</span>:
                            <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;strong&gt;&#x27;</span>)
                        elif <span style="color:#8A2BE2">tag</span> == <span style="color:#C9CA6B">&#x27;italic&#x27;</span>:
                            <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;em&gt;&#x27;</span>)
                        elif <span style="color:#8A2BE2">tag</span> == <span style="color:#C9CA6B">&#x27;underline&#x27;</span>:
                            <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;u&gt;&#x27;</span>)
                        <span style="color:#8A2BE2">active</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">tag</span>)
                    <span style="color:#FF0000">else</span>:
                        <span style="color:#75715E"><span style="color:#ffffff;background-color:#B22222"># syntax tag -&gt; open span with inline color style (or background for todo</span>)</span>
                        <span style="color:#8A2BE2">color</span> = <span style="color:#8A2BE2">_TAG_COLOR_MAP</span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">tag</span>)
                        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">tag</span> == <span style="color:#C9CA6B">&#x27;todo&#x27;</span>:
                            <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(f<span style="color:#C9CA6B">&#x27;&lt;span style=&quot;color:<span style="color:#75715E">#ffffff;background-color:#B22222&quot;&gt;&#x27;</span></span>)
                        elif <span style="color:#8A2BE2">color</span>:
                            <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(f<span style="color:#C9CA6B">&#x27;&lt;span style=&quot;color:{color}&quot;&gt;&#x27;</span>)
                        <span style="color:#FF0000">else</span>:
                            <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;span&gt;&#x27;</span>)
                        <span style="color:#8A2BE2">active</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">tag</span>)

            <span style="color:#8A2BE2">next_pos</span> = <span style="color:#8A2BE2">positions</span>[<span style="color:#8A2BE2">i</span> + <span style="color:#FDFD6A">1</span>]
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">next_pos</span> &lt;= <span style="color:#8A2BE2">pos</span>:
                <span style="color:#FF0000">continue</span>
            <span style="color:#8A2BE2">seg</span> = <span style="color:#8A2BE2">content</span>[<span style="color:#8A2BE2">pos</span>:<span style="color:#8A2BE2">next_pos</span>]
            <span style="color:#75715E"># escape any HTML in the segment</span>
            <span style="color:#8A2BE2">seg_escaped</span> = html.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">seg</span>)
            <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">seg_escaped</span>)

        <span style="color:#75715E"># close any remaining open tags</span>
        <span style="color:#FF0000">while</span> <span style="color:#8A2BE2">active</span>:
            <span style="color:#8A2BE2">t</span> = <span style="color:#8A2BE2">active</span>.<span style="color:#33CCFF">pop</span>()
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;bold&#x27;</span>, <span style="color:#C9CA6B">&#x27;italic&#x27;</span>, <span style="color:#C9CA6B">&#x27;underline&#x27;</span>):
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">t</span> == <span style="color:#C9CA6B">&#x27;bold&#x27;</span>:
                    <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;/strong&gt;&#x27;</span>)
                elif <span style="color:#8A2BE2">t</span> == <span style="color:#C9CA6B">&#x27;italic&#x27;</span>:
                    <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;/em&gt;&#x27;</span>)
                elif <span style="color:#8A2BE2">t</span> == <span style="color:#C9CA6B">&#x27;underline&#x27;</span>:
                    <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;/u&gt;&#x27;</span>)
            <span style="color:#FF0000">else</span>:
                <span style="color:#8A2BE2">out_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#C9CA6B">&#x27;&lt;/span&gt;&#x27;</span>)

        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>.<span style="color:#33CCFF">join</span>(<span style="color:#8A2BE2">out_parts</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">try</span>:
            <span style="color:#FF0000">return</span> html.<span style="color:#33CCFF">escape</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>))
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>

<span style="color:#8A2BE2"><span style="color:#FF79C6">INI_PATH</span></span> = <span style="color:#C9CA6B">&#x27;config.ini&#x27;</span>
<span style="color:#8A2BE2">config</span> = configparser.<span style="color:#33CCFF">ConfigParser</span>()
<span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> os.<span style="color:#33CCFF">path</span>.<span style="color:#33CCFF">isfile</span>(<span style="color:#8A2BE2">INI_PATH</span>):
    <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">read_dict</span>(<span style="color:#8A2BE2">DEFAULT_CONFIG</span>)
    <span style="color:#FF0000">with</span> <span style="color:#9CDCFE">open</span>(<span style="color:#8A2BE2">INI_PATH</span>, <span style="color:#C9CA6B">&#x27;w&#x27;</span>) <span style="color:#FF0000">as</span> f:
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">write</span>(f)
<span style="color:#FF0000">else</span>:
    <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">read</span>(<span style="color:#8A2BE2">INI_PATH</span>)

<span style="color:#75715E"># MRU helper module (keeps GUI file code focused)</span>
<span style="color:#FF0000">try</span>:
    <span style="color:#FF0000">import</span> recent_files <span style="color:#FF0000">as</span> _rf_mod
<span style="color:#FF0000">except</span> Exception:
    <span style="color:#FF0000">import</span> recent_files <span style="color:#FF0000">as</span> _rf_mod  <span style="color:#75715E"># fallback if running as script</span>

<span style="color:#8A2BE2"><span style="color:#FF79C6">RECENT_MAX</span></span> = getattr(_rf_mod, <span style="color:#C9CA6B">&#x27;RECENT_MAX&#x27;</span>, <span style="color:#FDFD6A">10</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">load_recent_files</span>():
    <span style="color:#FF0000">return</span> _rf_mod.<span style="color:#FFA500"><span style="color:#33CCFF">load_recent_files</span></span>(<span style="color:#8A2BE2">config</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">save_recent_files</span>(lst):
    <span style="color:#FF0000">return</span> _rf_mod.<span style="color:#FFA500"><span style="color:#33CCFF">save_recent_files</span></span>(<span style="color:#8A2BE2">config</span>, <span style="color:#8A2BE2">INI_PATH</span>, lst)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">add_recent_file</span>(path):
    <span style="color:#FF0000">return</span> _rf_mod.<span style="color:#FFA500"><span style="color:#33CCFF">add_recent_file</span></span>(<span style="color:#8A2BE2">config</span>, <span style="color:#8A2BE2">INI_PATH</span>, path,
                                   <span style="color:#8A2BE2">on_update</span>=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">refresh_recent_menu</span>(),
                                   <span style="color:#8A2BE2">max_items</span>=<span style="color:#8A2BE2">RECENT_MAX</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">clear_recent_files</span>():
    <span style="color:#FF0000">return</span> _rf_mod.<span style="color:#FFA500"><span style="color:#33CCFF">clear_recent_files</span></span>(<span style="color:#8A2BE2">config</span>, <span style="color:#8A2BE2">INI_PATH</span>,
                                      <span style="color:#8A2BE2">on_update</span>=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">refresh_recent_menu</span>())


<span style="color:#FF0000">def</span> <span style="color:#FFA500">open_recent_file</span>(path: <span style="color:#9CDCFE">str</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Open a recent file (called from recent menu).&quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">with</span> <span style="color:#9CDCFE">open</span>(path, <span style="color:#C9CA6B">&#x27;r&#x27;</span>, errors=<span style="color:#C9CA6B">&#x27;replace&#x27;</span>) <span style="color:#FF0000">as</span> fh:
            <span style="color:#8A2BE2">raw</span> = fh.<span style="color:#33CCFF">read</span>()
            <span style="color:#8A2BE2">content</span>, <span style="color:#8A2BE2">meta</span> = <span style="color:#FFA500">_extract_header_and_meta</span>(<span style="color:#8A2BE2">raw</span>)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">content</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">f&quot;&#x27;{path}&#x27; opened successfully!&quot;</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span> = path
        <span style="color:#FF0000">try</span>:
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_ML_AVAILABLE</span> <span style="color:#FF0000">and</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpen <span style="color:#FF0000">and</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loaded</span> <span style="color:#FF0000">and</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loading</span>:
                Thread(target=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">_start_model_load</span>(start_autocomplete=<span style="color:#9CDCFE">False</span>), daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

        <span style="color:#FFA500">add_recent_file</span>(path)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">meta</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">_apply_formatting_from_meta</span>(<span style="color:#8A2BE2">meta</span>))

        <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">updateSyntaxHighlighting</span></span>.<span style="color:#33CCFF">get</span>():
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInit</span></span>)
    <span style="color:#FF0000">except</span> Exception <span style="color:#FF0000">as</span> <span style="color:#8A2BE2">e</span>:
        messagebox.<span style="color:#33CCFF">showerror</span>(<span style="color:#C9CA6B">&quot;Error&quot;</span>, <span style="color:#9CDCFE">str</span>(<span style="color:#8A2BE2">e</span>))

<span style="color:#FF0000">def</span> <span style="color:#FFA500">_collect_all_tag_ranges</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Collect ranges for both formatting and syntax tags as absolute offsets.&quot;&quot;&quot;</span>
    <span style="color:#8A2BE2">tags_to_save</span> = (
        <span style="color:#75715E"># formatting tags</span>
        <span style="color:#C9CA6B">&#x27;bold&#x27;</span>, <span style="color:#C9CA6B">&#x27;italic&#x27;</span>, <span style="color:#C9CA6B">&#x27;underline&#x27;</span>, <span style="color:#C9CA6B">&#x27;all&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;underlineitalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;boldunderline&#x27;</span>, <span style="color:#C9CA6B">&#x27;bolditalic&#x27;</span>,
        <span style="color:#75715E"># syntax/highlight tags</span>
        <span style="color:#C9CA6B">&#x27;string&#x27;</span>, <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>, <span style="color:#C9CA6B">&#x27;comment&#x27;</span>, <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>, <span style="color:#C9CA6B">&#x27;def&#x27;</span>, <span style="color:#C9CA6B">&#x27;number&#x27;</span>, <span style="color:#C9CA6B">&#x27;variable&#x27;</span>,
        <span style="color:#C9CA6B">&#x27;decorator&#x27;</span>, <span style="color:#C9CA6B">&#x27;class_name&#x27;</span>, <span style="color:#C9CA6B">&#x27;constant&#x27;</span>, <span style="color:#C9CA6B">&#x27;attribute&#x27;</span>, <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>, <span style="color:#C9CA6B">&#x27;todo&#x27;</span>
    )
    <span style="color:#8A2BE2">data</span> = {}
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">tags_to_save</span>:
            <span style="color:#8A2BE2">ranges</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#8A2BE2">tag</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">ranges</span>:
                <span style="color:#FF0000">continue</span>
            <span style="color:#8A2BE2">arr</span> = []
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">ranges</span>), <span style="color:#FDFD6A">2</span>):
                <span style="color:#8A2BE2">s</span> = <span style="color:#8A2BE2">ranges</span>[<span style="color:#8A2BE2">i</span>]
                <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">ranges</span>[<span style="color:#8A2BE2">i</span> + <span style="color:#FDFD6A">1</span>]
                <span style="color:#75715E"># compute char offsets relative to buffer start</span>
                <span style="color:#8A2BE2">start</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">s</span>))
                <span style="color:#8A2BE2">end</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">e</span>))
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">end</span> &gt; <span style="color:#8A2BE2">start</span>:
                    <span style="color:#8A2BE2">arr</span>.<span style="color:#33CCFF">append</span>([<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>])
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">arr</span>:
                <span style="color:#8A2BE2">data</span>[<span style="color:#8A2BE2">tag</span>] = <span style="color:#8A2BE2">arr</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>
    <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">data</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_serialize_tags</span>(tags_dict):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Return header string (commented base64 JSON) for provided tags dict, or &#x27;&#x27; if empty.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> tags_dict:
            <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>
        <span style="color:#8A2BE2">meta</span> = {<span style="color:#C9CA6B">&#x27;version&#x27;</span>: <span style="color:#FDFD6A">1</span>, <span style="color:#C9CA6B">&#x27;tags&#x27;</span>: tags_dict}
        <span style="color:#8A2BE2">b64</span> = base64.<span style="color:#33CCFF">b64encode</span>(json.<span style="color:#33CCFF">dumps</span>(<span style="color:#8A2BE2">meta</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">encode</span></span>(<span style="color:#C9CA6B">&#x27;utf-8&#x27;</span>)).<span style="color:#8A2BE2"><span style="color:#33CCFF">decode</span></span>(<span style="color:#C9CA6B">&#x27;ascii&#x27;</span>)
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&quot;<span style="color:#75715E"># ---SIMPLEEDIT-META-BEGIN---\n# &quot;</span></span> + b64 + <span style="color:#C9CA6B">&quot;\n# ---SIMPLEEDIT-META-END---\n\n&quot;</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_parse_simple_markdown</span>(md_text):
    <span style="color:#C9CA6B">&quot;&quot;&quot;
    Very small markdown parser to extract bold/italic/underline markers and return plain text
    plus a tags dict compatible with _apply_formatting_from_meta (i.e. {tag: [[start,end], ...]}).
    Supports: ***bolditalic***, **bold**, *italic*, and &lt;u&gt;underline&lt;/u&gt;.
    This is intentionally simple and not a full markdown implementation.
    &quot;&quot;&quot;</span>
    <span style="color:#8A2BE2">tags</span> = {<span style="color:#C9CA6B">&#x27;bold&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;italic&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;underline&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;bolditalic&#x27;</span>: []}
    <span style="color:#8A2BE2">plain_parts</span> = []
    <span style="color:#8A2BE2">last</span> = <span style="color:#FDFD6A">0</span>
    <span style="color:#8A2BE2">out_index</span> = <span style="color:#FDFD6A">0</span>

    <span style="color:#75715E"># pattern captures groups: g1=***text***, g2=**text**, g3=*text*, g4=&lt;u&gt;text&lt;/u&gt;</span>
    <span style="color:#8A2BE2">pattern</span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\*\*\*([^\*]+?)\*\*\*|\*\*([^\*]+?)\*\*|\*([^\*]+?)\*|&lt;u&gt;(.*?)&lt;/u&gt;&#x27;</span>, re.<span style="color:#33CCFF">DOTALL</span>)
    <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">pattern</span>.<span style="color:#33CCFF">finditer</span>(md_text):
        <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
        <span style="color:#75715E"># append intermediate plain text</span>
        <span style="color:#8A2BE2">seg</span> = md_text[<span style="color:#8A2BE2">last</span>:<span style="color:#8A2BE2">start</span>]
        <span style="color:#8A2BE2">plain_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">seg</span>)
        <span style="color:#8A2BE2">out_index</span> += <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">seg</span>)
        <span style="color:#75715E"># choose which group matched and its content</span>
        <span style="color:#8A2BE2">content</span> = <span style="color:#9CDCFE">None</span>
        <span style="color:#8A2BE2">tag_name</span> = <span style="color:#9CDCFE">None</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">is</span> <span style="color:#FF0000">not</span> <span style="color:#9CDCFE">None</span>:
            <span style="color:#8A2BE2">content</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#8A2BE2">tag_name</span> = <span style="color:#C9CA6B">&#x27;bolditalic&#x27;</span>
        elif <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">2</span>) <span style="color:#FF0000">is</span> <span style="color:#FF0000">not</span> <span style="color:#9CDCFE">None</span>:
            <span style="color:#8A2BE2">content</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">2</span>)
            <span style="color:#8A2BE2">tag_name</span> = <span style="color:#C9CA6B">&#x27;bold&#x27;</span>
        elif <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">3</span>) <span style="color:#FF0000">is</span> <span style="color:#FF0000">not</span> <span style="color:#9CDCFE">None</span>:
            <span style="color:#8A2BE2">content</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">3</span>)
            <span style="color:#8A2BE2">tag_name</span> = <span style="color:#C9CA6B">&#x27;italic&#x27;</span>
        elif <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">4</span>) <span style="color:#FF0000">is</span> <span style="color:#FF0000">not</span> <span style="color:#9CDCFE">None</span>:
            <span style="color:#8A2BE2">content</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">4</span>)
            <span style="color:#8A2BE2">tag_name</span> = <span style="color:#C9CA6B">&#x27;underline&#x27;</span>
        <span style="color:#FF0000">else</span>:
            <span style="color:#8A2BE2">content</span> = md_text[<span style="color:#8A2BE2">start</span>:<span style="color:#8A2BE2">end</span>]
            <span style="color:#8A2BE2">tag_name</span> = <span style="color:#9CDCFE">None</span>

        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">content</span> <span style="color:#FF0000">is</span> <span style="color:#9CDCFE">None</span>:
            <span style="color:#8A2BE2">content</span> = <span style="color:#C9CA6B">&#x27;&#x27;</span>
        <span style="color:#75715E"># append content and record tag range</span>
        <span style="color:#8A2BE2">plain_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">content</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">tag_name</span>:
            <span style="color:#8A2BE2">tags</span>.<span style="color:#33CCFF">setdefault</span>(<span style="color:#8A2BE2">tag_name</span>, []).<span style="color:#33CCFF">append</span>([<span style="color:#8A2BE2">out_index</span>, <span style="color:#8A2BE2">out_index</span> + <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">content</span>)])
        <span style="color:#8A2BE2">out_index</span> += <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">content</span>)
        <span style="color:#8A2BE2">last</span> = <span style="color:#8A2BE2">end</span>

    <span style="color:#75715E"># append tail</span>
    <span style="color:#8A2BE2">tail</span> = md_text[<span style="color:#8A2BE2">last</span>:]
    <span style="color:#8A2BE2">plain_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">tail</span>)
    <span style="color:#8A2BE2">plain_text</span> = <span style="color:#C9CA6B">&#x27;&#x27;</span>.<span style="color:#33CCFF">join</span>(<span style="color:#8A2BE2">plain_parts</span>)

    <span style="color:#75715E"># remove empty tag lists</span>
    <span style="color:#8A2BE2">tags</span> = {k: v <span style="color:#FF0000">for</span> k, v <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">tags</span>.<span style="color:#33CCFF">items</span>() <span style="color:#FF0000">if</span> v}
    <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">plain_text</span>, <span style="color:#8A2BE2">tags</span>

<span style="color:#FF0000">def</span> <span style="color:#FFA500">refresh_recent_menu</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Rebuild the `recentMenu` items from persisted MRU list.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">recentMenu</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#8A2BE2">files</span> = <span style="color:#FFA500">load_recent_files</span>()
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">files</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">recentMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&quot;(no recent files)&quot;</span>, state=<span style="color:#C9CA6B">&#x27;disabled&#x27;</span>)
            <span style="color:#FF0000">return</span>

        <span style="color:#FF0000">for</span> path <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">files</span>:
            <span style="color:#8A2BE2">label</span> = os.<span style="color:#33CCFF">path</span>.<span style="color:#33CCFF">basename</span>(path) <span style="color:#FF0000">or</span> path
            <span style="color:#FFFF00"><span style="color:#8A2BE2">recentMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#8A2BE2">label</span>, command=<span style="color:#FF0000">lambda</span> p=path: <span style="color:#FFA500">open_recent_file</span>(p))

        <span style="color:#FFFF00"><span style="color:#8A2BE2">recentMenu</span></span>.<span style="color:#33CCFF">add_separator</span>()
        <span style="color:#FFFF00"><span style="color:#8A2BE2">recentMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&quot;Clear Recent&quot;</span>, command=<span style="color:#FFA500">clear_recent_files</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#75715E"># keep UI resilient to errors</span>
        <span style="color:#FF0000">pass</span>


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Config values (typed)</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;fontName&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;fontSize&#x27;</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">fontColor</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;fontColor&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColor</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;backgroundColor&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">undoSetting</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;undoSetting&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColor</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;cursorColor&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">aiMaxContext</span></span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;aiMaxContext&#x27;</span>))
<span style="color:#8A2BE2">temperature</span> = float(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;temperature&#x27;</span>))
<span style="color:#8A2BE2">top_k</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;top_k&#x27;</span>))
<span style="color:#8A2BE2">seed</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;seed&#x27;</span>))

random.<span style="color:#8A2BE2"><span style="color:#33CCFF">seed</span></span>(<span style="color:#8A2BE2">seed</span>)
<span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_ML_AVAILABLE</span>:
    torch.<span style="color:#33CCFF">manual_seed</span>(<span style="color:#8A2BE2">seed</span> + random.<span style="color:#33CCFF">randint</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FDFD6A">9999</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpen = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;loadAIOnOpen&#x27;</span>, fallback=<span style="color:#9CDCFE">False</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNew = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&#x27;Section1&#x27;</span>, <span style="color:#C9CA6B">&#x27;loadAIOnNew&#x27;</span>, fallback=<span style="color:#9CDCFE">False</span>)

<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Optional model init (lazy-loaded on user request)</span>
<span style="color:#8A2BE2">model</span> = <span style="color:#9CDCFE">None</span>
<span style="color:#8A2BE2">original_model</span> = <span style="color:#9CDCFE">None</span>
<span style="color:#8A2BE2">encode</span> = <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">s</span>: []
<span style="color:#8A2BE2">decode</span> = <span style="color:#FF0000">lambda</span> l: <span style="color:#C9CA6B">&quot;&quot;</span>
<span style="color:#8A2BE2">_model_loading</span> = <span style="color:#9CDCFE">False</span>
<span style="color:#8A2BE2">_model_loaded</span> = <span style="color:#9CDCFE">False</span>

<span style="color:#FF0000">def</span> <span style="color:#FFA500">unload_model</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Unload the AI model and update UI. Visible only when a model is loaded.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">global</span> <span style="color:#8A2BE2">model</span>, <span style="color:#8A2BE2">original_model</span>, <span style="color:#8A2BE2">encode</span>, <span style="color:#8A2BE2">decode</span>, <span style="color:#8A2BE2">_model_loaded</span>, <span style="color:#8A2BE2">_model_loading</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loaded</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#75715E"># Clear references so Python can GC model memory</span>
        <span style="color:#8A2BE2">model</span> = <span style="color:#9CDCFE">None</span>
        <span style="color:#8A2BE2">original_model</span> = <span style="color:#9CDCFE">None</span>
        <span style="color:#8A2BE2">encode</span> = <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">s</span>: []
        <span style="color:#8A2BE2">decode</span> = <span style="color:#FF0000">lambda</span> l: <span style="color:#C9CA6B">&quot;&quot;</span>
        <span style="color:#8A2BE2">_model_loaded</span> = <span style="color:#9CDCFE">False</span>
        <span style="color:#8A2BE2">_model_loading</span> = <span style="color:#9CDCFE">False</span>

        <span style="color:#75715E"># UI updates must run on main thread</span>
        <span style="color:#FF0000">def</span> <span style="color:#FFA500">ui_updates</span>():
            <span style="color:#FF0000">try</span>:
                <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;AI model unloaded.&quot;</span>
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#FF0000">pass</span>
            <span style="color:#FF0000">try</span>:
                <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonA</span></span>I.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#8A2BE2">_AI_BUTTON_DEFAULT_TEXT</span>)
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#FF0000">pass</span>
            <span style="color:#FF0000">try</span>:
                <span style="color:#75715E"># hide unload button</span>
                <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonUnload</span></span>.<span style="color:#33CCFF">pack_forget</span>()
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#FF0000">pass</span>
            <span style="color:#FF0000">try</span>:
                <span style="color:#75715E"># clear params label</span>
                <span style="color:#FFFF00"><span style="color:#8A2BE2">paramsLabel</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">&quot;&quot;</span>)
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#FF0000">pass</span>

        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFA500">ui_updates</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_start_model_load</span>(start_autocomplete: bool = <span style="color:#9CDCFE">False</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Load model in a background thread and show a progress popup.
    If start_autocomplete is True, start `python_ai_autocomplete` after load.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">global</span> <span style="color:#8A2BE2">model</span>, <span style="color:#8A2BE2">original_model</span>, <span style="color:#8A2BE2">encode</span>, <span style="color:#8A2BE2">decode</span>, <span style="color:#8A2BE2">_model_loading</span>, <span style="color:#8A2BE2">_model_loaded</span>

    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_model_loaded</span> <span style="color:#FF0000">or</span> <span style="color:#8A2BE2">_model_loading</span>:
        <span style="color:#FF0000">return</span>

    <span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>, <span style="color:#8A2BE2">status</span> = <span style="color:#FFA500">show_progress_popup</span>(<span style="color:#C9CA6B">&quot;Loading AI model&quot;</span>, determinate=<span style="color:#9CDCFE">True</span>)
    <span style="color:#8A2BE2">status</span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Initializing...&quot;</span>

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">worker</span>():
        <span style="color:#75715E"># Ensure assignments update module-level variables</span>
        <span style="color:#FF0000">global</span> <span style="color:#8A2BE2">model</span>, <span style="color:#8A2BE2">original_model</span>, <span style="color:#8A2BE2">encode</span>, <span style="color:#8A2BE2">decode</span>, <span style="color:#8A2BE2">_model_loading</span>, <span style="color:#8A2BE2">_model_loaded</span>
        <span style="color:#FF0000">nonlocal</span> <span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>, <span style="color:#8A2BE2">status</span>
        <span style="color:#FF0000">try</span>:
            <span style="color:#8A2BE2">_model_loading</span> = <span style="color:#9CDCFE">True</span>
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">status</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">&quot;Loading checkpoint...&quot;</span>))
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">pb</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(value=<span style="color:#FDFD6A">10</span>))
            <span style="color:#FF0000">try</span>:
                <span style="color:#8A2BE2">init_from</span> = <span style="color:#C9CA6B">&#x27;resume&#x27;</span>
                <span style="color:#8A2BE2">out_dir</span> = <span style="color:#C9CA6B">&#x27;out&#x27;</span>
                <span style="color:#8A2BE2">ckpt_path</span> = os.<span style="color:#33CCFF">path</span>.<span style="color:#33CCFF">join</span>(<span style="color:#8A2BE2">out_dir</span>, <span style="color:#C9CA6B">&#x27;ckpt.pt&#x27;</span>)
                <span style="color:#8A2BE2">checkpoint</span> = torch.<span style="color:#33CCFF">load</span>(<span style="color:#8A2BE2">ckpt_path</span>, map_location=<span style="color:#C9CA6B">&#x27;cpu&#x27;</span>, weights_only=<span style="color:#9CDCFE">True</span>)
            <span style="color:#FF0000">except</span> Exception <span style="color:#FF0000">as</span> ex:
                <span style="color:#FF0000">raise</span> RuntimeError(<span style="color:#C9CA6B">f&quot;Failed to load checkpoint: {ex}&quot;</span>)

            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">pb</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(value=<span style="color:#FDFD6A">30</span>))
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">status</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">&quot;Constructing model...&quot;</span>))
            <span style="color:#FF0000">try</span>:
                <span style="color:#8A2BE2">gptconf</span> = GPTConfig(**<span style="color:#8A2BE2">checkpoint</span>[<span style="color:#C9CA6B">&#x27;model_args&#x27;</span>])
                <span style="color:#8A2BE2">model_local</span> = GPT(<span style="color:#8A2BE2">gptconf</span>)
                <span style="color:#8A2BE2">state_dict</span> = <span style="color:#8A2BE2">checkpoint</span>[<span style="color:#C9CA6B">&#x27;model&#x27;</span>]
                <span style="color:#8A2BE2">unwanted_prefix</span> = <span style="color:#C9CA6B">&#x27;_orig_mod.&#x27;</span>
                <span style="color:#FF0000">for</span> k <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">list</span>(<span style="color:#8A2BE2">state_dict</span>.<span style="color:#33CCFF">keys</span>()):
                    <span style="color:#FF0000">if</span> k.<span style="color:#33CCFF">startswith</span>(<span style="color:#8A2BE2">unwanted_prefix</span>):
                        <span style="color:#8A2BE2">state_dict</span>[k[<span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">unwanted_prefix</span>):]] = <span style="color:#8A2BE2">state_dict</span>.<span style="color:#33CCFF">pop</span>(k)
                <span style="color:#8A2BE2">model_local</span>.<span style="color:#33CCFF">load_state_dict</span>(<span style="color:#8A2BE2">state_dict</span>)
                <span style="color:#8A2BE2">model_local</span>.<span style="color:#33CCFF">eval</span>()
                <span style="color:#8A2BE2">model_local</span>.<span style="color:#33CCFF">to</span>(<span style="color:#C9CA6B">&#x27;cpu&#x27;</span>)
            <span style="color:#FF0000">except</span> Exception <span style="color:#FF0000">as</span> ex:
                <span style="color:#FF0000">raise</span> RuntimeError(<span style="color:#C9CA6B">f&quot;Failed to construct/load model state: {ex}&quot;</span>)

            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">pb</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(value=<span style="color:#FDFD6A">60</span>))
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">status</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">&quot;Compiling model (may take a moment)...&quot;</span>))
            <span style="color:#FF0000">try</span>:
                <span style="color:#75715E"># preserve original for fallback</span>
                <span style="color:#8A2BE2">original_model</span> = <span style="color:#8A2BE2">model_local</span>
                <span style="color:#FF0000">if</span> sys.<span style="color:#33CCFF">platform</span> == <span style="color:#C9CA6B">&quot;win32&quot;</span> <span style="color:#FF0000">and</span> shutil.<span style="color:#33CCFF">which</span>(<span style="color:#C9CA6B">&quot;cl&quot;</span>) <span style="color:#FF0000">is</span> <span style="color:#9CDCFE">None</span>:
                    <span style="color:#FF0000">try</span>:
                        <span style="color:#8A2BE2">compiled</span> = torch.<span style="color:#33CCFF">compile</span>(<span style="color:#8A2BE2">model_local</span>, backend=<span style="color:#C9CA6B">&quot;eager&quot;</span>, mode=<span style="color:#C9CA6B">&quot;reduce-overhead&quot;</span>)
                    <span style="color:#FF0000">except</span> Exception:
                        <span style="color:#8A2BE2">compiled</span> = <span style="color:#8A2BE2">model_local</span>
                <span style="color:#FF0000">else</span>:
                    <span style="color:#FF0000">try</span>:
                        <span style="color:#8A2BE2">compiled</span> = torch.<span style="color:#33CCFF">compile</span>(<span style="color:#8A2BE2">model_local</span>, mode=<span style="color:#C9CA6B">&quot;reduce-overhead&quot;</span>)
                    <span style="color:#FF0000">except</span> Exception:
                        <span style="color:#8A2BE2">compiled</span> = <span style="color:#8A2BE2">model_local</span>
                <span style="color:#8A2BE2">model</span> = <span style="color:#8A2BE2">compiled</span>
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#75715E"># if compile fails, keep the eager model</span>
                <span style="color:#8A2BE2">model</span> = <span style="color:#8A2BE2">model_local</span>

            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">pb</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(value=<span style="color:#FDFD6A">80</span>))
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">status</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">&quot;Initializing tokenizer...&quot;</span>))
            <span style="color:#FF0000">try</span>:
                <span style="color:#8A2BE2">enc</span> = tiktoken.<span style="color:#33CCFF">get_encoding</span>(<span style="color:#C9CA6B">&quot;gpt2&quot;</span>)
                <span style="color:#8A2BE2">encode</span> = <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">s</span>: <span style="color:#8A2BE2">enc</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">encode</span></span>(<span style="color:#8A2BE2">s</span>, allowed_special={<span style="color:#C9CA6B">&quot;&lt;|endoftext|&gt;&quot;</span>})
                <span style="color:#8A2BE2">decode</span> = <span style="color:#FF0000">lambda</span> l: <span style="color:#8A2BE2">enc</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">decode</span></span>(l)
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#8A2BE2">encode</span> = <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">s</span>: []
                <span style="color:#8A2BE2">decode</span> = <span style="color:#FF0000">lambda</span> l: <span style="color:#C9CA6B">&quot;&quot;</span>

            <span style="color:#8A2BE2">_model_loaded</span> = <span style="color:#9CDCFE">True</span>
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">&quot;AI model loaded.&quot;</span>))
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#8A2BE2">pb</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(value=<span style="color:#FDFD6A">100</span>))

            <span style="color:#75715E"># update UI: compute initial context token count on main thread (safe access to textArea)</span>
            <span style="color:#FF0000">def</span> <span style="color:#FFA500">set_loaded_ui</span>():
                <span style="color:#FF0000">try</span>:
                    <span style="color:#75715E"># determine selection / context same as autocomplete does</span>
                    <span style="color:#FF0000">try</span>:
                        <span style="color:#8A2BE2">ranges</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#C9CA6B">&quot;sel&quot;</span>)
                        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">ranges</span>:
                            <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span> = <span style="color:#8A2BE2">ranges</span>[<span style="color:#FDFD6A">0</span>], <span style="color:#8A2BE2">ranges</span>[<span style="color:#FDFD6A">1</span>]
                        <span style="color:#FF0000">else</span>:
                            <span style="color:#8A2BE2">start</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(f<span style="color:#C9CA6B">&#x27;insert-{aiMaxContext}c&#x27;</span>)
                            <span style="color:#8A2BE2">end</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>)
                    <span style="color:#FF0000">except</span> Exception:
                        <span style="color:#8A2BE2">start</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(f<span style="color:#C9CA6B">&#x27;insert-{aiMaxContext}c&#x27;</span>)
                        <span style="color:#8A2BE2">end</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>)
                    <span style="color:#FF0000">try</span>:
                        <span style="color:#8A2BE2">content</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)
                        <span style="color:#8A2BE2">n</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">encode</span>(<span style="color:#8A2BE2">content</span>)) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">encode</span> <span style="color:#FF0000">else</span> <span style="color:#FDFD6A">0</span>
                    <span style="color:#FF0000">except</span> Exception:
                        <span style="color:#8A2BE2">n</span> = <span style="color:#FDFD6A">0</span>
                    <span style="color:#FF0000">try</span>:
                        <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonA</span></span>I.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">f&quot;AI Autocomplete - ctx: {n}&quot;</span>)
                    <span style="color:#FF0000">except</span> Exception:
                        <span style="color:#FF0000">pass</span>
                    <span style="color:#FF0000">try</span>:
                        <span style="color:#75715E"># show unload button (only when model is loaded)</span>
                        <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonUnload</span></span>.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
                    <span style="color:#FF0000">except</span> Exception:
                        <span style="color:#FF0000">pass</span>
                    <span style="color:#FF0000">try</span>:
                        <span style="color:#75715E"># update params label</span>
                        <span style="color:#FFFF00"><span style="color:#8A2BE2">paramsLabel</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#FFA500">_get_model_param_text</span>())
                    <span style="color:#FF0000">except</span> Exception:
                        <span style="color:#FF0000">pass</span>
                <span style="color:#FF0000">except</span> Exception:
                    <span style="color:#FF0000">pass</span>

            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFA500">set_loaded_ui</span>)

        <span style="color:#FF0000">except</span> Exception <span style="color:#FF0000">as</span> <span style="color:#8A2BE2">e</span>:
            <span style="color:#8A2BE2">model</span> = <span style="color:#9CDCFE">None</span>
            <span style="color:#8A2BE2">original_model</span> = <span style="color:#9CDCFE">None</span>
            <span style="color:#8A2BE2">_model_loaded</span> = <span style="color:#9CDCFE">False</span>
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">f&quot;AI load error: {e}&quot;</span>))
        <span style="color:#FF0000">finally</span>:
            <span style="color:#8A2BE2">_model_loading</span> = <span style="color:#9CDCFE">False</span>
            <span style="color:#FF0000">try</span>:
                <span style="color:#FFA500">close_progress_popup</span>(<span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>)
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#FF0000">pass</span>

            <span style="color:#75715E"># if requested, automatically begin autocomplete after load</span>
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_model_loaded</span> <span style="color:#FF0000">and</span> start_autocomplete:
                <span style="color:#FF0000">try</span>:
                    Thread(target=<span style="color:#FFA500">python_ai_autocomplete</span>, daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()
                <span style="color:#FF0000">except</span> Exception:
                    <span style="color:#FF0000">pass</span>

    Thread(target=<span style="color:#FFA500">worker</span>, daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()



<span style="color:#FF0000">def</span> <span style="color:#FFA500">on_ai_button_click</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Handler bound to the AI toolbar button.
    If model is loaded -&gt; start autocomplete. If not loaded -&gt; load it (showing progress).&quot;&quot;&quot;</span>
    <span style="color:#FF0000">global</span> <span style="color:#8A2BE2">_model_loaded</span>, <span style="color:#8A2BE2">_model_loading</span>

    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_ML_AVAILABLE</span>:
        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;AI libraries not available.&quot;</span>
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>
        <span style="color:#FF0000">return</span>

    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_model_loaded</span>:
        <span style="color:#75715E"># Already loaded: run autocomplete in background to keep UI responsive</span>
        Thread(target=<span style="color:#FFA500">python_ai_autocomplete</span>, daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()
        <span style="color:#FF0000">return</span>

    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_model_loading</span>:
        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Model is already loading...&quot;</span>
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>
        <span style="color:#FF0000">return</span>

    <span style="color:#75715E"># Start load and immediately begin autocomplete after load completes</span>
    <span style="color:#FFA500">_start_model_load</span>(start_autocomplete=<span style="color:#9CDCFE">True</span>)

<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Helper utilities</span>
<span style="color:#75715E"># -------------------------</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">get_hex_color</span>(color_tuple):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Return a hex string from a colorchooser return value.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> color_tuple:
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&quot;&quot;</span>
    <span style="color:#FF0000">if</span> <span style="color:#9CDCFE">isinstance</span>(color_tuple, tuple) <span style="color:#FF0000">and</span> <span style="color:#9CDCFE">len</span>(color_tuple) &gt;= <span style="color:#FDFD6A">2</span>:
        <span style="color:#75715E"># colorchooser returns ((r,g,b), <span style="color:#C9CA6B">&#x27;#rrggbb&#x27;</span>)</span>
        <span style="color:#FF0000">return</span> color_tuple[<span style="color:#FDFD6A">1</span>]
    <span style="color:#8A2BE2">m</span> = re.<span style="color:#33CCFF">search</span>(r<span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#\w+&#x27;</span></span>, str(color_tuple))
    <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">0</span>) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">else</span> <span style="color:#C9CA6B">&quot;&quot;</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">selection_or_all</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Return a (start, end) range for the current selection or entire buffer.&quot;&quot;&quot;</span>
    <span style="color:#8A2BE2">ranges</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#C9CA6B">&quot;sel&quot;</span>)
    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">ranges</span>:
        <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">ranges</span>[<span style="color:#FDFD6A">0</span>], <span style="color:#8A2BE2">ranges</span>[<span style="color:#FDFD6A">1</span>]
    <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end-1c&quot;</span>


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Tkinter UI - create root and widgets</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span> = Tk()
<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">geometry</span>(<span style="color:#C9CA6B">&quot;800x600&quot;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">title</span></span>(<span style="color:#C9CA6B">&#x27;SimpleEdit&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span> = <span style="color:#C9CA6B">&quot;&quot;</span>

<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span> = Menu(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(menu=<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span>)

<span style="color:#75715E"># File/Edit menus</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span> = Menu(<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span>, tearoff=<span style="color:#9CDCFE">False</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">recentMenu</span></span> = Menu(<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span>, tearoff=<span style="color:#9CDCFE">False</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span> = Menu(<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span>, tearoff=<span style="color:#9CDCFE">False</span>)

<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span>.<span style="color:#33CCFF">add_cascade</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&quot;File&quot;</span>, menu=<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;New&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFFF00"><span style="color:#FFA500">newFile</span></span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_separator</span>()
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Open&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">open_file_threaded</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_cascade</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&quot;Open Recent&quot;</span>, menu=<span style="color:#FFFF00"><span style="color:#8A2BE2">recentMenu</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_separator</span>()
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Save&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">save_file</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Save As&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">save_file_as</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Save as Markdown&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">save_as_markdown</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_separator</span>()
<span style="color:#FFFF00"><span style="color:#8A2BE2">fileMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Exit&#x27;</span>, command=<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">destroy</span>)

<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span>.<span style="color:#33CCFF">add_cascade</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&quot;Edit&quot;</span>, menu=<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Cut&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">cut_selected_text</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Copy&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">copy_to_clipboard</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Paste&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">paste_from_clipboard</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>.<span style="color:#33CCFF">add_separator</span>()
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Undo&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">edit_undo</span>(), accelerator=<span style="color:#C9CA6B">&#x27;Ctrl+Z&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Redo&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">edit_redo</span>(), accelerator=<span style="color:#C9CA6B">&#x27;Ctrl+Y&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Find/Replace&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">open_find_replace</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">editMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&#x27;Go To Line&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">go_to_line</span>(), accelerator=<span style="color:#C9CA6B">&#x27;Ctrl+G&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;Control-g&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: <span style="color:#FFA500">go_to_line</span>())

<span style="color:#75715E"># Helper to return a nicely formatted parameter count string for the loaded model</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">_get_model_param_text</span>():
    <span style="color:#FF0000">try</span>:
        <span style="color:#75715E"># prefer the original_model (uncompiled) if available for accurate counting</span>
        <span style="color:#8A2BE2">m</span> = <span style="color:#8A2BE2">original_model</span> <span style="color:#FF0000">if</span> <span style="color:#C9CA6B">&#x27;original_model&#x27;</span> <span style="color:#FF0000">in</span> globals() <span style="color:#FF0000">and</span> <span style="color:#8A2BE2">original_model</span> <span style="color:#FF0000">is</span> <span style="color:#FF0000">not</span> <span style="color:#9CDCFE">None</span> <span style="color:#FF0000">else</span> <span style="color:#8A2BE2">model</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">is</span> <span style="color:#9CDCFE">None</span>:
            <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&quot;&quot;</span>
        <span style="color:#FF0000">if</span> hasattr(<span style="color:#8A2BE2">m</span>, <span style="color:#C9CA6B">&#x27;get_num_params&#x27;</span>):
            <span style="color:#8A2BE2">n</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">get_num_params</span>(non_embedding=<span style="color:#9CDCFE">True</span>))
        <span style="color:#FF0000">else</span>:
            <span style="color:#8A2BE2">n</span> = sum(p.<span style="color:#33CCFF">numel</span>() <span style="color:#FF0000">for</span> p <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">parameters</span>())
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">n</span> &lt;= <span style="color:#FDFD6A">0</span>:
            <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&quot;&quot;</span>
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">f&quot;Params: {n/1e6:.2f}M&quot;</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&quot;&quot;</span>

<span style="color:#75715E"># --- Symbols menu &amp; manager -------------------------------------------------</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">symbolsMenu</span></span> = Menu(<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span>, tearoff=<span style="color:#9CDCFE">False</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">menuBar</span></span>.<span style="color:#33CCFF">add_cascade</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&quot;Symbols&quot;</span>, menu=<span style="color:#FFFF00"><span style="color:#8A2BE2">symbolsMenu</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">symbolsMenu</span></span>.<span style="color:#33CCFF">add_command</span>(<span style="color:#8A2BE2">label</span>=<span style="color:#C9CA6B">&quot;Manage Symbols...&quot;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">open_symbols_manager</span>())


<span style="color:#FF0000">def</span> <span style="color:#FFA500">open_symbols_manager</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Small dialog to view/edit/remove/swap persisted vars/defs.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">global</span> persisted_vars, persisted_defs

    <span style="color:#8A2BE2">dlg</span> = Toplevel(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">title</span></span>(<span style="color:#C9CA6B">&quot;Manage Symbols&quot;</span>)
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">transient</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">grab_set</span>()
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">resizable</span>(<span style="color:#9CDCFE">False</span>, <span style="color:#9CDCFE">False</span>)

    <span style="color:#8A2BE2">container</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">dlg</span>, padding=<span style="color:#FDFD6A">10</span>)
    <span style="color:#8A2BE2">container</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">0</span>, sticky=<span style="color:#C9CA6B">&#x27;nsew&#x27;</span>)

    <span style="color:#75715E"># Vars column</span>
    ttk.<span style="color:#33CCFF">Label</span>(<span style="color:#8A2BE2">container</span>, text=<span style="color:#C9CA6B">&quot;Persisted Variables&quot;</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">0</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>)
    <span style="color:#8A2BE2">vars_frame</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">container</span>)
    <span style="color:#8A2BE2">vars_frame</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">1</span>, column=<span style="color:#FDFD6A">0</span>, padx=(<span style="color:#FDFD6A">0</span>, <span style="color:#FDFD6A">8</span>), sticky=<span style="color:#C9CA6B">&#x27;nsew&#x27;</span>)
    <span style="color:#8A2BE2">vars_lb</span> = Listbox(<span style="color:#8A2BE2">vars_frame</span>, selectmode=SINGLE, height=<span style="color:#FDFD6A">10</span>, exportselection=<span style="color:#9CDCFE">False</span>)
    <span style="color:#8A2BE2">vars_scroll</span> = ttk.<span style="color:#33CCFF">Scrollbar</span>(<span style="color:#8A2BE2">vars_frame</span>, orient=VERTICAL, command=<span style="color:#8A2BE2">vars_lb</span>.<span style="color:#33CCFF">yview</span>)
    <span style="color:#8A2BE2">vars_lb</span>.<span style="color:#33CCFF">configure</span>(yscrollcommand=<span style="color:#8A2BE2">vars_scroll</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>)
    <span style="color:#8A2BE2">vars_lb</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">0</span>, sticky=<span style="color:#C9CA6B">&#x27;nsew&#x27;</span>)
    <span style="color:#8A2BE2">vars_scroll</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;ns&#x27;</span>)
    <span style="color:#8A2BE2">vars_frame</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">0</span>, weight=<span style="color:#FDFD6A">1</span>)

    <span style="color:#75715E"># Defs column</span>
    ttk.<span style="color:#33CCFF">Label</span>(<span style="color:#8A2BE2">container</span>, text=<span style="color:#C9CA6B">&quot;Persisted Definitions (defs/classes)&quot;</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>)
    <span style="color:#8A2BE2">defs_frame</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">container</span>)
    <span style="color:#8A2BE2">defs_frame</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">1</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;nsew&#x27;</span>)
    <span style="color:#8A2BE2">defs_lb</span> = Listbox(<span style="color:#8A2BE2">defs_frame</span>, selectmode=SINGLE, height=<span style="color:#FDFD6A">10</span>, exportselection=<span style="color:#9CDCFE">False</span>)
    <span style="color:#8A2BE2">defs_scroll</span> = ttk.<span style="color:#33CCFF">Scrollbar</span>(<span style="color:#8A2BE2">defs_frame</span>, orient=VERTICAL, command=<span style="color:#8A2BE2">defs_lb</span>.<span style="color:#33CCFF">yview</span>)
    <span style="color:#8A2BE2">defs_lb</span>.<span style="color:#33CCFF">configure</span>(yscrollcommand=<span style="color:#8A2BE2">defs_scroll</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>)
    <span style="color:#8A2BE2">defs_lb</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">0</span>, sticky=<span style="color:#C9CA6B">&#x27;nsew&#x27;</span>)
    <span style="color:#8A2BE2">defs_scroll</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;ns&#x27;</span>)
    <span style="color:#8A2BE2">defs_frame</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">0</span>, weight=<span style="color:#FDFD6A">1</span>)

    <span style="color:#75715E"># populate lists</span>
    <span style="color:#FF0000">def</span> <span style="color:#FFA500">refresh_lists</span>():
        <span style="color:#8A2BE2">vars_lb</span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#8A2BE2">defs_lb</span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FF0000">for</span> v <span style="color:#FF0000">in</span> sorted(persisted_vars):
            <span style="color:#8A2BE2">vars_lb</span>.<span style="color:#33CCFF">insert</span>(END, v)
        <span style="color:#FF0000">for</span> d <span style="color:#FF0000">in</span> sorted(persisted_defs):
            <span style="color:#8A2BE2">defs_lb</span>.<span style="color:#33CCFF">insert</span>(END, d)
        <span style="color:#FFA500">_save_symbol_buffers</span>(persisted_vars, persisted_defs)

    <span style="color:#FFA500">refresh_lists</span>()

    <span style="color:#75715E"># utilities</span>
    <span style="color:#8A2BE2"><span style="color:#FF79C6">ID_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;^[A-Za-z_]\w*$&#x27;</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">_get_sel</span>(lb):
        <span style="color:#8A2BE2">sel</span> = lb.<span style="color:#33CCFF">curselection</span>()
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">sel</span>:
            <span style="color:#FF0000">return</span> <span style="color:#9CDCFE">None</span>, <span style="color:#9CDCFE">None</span>
        <span style="color:#8A2BE2">idx</span> = <span style="color:#8A2BE2">sel</span>[<span style="color:#FDFD6A">0</span>]
        <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">idx</span>, lb.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">idx</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">do_edit</span>(lb, src_set):
        <span style="color:#8A2BE2">idx</span>, <span style="color:#8A2BE2">name</span> = <span style="color:#FFA500">_get_sel</span>(lb)
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">name</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#8A2BE2">prompt</span> = <span style="color:#C9CA6B">f&quot;Edit identifier (current: {name})&quot;</span>
        <span style="color:#8A2BE2">new</span> = simpledialog.<span style="color:#33CCFF">askstring</span>(<span style="color:#C9CA6B">&quot;Edit symbol&quot;</span>, <span style="color:#8A2BE2">prompt</span>, initialvalue=<span style="color:#8A2BE2">name</span>, parent=<span style="color:#8A2BE2">dlg</span>)
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">new</span> <span style="color:#FF0000">or</span> <span style="color:#8A2BE2">new</span>.<span style="color:#33CCFF">strip</span>() == <span style="color:#C9CA6B">&quot;&quot;</span> <span style="color:#FF0000">or</span> <span style="color:#8A2BE2">new</span> == <span style="color:#8A2BE2">name</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#8A2BE2">new</span> = <span style="color:#8A2BE2">new</span>.<span style="color:#33CCFF">strip</span>()
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">ID_RE</span>.<span style="color:#FF0000"><span style="color:#33CCFF">match</span></span>(<span style="color:#8A2BE2">new</span>):
            messagebox.<span style="color:#33CCFF">showerror</span>(<span style="color:#C9CA6B">&quot;Invalid name&quot;</span>, <span style="color:#C9CA6B">&quot;Name must be a valid Python identifier.&quot;</span>, parent=<span style="color:#8A2BE2">dlg</span>)
            <span style="color:#FF0000">return</span>
        <span style="color:#75715E"># don&#x27;t allow duplicates across both buffers</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">new</span> <span style="color:#FF0000">in</span> persisted_vars <span style="color:#FF0000">or</span> <span style="color:#8A2BE2">new</span> <span style="color:#FF0000">in</span> persisted_defs:
            messagebox.<span style="color:#33CCFF">showerror</span>(<span style="color:#C9CA6B">&quot;Duplicate&quot;</span>, <span style="color:#C9CA6B">&quot;That identifier already exists.&quot;</span>, parent=<span style="color:#8A2BE2">dlg</span>)
            <span style="color:#FF0000">return</span>
        <span style="color:#75715E"># perform rename</span>
        <span style="color:#FF0000">try</span>:
            src_set.<span style="color:#33CCFF">discard</span>(<span style="color:#8A2BE2">name</span>)
            src_set.<span style="color:#FFA500"><span style="color:#33CCFF">add</span></span>(<span style="color:#8A2BE2">new</span>)
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">return</span>
        <span style="color:#FFA500">refresh_lists</span>()
        <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInitT</span></span>()

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">do_swap_from_vars</span>():
        <span style="color:#8A2BE2">idx</span>, <span style="color:#8A2BE2">name</span> = <span style="color:#FFA500">_get_sel</span>(<span style="color:#8A2BE2">vars_lb</span>)
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">name</span>:
            <span style="color:#FF0000">return</span>
        persisted_vars.<span style="color:#33CCFF">discard</span>(<span style="color:#8A2BE2">name</span>)
        persisted_defs.<span style="color:#FFA500"><span style="color:#33CCFF">add</span></span>(<span style="color:#8A2BE2">name</span>)
        <span style="color:#FFA500">refresh_lists</span>()
        <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInitT</span></span>()

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">do_swap_from_defs</span>():
        <span style="color:#8A2BE2">idx</span>, <span style="color:#8A2BE2">name</span> = <span style="color:#FFA500">_get_sel</span>(<span style="color:#8A2BE2">defs_lb</span>)
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">name</span>:
            <span style="color:#FF0000">return</span>
        persisted_defs.<span style="color:#33CCFF">discard</span>(<span style="color:#8A2BE2">name</span>)
        persisted_vars.<span style="color:#FFA500"><span style="color:#33CCFF">add</span></span>(<span style="color:#8A2BE2">name</span>)
        <span style="color:#FFA500">refresh_lists</span>()
        <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInitT</span></span>()

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">do_delete</span>(lb, src_set):
        <span style="color:#8A2BE2">idx</span>, <span style="color:#8A2BE2">name</span> = <span style="color:#FFA500">_get_sel</span>(lb)
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">name</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> messagebox.<span style="color:#33CCFF">askyesno</span>(<span style="color:#C9CA6B">&quot;Confirm&quot;</span>, <span style="color:#C9CA6B">f&quot;Delete &#x27;{name}&#x27;?&quot;</span>, parent=<span style="color:#8A2BE2">dlg</span>):
            <span style="color:#FF0000">return</span>
        src_set.<span style="color:#33CCFF">discard</span>(<span style="color:#8A2BE2">name</span>)
        <span style="color:#FFA500">refresh_lists</span>()
        <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInitT</span></span>()

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">do_clear_all</span>():
        <span style="color:#FF0000">if</span> messagebox.<span style="color:#33CCFF">askyesno</span>(<span style="color:#C9CA6B">&quot;Confirm&quot;</span>, <span style="color:#C9CA6B">&quot;Clear ALL persisted symbols?&quot;</span>, parent=<span style="color:#8A2BE2">dlg</span>):
            persisted_vars.<span style="color:#33CCFF">clear</span>()
            persisted_defs.<span style="color:#33CCFF">clear</span>()
            <span style="color:#FFA500">refresh_lists</span>()
            <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInitT</span></span>()

    <span style="color:#75715E"># action buttons for vars</span>
    <span style="color:#8A2BE2">btns_vars</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">container</span>)
    <span style="color:#8A2BE2">btns_vars</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">2</span>, column=<span style="color:#FDFD6A">0</span>, pady=(<span style="color:#FDFD6A">8</span>, <span style="color:#FDFD6A">0</span>), sticky=<span style="color:#C9CA6B">&#x27;ew&#x27;</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btns_vars</span>, text=<span style="color:#C9CA6B">&quot;Edit&quot;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">do_edit</span>(<span style="color:#8A2BE2">vars_lb</span>, persisted_vars)).<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">4</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btns_vars</span>, text=<span style="color:#C9CA6B">&quot;Swap â†’ Defs&quot;</span>, command=<span style="color:#FFA500">do_swap_from_vars</span>).<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">4</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btns_vars</span>, text=<span style="color:#C9CA6B">&quot;Delete&quot;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">do_delete</span>(<span style="color:#8A2BE2">vars_lb</span>, persisted_vars)).<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">4</span>)

    <span style="color:#75715E"># action buttons for defs</span>
    <span style="color:#8A2BE2">btns_defs</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">container</span>)
    <span style="color:#8A2BE2">btns_defs</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">2</span>, column=<span style="color:#FDFD6A">1</span>, pady=(<span style="color:#FDFD6A">8</span>, <span style="color:#FDFD6A">0</span>), sticky=<span style="color:#C9CA6B">&#x27;ew&#x27;</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btns_defs</span>, text=<span style="color:#C9CA6B">&quot;Edit&quot;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">do_edit</span>(<span style="color:#8A2BE2">defs_lb</span>, persisted_defs)).<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">4</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btns_defs</span>, text=<span style="color:#C9CA6B">&quot;Swap â†’ Vars&quot;</span>, command=<span style="color:#FFA500">do_swap_from_defs</span>).<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">4</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btns_defs</span>, text=<span style="color:#C9CA6B">&quot;Delete&quot;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">do_delete</span>(<span style="color:#8A2BE2">defs_lb</span>, persisted_defs)).<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">4</span>)

    <span style="color:#75715E"># bottom actions</span>
    <span style="color:#8A2BE2">action_frame</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">container</span>)
    <span style="color:#8A2BE2">action_frame</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">3</span>, column=<span style="color:#FDFD6A">0</span>, columnspan=<span style="color:#FDFD6A">2</span>, pady=(<span style="color:#FDFD6A">12</span>, <span style="color:#FDFD6A">0</span>), sticky=<span style="color:#C9CA6B">&#x27;ew&#x27;</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">action_frame</span>, text=<span style="color:#C9CA6B">&quot;Clear All&quot;</span>, command=<span style="color:#FFA500">do_clear_all</span>).<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">4</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">action_frame</span>, text=<span style="color:#C9CA6B">&quot;Close&quot;</span>, command=<span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">destroy</span>).<span style="color:#33CCFF">pack</span>(side=RIGHT, padx=<span style="color:#FDFD6A">4</span>)

    <span style="color:#75715E"># double-click to edit</span>
    <span style="color:#8A2BE2">vars_lb</span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&quot;&lt;Double-Button-1&gt;&quot;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: <span style="color:#FFA500">do_edit</span>(<span style="color:#8A2BE2">vars_lb</span>, persisted_vars))
    <span style="color:#8A2BE2">defs_lb</span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&quot;&lt;Double-Button-1&gt;&quot;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: <span style="color:#FFA500">do_edit</span>(<span style="color:#8A2BE2">defs_lb</span>, persisted_defs))

    <span style="color:#75715E"># keyboard shortcuts</span>
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;Delete&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: (<span style="color:#FFA500">do_delete</span>(<span style="color:#8A2BE2">vars_lb</span>, persisted_vars) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">vars_lb</span>.<span style="color:#33CCFF">curselection</span>() <span style="color:#FF0000">else</span> <span style="color:#FFA500">do_delete</span>(<span style="color:#8A2BE2">defs_lb</span>, persisted_defs)))
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;Escape&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">destroy</span>())

    <span style="color:#75715E"># ensure dialog centered</span>
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">update_idletasks</span>()
    <span style="color:#FFA500">center_window</span>(<span style="color:#8A2BE2">dlg</span>)


<span style="color:#75715E"># toolbar</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span> = Frame(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>, <span style="color:#8A2BE2">bg</span>=<span style="color:#C9CA6B">&#x27;blue&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>.<span style="color:#33CCFF">pack</span>(side=TOP, fill=X)

<span style="color:#75715E"># initialize line numbers canvas placeholder</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span> = <span style="color:#9CDCFE">None</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">init_line_numbers</span>():
    <span style="color:#FF0000">global</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span>
    <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span> <span style="color:#FF0000">is</span> <span style="color:#9CDCFE">None</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span> = Canvas(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>, width=<span style="color:#FDFD6A">40</span>, <span style="color:#8A2BE2">bg</span>=<span style="color:#C9CA6B">&#x27;black&#x27;</span>, highlightthickness=<span style="color:#FDFD6A">0</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span>.<span style="color:#33CCFF">pack</span>(side=LEFT, fill=Y)

<span style="color:#75715E"># status bar area (now a frame so we can place a button at lower-right)</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">statusFrame</span></span> = Frame(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">statusFrame</span></span>.<span style="color:#33CCFF">pack</span>(side=BOTTOM, fill=X)

<span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span> = Label(<span style="color:#FFFF00"><span style="color:#8A2BE2">statusFrame</span></span>, text=<span style="color:#C9CA6B">&quot;Ready&quot;</span>, bd=<span style="color:#FDFD6A">1</span>, relief=SUNKEN, anchor=W)
<span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>.<span style="color:#33CCFF">pack</span>(side=LEFT, fill=X, expand=<span style="color:#9CDCFE">True</span>)

<span style="color:#75715E"># Right-aligned params label (hidden/empty until model is loaded)</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">paramsLabel</span></span> = Label(<span style="color:#FFFF00"><span style="color:#8A2BE2">statusFrame</span></span>, text=<span style="color:#C9CA6B">&quot;&quot;</span>, bd=<span style="color:#FDFD6A">1</span>, relief=SUNKEN, anchor=E)
<span style="color:#FFFF00"><span style="color:#8A2BE2">paramsLabel</span></span>.<span style="color:#33CCFF">pack</span>(side=RIGHT, padx=<span style="color:#FDFD6A">6</span>)

<span style="color:#75715E"># placeholder for refresh button (created below near bindings so function names exist)</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">refreshSyntaxButton</span></span> = <span style="color:#9CDCFE">None</span>

<span style="color:#FFA500">init_line_numbers</span>()

<span style="color:#75715E"># Text area</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span> = Text(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>, insertbackground=<span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColor</span></span>, undo=<span style="color:#FFFF00"><span style="color:#8A2BE2">undoSetting</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">pack</span>(side=LEFT, fill=BOTH, expand=<span style="color:#9CDCFE">True</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>[<span style="color:#C9CA6B">&#x27;bg&#x27;</span>] = <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColor</span></span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>[<span style="color:#C9CA6B">&#x27;fg&#x27;</span>] = <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColor</span></span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>[<span style="color:#C9CA6B">&#x27;font&#x27;</span>] = (<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>)

<span style="color:#75715E"># scrollbar</span>
<span style="color:#8A2BE2">scroll</span> = Scrollbar(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>, command=<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">yview</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">configure</span>(yscrollcommand=<span style="color:#8A2BE2">scroll</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>)
<span style="color:#8A2BE2">scroll</span>.<span style="color:#33CCFF">pack</span>(side=RIGHT, fill=Y)



<span style="color:#75715E"># tag configs (extended)</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;number&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#FDFD6A&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;selfs&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;yellow&quot;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;variable&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#8A2BE2&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;decorator&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#66CDAA&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;class_name&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#FFB86B&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;constant&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#FF79C6&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;attribute&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#33ccff&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;builtin&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#9CDCFE&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;def&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;orange&quot;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;keyword&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;red&quot;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;string&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#C9CA6B&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;operator&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#AAAAAA&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;comment&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#75715E&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;todo&quot;</span>, foreground=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#ffffff&quot;</span></span>, background=<span style="color:#C9CA6B">&quot;#B22222&quot;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;bold&quot;</span>, font=(<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>, <span style="color:#C9CA6B">&quot;bold&quot;</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;italic&quot;</span>, font=(<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>, <span style="color:#C9CA6B">&quot;italic&quot;</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;underline&quot;</span>, font=(<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>, <span style="color:#C9CA6B">&quot;underline&quot;</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;all&quot;</span>, font=(<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>, <span style="color:#C9CA6B">&quot;bold&quot;</span>, <span style="color:#C9CA6B">&quot;italic&quot;</span>, <span style="color:#C9CA6B">&quot;underline&quot;</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;underlineitalic&quot;</span>, font=(<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>, <span style="color:#C9CA6B">&quot;italic&quot;</span>, <span style="color:#C9CA6B">&quot;underline&quot;</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;boldunderline&quot;</span>, font=(<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>, <span style="color:#C9CA6B">&quot;bold&quot;</span>, <span style="color:#C9CA6B">&quot;underline&quot;</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;bolditalic&quot;</span>, font=(<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>, <span style="color:#C9CA6B">&quot;bold&quot;</span>, <span style="color:#C9CA6B">&quot;italic&quot;</span>))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;currentLine&quot;</span>, background=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#222222&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;trailingWhitespace&quot;</span>, background=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#331111&quot;</span></span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_config</span>(<span style="color:#C9CA6B">&quot;find_match&quot;</span>, background=<span style="color:#C9CA6B">&quot;<span style="color:#75715E">#444444&quot;</span></span>, foreground=<span style="color:#C9CA6B">&#x27;white&#x27;</span>)
<span style="color:#75715E"># new variable tag</span>


<span style="color:#75715E"># precompiled regexes / keyword lists (module scope)</span>
<span style="color:#8A2BE2"><span style="color:#FF79C6">KEYWORDS</span></span> = [
    <span style="color:#C9CA6B">&#x27;if&#x27;</span>, <span style="color:#C9CA6B">&#x27;else&#x27;</span>, <span style="color:#C9CA6B">&#x27;while&#x27;</span>, <span style="color:#C9CA6B">&#x27;for&#x27;</span>, <span style="color:#C9CA6B">&#x27;return&#x27;</span>, <span style="color:#C9CA6B">&#x27;def&#x27;</span>, <span style="color:#C9CA6B">&#x27;from&#x27;</span>, <span style="color:#C9CA6B">&#x27;import&#x27;</span>, <span style="color:#C9CA6B">&#x27;class&#x27;</span>,
    <span style="color:#C9CA6B">&#x27;try&#x27;</span>, <span style="color:#C9CA6B">&#x27;except&#x27;</span>, <span style="color:#C9CA6B">&#x27;finally&#x27;</span>, <span style="color:#C9CA6B">&#x27;with&#x27;</span>, <span style="color:#C9CA6B">&#x27;as&#x27;</span>, <span style="color:#C9CA6B">&#x27;lambda&#x27;</span>, <span style="color:#C9CA6B">&#x27;in&#x27;</span>, <span style="color:#C9CA6B">&#x27;is&#x27;</span>, <span style="color:#C9CA6B">&#x27;not&#x27;</span>,
    <span style="color:#C9CA6B">&#x27;and&#x27;</span>, <span style="color:#C9CA6B">&#x27;or&#x27;</span>, <span style="color:#C9CA6B">&#x27;yield&#x27;</span>, <span style="color:#C9CA6B">&#x27;raise&#x27;</span>, <span style="color:#C9CA6B">&#x27;global&#x27;</span>, <span style="color:#C9CA6B">&#x27;nonlocal&#x27;</span>, <span style="color:#C9CA6B">&#x27;assert&#x27;</span>, <span style="color:#C9CA6B">&#x27;del&#x27;</span>,
    <span style="color:#C9CA6B">&#x27;async&#x27;</span>, <span style="color:#C9CA6B">&#x27;await&#x27;</span>, <span style="color:#C9CA6B">&#x27;pass&#x27;</span>, <span style="color:#C9CA6B">&#x27;break&#x27;</span>, <span style="color:#C9CA6B">&#x27;continue&#x27;</span>, <span style="color:#C9CA6B">&#x27;match&#x27;</span>, <span style="color:#C9CA6B">&#x27;case&#x27;</span>
]
<span style="color:#8A2BE2"><span style="color:#FF79C6">KEYWORD_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b(&#x27;</span> + r<span style="color:#C9CA6B">&#x27;|&#x27;</span>.<span style="color:#33CCFF">join</span>(map(re.<span style="color:#33CCFF">escape</span>, <span style="color:#8A2BE2">KEYWORDS</span>)) + r<span style="color:#C9CA6B">&#x27;)\b&#x27;</span>)

<span style="color:#75715E"># short list of builtins you want highlighted (extend as needed)</span>
<span style="color:#8A2BE2"><span style="color:#FF79C6">BUILTINS</span></span> = [<span style="color:#C9CA6B">&#x27;len&#x27;</span>, <span style="color:#C9CA6B">&#x27;range&#x27;</span>, <span style="color:#C9CA6B">&#x27;print&#x27;</span>, <span style="color:#C9CA6B">&#x27;open&#x27;</span>, <span style="color:#C9CA6B">&#x27;isinstance&#x27;</span>, <span style="color:#C9CA6B">&#x27;int&#x27;</span>, <span style="color:#C9CA6B">&#x27;str&#x27;</span>, <span style="color:#C9CA6B">&#x27;list&#x27;</span>, <span style="color:#C9CA6B">&#x27;dict&#x27;</span>, <span style="color:#C9CA6B">&#x27;set&#x27;</span>, <span style="color:#C9CA6B">&#x27;True&#x27;</span>, <span style="color:#C9CA6B">&#x27;False&#x27;</span>, <span style="color:#C9CA6B">&#x27;None&#x27;</span>]
<span style="color:#8A2BE2"><span style="color:#FF79C6">BUILTIN_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b(&#x27;</span> + r<span style="color:#C9CA6B">&#x27;|&#x27;</span>.<span style="color:#33CCFF">join</span>(map(re.<span style="color:#33CCFF">escape</span>, <span style="color:#8A2BE2">BUILTINS</span>)) + r<span style="color:#C9CA6B">&#x27;)\b&#x27;</span>)

<span style="color:#8A2BE2"><span style="color:#FF79C6">STRING_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(&quot;&quot;&quot;[\s\S]*?&quot;&quot;&quot;|\&#x27;</span>\<span style="color:#C9CA6B">&#x27;\&#x27;</span>[\<span style="color:#8A2BE2">s</span>\S]*?\<span style="color:#C9CA6B">&#x27;\&#x27;</span>\<span style="color:#C9CA6B">&#x27;|&quot;[^&quot;\n]*&quot;|&#x27;</span> + r<span style="color:#C9CA6B">&quot;&#x27;[^&#x27;\n]*&#x27;)&quot;</span>, re.<span style="color:#33CCFF">DOTALL</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">COMMENT_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#[^\n]*&#x27;</span></span>)
<span style="color:#75715E"># better number regex (precompile at module scope)</span>
<span style="color:#8A2BE2"><span style="color:#FF79C6">NUMBER_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(
    r<span style="color:#C9CA6B">&#x27;\b(?:0b[01_]+|0o[0-7_]+|0x[0-9A-Fa-f_]+|&#x27;</span>
    r<span style="color:#C9CA6B">&#x27;\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)(?:[jJ])?\b&#x27;</span>
)
<span style="color:#8A2BE2"><span style="color:#FF79C6">DECORATOR_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(?m)^\s*@([A-Za-z_]\w*)&#x27;</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">CLASS_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\bclass\s+([A-Za-z_]\w*)&#x27;</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">VAR_ASSIGN_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(?m)^[ \t]*([A-Za-z_]\w*)\s*=&#x27;</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">CONSTANT_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(?m)^[ \t]*([A-Z][_A-Z0-9]+)\s*=&#x27;</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">ATTRIBUTE_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\.([A-Za-z_]\w*)&#x27;</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">TODO_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;<span style="color:#75715E"><span style="color:#ffffff;background-color:#B22222">#.*\b(TODO|FIXME|NOTE</span>)\b&#x27;</span></span>, re.IGNORECASE)
<span style="color:#75715E"># extend `selfs` to include attribute names like <span style="color:#C9CA6B">&#x27;after&#x27;</span></span>
<span style="color:#8A2BE2"><span style="color:#FF79C6">SELFS_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b(?:[a-z])(?:[A-Z]?[a-z])*(?:[A-Z][a-z]*)|\b(self|root|after)\b&#x27;</span>)
<span style="color:#75715E"># variable annotation (may include optional assignment)</span>
<span style="color:#8A2BE2"><span style="color:#FF79C6">VAR_ANNOT_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(?m)^[ \t]*([A-Za-z_]\w*)\s*:\s*([^=\n]+)(?:=.*)?$&#x27;</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">FSTRING_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&quot;(?:[fF][rRuU]?|[rR][fF]?)(\&quot;</span>\<span style="color:#C9CA6B">&quot;\&quot;</span>[\<span style="color:#8A2BE2">s</span>\S]*?\<span style="color:#C9CA6B">&quot;\&quot;</span>\<span style="color:#C9CA6B">&quot;|&#x27;&#x27;&#x27;[\s\S]*?&#x27;&#x27;&#x27;|\&quot;</span>[^\<span style="color:#8A2BE2">n</span>\<span style="color:#C9CA6B">&quot;]*\&quot;</span>|<span style="color:#C9CA6B">&#x27;[^\\n&#x27;</span>]*&#x27;)&quot;, re.<span style="color:#33CCFF">DOTALL</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">DUNDER_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b__\w+__\b&#x27;</span>)
<span style="color:#8A2BE2"><span style="color:#FF79C6">CLASS_BASES_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(?m)^[ \t]*class\s+[A-Za-z_]\w*\s*\(([^)]*)\)&#x27;</span>)

<span style="color:#75715E"># treat matched group(1) as variable name (tag as <span style="color:#C9CA6B">&quot;variable&quot;</span> or <span style="color:#C9CA6B">&quot;annotation&quot;</span>)</span>

<span style="color:#75715E"># persisted symbol buffers (vars + defs) â€” load/save from config</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">_load_symbol_buffers</span>():
    <span style="color:#8A2BE2">vars_raw</span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Symbols&#x27;</span>, <span style="color:#C9CA6B">&#x27;vars&#x27;</span>, fallback=<span style="color:#C9CA6B">&#x27;&#x27;</span>)
    <span style="color:#8A2BE2">defs_raw</span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;Symbols&#x27;</span>, <span style="color:#C9CA6B">&#x27;defs&#x27;</span>, fallback=<span style="color:#C9CA6B">&#x27;&#x27;</span>)
    <span style="color:#8A2BE2">vars_set</span> = <span style="color:#9CDCFE">set</span>(<span style="color:#8A2BE2">x</span> <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">x</span> <span style="color:#FF0000">in</span> (v.<span style="color:#33CCFF">strip</span>() <span style="color:#FF0000">for</span> v <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">vars_raw</span>.<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;,&#x27;</span>)) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">x</span>)
    <span style="color:#8A2BE2">defs_set</span> = <span style="color:#9CDCFE">set</span>(<span style="color:#8A2BE2">x</span> <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">x</span> <span style="color:#FF0000">in</span> (d.<span style="color:#33CCFF">strip</span>() <span style="color:#FF0000">for</span> d <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">defs_raw</span>.<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;,&#x27;</span>)) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">x</span>)
    <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">vars_set</span>, <span style="color:#8A2BE2">defs_set</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_save_symbol_buffers</span>(<span style="color:#8A2BE2">vars_set</span>, <span style="color:#8A2BE2">defs_set</span>):
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">has_section</span>(<span style="color:#C9CA6B">&#x27;Symbols&#x27;</span>):
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">add_section</span>(<span style="color:#C9CA6B">&#x27;Symbols&#x27;</span>)
    <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&#x27;Symbols&#x27;</span>, <span style="color:#C9CA6B">&#x27;vars&#x27;</span>, <span style="color:#C9CA6B">&#x27;,&#x27;</span>.<span style="color:#33CCFF">join</span>(sorted(<span style="color:#8A2BE2">vars_set</span>)))
    <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&#x27;Symbols&#x27;</span>, <span style="color:#C9CA6B">&#x27;defs&#x27;</span>, <span style="color:#C9CA6B">&#x27;,&#x27;</span>.<span style="color:#33CCFF">join</span>(sorted(<span style="color:#8A2BE2">defs_set</span>)))
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">with</span> <span style="color:#9CDCFE">open</span>(<span style="color:#8A2BE2">INI_PATH</span>, <span style="color:#C9CA6B">&#x27;w&#x27;</span>) <span style="color:#FF0000">as</span> f:
            <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">write</span>(f)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>

<span style="color:#FF0000">def</span> <span style="color:#FFA500">_serialize_formatting</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Return header string (commented base64 JSON) for current non-syntax tags, or &#x27;&#x27; if no formatting.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">tags_to_save</span> = (<span style="color:#C9CA6B">&#x27;bold&#x27;</span>, <span style="color:#C9CA6B">&#x27;italic&#x27;</span>, <span style="color:#C9CA6B">&#x27;underline&#x27;</span>, <span style="color:#C9CA6B">&#x27;all&#x27;</span>,
                        <span style="color:#C9CA6B">&#x27;underlineitalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;boldunderline&#x27;</span>, <span style="color:#C9CA6B">&#x27;bolditalic&#x27;</span>)
        <span style="color:#8A2BE2">data</span> = {}
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">tags_to_save</span>:
            <span style="color:#8A2BE2">ranges</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#8A2BE2">tag</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">ranges</span>:
                <span style="color:#FF0000">continue</span>
            <span style="color:#8A2BE2">arr</span> = []
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">ranges</span>), <span style="color:#FDFD6A">2</span>):
                <span style="color:#8A2BE2">s</span> = <span style="color:#8A2BE2">ranges</span>[<span style="color:#8A2BE2">i</span>]
                <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">ranges</span>[<span style="color:#8A2BE2">i</span> + <span style="color:#FDFD6A">1</span>]
                <span style="color:#75715E"># compute char offsets relative to buffer start</span>
                <span style="color:#8A2BE2">start</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">s</span>))
                <span style="color:#8A2BE2">end</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">e</span>))
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">end</span> &gt; <span style="color:#8A2BE2">start</span>:
                    <span style="color:#8A2BE2">arr</span>.<span style="color:#33CCFF">append</span>([<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>])
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">arr</span>:
                <span style="color:#8A2BE2">data</span>[<span style="color:#8A2BE2">tag</span>] = <span style="color:#8A2BE2">arr</span>
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">data</span>:
            <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>
        <span style="color:#8A2BE2">meta</span> = {<span style="color:#C9CA6B">&#x27;version&#x27;</span>: <span style="color:#FDFD6A">1</span>, <span style="color:#C9CA6B">&#x27;tags&#x27;</span>: <span style="color:#8A2BE2">data</span>}
        <span style="color:#8A2BE2">b64</span> = base64.<span style="color:#33CCFF">b64encode</span>(json.<span style="color:#33CCFF">dumps</span>(<span style="color:#8A2BE2">meta</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">encode</span></span>(<span style="color:#C9CA6B">&#x27;utf-8&#x27;</span>)).<span style="color:#8A2BE2"><span style="color:#33CCFF">decode</span></span>(<span style="color:#C9CA6B">&#x27;ascii&#x27;</span>)
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&quot;<span style="color:#75715E"># ---SIMPLEEDIT-META-BEGIN---\n# &quot;</span></span> + b64 + <span style="color:#C9CA6B">&quot;\n# ---SIMPLEEDIT-META-END---\n\n&quot;</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_apply_formatting_from_meta</span>(<span style="color:#8A2BE2">meta</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Apply saved tag ranges (meta is dict with key &#x27;tags&#x27;) on the UI thread.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">tags</span> = <span style="color:#8A2BE2">meta</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;tags&#x27;</span>, {}) <span style="color:#FF0000">if</span> <span style="color:#9CDCFE">isinstance</span>(<span style="color:#8A2BE2">meta</span>, <span style="color:#9CDCFE">dict</span>) <span style="color:#FF0000">else</span> {}
        <span style="color:#75715E"># We need to ensure tags exist; tag_add will silently fail if indices out of range</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">tag</span>, <span style="color:#8A2BE2">ranges</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">tags</span>.<span style="color:#33CCFF">items</span>():
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">ranges</span>:
                <span style="color:#FF0000">try</span>:
                    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#8A2BE2">tag</span>, <span style="color:#C9CA6B">f&quot;1.0 + {int(start)}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {int(end)}c&quot;</span>)
                <span style="color:#FF0000">except</span> Exception:
                    <span style="color:#FF0000">pass</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_extract_header_and_meta</span>(<span style="color:#8A2BE2">raw</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;
    If raw begins with the SIMPLEEDIT header return (content, meta) where content
    is the visible file without header and meta is the parsed dict; otherwise return (raw, None).
    &quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">raw</span>.<span style="color:#33CCFF">startswith</span>(<span style="color:#C9CA6B">&quot;<span style="color:#75715E"># ---SIMPLEEDIT-META-BEGIN---&quot;</span></span>):
            <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">raw</span>, <span style="color:#9CDCFE">None</span>
        <span style="color:#8A2BE2">lines</span> = <span style="color:#8A2BE2">raw</span>.<span style="color:#33CCFF">splitlines</span>(<span style="color:#9CDCFE">True</span>)
        <span style="color:#8A2BE2">i</span> = <span style="color:#FDFD6A">0</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">lines</span>[<span style="color:#FDFD6A">0</span>].<span style="color:#33CCFF">strip</span>() != <span style="color:#C9CA6B">&quot;<span style="color:#75715E"># ---SIMPLEEDIT-META-BEGIN---&quot;</span></span>:
            <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">raw</span>, <span style="color:#9CDCFE">None</span>
        <span style="color:#8A2BE2">i</span> = <span style="color:#FDFD6A">1</span>
        <span style="color:#8A2BE2">b64_parts</span> = []
        <span style="color:#FF0000">while</span> <span style="color:#8A2BE2">i</span> &lt; <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">lines</span>) <span style="color:#FF0000">and</span> <span style="color:#8A2BE2">lines</span>[<span style="color:#8A2BE2">i</span>].<span style="color:#33CCFF">strip</span>() != <span style="color:#C9CA6B">&quot;<span style="color:#75715E"># ---SIMPLEEDIT-META-END---&quot;</span></span>:
            <span style="color:#8A2BE2">line</span> = <span style="color:#8A2BE2">lines</span>[<span style="color:#8A2BE2">i</span>]
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">line</span>.<span style="color:#33CCFF">startswith</span>(<span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#&#x27;</span></span>):
                <span style="color:#8A2BE2">b64_parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">line</span>[<span style="color:#FDFD6A">1</span>:].<span style="color:#33CCFF">strip</span>())
            <span style="color:#8A2BE2">i</span> += <span style="color:#FDFD6A">1</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">i</span> &gt;= <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">lines</span>):
            <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">raw</span>, <span style="color:#9CDCFE">None</span>
        <span style="color:#75715E"># content starts after the END marker line</span>
        <span style="color:#8A2BE2">content</span> = <span style="color:#C9CA6B">&#x27;&#x27;</span>.<span style="color:#33CCFF">join</span>(<span style="color:#8A2BE2">lines</span>[<span style="color:#8A2BE2">i</span> + <span style="color:#FDFD6A">1</span>:])
        <span style="color:#8A2BE2">b64</span> = <span style="color:#C9CA6B">&#x27;&#x27;</span>.<span style="color:#33CCFF">join</span>(<span style="color:#8A2BE2">b64_parts</span>)
        <span style="color:#FF0000">try</span>:
            <span style="color:#8A2BE2">meta</span> = json.<span style="color:#33CCFF">loads</span>(base64.<span style="color:#33CCFF">b64decode</span>(<span style="color:#8A2BE2">b64</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">decode</span></span>(<span style="color:#C9CA6B">&#x27;utf-8&#x27;</span>))
            <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">content</span>, <span style="color:#8A2BE2">meta</span>
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">content</span>, <span style="color:#9CDCFE">None</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">raw</span>, <span style="color:#9CDCFE">None</span>

<span style="color:#FF0000">def</span> <span style="color:#FFA500">_apply_full_tags</span>(<span style="color:#8A2BE2">actions</span>, <span style="color:#8A2BE2">new_vars</span>, <span style="color:#8A2BE2">new_defs</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Apply tag actions on the main/UI thread and persist discovered symbols.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#75715E"># clear tags across the whole buffer first</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;string&#x27;</span>, <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>, <span style="color:#C9CA6B">&#x27;comment&#x27;</span>, <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>, <span style="color:#C9CA6B">&#x27;def&#x27;</span>, <span style="color:#C9CA6B">&#x27;number&#x27;</span>, <span style="color:#C9CA6B">&#x27;variable&#x27;</span>,
                  <span style="color:#C9CA6B">&#x27;decorator&#x27;</span>, <span style="color:#C9CA6B">&#x27;class_name&#x27;</span>, <span style="color:#C9CA6B">&#x27;constant&#x27;</span>, <span style="color:#C9CA6B">&#x27;attribute&#x27;</span>, <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>, <span style="color:#C9CA6B">&#x27;todo&#x27;</span>):
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#8A2BE2">t</span>, <span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end&quot;</span>)

        <span style="color:#75715E"># add tags collected by the worker</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">tag</span>, <span style="color:#8A2BE2">ranges</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">actions</span>.<span style="color:#33CCFF">items</span>():
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">ranges</span>:
                <span style="color:#FF0000">continue</span>
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">ranges</span>:
                <span style="color:#75715E"># s/e are absolute character offsets from start of buffer</span>
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#8A2BE2">tag</span>, <span style="color:#C9CA6B">f&quot;1.0 + {s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {e}c&quot;</span>)

        <span style="color:#75715E"># persist newly discovered symbols (union)</span>
        <span style="color:#8A2BE2">updated</span> = <span style="color:#9CDCFE">False</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">new_vars</span>:
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">new_vars</span>.<span style="color:#33CCFF">issubset</span>(persisted_vars):
                persisted_vars.<span style="color:#33CCFF">update</span>(<span style="color:#8A2BE2">new_vars</span>)
                <span style="color:#8A2BE2">updated</span> = <span style="color:#9CDCFE">True</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">new_defs</span>:
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">new_defs</span>.<span style="color:#33CCFF">issubset</span>(persisted_defs):
                persisted_defs.<span style="color:#33CCFF">update</span>(<span style="color:#8A2BE2">new_defs</span>)
                <span style="color:#8A2BE2">updated</span> = <span style="color:#9CDCFE">True</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">updated</span>:
            <span style="color:#FFA500">_save_symbol_buffers</span>(persisted_vars, persisted_defs)

        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Ready&quot;</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#75715E"># keep UI resilient to errors</span>
        <span style="color:#FF0000">pass</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_bg_full_scan_and_collect</span>(<span style="color:#8A2BE2">content</span>, progress_callback=<span style="color:#9CDCFE">None</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Background worker: scan content string and return tag ranges + discovered symbols.

    Accepts optional progress_callback(percent:int, message:str) which will be called
    periodically from the worker thread. Caller must ensure UI updates happen on main thread
    (i.e. use root.after inside the callback).
    Returns (actions_dict, new_vars_set, new_defs_set)
    where actions_dict is mapping tag -&gt; list of (abs_start, abs_end) offsets.
    &quot;&quot;&quot;</span>
    <span style="color:#8A2BE2">actions</span> = {
        <span style="color:#C9CA6B">&#x27;string&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;comment&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;number&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;decorator&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;class_name&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;variable&#x27;</span>: [],
        <span style="color:#C9CA6B">&#x27;constant&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;attribute&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;def&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>: [], <span style="color:#C9CA6B">&#x27;todo&#x27;</span>: []
    }

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">report</span>(pct, msg=<span style="color:#9CDCFE">None</span>):
        <span style="color:#FF0000">try</span>:
            <span style="color:#FF0000">if</span> progress_callback:
                progress_callback(<span style="color:#9CDCFE">int</span>(pct), msg <span style="color:#FF0000">or</span> <span style="color:#C9CA6B">&quot;&quot;</span>)
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

    <span style="color:#FF0000">try</span>:
        <span style="color:#75715E"># We&#x27;ll report progress in steps as we run each major pass.</span>
        <span style="color:#75715E"># List of passes (name, function to run)</span>
        <span style="color:#8A2BE2">protected_spans</span> = []

        <span style="color:#75715E"># Pass 1: strings</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">2</span>, <span style="color:#C9CA6B">&quot;Scanning strings...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">STRING_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;string&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#8A2BE2">protected_spans</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">8</span>)

        <span style="color:#75715E"># Pass 2: comments and TODOs</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">9</span>, <span style="color:#C9CA6B">&quot;Scanning comments...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">COMMENT_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;comment&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#8A2BE2">protected_spans</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#8A2BE2">mm</span> = <span style="color:#8A2BE2">TODO_RE</span>.<span style="color:#33CCFF">search</span>(<span style="color:#8A2BE2">content</span>, <span style="color:#8A2BE2">m</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>(), <span style="color:#8A2BE2">m</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">end</span></span>())
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">mm</span>:
                ts, te = <span style="color:#8A2BE2">mm</span>.<span style="color:#33CCFF">span</span>()
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;todo&#x27;</span>].<span style="color:#33CCFF">append</span>((ts, te))
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">14</span>)

        <span style="color:#FF0000">def</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
            <span style="color:#FF0000">for</span> ps, pe <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">protected_spans</span>:
                <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> (<span style="color:#8A2BE2">e</span> &lt;= ps <span style="color:#FF0000">or</span> <span style="color:#8A2BE2">s</span> &gt;= pe):
                    <span style="color:#FF0000">return</span> <span style="color:#9CDCFE">True</span>
            <span style="color:#FF0000">return</span> <span style="color:#9CDCFE">False</span>

        <span style="color:#75715E"># Pass 3: numbers</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">16</span>, <span style="color:#C9CA6B">&quot;Scanning numbers...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span>, <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> enumerate(<span style="color:#8A2BE2">NUMBER_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>)):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;number&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#75715E"># occasionally yield progress</span>
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">and</span> (<span style="color:#8A2BE2">i</span> % <span style="color:#FDFD6A">200</span>) == <span style="color:#FDFD6A">0</span>:
                <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">16</span> + min(<span style="color:#FDFD6A">10</span>, <span style="color:#8A2BE2">i</span> // <span style="color:#FDFD6A">200</span>), <span style="color:#C9CA6B">&quot;Scanning numbers...&quot;</span>)
                time.<span style="color:#33CCFF">sleep</span>(<span style="color:#FDFD6A">0</span>)  <span style="color:#75715E"># yield thread</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">22</span>)

        <span style="color:#75715E"># Pass 4: decorators</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">23</span>, <span style="color:#C9CA6B">&quot;Scanning decorators...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">DECORATOR_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;decorator&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">27</span>)

        <span style="color:#75715E"># Pass 5: classes</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">28</span>, <span style="color:#C9CA6B">&quot;Scanning classes...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">CLASS_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;class_name&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">32</span>)

        <span style="color:#75715E"># Pass 6: variable assignments</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">33</span>, <span style="color:#C9CA6B">&quot;Scanning variable assignments...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span>, <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> enumerate(<span style="color:#8A2BE2">VAR_ASSIGN_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>)):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;variable&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">and</span> (<span style="color:#8A2BE2">i</span> % <span style="color:#FDFD6A">200</span>) == <span style="color:#FDFD6A">0</span>:
                <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">33</span> + min(<span style="color:#FDFD6A">8</span>, <span style="color:#8A2BE2">i</span> // <span style="color:#FDFD6A">200</span>), <span style="color:#C9CA6B">&quot;Scanning variable assignments...&quot;</span>)
                time.<span style="color:#33CCFF">sleep</span>(<span style="color:#FDFD6A">0</span>)
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">41</span>)

        <span style="color:#75715E"># Pass 7: constants ALL_CAPS</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">42</span>, <span style="color:#C9CA6B">&quot;Scanning constants...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">CONSTANT_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;constant&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">46</span>)

        <span style="color:#75715E"># Pass 8: attributes (a.b -&gt; tag <span style="color:#C9CA6B">&#x27;b&#x27;</span>)</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">47</span>, <span style="color:#C9CA6B">&quot;Scanning attributes...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span>, <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> enumerate(<span style="color:#8A2BE2">ATTRIBUTE_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>)):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;attribute&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">and</span> (<span style="color:#8A2BE2">i</span> % <span style="color:#FDFD6A">500</span>) == <span style="color:#FDFD6A">0</span>:
                <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">47</span> + min(<span style="color:#FDFD6A">8</span>, <span style="color:#8A2BE2">i</span> // <span style="color:#FDFD6A">500</span>), <span style="color:#C9CA6B">&quot;Scanning attributes...&quot;</span>)
                time.<span style="color:#33CCFF">sleep</span>(<span style="color:#FDFD6A">0</span>)
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">55</span>)

        <span style="color:#75715E"># Pass 9: dunder names</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">56</span>, <span style="color:#C9CA6B">&quot;Scanning dunder names...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">DUNDER_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;def&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">60</span>)

        <span style="color:#75715E"># Pass 10: f-strings (tag whole)</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">61</span>, <span style="color:#C9CA6B">&quot;Scanning f-strings...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">FSTRING_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#75715E"># already tagged as <span style="color:#C9CA6B">&quot;string&quot;</span>; we keep for completeness</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">64</span>)

        <span style="color:#75715E"># Pass 11: defs discovery and marking</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">65</span>, <span style="color:#C9CA6B">&quot;Discovering defs...&quot;</span>)
        <span style="color:#FF0000">try</span>:
            <span style="color:#8A2BE2"><span style="color:#FF79C6">DEF_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(?m)^[ \t]*def\s+([A-Za-z_]\w*)\s*\(&#x27;</span>)
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#8A2BE2"><span style="color:#FF79C6">DEF_RE</span></span> = <span style="color:#9CDCFE">None</span>
        <span style="color:#8A2BE2">new_defs</span> = <span style="color:#9CDCFE">set</span>()
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">DEF_RE</span>:
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span>, <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> enumerate(<span style="color:#8A2BE2">DEF_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>)):
                <span style="color:#8A2BE2">name</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>)
                <span style="color:#8A2BE2">new_defs</span>.<span style="color:#FFA500"><span style="color:#33CCFF">add</span></span>(<span style="color:#8A2BE2">name</span>)
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">and</span> (<span style="color:#8A2BE2">i</span> % <span style="color:#FDFD6A">200</span>) == <span style="color:#FDFD6A">0</span>:
                    <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">65</span> + min(<span style="color:#FDFD6A">6</span>, <span style="color:#8A2BE2">i</span> // <span style="color:#FDFD6A">200</span>), <span style="color:#C9CA6B">&quot;Discovering defs...&quot;</span>)
                    time.<span style="color:#33CCFF">sleep</span>(<span style="color:#FDFD6A">0</span>)
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">72</span>)

        <span style="color:#75715E"># Pass 12: create def-tags by searching occurrences</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">73</span>, <span style="color:#C9CA6B">&quot;Tagging defs...&quot;</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">new_defs</span>:
            <span style="color:#8A2BE2">pattern</span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b(&#x27;</span> + r<span style="color:#C9CA6B">&#x27;|&#x27;</span>.<span style="color:#33CCFF">join</span>(re.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">x</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">x</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">new_defs</span>) + r<span style="color:#C9CA6B">&#x27;)\b&#x27;</span>)
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">pattern</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
                <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
                <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                    <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;def&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">76</span>)

        <span style="color:#75715E"># Pass 13: keywords and builtins</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">77</span>, <span style="color:#C9CA6B">&quot;Scanning keywords and builtins...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span>, <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> enumerate(<span style="color:#8A2BE2">KEYWORD_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>)):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;keyword&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">and</span> (<span style="color:#8A2BE2">i</span> % <span style="color:#FDFD6A">1000</span>) == <span style="color:#FDFD6A">0</span>:
                <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">77</span> + min(<span style="color:#FDFD6A">8</span>, <span style="color:#8A2BE2">i</span> // <span style="color:#FDFD6A">1000</span>), <span style="color:#C9CA6B">&quot;Scanning keywords...&quot;</span>)
                time.<span style="color:#33CCFF">sleep</span>(<span style="color:#FDFD6A">0</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span>, <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> enumerate(<span style="color:#8A2BE2">BUILTIN_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>)):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;builtin&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">and</span> (<span style="color:#8A2BE2">i</span> % <span style="color:#FDFD6A">1000</span>) == <span style="color:#FDFD6A">0</span>:
                <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">85</span> + min(<span style="color:#FDFD6A">5</span>, <span style="color:#8A2BE2">i</span> // <span style="color:#FDFD6A">1000</span>), <span style="color:#C9CA6B">&quot;Scanning builtins...&quot;</span>)
                time.<span style="color:#33CCFF">sleep</span>(<span style="color:#FDFD6A">0</span>)
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">88</span>)

        <span style="color:#75715E"># Pass 14: selfs/attributes highlight</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">89</span>, <span style="color:#C9CA6B">&quot;Scanning self/attributes...&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">SELFS_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;selfs&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">90</span>)

        <span style="color:#75715E"># Pass 15: variables discovered across full file</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">91</span>, <span style="color:#C9CA6B">&quot;Collecting variables...&quot;</span>)
        <span style="color:#8A2BE2">new_vars</span> = {<span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">VAR_ASSIGN_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>)}
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">93</span>)

        <span style="color:#75715E"># Pass 16: include persisted buffers</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">94</span>, <span style="color:#C9CA6B">&quot;Tagging persisted symbols...&quot;</span>)
        <span style="color:#FF0000">if</span> persisted_vars:
            <span style="color:#FF0000">try</span>:
                <span style="color:#8A2BE2">pattern_pv</span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b(&#x27;</span> + r<span style="color:#C9CA6B">&#x27;|&#x27;</span>.<span style="color:#33CCFF">join</span>(re.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">x</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">x</span> <span style="color:#FF0000">in</span> persisted_vars) + r<span style="color:#C9CA6B">&#x27;)\b&#x27;</span>)
                <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">pattern_pv</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
                    <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
                    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                        <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;variable&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#FF0000">except</span> re.<span style="color:#33CCFF">error</span>:
                <span style="color:#FF0000">pass</span>
        <span style="color:#FF0000">if</span> persisted_defs:
            <span style="color:#FF0000">try</span>:
                <span style="color:#8A2BE2">pattern_pd</span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b(&#x27;</span> + r<span style="color:#C9CA6B">&#x27;|&#x27;</span>.<span style="color:#33CCFF">join</span>(re.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">x</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">x</span> <span style="color:#FF0000">in</span> persisted_defs) + r<span style="color:#C9CA6B">&#x27;)\b&#x27;</span>)
                <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">pattern_pd</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
                    <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
                    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                        <span style="color:#8A2BE2">actions</span>[<span style="color:#C9CA6B">&#x27;def&#x27;</span>].<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#FF0000">except</span> re.<span style="color:#33CCFF">error</span>:
                <span style="color:#FF0000">pass</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">98</span>)

        <span style="color:#75715E"># Finalize</span>
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">100</span>, <span style="color:#C9CA6B">&quot;Done, please wait while highlighting is applied&quot;</span>)
        <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">actions</span>, <span style="color:#8A2BE2">new_vars</span>, <span style="color:#8A2BE2">new_defs</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FFA500">report</span>(<span style="color:#FDFD6A">100</span>, <span style="color:#C9CA6B">&quot;Error&quot;</span>)
        <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">actions</span>, <span style="color:#9CDCFE">set</span>(), <span style="color:#9CDCFE">set</span>()

<span style="color:#75715E"># initialize persisted buffers</span>
persisted_vars, persisted_defs = <span style="color:#FFA500">_load_symbol_buffers</span>()

<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Actions: clipboard / cut / paste</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">copy_to_clipboard</span>():
    <span style="color:#FF0000">try</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">copiedText</span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">selection_get</span>()
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">clipboard_clear</span>()
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">clipboard_append</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">copiedText</span></span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">paste_from_clipboard</span>():
    <span style="color:#FF0000">try</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">pastedText</span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">clipboard_get</span>()
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">pastedText</span></span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">cut_selected_text</span>():
    <span style="color:#FF0000">try</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">cuttedText</span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">selection_get</span>()
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">delete</span>(SEL_FIRST, SEL_LAST)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">clipboard_clear</span>()
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">clipboard_append</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">cuttedText</span></span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Formatting toggles</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">toggle_tag_complex</span>(<span style="color:#8A2BE2">tag</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;High-level toggling that preserves combinations similar to original behaviour.&quot;&quot;&quot;</span>
    <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span> = <span style="color:#FFA500">selection_or_all</span>()
    <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#8A2BE2">tag</span>):
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#8A2BE2">tag</span>, <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)
        <span style="color:#FF0000">return</span>

    <span style="color:#75715E"># Simplified combination logic: remove mutually exclusive combinations and add requested tag.</span>
    <span style="color:#75715E"># Keep the previous detailed transformations minimal but consistent.</span>
    <span style="color:#75715E"># Remove <span style="color:#C9CA6B">&#x27;all&#x27;</span> if adding single style; remove conflicting combos.</span>
    <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;all&#x27;</span>, <span style="color:#C9CA6B">&#x27;bolditalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;underlineitalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;boldunderline&#x27;</span>):
        <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#8A2BE2">t</span>):
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#8A2BE2">t</span>, <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)

    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#8A2BE2">tag</span>, <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">format_bold</span>():
    <span style="color:#FFA500">toggle_tag_complex</span>(<span style="color:#C9CA6B">&quot;bold&quot;</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">format_italic</span>():
    <span style="color:#FFA500">toggle_tag_complex</span>(<span style="color:#C9CA6B">&quot;italic&quot;</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">format_underline</span>():
    <span style="color:#FFA500">toggle_tag_complex</span>(<span style="color:#C9CA6B">&quot;underline&quot;</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">remove_all_formatting</span>():
    <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span> = <span style="color:#FFA500">selection_or_all</span>()
    <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&quot;underline&quot;</span>, <span style="color:#C9CA6B">&quot;underlineitalic&quot;</span>, <span style="color:#C9CA6B">&quot;all&quot;</span>, <span style="color:#C9CA6B">&quot;boldunderline&quot;</span>, <span style="color:#C9CA6B">&quot;italic&quot;</span>, <span style="color:#C9CA6B">&quot;bold&quot;</span>, <span style="color:#C9CA6B">&quot;bolditalic&quot;</span>):
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#8A2BE2">t</span>, <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># File operations (single-copy implementations)</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">get_size_of_textarea_lines</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Return count of lines as a simple progress metric.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">return</span> <span style="color:#9CDCFE">len</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>).<span style="color:#33CCFF">splitlines</span>()) <span style="color:#FF0000">or</span> <span style="color:#FDFD6A">1</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">save_file_as</span>():
    <span style="color:#75715E"># asks save-as if no filename is set</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span> = filedialog.<span style="color:#33CCFF">asksaveasfilename</span>(
        <span style="color:#8A2BE2">initialdir</span>=os.<span style="color:#33CCFF">path</span>.<span style="color:#33CCFF">expanduser</span>(<span style="color:#C9CA6B">&quot;~&quot;</span>),
        <span style="color:#8A2BE2">title</span>=<span style="color:#C9CA6B">&quot;Save as SimpleEdit Text (.set), Markdown (.md) or other&quot;</span>,
        <span style="color:#8A2BE2">defaultextension</span>=<span style="color:#C9CA6B">&#x27;.set&#x27;</span>,
        <span style="color:#8A2BE2">filetypes</span>=(
            (<span style="color:#C9CA6B">&quot;SimpleEdit Text files&quot;</span>, <span style="color:#C9CA6B">&quot;*.set&quot;</span>),
            (<span style="color:#C9CA6B">&quot;Markdown files&quot;</span>, <span style="color:#C9CA6B">&quot;*.md&quot;</span>),
            (<span style="color:#C9CA6B">&quot;Text files&quot;</span>, <span style="color:#C9CA6B">&quot;*.txt&quot;</span>),
            (<span style="color:#C9CA6B">&quot;Python Source files&quot;</span>, <span style="color:#C9CA6B">&quot;*.py&quot;</span>),
            (<span style="color:#C9CA6B">&quot;All files&quot;</span>, <span style="color:#C9CA6B">&quot;*.*&quot;</span>),
        )
    )
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>:
        <span style="color:#FF0000">return</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>
    <span style="color:#75715E"># fall through to normal save</span>
    <span style="color:#FFA500">save_file</span>()


<span style="color:#FF0000">def</span> <span style="color:#FFA500">save_file_as2</span>():
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>2 = filedialog.<span style="color:#33CCFF">asksaveasfilename</span>(
        <span style="color:#8A2BE2">initialdir</span>=os.<span style="color:#33CCFF">path</span>.<span style="color:#33CCFF">expanduser</span>(<span style="color:#C9CA6B">&quot;~&quot;</span>),
        <span style="color:#8A2BE2">title</span>=<span style="color:#C9CA6B">&quot;Save as SimpleEdit Text (.set), Markdown (.md) or other&quot;</span>,
        <span style="color:#8A2BE2">defaultextension</span>=<span style="color:#C9CA6B">&#x27;.set&#x27;</span>,
        <span style="color:#8A2BE2">filetypes</span>=(
            (<span style="color:#C9CA6B">&quot;SimpleEdit Text files&quot;</span>, <span style="color:#C9CA6B">&quot;*.set&quot;</span>),
            (<span style="color:#C9CA6B">&quot;Markdown files&quot;</span>, <span style="color:#C9CA6B">&quot;*.md&quot;</span>),
            (<span style="color:#C9CA6B">&quot;Text files&quot;</span>, <span style="color:#C9CA6B">&quot;*.txt&quot;</span>),
            (<span style="color:#C9CA6B">&quot;Python Source files&quot;</span>, <span style="color:#C9CA6B">&quot;*.py&quot;</span>),
            (<span style="color:#C9CA6B">&quot;All files&quot;</span>, <span style="color:#C9CA6B">&quot;*.*&quot;</span>),
        )
    )
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>2:
        <span style="color:#FF0000">return</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>2
    <span style="color:#FFA500">save_file</span>()


<span style="color:#FF0000">def</span> <span style="color:#FFA500">save_file</span>():
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span>:
        <span style="color:#FFA500">save_file_as</span>()
        <span style="color:#FF0000">return</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">content</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>)
        <span style="color:#75715E"># automatically embed formatting header for .set files,</span>
        <span style="color:#75715E"># or if the user explicitly enabled the option in settings.</span>
        <span style="color:#8A2BE2">save_formatting</span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;saveFormattingInFile&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>) \
                          <span style="color:#FF0000">or</span> (<span style="color:#9CDCFE">isinstance</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span>, <span style="color:#9CDCFE">str</span>) <span style="color:#FF0000">and</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span>.<span style="color:#33CCFF">lower</span>().<span style="color:#33CCFF">endswith</span>(<span style="color:#C9CA6B">&#x27;.set&#x27;</span>))
        <span style="color:#8A2BE2">header</span> = <span style="color:#FFA500">_serialize_formatting</span>() <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">save_formatting</span> <span style="color:#FF0000">else</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>
        <span style="color:#FF0000">with</span> <span style="color:#9CDCFE">open</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span>, <span style="color:#C9CA6B">&#x27;w&#x27;</span>, errors=<span style="color:#C9CA6B">&#x27;replace&#x27;</span>) <span style="color:#FF0000">as</span> f:
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">header</span>:
                f.<span style="color:#33CCFF">write</span>(<span style="color:#8A2BE2">header</span>)
            f.<span style="color:#33CCFF">write</span>(<span style="color:#8A2BE2">content</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">f&quot;&#x27;{root.fileName}&#x27; saved successfully!&quot;</span>
        <span style="color:#FFA500">add_recent_file</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span>)
        <span style="color:#FFA500">refresh_recent_menu</span>()
    <span style="color:#FF0000">except</span> Exception <span style="color:#FF0000">as</span> <span style="color:#8A2BE2">e</span>:
        messagebox.<span style="color:#33CCFF">showerror</span>(<span style="color:#C9CA6B">&quot;Error&quot;</span>, <span style="color:#9CDCFE">str</span>(<span style="color:#8A2BE2">e</span>))


<span style="color:#FF0000">def</span> <span style="color:#FFA500">open_file_threaded</span>():
    <span style="color:#75715E"># runs in thread</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span> = filedialog.<span style="color:#33CCFF">askopenfilename</span>(
            <span style="color:#8A2BE2">initialdir</span>=os.<span style="color:#33CCFF">path</span>.<span style="color:#33CCFF">expanduser</span>(<span style="color:#C9CA6B">&quot;~&quot;</span>),
            <span style="color:#8A2BE2">title</span>=<span style="color:#C9CA6B">&quot;Select file&quot;</span>,
            <span style="color:#8A2BE2">filetypes</span>=(
                (<span style="color:#C9CA6B">&quot;SimpleEdit Text files&quot;</span>, <span style="color:#C9CA6B">&quot;*.set&quot;</span>),
                (<span style="color:#C9CA6B">&quot;Markdown files&quot;</span>, <span style="color:#C9CA6B">&quot;*.md&quot;</span>),
                (<span style="color:#C9CA6B">&quot;HTML files&quot;</span>, <span style="color:#C9CA6B">&quot;*.html&quot;</span>),
                (<span style="color:#C9CA6B">&quot;Text files&quot;</span>, <span style="color:#C9CA6B">&quot;*.txt&quot;</span>),
                (<span style="color:#C9CA6B">&quot;Python Source files&quot;</span>, <span style="color:#C9CA6B">&quot;*.py&quot;</span>),
                (<span style="color:#C9CA6B">&quot;All files&quot;</span>, <span style="color:#C9CA6B">&quot;*.*&quot;</span>),
            )
        )
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#FF0000">with</span> <span style="color:#9CDCFE">open</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>, <span style="color:#C9CA6B">&#x27;r&#x27;</span>, errors=<span style="color:#C9CA6B">&#x27;replace&#x27;</span>, encoding=<span style="color:#C9CA6B">&#x27;utf-8&#x27;</span>) <span style="color:#FF0000">as</span> f:
            <span style="color:#8A2BE2">raw</span> = f.<span style="color:#33CCFF">read</span>()

        <span style="color:#75715E"># First try to extract SIMPLEEDIT meta (preferred)</span>
        <span style="color:#8A2BE2">content</span>, <span style="color:#8A2BE2">meta</span> = <span style="color:#FFA500">_extract_header_and_meta</span>(<span style="color:#8A2BE2">raw</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">meta</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">content</span>)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">f&quot;&#x27;{fileName}&#x27; opened successfully!&quot;</span>
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>
            <span style="color:#FFA500">add_recent_file</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>)
            <span style="color:#FFA500">refresh_recent_menu</span>()
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">_apply_formatting_from_meta</span>(<span style="color:#8A2BE2">meta</span>))
            <span style="color:#FF0000">try</span>:
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_ML_AVAILABLE</span> <span style="color:#FF0000">and</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpen <span style="color:#FF0000">and</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loaded</span> <span style="color:#FF0000">and</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loading</span>:
                    Thread(target=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">_start_model_load</span>(start_autocomplete=<span style="color:#9CDCFE">False</span>), daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#FF0000">pass</span>
            <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">updateSyntaxHighlighting</span></span>.<span style="color:#33CCFF">get</span>():
                <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInit</span></span>)
            <span style="color:#FF0000">return</span>

        <span style="color:#75715E"># If no meta and file is .md or .html attempt HTML-aware parsing to reconstruct tags</span>
        <span style="color:#8A2BE2">ext</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>.<span style="color:#33CCFF">lower</span>().<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[-<span style="color:#FDFD6A">1</span>]
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">ext</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;md&#x27;</span>, <span style="color:#C9CA6B">&#x27;html&#x27;</span>, <span style="color:#C9CA6B">&#x27;htm&#x27;</span>):
            plain, tags_meta = <span style="color:#FFA500">_parse_html_and_apply</span>(<span style="color:#8A2BE2">raw</span>)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, plain)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>
            <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">f&quot;&#x27;{fileName}&#x27; opened (HTML/MD parsed)!&quot;</span>
            <span style="color:#FFA500">add_recent_file</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>)
            <span style="color:#FFA500">refresh_recent_menu</span>()
            <span style="color:#FF0000">if</span> tags_meta <span style="color:#FF0000">and</span> tags_meta.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;tags&#x27;</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">_apply_formatting_from_meta</span>(tags_meta))
            <span style="color:#75715E"># still run normal syntax-highlighting pass to refresh persisted symbol highlights</span>
            <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">updateSyntaxHighlighting</span></span>.<span style="color:#33CCFF">get</span>():
                <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInit</span></span>)
            <span style="color:#FF0000">return</span>

        <span style="color:#75715E"># Fallback: no meta and not md/html - insert raw</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">raw</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">f&quot;&#x27;{fileName}&#x27; opened successfully!&quot;</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>
        <span style="color:#FF0000">try</span>:
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_ML_AVAILABLE</span> <span style="color:#FF0000">and</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpen <span style="color:#FF0000">and</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loaded</span> <span style="color:#FF0000">and</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loading</span>:
                Thread(target=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">_start_model_load</span>(start_autocomplete=<span style="color:#9CDCFE">False</span>), daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>
        <span style="color:#FFA500">add_recent_file</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>)
        <span style="color:#FFA500">refresh_recent_menu</span>()
        <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">updateSyntaxHighlighting</span></span>.<span style="color:#33CCFF">get</span>():
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInit</span></span>)
    <span style="color:#FF0000">except</span> Exception <span style="color:#FF0000">as</span> <span style="color:#8A2BE2">e</span>:
        messagebox.<span style="color:#33CCFF">showerror</span>(<span style="color:#C9CA6B">&quot;Error&quot;</span>, <span style="color:#9CDCFE">str</span>(<span style="color:#8A2BE2">e</span>))

<span style="color:#FF0000">def</span> <span style="color:#FFA500">_collect_formatting_ranges</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Return dict mapping formatting tag -&gt; list of (start_offset, end_offset).&quot;&quot;&quot;</span>
    <span style="color:#8A2BE2">tags_to_check</span> = (<span style="color:#C9CA6B">&#x27;bold&#x27;</span>, <span style="color:#C9CA6B">&#x27;italic&#x27;</span>, <span style="color:#C9CA6B">&#x27;underline&#x27;</span>, <span style="color:#C9CA6B">&#x27;all&#x27;</span>,
                     <span style="color:#C9CA6B">&#x27;underlineitalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;boldunderline&#x27;</span>, <span style="color:#C9CA6B">&#x27;bolditalic&#x27;</span>)
    <span style="color:#8A2BE2">out</span> = {}
    <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">tags_to_check</span>:
        <span style="color:#8A2BE2">ranges</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#8A2BE2">tag</span>)
        <span style="color:#8A2BE2">arr</span> = []
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">ranges</span>), <span style="color:#FDFD6A">2</span>):
            <span style="color:#8A2BE2">s</span> = <span style="color:#8A2BE2">ranges</span>[<span style="color:#8A2BE2">i</span>]
            <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">ranges</span>[<span style="color:#8A2BE2">i</span> + <span style="color:#FDFD6A">1</span>]
            <span style="color:#8A2BE2">start</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">s</span>))
            <span style="color:#8A2BE2">end</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">end</span> &gt; <span style="color:#8A2BE2">start</span>:
                <span style="color:#8A2BE2">arr</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>))
        <span style="color:#8A2BE2">out</span>[<span style="color:#8A2BE2">tag</span>] = <span style="color:#8A2BE2">arr</span>
    <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">out</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_wrap_segment_by_tags</span>(seg_text: <span style="color:#9CDCFE">str</span>, active_tags: <span style="color:#9CDCFE">set</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Wrap a text segment according to active tag set into Markdown/HTML.&quot;&quot;&quot;</span>
    <span style="color:#75715E"># Determine boolean flags considering explicit combo tags and <span style="color:#C9CA6B">&#x27;all&#x27;</span></span>
    <span style="color:#8A2BE2">has_bold</span> = any(<span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> active_tags <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;bold&#x27;</span>, <span style="color:#C9CA6B">&#x27;bolditalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;boldunderline&#x27;</span>, <span style="color:#C9CA6B">&#x27;all&#x27;</span>))
    <span style="color:#8A2BE2">has_italic</span> = any(<span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> active_tags <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;italic&#x27;</span>, <span style="color:#C9CA6B">&#x27;bolditalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;underlineitalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;all&#x27;</span>))
    <span style="color:#8A2BE2">has_underline</span> = any(<span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> active_tags <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;underline&#x27;</span>, <span style="color:#C9CA6B">&#x27;boldunderline&#x27;</span>, <span style="color:#C9CA6B">&#x27;underlineitalic&#x27;</span>, <span style="color:#C9CA6B">&#x27;all&#x27;</span>))

    <span style="color:#8A2BE2">inner</span> = seg_text
    <span style="color:#75715E"># Prefer Markdown bold+italic triple-star where supported</span>
    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">has_bold</span> <span style="color:#FF0000">and</span> <span style="color:#8A2BE2">has_italic</span>:
        <span style="color:#8A2BE2">inner</span> = <span style="color:#C9CA6B">f&quot;***{inner}***&quot;</span>
    elif <span style="color:#8A2BE2">has_bold</span>:
        <span style="color:#8A2BE2">inner</span> = <span style="color:#C9CA6B">f&quot;**{inner}**&quot;</span>
    elif <span style="color:#8A2BE2">has_italic</span>:
        <span style="color:#8A2BE2">inner</span> = <span style="color:#C9CA6B">f&quot;*{inner}*&quot;</span>

    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">has_underline</span>:
        <span style="color:#75715E"># Markdown doesn&#x27;t have native underline; use HTML &lt;u&gt; for compatibility</span>
        <span style="color:#8A2BE2">inner</span> = <span style="color:#C9CA6B">f&quot;&lt;u&gt;{inner}&lt;/u&gt;&quot;</span>

    <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">inner</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">_convert_buffer_to_markdown</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Convert buffer text applying formatting tags to Markdown/HTML and return string.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">content</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>)
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">content</span>:
            <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>

        <span style="color:#8A2BE2">ranges_by_tag</span> = <span style="color:#FFA500">_collect_formatting_ranges</span>()

        <span style="color:#75715E"># Build events (pos, kind, tag) where kind is <span style="color:#C9CA6B">&#x27;start&#x27;</span> or <span style="color:#C9CA6B">&#x27;end&#x27;</span></span>
        <span style="color:#8A2BE2">events</span> = []
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">tag</span>, <span style="color:#8A2BE2">ranges</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">ranges_by_tag</span>.<span style="color:#33CCFF">items</span>():
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">ranges</span>:
                <span style="color:#8A2BE2">events</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#C9CA6B">&#x27;start&#x27;</span>, <span style="color:#8A2BE2">tag</span>))
                <span style="color:#8A2BE2">events</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">e</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>, <span style="color:#8A2BE2">tag</span>))

        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">events</span>:
            <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">content</span>

        <span style="color:#75715E"># Group events by position; end events must be applied before start events at same pos</span>
        <span style="color:#8A2BE2">events_by_pos</span> = {}
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">pos</span>, kind, <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">events</span>:
            <span style="color:#8A2BE2">events_by_pos</span>.<span style="color:#33CCFF">setdefault</span>(<span style="color:#8A2BE2">pos</span>, []).<span style="color:#33CCFF">append</span>((kind, <span style="color:#8A2BE2">tag</span>))

        <span style="color:#8A2BE2">positions</span> = sorted(<span style="color:#8A2BE2">events_by_pos</span>.<span style="color:#33CCFF">keys</span>())
        <span style="color:#75715E"># also ensure we include file start and end as segment boundaries</span>
        <span style="color:#FF0000">if</span> <span style="color:#FDFD6A">0</span> <span style="color:#FF0000">not</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">positions</span>:
            <span style="color:#8A2BE2">positions</span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FDFD6A">0</span>)
        <span style="color:#8A2BE2">file_end</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">content</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">file_end</span> <span style="color:#FF0000">not</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">positions</span>:
            <span style="color:#8A2BE2">positions</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">file_end</span>)
        <span style="color:#8A2BE2">positions</span> = sorted(<span style="color:#9CDCFE">set</span>(<span style="color:#8A2BE2">positions</span>))

        <span style="color:#75715E"># Build a mapping of pos -&gt; sorted events (end before start)</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">pos</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">events_by_pos</span>:
            <span style="color:#8A2BE2">events_by_pos</span>[<span style="color:#8A2BE2">pos</span>].<span style="color:#33CCFF">sort</span>(key=<span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">x</span>: <span style="color:#FDFD6A">0</span> <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">x</span>[<span style="color:#FDFD6A">0</span>] == <span style="color:#C9CA6B">&#x27;end&#x27;</span> <span style="color:#FF0000">else</span> <span style="color:#FDFD6A">1</span>)

        <span style="color:#8A2BE2">parts</span> = []
        <span style="color:#8A2BE2">active</span> = <span style="color:#9CDCFE">set</span>()

        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">i</span> <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">positions</span>) - <span style="color:#FDFD6A">1</span>):
            <span style="color:#8A2BE2">pos</span> = <span style="color:#8A2BE2">positions</span>[<span style="color:#8A2BE2">i</span>]
            <span style="color:#75715E"># apply events at this pos: end events first then start events (already ordered)</span>
            <span style="color:#FF0000">for</span> kind, <span style="color:#8A2BE2">tag</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">events_by_pos</span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">pos</span>, []):
                <span style="color:#FF0000">if</span> kind == <span style="color:#C9CA6B">&#x27;start&#x27;</span>:
                    <span style="color:#8A2BE2">active</span>.<span style="color:#FFA500"><span style="color:#33CCFF">add</span></span>(<span style="color:#8A2BE2">tag</span>)
                elif kind == <span style="color:#C9CA6B">&#x27;end&#x27;</span>:
                    <span style="color:#8A2BE2">active</span>.<span style="color:#33CCFF">discard</span>(<span style="color:#8A2BE2">tag</span>)

            <span style="color:#8A2BE2">next_pos</span> = <span style="color:#8A2BE2">positions</span>[<span style="color:#8A2BE2">i</span> + <span style="color:#FDFD6A">1</span>]
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">next_pos</span> &lt;= <span style="color:#8A2BE2">pos</span>:
                <span style="color:#FF0000">continue</span>
            <span style="color:#8A2BE2">seg</span> = <span style="color:#8A2BE2">content</span>[<span style="color:#8A2BE2">pos</span>:<span style="color:#8A2BE2">next_pos</span>]
            <span style="color:#8A2BE2">wrapped</span> = <span style="color:#FFA500">_wrap_segment_by_tags</span>(<span style="color:#8A2BE2">seg</span>, <span style="color:#8A2BE2">active</span>)
            <span style="color:#8A2BE2">parts</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">wrapped</span>)

        <span style="color:#75715E"># There may be trailing events at final position (no further segment) - ignore.</span>
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>.<span style="color:#33CCFF">join</span>(<span style="color:#8A2BE2">parts</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#75715E"># fall back to raw content on any failure</span>
        <span style="color:#FF0000">try</span>:
            <span style="color:#FF0000">return</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>)
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">save_as_markdown</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Save buffer as .md or .html. Output contains visible HTML spans for syntax
    and formatting so the saved file renders with highlighting. Metadata header is not required.
    &quot;&quot;&quot;</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span> = filedialog.<span style="color:#33CCFF">asksaveasfilename</span>(
        <span style="color:#8A2BE2">initialdir</span>=os.<span style="color:#33CCFF">path</span>.<span style="color:#33CCFF">expanduser</span>(<span style="color:#C9CA6B">&quot;~&quot;</span>),
        <span style="color:#8A2BE2">title</span>=<span style="color:#C9CA6B">&quot;Save as Markdown (.md) or HTML (.html) (preserves visible highlighting)&quot;</span>,
        <span style="color:#8A2BE2">defaultextension</span>=<span style="color:#C9CA6B">&#x27;.md&#x27;</span>,
        <span style="color:#8A2BE2">filetypes</span>=(
            (<span style="color:#C9CA6B">&quot;Markdown files&quot;</span>, <span style="color:#C9CA6B">&quot;*.md&quot;</span>),
            (<span style="color:#C9CA6B">&quot;HTML files&quot;</span>, <span style="color:#C9CA6B">&quot;*.html&quot;</span>),
            (<span style="color:#C9CA6B">&quot;Text files&quot;</span>, <span style="color:#C9CA6B">&quot;*.txt&quot;</span>),
            (<span style="color:#C9CA6B">&quot;All files&quot;</span>, <span style="color:#C9CA6B">&quot;*.*&quot;</span>),
        )
    )
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>:
        <span style="color:#FF0000">return</span>

    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">fragment</span> = <span style="color:#FFA500">_convert_buffer_to_html_fragment</span>()
        <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>.<span style="color:#33CCFF">lower</span>().<span style="color:#33CCFF">endswith</span>(<span style="color:#C9CA6B">&#x27;.html&#x27;</span>):
            <span style="color:#75715E"># wrap in minimal HTML document with inline styles for monospace font</span>
            <span style="color:#8A2BE2">html_doc</span> = (
                <span style="color:#C9CA6B">&#x27;&lt;!doctype html&gt;\n&lt;html lang=&quot;en&quot;&gt;\n&lt;head&gt;\n&lt;meta charset=&quot;utf-8&quot;&gt;\n&#x27;</span>
                <span style="color:#C9CA6B">&#x27;&lt;meta name=&quot;viewport&quot; content=&quot;width=device-width,initial-scale=1&quot;&gt;\n&#x27;</span>
                <span style="color:#C9CA6B">&#x27;&lt;title&gt;SimpleEdit Export&lt;/title&gt;\n&#x27;</span>
                <span style="color:#C9CA6B">&#x27;&lt;style&gt;body{{background:{bg};color:{fg};font-family:{font},monospace;white-space:pre-wrap;}}&lt;/style&gt;\n&#x27;</span>
                <span style="color:#C9CA6B">&#x27;&lt;/head&gt;\n&lt;body&gt;\n{body}\n&lt;/body&gt;\n&lt;/html&gt;\n&#x27;</span>
            ).<span style="color:#33CCFF">format</span>(<span style="color:#8A2BE2">bg</span>=<span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColor</span></span>, fg=<span style="color:#FFFF00"><span style="color:#8A2BE2">fontColor</span></span>, font=<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, body=<span style="color:#8A2BE2">fragment</span>)
            <span style="color:#FF0000">with</span> <span style="color:#9CDCFE">open</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>, <span style="color:#C9CA6B">&#x27;w&#x27;</span>, errors=<span style="color:#C9CA6B">&#x27;replace&#x27;</span>, encoding=<span style="color:#C9CA6B">&#x27;utf-8&#x27;</span>) <span style="color:#FF0000">as</span> f:
                f.<span style="color:#33CCFF">write</span>(<span style="color:#8A2BE2">html_doc</span>)
        <span style="color:#FF0000">else</span>:
            <span style="color:#75715E"># .md - write fragment (raw HTML allowed in Markdown)</span>
            <span style="color:#FF0000">with</span> <span style="color:#9CDCFE">open</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>, <span style="color:#C9CA6B">&#x27;w&#x27;</span>, errors=<span style="color:#C9CA6B">&#x27;replace&#x27;</span>, encoding=<span style="color:#C9CA6B">&#x27;utf-8&#x27;</span>) <span style="color:#FF0000">as</span> f:
                f.<span style="color:#33CCFF">write</span>(<span style="color:#8A2BE2">fragment</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">f&quot;&#x27;{fileName}&#x27; saved successfully!&quot;</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#8A2BE2"><span style="color:#33CCFF">fileName</span></span></span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>
        <span style="color:#FFA500">add_recent_file</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">fileName</span></span>)
        <span style="color:#FFA500">refresh_recent_menu</span>()
    <span style="color:#FF0000">except</span> Exception <span style="color:#FF0000">as</span> <span style="color:#8A2BE2">e</span>:
        messagebox.<span style="color:#33CCFF">showerror</span>(<span style="color:#C9CA6B">&quot;Error&quot;</span>, <span style="color:#9CDCFE">str</span>(<span style="color:#8A2BE2">e</span>))

<span style="color:#75715E"># --- Parse saved HTML fragments or full HTML docs back into plain text + tags ---</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">_parse_html_and_apply</span>(<span style="color:#8A2BE2">raw</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;
    Parse raw HTML fragment or document and extract plain text and tag ranges.
    Returns (plain_text, tags_dict) where tags_dict matches _apply_formatting_from_meta format.
    &quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#75715E"># If full document, try to extract body contents heuristically</span>
        <span style="color:#8A2BE2">m</span> = re.<span style="color:#33CCFF">search</span>(r<span style="color:#C9CA6B">&#x27;&lt;body[^&gt;]*&gt;(.*)&lt;/body&gt;&#x27;</span>, <span style="color:#8A2BE2">raw</span>, flags=re.<span style="color:#33CCFF">DOTALL</span> | re.<span style="color:#33CCFF">IGNORECASE</span>)
        <span style="color:#8A2BE2">fragment</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">else</span> <span style="color:#8A2BE2">raw</span>

        <span style="color:#8A2BE2">parser</span> = _SimpleHTMLToTagged()
        <span style="color:#8A2BE2">parser</span>.<span style="color:#33CCFF">feed</span>(<span style="color:#8A2BE2">fragment</span>)
        plain, <span style="color:#8A2BE2">ranges</span> = <span style="color:#8A2BE2">parser</span>.<span style="color:#FFA500"><span style="color:#33CCFF">get_result</span></span>()
        <span style="color:#75715E"># convert ranges (already [[s,e],...]) into meta shape</span>
        <span style="color:#FF0000">return</span> plain, {<span style="color:#C9CA6B">&#x27;tags&#x27;</span>: <span style="color:#8A2BE2">ranges</span>}
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">raw</span>, {}


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Highlighting</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Highlighting toggle (initialized from config)</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">updateSyntaxHighlighting</span></span> = IntVar(value=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;syntaxHighlighting&quot;</span>, fallback=<span style="color:#9CDCFE">True</span>))


<span style="color:#FF0000">def</span> <span style="color:#FFA500">match_case_like_this</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>):
    <span style="color:#8A2BE2">pattern</span> = r<span style="color:#C9CA6B">&#x27;def\s+([\w_]+)\s*\(&#x27;</span>
    <span style="color:#8A2BE2">matches</span> = []
    <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">line</span> <span style="color:#FF0000">in</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>).<span style="color:#33CCFF">splitlines</span>():
        <span style="color:#8A2BE2">m</span> = re.<span style="color:#33CCFF">search</span>(<span style="color:#8A2BE2">pattern</span>, <span style="color:#8A2BE2">line</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m</span>:
            <span style="color:#8A2BE2">matches</span>.<span style="color:#33CCFF">append</span>(r<span style="color:#C9CA6B">&#x27;\b&#x27;</span> + re.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>)) + r<span style="color:#C9CA6B">&#x27;\b&#x27;</span>)
    <span style="color:#FF0000">return</span> r<span style="color:#C9CA6B">&#x27;|&#x27;</span>.<span style="color:#33CCFF">join</span>(<span style="color:#8A2BE2">matches</span>) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">matches</span> <span style="color:#FF0000">else</span> r<span style="color:#C9CA6B">&#x27;\b\b&#x27;</span>


<span style="color:#8A2BE2">match_string</span> = r<span style="color:#C9CA6B">&#x27;\b\b&#x27;</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">highlight_python_helper</span>(event=<span style="color:#9CDCFE">None</span>, scan_start=<span style="color:#9CDCFE">None</span>, scan_end=<span style="color:#9CDCFE">None</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;Highlight a local region near the current cursor.

    By default this function will only scan the visible region to reduce work
    on large files. It will also tag names from the persisted buffers so those
    identifiers remain highlighted even if their definition is outside the visible region.
    &quot;&quot;&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">global</span> persisted_vars, persisted_defs

        <span style="color:#75715E"># determine region to scan (visible region by default)</span>
        <span style="color:#FF0000">if</span> scan_start <span style="color:#FF0000">is</span> <span style="color:#9CDCFE">None</span> <span style="color:#FF0000">or</span> scan_end <span style="color:#FF0000">is</span> <span style="color:#9CDCFE">None</span>:
            <span style="color:#FF0000">try</span>:
                <span style="color:#8A2BE2">first_visible</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;@0,0&#x27;</span>)
                <span style="color:#8A2BE2">last_visible</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(f<span style="color:#C9CA6B">&#x27;@0,{textArea.winfo_height()}&#x27;</span>)
                <span style="color:#8A2BE2">start_line</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">first_visible</span>.<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[<span style="color:#FDFD6A">0</span>])
                <span style="color:#8A2BE2">end_line</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">last_visible</span>.<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[<span style="color:#FDFD6A">0</span>])
                <span style="color:#8A2BE2">start</span> = f<span style="color:#C9CA6B">&#x27;{start_line}.0&#x27;</span>
                <span style="color:#8A2BE2">end</span> = f<span style="color:#C9CA6B">&#x27;{end_line}.0 lineend&#x27;</span>
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#8A2BE2">start</span> = <span style="color:#C9CA6B">&quot;1.0&quot;</span>
                <span style="color:#8A2BE2">end</span> = <span style="color:#C9CA6B">&quot;end-1c&quot;</span>
        <span style="color:#FF0000">else</span>:
            <span style="color:#8A2BE2">start</span> = scan_start
            <span style="color:#8A2BE2">end</span> = scan_end

        <span style="color:#75715E"># content for region and absolute char offset of region start</span>
        <span style="color:#8A2BE2">content</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)
        <span style="color:#8A2BE2">base_offset</span> = <span style="color:#FDFD6A">0</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">start</span> != <span style="color:#C9CA6B">&quot;1.0&quot;</span>:
            <span style="color:#8A2BE2">before</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#8A2BE2">start</span>)
            <span style="color:#8A2BE2">base_offset</span> = <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">before</span>)

        <span style="color:#75715E"># remove tags only in the scanned region</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;string&#x27;</span>, <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>, <span style="color:#C9CA6B">&#x27;comment&#x27;</span>, <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>, <span style="color:#C9CA6B">&#x27;def&#x27;</span>, <span style="color:#C9CA6B">&#x27;number&#x27;</span>, <span style="color:#C9CA6B">&#x27;variable&#x27;</span>,
                  <span style="color:#C9CA6B">&#x27;decorator&#x27;</span>, <span style="color:#C9CA6B">&#x27;class_name&#x27;</span>, <span style="color:#C9CA6B">&#x27;constant&#x27;</span>, <span style="color:#C9CA6B">&#x27;attribute&#x27;</span>, <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>, <span style="color:#C9CA6B">&#x27;todo&#x27;</span>):
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#8A2BE2">t</span>, <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)

        <span style="color:#8A2BE2">protected_spans</span> = []  <span style="color:#75715E"># keep (s, e) offsets relative to content for strings/comments</span>

        <span style="color:#75715E"># strings and comments first -- protect their spans</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">STRING_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;string&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)
            <span style="color:#8A2BE2">protected_spans</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">COMMENT_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;comment&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)
            <span style="color:#8A2BE2">protected_spans</span>.<span style="color:#33CCFF">append</span>((<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>))
            <span style="color:#8A2BE2">mm</span> = <span style="color:#8A2BE2">TODO_RE</span>.<span style="color:#33CCFF">search</span>(<span style="color:#8A2BE2">content</span>, <span style="color:#8A2BE2">m</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>(), <span style="color:#8A2BE2">m</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">end</span></span>())
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">mm</span>:
                ts, te = <span style="color:#8A2BE2">mm</span>.<span style="color:#33CCFF">span</span>()
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;todo&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + ts}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + te}c&quot;</span>)

        <span style="color:#FF0000">def</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
            <span style="color:#FF0000">for</span> ps, pe <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">protected_spans</span>:
                <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> (<span style="color:#8A2BE2">e</span> &lt;= ps <span style="color:#FF0000">or</span> <span style="color:#8A2BE2">s</span> &gt;= pe):
                    <span style="color:#FF0000">return</span> <span style="color:#9CDCFE">True</span>
            <span style="color:#FF0000">return</span> <span style="color:#9CDCFE">False</span>

        <span style="color:#75715E"># numbers</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">NUMBER_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;number&quot;</span>, f<span style="color:#C9CA6B">&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#75715E"># decorators</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">DECORATOR_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;decorator&quot;</span>, f<span style="color:#C9CA6B">&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#75715E"># classes</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">CLASS_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;class_name&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#75715E"># variable assignments (first non-whitespace word on a line)</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">VAR_ASSIGN_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;variable&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#75715E"># constants ALL_CAPS</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">CONSTANT_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;constant&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#75715E"># attribute names (a.b -&gt; tag <span style="color:#C9CA6B">&#x27;b&#x27;</span>)</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">ATTRIBUTE_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;attribute&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">DUNDER_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;def&quot;</span>, f<span style="color:#C9CA6B">&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">FSTRING_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#75715E"># tag entire fstring as <span style="color:#C9CA6B">&quot;string&quot;</span> already covered; then highlight expressions in braces</span>
            <span style="color:#8A2BE2">ftext</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">0</span>)
            <span style="color:#FF0000">for</span> be <span style="color:#FF0000">in</span> re.<span style="color:#33CCFF">finditer</span>(r<span style="color:#C9CA6B">&#x27;\{([^}]+)\}&#x27;</span>, <span style="color:#8A2BE2">ftext</span>):
                <span style="color:#8A2BE2">expr_s</span> = <span style="color:#8A2BE2">s</span> + be.<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>(<span style="color:#FDFD6A">1</span>)
                <span style="color:#8A2BE2">expr_e</span> = <span style="color:#8A2BE2">s</span> + be.<span style="color:#8A2BE2"><span style="color:#33CCFF">end</span></span>(<span style="color:#FDFD6A">1</span>)
                <span style="color:#75715E"># if you want to treat inner expression with keywords/builtins:</span>
                <span style="color:#8A2BE2">sub</span> = <span style="color:#8A2BE2">content</span>[<span style="color:#8A2BE2">expr_s</span>:<span style="color:#8A2BE2">expr_e</span>]
                <span style="color:#75715E"># small heuristic: run keyword/builtin regex on sub and tag matches (or tag whole expr)</span>
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;string&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)
                <span style="color:#75715E"># optionally tag inner expression as <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>/<span style="color:#C9CA6B">&#x27;keyword&#x27;</span> by re-applying regex on sub</span>
        <span style="color:#75715E"># dynamic defs (existing behaviour)</span>
        <span style="color:#FF0000">global</span> <span style="color:#8A2BE2">match_string</span>
        <span style="color:#8A2BE2">match_string</span> = <span style="color:#FFA500">match_case_like_this</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">match_string</span> <span style="color:#FF0000">and</span> <span style="color:#8A2BE2">match_string</span> != r<span style="color:#C9CA6B">&#x27;\b\b&#x27;</span>:
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> re.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">match_string</span>, <span style="color:#8A2BE2">content</span>):
                <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
                <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;def&quot;</span>, f<span style="color:#C9CA6B">&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#75715E"># keywords and builtins</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">KEYWORD_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;keyword&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">BUILTIN_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;builtin&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#75715E"># selfs/attributes highlight (include <span style="color:#C9CA6B">&#x27;after&#x27;</span> as requested)</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">SELFS_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>()
            <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;selfs&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

        <span style="color:#75715E"># tag persisted buffers inside the scanned region (so removed window items still highlight)</span>
        <span style="color:#FF0000">if</span> persisted_vars:
            <span style="color:#8A2BE2">pattern</span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b(&#x27;</span> + r<span style="color:#C9CA6B">&#x27;|&#x27;</span>.<span style="color:#33CCFF">join</span>(re.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">x</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">x</span> <span style="color:#FF0000">in</span> persisted_vars) + r<span style="color:#C9CA6B">&#x27;)\b&#x27;</span>)
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">pattern</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
                <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
                <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;variable&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)
        <span style="color:#FF0000">if</span> persisted_defs:
            <span style="color:#8A2BE2">pattern_def</span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;\b(&#x27;</span> + r<span style="color:#C9CA6B">&#x27;|&#x27;</span>.<span style="color:#33CCFF">join</span>(re.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">x</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">x</span> <span style="color:#FF0000">in</span> persisted_defs) + r<span style="color:#C9CA6B">&#x27;)\b&#x27;</span>)
            <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">pattern_def</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">content</span>):
                <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">span</span>(<span style="color:#FDFD6A">1</span>)
                <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFA500">overlaps_protected</span>(<span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>):
                    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&quot;def&quot;</span>, f<span style="color:#C9CA6B">&quot;1.0 + {base_offset + s}c&quot;</span>, <span style="color:#C9CA6B">f&quot;1.0 + {base_offset + e}c&quot;</span>)

    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Progress popup helpers (centered, auto-close)</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">center_window</span>(win):
    win.<span style="color:#33CCFF">update_idletasks</span>()
    <span style="color:#8A2BE2">w</span> = win.<span style="color:#33CCFF">winfo_width</span>()
    <span style="color:#8A2BE2">h</span> = win.<span style="color:#33CCFF">winfo_height</span>()
    <span style="color:#8A2BE2">sw</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">winfo_screenwidth</span>()
    <span style="color:#8A2BE2">sh</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">winfo_screenheight</span>()
    <span style="color:#8A2BE2">x</span> = max(<span style="color:#FDFD6A">0</span>, (<span style="color:#8A2BE2">sw</span> // <span style="color:#FDFD6A">2</span>) - (<span style="color:#8A2BE2">w</span> // <span style="color:#FDFD6A">2</span>))
    <span style="color:#8A2BE2">y</span> = max(<span style="color:#FDFD6A">0</span>, (<span style="color:#8A2BE2">sh</span> // <span style="color:#FDFD6A">2</span>) - (<span style="color:#8A2BE2">h</span> // <span style="color:#FDFD6A">2</span>))
    win.<span style="color:#33CCFF">geometry</span>(<span style="color:#C9CA6B">f&quot;{w}x{h}+{x}+{y}&quot;</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">show_progress_popup</span>(<span style="color:#8A2BE2">title</span>, determinate=<span style="color:#9CDCFE">True</span>):
    <span style="color:#C9CA6B">&quot;&quot;&quot;
    Create a centered progress dialog and return (dlg, progressbar, status_label).

    By default the progressbar is determinate (determinate=True). Callers that
    prefer an indeterminate spinner can pass determinate=False.

    The returned Progressbar widget will have a 0-100 range when determinate.
    &quot;&quot;&quot;</span>
    <span style="color:#8A2BE2">dlg</span> = Toplevel(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">title</span></span>(<span style="color:#8A2BE2">title</span>)
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">transient</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">grab_set</span>()
    Label(<span style="color:#8A2BE2">dlg</span>, text=<span style="color:#8A2BE2">title</span>).<span style="color:#33CCFF">pack</span>(padx=<span style="color:#FDFD6A">10</span>, pady=(<span style="color:#FDFD6A">10</span>, <span style="color:#FDFD6A">0</span>))

    <span style="color:#FF0000">if</span> determinate:
        <span style="color:#8A2BE2">pb</span> = ttk.<span style="color:#33CCFF">Progressbar</span>(<span style="color:#8A2BE2">dlg</span>, mode=<span style="color:#C9CA6B">&#x27;determinate&#x27;</span>, length=<span style="color:#FDFD6A">360</span>, maximum=<span style="color:#FDFD6A">100</span>, value=<span style="color:#FDFD6A">0</span>)
    <span style="color:#FF0000">else</span>:
        <span style="color:#8A2BE2">pb</span> = ttk.<span style="color:#33CCFF">Progressbar</span>(<span style="color:#8A2BE2">dlg</span>, mode=<span style="color:#C9CA6B">&#x27;indeterminate&#x27;</span>, length=<span style="color:#FDFD6A">360</span>)

    <span style="color:#8A2BE2">pb</span>.<span style="color:#33CCFF">pack</span>(padx=<span style="color:#FDFD6A">10</span>, pady=<span style="color:#FDFD6A">10</span>)
    <span style="color:#8A2BE2">status</span> = Label(<span style="color:#8A2BE2">dlg</span>, text=<span style="color:#C9CA6B">&quot;&quot;</span>)
    <span style="color:#8A2BE2">status</span>.<span style="color:#33CCFF">pack</span>(padx=<span style="color:#FDFD6A">10</span>, pady=(<span style="color:#FDFD6A">0</span>, <span style="color:#FDFD6A">10</span>))
    <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">update_idletasks</span>()
    <span style="color:#FFA500">center_window</span>(<span style="color:#8A2BE2">dlg</span>)

    <span style="color:#75715E"># start indeterminate only when requested</span>
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> determinate:
        <span style="color:#FF0000">try</span>:
            <span style="color:#8A2BE2">pb</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

    <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>, <span style="color:#8A2BE2">status</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">close_progress_popup</span>(<span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>=<span style="color:#9CDCFE">None</span>):
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">pb</span>:
            <span style="color:#8A2BE2">pb</span>.<span style="color:#33CCFF">stop</span>()
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">grab_release</span>()
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">destroy</span>()
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#FF0000">def</span> <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInit</span></span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Trigger a non-blocking initial syntax scan on load (snapshot + background worker).&quot;&quot;&quot;</span>
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">updateSyntaxHighlighting</span></span>.<span style="color:#33CCFF">get</span>():
        <span style="color:#75715E"># clear tags (include new tags)</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;string&#x27;</span>, <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>, <span style="color:#C9CA6B">&#x27;comment&#x27;</span>, <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>, <span style="color:#C9CA6B">&#x27;def&#x27;</span>, <span style="color:#C9CA6B">&#x27;number&#x27;</span>, <span style="color:#C9CA6B">&#x27;variable&#x27;</span>,
                  <span style="color:#C9CA6B">&#x27;decorator&#x27;</span>, <span style="color:#C9CA6B">&#x27;class_name&#x27;</span>, <span style="color:#C9CA6B">&#x27;constant&#x27;</span>, <span style="color:#C9CA6B">&#x27;attribute&#x27;</span>, <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>, <span style="color:#C9CA6B">&#x27;todo&#x27;</span>):
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#8A2BE2">t</span>, <span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end&quot;</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Syntax highlighting disabled.&quot;</span>
        <span style="color:#FF0000">return</span>

    <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Processing initial syntax...&quot;</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">update_idletasks</span>()

    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">content_snapshot</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end-1c&quot;</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#8A2BE2">content_snapshot</span> = <span style="color:#C9CA6B">&quot;&quot;</span>

    <span style="color:#75715E"># show progress popup (starts indeterminate)</span>
    <span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>, <span style="color:#8A2BE2">status</span> = <span style="color:#FFA500">show_progress_popup</span>(<span style="color:#C9CA6B">&quot;Initial syntax highlighting&quot;</span>)
    <span style="color:#8A2BE2">status</span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Scanning...&quot;</span>

    <span style="color:#75715E"># progress callback MUST be safe to call from worker thread.</span>
    <span style="color:#FF0000">def</span> <span style="color:#FFA500">progress_cb</span>(pct, msg=<span style="color:#C9CA6B">&quot;&quot;</span>):
        <span style="color:#75715E"># schedule UI update on main thread</span>
        <span style="color:#FF0000">def</span> <span style="color:#FFA500">ui</span>():
            <span style="color:#FF0000">try</span>:
                <span style="color:#75715E"># switch to determinate on first meaningful update</span>
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">pb</span>[<span style="color:#C9CA6B">&#x27;mode&#x27;</span>] != <span style="color:#C9CA6B">&#x27;determinate&#x27;</span>:
                    <span style="color:#8A2BE2">pb</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(mode=<span style="color:#C9CA6B">&#x27;determinate&#x27;</span>, maximum=<span style="color:#FDFD6A">100</span>)
                <span style="color:#8A2BE2">pb</span>[<span style="color:#C9CA6B">&#x27;value&#x27;</span>] = max(<span style="color:#FDFD6A">0</span>, min(<span style="color:#FDFD6A">100</span>, <span style="color:#9CDCFE">int</span>(pct)))
                <span style="color:#8A2BE2">status</span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = msg <span style="color:#FF0000">or</span> <span style="color:#C9CA6B">f&quot;{pb[&#x27;value&#x27;]}%&quot;</span>
                <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">update_idletasks</span>()
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#FF0000">pass</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFA500">ui</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">worker</span>():
        <span style="color:#8A2BE2">actions</span>, <span style="color:#8A2BE2">new_vars</span>, <span style="color:#8A2BE2">new_defs</span> = <span style="color:#FFA500">_bg_full_scan_and_collect</span>(<span style="color:#8A2BE2">content_snapshot</span>, progress_callback=<span style="color:#FFA500">progress_cb</span>)
        <span style="color:#75715E"># schedule application of tags on UI thread and finish-up steps</span>
        <span style="color:#FF0000">def</span> <span style="color:#FFA500">apply_and_finish</span>():
            <span style="color:#FF0000">try</span>:
                <span style="color:#FFA500">_apply_full_tags</span>(<span style="color:#8A2BE2">actions</span>, <span style="color:#8A2BE2">new_vars</span>, <span style="color:#8A2BE2">new_defs</span>)
                <span style="color:#75715E"># Full content scan to discover new symbols (persist them)</span>
                <span style="color:#8A2BE2">full</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end-1c&quot;</span>)
                <span style="color:#8A2BE2">new_vars2</span> = {<span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">VAR_ASSIGN_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">full</span>)}
                <span style="color:#FF0000">try</span>:
                    <span style="color:#8A2BE2"><span style="color:#FF79C6">DEF_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(?m)^[ \t]*def\s+([A-Za-z_]\w*)\s*\(&#x27;</span>)
                <span style="color:#FF0000">except</span> Exception:
                    <span style="color:#8A2BE2"><span style="color:#FF79C6">DEF_RE</span></span> = <span style="color:#9CDCFE">None</span>
                <span style="color:#8A2BE2">new_defs2</span> = <span style="color:#9CDCFE">set</span>()
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">DEF_RE</span>:
                    <span style="color:#8A2BE2">new_defs2</span> = {<span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">DEF_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">full</span>)}
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">new_vars2</span>:
                    persisted_vars.<span style="color:#33CCFF">update</span>(<span style="color:#8A2BE2">new_vars2</span>)
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">new_defs2</span>:
                    persisted_defs.<span style="color:#33CCFF">update</span>(<span style="color:#8A2BE2">new_defs2</span>)
                <span style="color:#FFA500">_save_symbol_buffers</span>(persisted_vars, persisted_defs)

                <span style="color:#75715E"># force full-buffer scan and tagging</span>
                <span style="color:#FFA500">highlight_python_helper</span>(<span style="color:#9CDCFE">None</span>, scan_start=<span style="color:#C9CA6B">&quot;1.0&quot;</span>, scan_end=<span style="color:#C9CA6B">&quot;end-1c&quot;</span>)
                <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Ready&quot;</span>
            <span style="color:#FF0000">finally</span>:
                <span style="color:#FFA500">close_progress_popup</span>(<span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>)

        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFA500">apply_and_finish</span>)
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FFA500">close_progress_popup</span>(<span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>)

    Thread(target=<span style="color:#FFA500">worker</span>, daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()


<span style="color:#FF0000">def</span> <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInitT</span></span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Compatibility wrapper used around the codebase; simply calls the non-blocking init.&quot;&quot;&quot;</span>
    <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInit</span></span>()


<span style="color:#FF0000">def</span> <span style="color:#FFA500">refresh_full_syntax</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Manual refresh for full-file syntax highlighting with progress popup.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">updateSyntaxHighlighting</span></span>.<span style="color:#33CCFF">get</span>():
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;string&#x27;</span>, <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>, <span style="color:#C9CA6B">&#x27;comment&#x27;</span>, <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>, <span style="color:#C9CA6B">&#x27;def&#x27;</span>, <span style="color:#C9CA6B">&#x27;number&#x27;</span>, <span style="color:#C9CA6B">&#x27;variable&#x27;</span>,
                  <span style="color:#C9CA6B">&#x27;decorator&#x27;</span>, <span style="color:#C9CA6B">&#x27;class_name&#x27;</span>, <span style="color:#C9CA6B">&#x27;constant&#x27;</span>, <span style="color:#C9CA6B">&#x27;attribute&#x27;</span>, <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>, <span style="color:#C9CA6B">&#x27;todo&#x27;</span>):
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#8A2BE2">t</span>, <span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end&quot;</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Syntax highlighting disabled.&quot;</span>
        <span style="color:#FF0000">return</span>

    <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Refreshing syntax...&quot;</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">update_idletasks</span>()

    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">content_snapshot</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end-1c&quot;</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#8A2BE2">content_snapshot</span> = <span style="color:#C9CA6B">&quot;&quot;</span>

    <span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>, <span style="color:#8A2BE2">status</span> = <span style="color:#FFA500">show_progress_popup</span>(<span style="color:#C9CA6B">&quot;Refreshing syntax&quot;</span>)
    <span style="color:#8A2BE2">status</span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Scanning...&quot;</span>

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">progress_cb</span>(pct, msg=<span style="color:#C9CA6B">&quot;&quot;</span>):
        <span style="color:#FF0000">def</span> <span style="color:#FFA500">ui</span>():
            <span style="color:#FF0000">try</span>:
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">pb</span>[<span style="color:#C9CA6B">&#x27;mode&#x27;</span>] != <span style="color:#C9CA6B">&#x27;determinate&#x27;</span>:
                    <span style="color:#8A2BE2">pb</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(mode=<span style="color:#C9CA6B">&#x27;determinate&#x27;</span>, maximum=<span style="color:#FDFD6A">100</span>)
                <span style="color:#8A2BE2">pb</span>[<span style="color:#C9CA6B">&#x27;value&#x27;</span>] = max(<span style="color:#FDFD6A">0</span>, min(<span style="color:#FDFD6A">100</span>, <span style="color:#9CDCFE">int</span>(pct)))
                <span style="color:#8A2BE2">status</span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = msg <span style="color:#FF0000">or</span> <span style="color:#C9CA6B">f&quot;{pb[&#x27;value&#x27;]}%&quot;</span>
                <span style="color:#8A2BE2">dlg</span>.<span style="color:#33CCFF">update_idletasks</span>()
            <span style="color:#FF0000">except</span> Exception:
                <span style="color:#FF0000">pass</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFA500">ui</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">worker</span>():
        <span style="color:#8A2BE2">actions</span>, <span style="color:#8A2BE2">new_vars</span>, <span style="color:#8A2BE2">new_defs</span> = <span style="color:#FFA500">_bg_full_scan_and_collect</span>(<span style="color:#8A2BE2">content_snapshot</span>, progress_callback=<span style="color:#FFA500">progress_cb</span>)
        <span style="color:#FF0000">def</span> <span style="color:#FFA500">apply_and_close</span>():
            <span style="color:#FF0000">try</span>:
                <span style="color:#FFA500">_apply_full_tags</span>(<span style="color:#8A2BE2">actions</span>, <span style="color:#8A2BE2">new_vars</span>, <span style="color:#8A2BE2">new_defs</span>)
                <span style="color:#75715E"># persist any discoveries from a full scan</span>
                <span style="color:#8A2BE2">full</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end-1c&quot;</span>)
                <span style="color:#8A2BE2">new_vars2</span> = {<span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">VAR_ASSIGN_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">full</span>)}
                <span style="color:#FF0000">try</span>:
                    <span style="color:#8A2BE2"><span style="color:#FF79C6">DEF_RE</span></span> = re.<span style="color:#33CCFF">compile</span>(r<span style="color:#C9CA6B">&#x27;(?m)^[ \t]*def\s+([A-Za-z_]\w*)\s*\(&#x27;</span>)
                <span style="color:#FF0000">except</span> Exception:
                    <span style="color:#8A2BE2"><span style="color:#FF79C6">DEF_RE</span></span> = <span style="color:#9CDCFE">None</span>
                <span style="color:#8A2BE2">new_defs2</span> = <span style="color:#9CDCFE">set</span>()
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">DEF_RE</span>:
                    <span style="color:#8A2BE2">new_defs2</span> = {<span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">DEF_RE</span>.<span style="color:#33CCFF">finditer</span>(<span style="color:#8A2BE2">full</span>)}
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">new_vars2</span>:
                    persisted_vars.<span style="color:#33CCFF">update</span>(<span style="color:#8A2BE2">new_vars2</span>)
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">new_defs2</span>:
                    persisted_defs.<span style="color:#33CCFF">update</span>(<span style="color:#8A2BE2">new_defs2</span>)
                <span style="color:#FFA500">_save_symbol_buffers</span>(persisted_vars, persisted_defs)
                <span style="color:#FFA500">highlight_python_helper</span>(<span style="color:#9CDCFE">None</span>, scan_start=<span style="color:#C9CA6B">&quot;1.0&quot;</span>, scan_end=<span style="color:#C9CA6B">&quot;end-1c&quot;</span>)
                <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Ready&quot;</span>
            <span style="color:#FF0000">finally</span>:
                <span style="color:#FFA500">close_progress_popup</span>(<span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>)

        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFA500">apply_and_close</span>)
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FFA500">close_progress_popup</span>(<span style="color:#8A2BE2">dlg</span>, <span style="color:#8A2BE2">pb</span>)

    Thread(target=<span style="color:#FFA500">worker</span>, daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Utility ribbons: trailing whitespace, line numbers, caret</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">show_trailing_whitespace</span>():
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">first_visible</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;@0,0&#x27;</span>)
        <span style="color:#8A2BE2">last_visible</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(f<span style="color:#C9CA6B">&#x27;@0,{textArea.winfo_height()}&#x27;</span>)
        <span style="color:#8A2BE2">start_line</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">first_visible</span>.<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[<span style="color:#FDFD6A">0</span>])
        <span style="color:#8A2BE2">end_line</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">last_visible</span>.<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[<span style="color:#FDFD6A">0</span>])
        <span style="color:#FF0000">for</span> ln <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#8A2BE2">start_line</span>, <span style="color:#8A2BE2">end_line</span> + <span style="color:#FDFD6A">1</span>):
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#C9CA6B">&#x27;trailingWhitespace&#x27;</span>, f<span style="color:#C9CA6B">&#x27;{ln}.0&#x27;</span>, f<span style="color:#C9CA6B">&#x27;{ln}.0 lineend&#x27;</span>)
        <span style="color:#FF0000">for</span> ln <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#8A2BE2">start_line</span>, <span style="color:#8A2BE2">end_line</span> + <span style="color:#FDFD6A">1</span>):
            <span style="color:#8A2BE2">line_text</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(f<span style="color:#C9CA6B">&#x27;{ln}.0&#x27;</span>, f<span style="color:#C9CA6B">&#x27;{ln}.0 lineend&#x27;</span>)
            <span style="color:#8A2BE2">m</span> = re.<span style="color:#33CCFF">search</span>(r<span style="color:#C9CA6B">&#x27;[ \t]+$&#x27;</span>, <span style="color:#8A2BE2">line_text</span>)
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m</span>:
                <span style="color:#8A2BE2">s</span> = f<span style="color:#C9CA6B">&#x27;{ln}.0 + {m.start()}c&#x27;</span>
                <span style="color:#8A2BE2">e</span> = f<span style="color:#C9CA6B">&#x27;{ln}.0 + {m.end()}c&#x27;</span>
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&#x27;trailingWhitespace&#x27;</span>, <span style="color:#8A2BE2">s</span>, <span style="color:#8A2BE2">e</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#8A2BE2">pairs</span> = {<span style="color:#C9CA6B">&#x27;(&#x27;</span>: <span style="color:#C9CA6B">&#x27;)&#x27;</span>, <span style="color:#C9CA6B">&#x27;[&#x27;</span>: <span style="color:#C9CA6B">&#x27;]&#x27;</span>, <span style="color:#C9CA6B">&#x27;{&#x27;</span>: <span style="color:#C9CA6B">&#x27;}&#x27;</span>, <span style="color:#C9CA6B">&#x27;&quot;&#x27;</span>: <span style="color:#C9CA6B">&#x27;&quot;&#x27;</span>, <span style="color:#C9CA6B">&quot;&#x27;&quot;</span>: <span style="color:#C9CA6B">&quot;&#x27;&quot;</span>}


<span style="color:#FF0000">def</span> <span style="color:#FFA500">auto_pair</span>(event):
    <span style="color:#8A2BE2">ch</span> = event.<span style="color:#33CCFF">char</span>
    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">ch</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">pairs</span>:
        <span style="color:#8A2BE2">sel</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#C9CA6B">&#x27;sel&#x27;</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">sel</span>:
            <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span> = <span style="color:#8A2BE2">sel</span>
            <span style="color:#8A2BE2">inside</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">ch</span> + <span style="color:#8A2BE2">inside</span> + <span style="color:#8A2BE2">pairs</span>[<span style="color:#8A2BE2">ch</span>])
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">mark_set</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, <span style="color:#C9CA6B">f&quot;{start}+{len(ch) + len(inside)}c&quot;</span>)
        <span style="color:#FF0000">else</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, <span style="color:#8A2BE2">ch</span> + <span style="color:#8A2BE2">pairs</span>[<span style="color:#8A2BE2">ch</span>])
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">mark_set</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, <span style="color:#C9CA6B">&#x27;insert-1c&#x27;</span>)
        <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;break&#x27;</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">redraw_line_numbers</span>(event=<span style="color:#9CDCFE">None</span>):
    <span style="color:#FF0000">global</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span>
    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span>:
        <span style="color:#FF0000">return</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#C9CA6B">&#x27;all&#x27;</span>)
    <span style="color:#8A2BE2">i</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;@0,0&#x27;</span>)
    <span style="color:#FF0000">while</span> <span style="color:#9CDCFE">True</span>:
        <span style="color:#8A2BE2">dline</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">dlineinfo</span>(<span style="color:#8A2BE2">i</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">dline</span> <span style="color:#FF0000">is</span> <span style="color:#9CDCFE">None</span>:
            <span style="color:#FF0000">break</span>
        <span style="color:#8A2BE2">y</span> = <span style="color:#8A2BE2">dline</span>[<span style="color:#FDFD6A">1</span>]
        <span style="color:#8A2BE2">line</span> = <span style="color:#8A2BE2">i</span>.<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[<span style="color:#FDFD6A">0</span>]
        <span style="color:#FFFF00"><span style="color:#8A2BE2">lineNumbersCanvas</span></span>.<span style="color:#33CCFF">create_text</span>(<span style="color:#FDFD6A">2</span>, <span style="color:#8A2BE2">y</span>, anchor=<span style="color:#C9CA6B">&#x27;nw&#x27;</span>, text=<span style="color:#8A2BE2">line</span>, fill=<span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#555555&#x27;</span></span>)
        <span style="color:#8A2BE2">i</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(f<span style="color:#C9CA6B">&#x27;{i}+1line&#x27;</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">go_to_line</span>():
    <span style="color:#8A2BE2">line</span> = simpledialog.<span style="color:#33CCFF">askinteger</span>(<span style="color:#C9CA6B">&quot;Go To Line&quot;</span>, <span style="color:#C9CA6B">&quot;Line number:&quot;</span>, parent=<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>, minvalue=<span style="color:#FDFD6A">1</span>)
    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">line</span>:
        <span style="color:#8A2BE2">max_line</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>).<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[<span style="color:#FDFD6A">0</span>])
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">line</span> &gt; <span style="color:#8A2BE2">max_line</span>:
            <span style="color:#8A2BE2">line</span> = <span style="color:#8A2BE2">max_line</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">mark_set</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, f<span style="color:#C9CA6B">&#x27;{line}.0&#x27;</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">see</span>(f<span style="color:#C9CA6B">&#x27;{line}.0&#x27;</span>)
        <span style="color:#FFA500">highlight_current_line</span>()
        <span style="color:#FFA500">update_status_bar</span>()


<span style="color:#FF0000">def</span> <span style="color:#FFA500">open_find_replace</span>():
    <span style="color:#8A2BE2">fr</span> = Toplevel(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
    <span style="color:#8A2BE2">fr</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">title</span></span>(<span style="color:#C9CA6B">&quot;Find / Replace&quot;</span>)
    Label(<span style="color:#8A2BE2">fr</span>, text=<span style="color:#C9CA6B">&quot;Find&quot;</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">0</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">findE</span></span> = Entry(<span style="color:#8A2BE2">fr</span>, width=<span style="color:#FDFD6A">30</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">findE</span></span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">1</span>)
    Label(<span style="color:#8A2BE2">fr</span>, text=<span style="color:#C9CA6B">&quot;Replace&quot;</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">1</span>, column=<span style="color:#FDFD6A">0</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">replE</span></span> = Entry(<span style="color:#8A2BE2">fr</span>, width=<span style="color:#FDFD6A">30</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">replE</span></span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">1</span>, column=<span style="color:#FDFD6A">1</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">statusL</span></span> = Label(<span style="color:#8A2BE2">fr</span>, text=<span style="color:#C9CA6B">&quot;&quot;</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">statusL</span></span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">3</span>, columnspan=<span style="color:#FDFD6A">2</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">do_find</span>():
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#C9CA6B">&#x27;find_match&#x27;</span>, <span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
        <span style="color:#8A2BE2">pat</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">findE</span></span>.<span style="color:#33CCFF">get</span>()
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">pat</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#8A2BE2">content</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>)
        <span style="color:#8A2BE2">count</span> = <span style="color:#FDFD6A">0</span>
        <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">in</span> re.<span style="color:#33CCFF">finditer</span>(re.<span style="color:#33CCFF">escape</span>(<span style="color:#8A2BE2">pat</span>), <span style="color:#8A2BE2">content</span>):
            <span style="color:#8A2BE2">start</span> = <span style="color:#C9CA6B">f&quot;1.0 + {m.start()}c&quot;</span>
            <span style="color:#8A2BE2">end</span> = <span style="color:#C9CA6B">f&quot;1.0 + {m.end()}c&quot;</span>
            <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&#x27;find_match&#x27;</span>, <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)
            <span style="color:#8A2BE2">count</span> += <span style="color:#FDFD6A">1</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusL</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">f&quot;Matches: {count}&quot;</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">do_replace</span>():
        <span style="color:#8A2BE2">pat</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">findE</span></span>.<span style="color:#33CCFF">get</span>()
        <span style="color:#8A2BE2">repl</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">replE</span></span>.<span style="color:#33CCFF">get</span>()
        <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">pat</span>:
            <span style="color:#FF0000">return</span>
        <span style="color:#8A2BE2">content</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end-1c&#x27;</span>)
        <span style="color:#8A2BE2">new_content</span> = <span style="color:#8A2BE2">content</span>.<span style="color:#33CCFF">replace</span>(<span style="color:#8A2BE2">pat</span>, <span style="color:#8A2BE2">repl</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#8A2BE2">new_content</span>)
        <span style="color:#FFA500">do_find</span>()

    Button(<span style="color:#8A2BE2">fr</span>, text=<span style="color:#C9CA6B">&#x27;Find&#x27;</span>, command=<span style="color:#FFA500">do_find</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">2</span>, column=<span style="color:#FDFD6A">0</span>)
    Button(<span style="color:#8A2BE2">fr</span>, text=<span style="color:#C9CA6B">&#x27;Replace All&#x27;</span>, command=<span style="color:#FFA500">do_replace</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">2</span>, column=<span style="color:#FDFD6A">1</span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">update_status_bar</span>(event=<span style="color:#9CDCFE">None</span>):
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">line</span>, col = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>).<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">f&quot;Ln {line} Col {int(col) + 1}&quot;</span>
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>

    <span style="color:#75715E"># update params display if model is loaded (kept separate so line/col remains primary)</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_model_loaded</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">paramsLabel</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#FFA500">_get_model_param_text</span>())
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#FF0000">def</span> <span style="color:#FFA500">highlight_current_line</span>(event=<span style="color:#9CDCFE">None</span>):
    <span style="color:#FF0000">try</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#C9CA6B">&#x27;currentLine&#x27;</span>, <span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
        <span style="color:#8A2BE2">line</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>).<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[<span style="color:#FDFD6A">0</span>]
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_add</span>(<span style="color:#C9CA6B">&#x27;currentLine&#x27;</span>, f<span style="color:#C9CA6B">&#x27;{line}.0&#x27;</span>, f<span style="color:#C9CA6B">&#x27;{line}.0 lineend+1c&#x27;</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>


<span style="color:#75715E"># CHANGED: smart newline that preserves indentation context</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">smart_newline</span>(event):
    <span style="color:#FF0000">try</span>:
        <span style="color:#8A2BE2">insert_index</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>)
        <span style="color:#8A2BE2">line_no</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">insert_index</span>.<span style="color:#33CCFF">split</span>(<span style="color:#C9CA6B">&#x27;.&#x27;</span>)[<span style="color:#FDFD6A">0</span>])
        <span style="color:#8A2BE2">line_start</span> = <span style="color:#C9CA6B">f&quot;{line_no}.0&quot;</span>
        <span style="color:#8A2BE2">before</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">line_start</span>, <span style="color:#8A2BE2">insert_index</span>)
        <span style="color:#8A2BE2">leading_ws_match</span> = re.<span style="color:#FF0000"><span style="color:#33CCFF">match</span></span>(r<span style="color:#C9CA6B">&#x27;([ \t]*)&#x27;</span>, <span style="color:#8A2BE2">before</span>)
        <span style="color:#8A2BE2">current_indent</span> = <span style="color:#8A2BE2">leading_ws_match</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">leading_ws_match</span> <span style="color:#FF0000">else</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>
        <span style="color:#8A2BE2">indent_unit</span> = <span style="color:#C9CA6B">&#x27;\t&#x27;</span> <span style="color:#FF0000">if</span> <span style="color:#C9CA6B">&#x27;\t&#x27;</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">current_indent</span> <span style="color:#FF0000">else</span> <span style="color:#C9CA6B">&#x27; &#x27;</span> * <span style="color:#FDFD6A">4</span>
        <span style="color:#8A2BE2">stripped_left</span> = <span style="color:#8A2BE2">before</span>.<span style="color:#33CCFF">rstrip</span>()
        <span style="color:#8A2BE2">dedent_keywords</span> = (<span style="color:#C9CA6B">&#x27;return&#x27;</span>, <span style="color:#C9CA6B">&#x27;pass&#x27;</span>, <span style="color:#C9CA6B">&#x27;break&#x27;</span>, <span style="color:#C9CA6B">&#x27;continue&#x27;</span>, <span style="color:#C9CA6B">&#x27;raise&#x27;</span>, <span style="color:#C9CA6B">&#x27;yield&#x27;</span>)
        <span style="color:#8A2BE2">new_indent</span> = <span style="color:#8A2BE2">current_indent</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">stripped_left</span>.<span style="color:#33CCFF">endswith</span>(<span style="color:#C9CA6B">&#x27;:&#x27;</span>):
            <span style="color:#8A2BE2">new_indent</span> = <span style="color:#8A2BE2">current_indent</span> + <span style="color:#8A2BE2">indent_unit</span>
        <span style="color:#FF0000">else</span>:
            <span style="color:#8A2BE2">left_no_comment</span> = re.<span style="color:#33CCFF">split</span>(r<span style="color:#C9CA6B">&#x27;<span style="color:#75715E">#&#x27;</span></span>, stripped_left, 1)[0].strip()
            <span style="color:#8A2BE2">left_tokens</span> = <span style="color:#8A2BE2">left_no_comment</span>.<span style="color:#33CCFF">split</span>()
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">left_tokens</span> <span style="color:#FF0000">and</span> <span style="color:#8A2BE2">left_tokens</span>[<span style="color:#FDFD6A">0</span>] <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">dedent_keywords</span>:
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">current_indent</span>.<span style="color:#33CCFF">endswith</span>(<span style="color:#8A2BE2">indent_unit</span>):
                    <span style="color:#8A2BE2">new_indent</span> = <span style="color:#8A2BE2">current_indent</span>[:-<span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">indent_unit</span>)]
                <span style="color:#FF0000">else</span>:
                    <span style="color:#8A2BE2">new_indent</span> = <span style="color:#8A2BE2">current_indent</span>[:-<span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">indent_unit</span>)] <span style="color:#FF0000">if</span> <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">current_indent</span>) &gt;= <span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">indent_unit</span>) <span style="color:#FF0000">else</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>
            elif <span style="color:#8A2BE2">current_indent</span> == <span style="color:#C9CA6B">&#x27;&#x27;</span> <span style="color:#FF0000">and</span> <span style="color:#8A2BE2">stripped_left</span>.<span style="color:#33CCFF">strip</span>() != <span style="color:#C9CA6B">&#x27;&#x27;</span>:
                <span style="color:#8A2BE2">prev</span> = <span style="color:#8A2BE2">line_no</span> - <span style="color:#FDFD6A">1</span>
                <span style="color:#8A2BE2">prev_indent</span> = <span style="color:#C9CA6B">&#x27;&#x27;</span>
                <span style="color:#FF0000">while</span> <span style="color:#8A2BE2">prev</span> &gt;= <span style="color:#FDFD6A">1</span>:
                    <span style="color:#8A2BE2">prev_line</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">f&#x27;{prev}.0&#x27;</span>, f<span style="color:#C9CA6B">&#x27;{prev}.end&#x27;</span>)
                    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">prev_line</span>.<span style="color:#33CCFF">strip</span>() != <span style="color:#C9CA6B">&#x27;&#x27;</span>:
                        <span style="color:#8A2BE2">m</span> = re.<span style="color:#FF0000"><span style="color:#33CCFF">match</span></span>(r<span style="color:#C9CA6B">&#x27;([ \t]*)&#x27;</span>, <span style="color:#8A2BE2">prev_line</span>)
                        <span style="color:#8A2BE2">prev_indent</span> = <span style="color:#8A2BE2">m</span>.<span style="color:#33CCFF">group</span>(<span style="color:#FDFD6A">1</span>) <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">m</span> <span style="color:#FF0000">else</span> <span style="color:#C9CA6B">&#x27;&#x27;</span>
                        <span style="color:#FF0000">break</span>
                    <span style="color:#8A2BE2">prev</span> -= <span style="color:#FDFD6A">1</span>
                <span style="color:#8A2BE2">new_indent</span> = <span style="color:#8A2BE2">prev_indent</span>

        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, <span style="color:#C9CA6B">&#x27;\n&#x27;</span> + <span style="color:#8A2BE2">new_indent</span>)
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, <span style="color:#C9CA6B">&#x27;\n&#x27;</span>)
    <span style="color:#FF0000">return</span> <span style="color:#C9CA6B">&#x27;break&#x27;</span>


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># AI autocomplete (optional)</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">python_ai_autocomplete</span>():
    <span style="color:#FF0000">global</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonA</span></span>I
    <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">model</span> <span style="color:#FF0000">is</span> <span style="color:#9CDCFE">None</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;AI model not available.&quot;</span>
        <span style="color:#FF0000">return</span>

    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">try</span>:
            <span style="color:#8A2BE2">ranges</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_ranges</span>(<span style="color:#C9CA6B">&quot;sel&quot;</span>)
            <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">ranges</span>:
                <span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span> = <span style="color:#8A2BE2">ranges</span>[<span style="color:#FDFD6A">0</span>], <span style="color:#8A2BE2">ranges</span>[<span style="color:#FDFD6A">1</span>]
            <span style="color:#FF0000">else</span>:
                <span style="color:#8A2BE2">start</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(f<span style="color:#C9CA6B">&#x27;insert-{aiMaxContext}c&#x27;</span>)
                <span style="color:#8A2BE2">end</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>)
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#8A2BE2">start</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(f<span style="color:#C9CA6B">&#x27;insert-{aiMaxContext}c&#x27;</span>)
            <span style="color:#8A2BE2">end</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">index</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>)

        <span style="color:#8A2BE2">content</span> = <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">get</span>(<span style="color:#8A2BE2">start</span>, <span style="color:#8A2BE2">end</span>)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">maxTokens</span></span> = <span style="color:#9CDCFE">int</span>(<span style="color:#9CDCFE">len</span>(<span style="color:#8A2BE2">content</span>) / <span style="color:#FDFD6A">8</span> + <span style="color:#FDFD6A">128</span>)
        <span style="color:#8A2BE2">skipstrip</span> = <span style="color:#9CDCFE">False</span>
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">content</span> == <span style="color:#C9CA6B">&#x27;&#x27;</span>:
            <span style="color:#8A2BE2">skipstrip</span> = <span style="color:#9CDCFE">True</span>
            <span style="color:#8A2BE2">content</span> = <span style="color:#C9CA6B">&#x27;&lt;|endoftext|&gt;&#x27;</span>

        <span style="color:#8A2BE2">start_ids</span> = <span style="color:#8A2BE2">encode</span>(<span style="color:#8A2BE2">content</span>)
        <span style="color:#75715E"># prepare tensor on CPU</span>
        <span style="color:#8A2BE2">idx</span> = torch.<span style="color:#33CCFF">tensor</span>(<span style="color:#8A2BE2">start_ids</span>, dtype=torch.<span style="color:#33CCFF">long</span>, device=<span style="color:#C9CA6B">&#x27;cpu&#x27;</span>)[<span style="color:#9CDCFE">None</span>, :]

        <span style="color:#75715E"># update button to show current context length (UI thread)</span>
        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">n</span>=<span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">idx</span>.<span style="color:#33CCFF">size</span>(<span style="color:#FDFD6A">1</span>)): <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonA</span></span>I.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">f&quot;AI Autocomplete - ctx: {n}&quot;</span>))
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

        <span style="color:#75715E"># ensure UI is prepared: delete selection and set insert at start on main thread</span>
        <span style="color:#8A2BE2">prep_done</span> = threading.<span style="color:#33CCFF">Event</span>()

        <span style="color:#FF0000">def</span> <span style="color:#FFA500">ui_prep</span>():
            <span style="color:#FF0000">try</span>:
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">mark_set</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, <span style="color:#8A2BE2">end</span>)
                <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#C9CA6B">&quot;sel&quot;</span>, <span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
            <span style="color:#FF0000">finally</span>:
                <span style="color:#8A2BE2">prep_done</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>()

        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFA500">ui_prep</span>)
        <span style="color:#8A2BE2">prep_done</span>.<span style="color:#33CCFF">wait</span>()

        <span style="color:#8A2BE2">generated_ids</span> = []

        <span style="color:#75715E"># generation loop: sample one token at a time and stream it to the UI</span>
        <span style="color:#FF0000">with</span> torch.<span style="color:#33CCFF">inference_mode</span>():
            <span style="color:#FF0000">for</span> _ <span style="color:#FF0000">in</span> <span style="color:#9CDCFE">range</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">maxTokens</span></span>):
                <span style="color:#75715E"># crop context if needed</span>
                <span style="color:#8A2BE2">idx_cond</span> = <span style="color:#8A2BE2">idx</span> <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">idx</span>.<span style="color:#33CCFF">size</span>(<span style="color:#FDFD6A">1</span>) &lt;= <span style="color:#8A2BE2">model</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>.<span style="color:#33CCFF">block_size</span> <span style="color:#FF0000">else</span> <span style="color:#8A2BE2">idx</span>[:, -<span style="color:#8A2BE2">model</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>.<span style="color:#33CCFF">block_size</span>:]
                <span style="color:#8A2BE2">logits</span>, _ = <span style="color:#8A2BE2">model</span>(<span style="color:#8A2BE2">idx_cond</span>)
                <span style="color:#8A2BE2">logits</span> = <span style="color:#8A2BE2">logits</span>[:, -<span style="color:#FDFD6A">1</span>, :] / <span style="color:#8A2BE2">temperature</span>
                <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">top_k</span> <span style="color:#FF0000">is</span> <span style="color:#FF0000">not</span> <span style="color:#9CDCFE">None</span>:
                    v, _ = torch.<span style="color:#33CCFF">topk</span>(<span style="color:#8A2BE2">logits</span>, min(<span style="color:#8A2BE2">top_k</span>, <span style="color:#8A2BE2">logits</span>.<span style="color:#33CCFF">size</span>(-<span style="color:#FDFD6A">1</span>)))
                    <span style="color:#8A2BE2">logits</span>[<span style="color:#8A2BE2">logits</span> &lt; v[:, [-<span style="color:#FDFD6A">1</span>]]] = -float(<span style="color:#C9CA6B">&#x27;Inf&#x27;</span>)
                <span style="color:#8A2BE2">probs</span> = torch.<span style="color:#33CCFF">nn</span>.<span style="color:#33CCFF">functional</span>.<span style="color:#33CCFF">softmax</span>(<span style="color:#8A2BE2">logits</span>, dim=-<span style="color:#FDFD6A">1</span>)
                <span style="color:#8A2BE2">next_id</span> = torch.<span style="color:#33CCFF">multinomial</span>(<span style="color:#8A2BE2">probs</span>, num_samples=<span style="color:#FDFD6A">1</span>)
                <span style="color:#8A2BE2">idx</span> = torch.<span style="color:#33CCFF">cat</span>((<span style="color:#8A2BE2">idx</span>, <span style="color:#8A2BE2">next_id</span>), dim=<span style="color:#FDFD6A">1</span>)

                <span style="color:#75715E"># update button with new context length (UI thread)</span>
                <span style="color:#FF0000">try</span>:
                    <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">n</span>=<span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">idx</span>.<span style="color:#33CCFF">size</span>(<span style="color:#FDFD6A">1</span>)): <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonA</span></span>I.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">f&quot;AI Autocomplete - ctx: {n}&quot;</span>))
                <span style="color:#FF0000">except</span> Exception:
                    <span style="color:#FF0000">pass</span>

                <span style="color:#8A2BE2">token_id</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">next_id</span>[<span style="color:#FDFD6A">0</span>, <span style="color:#FDFD6A">0</span>].<span style="color:#33CCFF">item</span>())
                <span style="color:#8A2BE2">generated_ids</span>.<span style="color:#33CCFF">append</span>(<span style="color:#8A2BE2">token_id</span>)

                <span style="color:#75715E"># decode only the newly sampled token to a string fragment</span>
                <span style="color:#FF0000">try</span>:
                    <span style="color:#8A2BE2">piece</span> = <span style="color:#8A2BE2">decode</span>([<span style="color:#8A2BE2">token_id</span>])
                <span style="color:#FF0000">except</span> Exception:
                    <span style="color:#8A2BE2">piece</span> = <span style="color:#C9CA6B">&#x27;&#x27;</span>

                <span style="color:#75715E"># map end-of-text token to newline or strip according to previous behaviour</span>
                <span style="color:#FF0000">if</span> <span style="color:#C9CA6B">&#x27;&lt;|endoftext|&gt;&#x27;</span> <span style="color:#FF0000">in</span> <span style="color:#8A2BE2">piece</span>:
                    <span style="color:#FF0000">if</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">skipstrip</span>:
                        <span style="color:#8A2BE2">piece</span> = <span style="color:#8A2BE2">piece</span>.<span style="color:#33CCFF">replace</span>(<span style="color:#C9CA6B">&#x27;&lt;|endoftext|&gt;&#x27;</span>, <span style="color:#C9CA6B">&#x27;\n&#x27;</span>)
                    <span style="color:#FF0000">else</span>:
                        <span style="color:#8A2BE2">piece</span> = <span style="color:#8A2BE2">piece</span>.<span style="color:#33CCFF">replace</span>(<span style="color:#C9CA6B">&#x27;&lt;|endoftext|&gt;&#x27;</span>, <span style="color:#C9CA6B">&#x27;&#x27;</span>)

                <span style="color:#75715E"># schedule UI insertion of this token fragment</span>
                <span style="color:#FF0000">def</span> <span style="color:#FFA500">ui_insert</span>(p=<span style="color:#8A2BE2">piece</span>):
                    <span style="color:#FF0000">try</span>:
                        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#C9CA6B">&#x27;insert&#x27;</span>, p)
                        <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">see</span>(INSERT)
                        <span style="color:#FFA500">highlight_python_helper</span>(p)
                        <span style="color:#FFA500">update_status_bar</span>()
                    <span style="color:#FF0000">except</span> Exception:
                        <span style="color:#FF0000">pass</span>

                <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FFA500">ui_insert</span>)

        <span style="color:#75715E"># final UI update + status</span>
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">0</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">&quot;AI: insertion complete.&quot;</span>))
    <span style="color:#FF0000">except</span> Exception <span style="color:#FF0000">as</span> <span style="color:#8A2BE2">e</span>:
        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">f&quot;AI error: {e}&quot;</span>
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Bindings &amp; widget wiring</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># toolbar buttons (single definitions)</span>
<span style="color:#8A2BE2">btn1</span> = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;New&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFFF00"><span style="color:#FFA500">newFile</span></span>())
<span style="color:#8A2BE2">btn1</span>.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
<span style="color:#8A2BE2">btn2</span> = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Open&#x27;</span>, command=<span style="color:#FFA500">open_file_threaded</span>)
<span style="color:#8A2BE2">btn2</span>.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
<span style="color:#8A2BE2">btn3</span> = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Save&#x27;</span>, command=<span style="color:#FFA500">save_file_as</span>)
<span style="color:#8A2BE2">btn3</span>.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">btnSaveM</span></span>D = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Save MD&#x27;</span>, command=<span style="color:#FFA500">save_as_markdown</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">btnSaveM</span></span>D.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>1 = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Bold&#x27;</span>, command=<span style="color:#FFA500">format_bold</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>1.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>2 = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Italic&#x27;</span>, command=<span style="color:#FFA500">format_italic</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>2.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>3 = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Underline&#x27;</span>, command=<span style="color:#FFA500">format_underline</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>3.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>4 = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Remove Formatting&#x27;</span>, command=<span style="color:#FFA500">remove_all_formatting</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>4.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)
<span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_ML_AVAILABLE</span>:
    <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonA</span></span>I = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#8A2BE2">_AI_BUTTON_DEFAULT_TEXT</span>, command=<span style="color:#FF0000">lambda</span>: Thread(target=<span style="color:#FFA500">on_ai_button_click</span>, daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>())
    <span style="color:#75715E"># create unload button but don&#x27;t show it until model is loaded</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonUnload</span></span> = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Unload AI&#x27;</span>, command=<span style="color:#FFA500">unload_model</span>)
<span style="color:#FF0000">else</span>:
    <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonA</span></span>I = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;AI Unavailable&#x27;</span>, state=<span style="color:#C9CA6B">&#x27;disabled&#x27;</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">buttonUnload</span></span> = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Unload AI&#x27;</span>, state=<span style="color:#C9CA6B">&#x27;disabled&#x27;</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">buttonA</span></span>I.<span style="color:#33CCFF">pack</span>(side=LEFT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)

<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>5 = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">toolBar</span></span>, text=<span style="color:#C9CA6B">&#x27;Settings&#x27;</span>, command=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">setting_modal</span>())
<span style="color:#FFFF00"><span style="color:#8A2BE2">formatButton</span></span>5.<span style="color:#33CCFF">pack</span>(side=RIGHT, padx=<span style="color:#FDFD6A">2</span>, pady=<span style="color:#FDFD6A">2</span>)

<span style="color:#75715E"># create refresh button on status bar (lower-right)</span>
<span style="color:#FFFF00"><span style="color:#8A2BE2">refreshSyntaxButton</span></span> = Button(<span style="color:#FFFF00"><span style="color:#8A2BE2">statusFrame</span></span>, text=<span style="color:#C9CA6B">&#x27;Refresh Syntax&#x27;</span>, command=<span style="color:#FFA500">refresh_full_syntax</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">refreshSyntaxButton</span></span>.<span style="color:#33CCFF">pack</span>(side=RIGHT, padx=<span style="color:#FDFD6A">4</span>, pady=<span style="color:#FDFD6A">2</span>)

<span style="color:#75715E"># Bindings</span>
<span style="color:#FF0000">for</span> k <span style="color:#FF0000">in</span> [<span style="color:#C9CA6B">&#x27;(&#x27;</span>, <span style="color:#C9CA6B">&#x27;[&#x27;</span>, <span style="color:#C9CA6B">&#x27;{&#x27;</span>, <span style="color:#C9CA6B">&#x27;&quot;&#x27;</span>, <span style="color:#C9CA6B">&quot;&#x27;&quot;</span>]:
    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">bind</span>(k, <span style="color:#FFA500">auto_pair</span>)
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;Return&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: (<span style="color:#FFA500">smart_newline</span>, <span style="color:#FFA500">highlight_python_helper</span>(<span style="color:#8A2BE2">e</span>)))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;KeyRelease&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: (<span style="color:#FFA500">highlight_python_helper</span>(<span style="color:#8A2BE2">e</span>), <span style="color:#FFA500">highlight_current_line</span>(), <span style="color:#FFA500">redraw_line_numbers</span>(), <span style="color:#FFA500">update_status_bar</span>(), <span style="color:#FFA500">show_trailing_whitespace</span>()))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;Button-1&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">after_idle</span>(<span style="color:#FF0000">lambda</span>: (<span style="color:#FFA500">highlight_python_helper</span>(<span style="color:#8A2BE2">e</span>), <span style="color:#FFA500">highlight_current_line</span>(), <span style="color:#FFA500">redraw_line_numbers</span>(), <span style="color:#FFA500">update_status_bar</span>(), <span style="color:#FFA500">show_trailing_whitespace</span>())))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;MouseWheel&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: (<span style="color:#FFA500">highlight_python_helper</span>(<span style="color:#8A2BE2">e</span>), <span style="color:#FFA500">redraw_line_numbers</span>(), <span style="color:#FFA500">show_trailing_whitespace</span>()))
<span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;Configure&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> <span style="color:#8A2BE2">e</span>: (<span style="color:#FFA500">redraw_line_numbers</span>(), <span style="color:#FFA500">show_trailing_whitespace</span>()))
<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">bind</span>(<span style="color:#C9CA6B">&#x27;&lt;Control-Key-s&gt;&#x27;</span>, <span style="color:#FF0000">lambda</span> event: <span style="color:#FFA500">save_file</span>())

<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Settings modal</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">create_config_window</span>():
    <span style="color:#8A2BE2">top</span> = Toplevel(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
    <span style="color:#8A2BE2">top</span>.<span style="color:#33CCFF">transient</span>(<span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>)
    <span style="color:#8A2BE2">top</span>.<span style="color:#33CCFF">grab_set</span>()
    <span style="color:#8A2BE2">top</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">title</span></span>(<span style="color:#C9CA6B">&quot;Settings&quot;</span>)
    <span style="color:#8A2BE2">top</span>.<span style="color:#33CCFF">resizable</span>(<span style="color:#9CDCFE">False</span>, <span style="color:#9CDCFE">False</span>)

    <span style="color:#75715E"># outer container with padding for nicer spacing</span>
    <span style="color:#8A2BE2">container</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">top</span>, padding=<span style="color:#FDFD6A">12</span>)
    <span style="color:#8A2BE2">container</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">0</span>, sticky=<span style="color:#C9CA6B">&#x27;nsew&#x27;</span>)

    <span style="color:#75715E"># Grid configuration for neat alignment</span>
    <span style="color:#8A2BE2">container</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">0</span>, weight=<span style="color:#FDFD6A">0</span>)
    <span style="color:#8A2BE2">container</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">1</span>, weight=<span style="color:#FDFD6A">1</span>)
    <span style="color:#8A2BE2">container</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">2</span>, weight=<span style="color:#FDFD6A">0</span>)

    <span style="color:#75715E"># Helper to create label + entry + optional swatch button</span>
    <span style="color:#FF0000">def</span> <span style="color:#FFA500">mk_row</span>(label_text, row, initial=<span style="color:#C9CA6B">&#x27;&#x27;</span>, width=<span style="color:#FDFD6A">24</span>):
        ttk.<span style="color:#33CCFF">Label</span>(<span style="color:#8A2BE2">container</span>, text=label_text).<span style="color:#33CCFF">grid</span>(row=row, column=<span style="color:#FDFD6A">0</span>, sticky=<span style="color:#C9CA6B">&#x27;e&#x27;</span>, padx=(<span style="color:#FDFD6A">0</span>,<span style="color:#FDFD6A">8</span>), pady=<span style="color:#FDFD6A">6</span>)
        <span style="color:#8A2BE2">ent</span> = ttk.<span style="color:#33CCFF">Entry</span>(<span style="color:#8A2BE2">container</span>, width=width)
        <span style="color:#8A2BE2">ent</span>.<span style="color:#33CCFF">grid</span>(row=row, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;ew&#x27;</span>, pady=<span style="color:#FDFD6A">6</span>)
        <span style="color:#8A2BE2">ent</span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, initial)
        <span style="color:#FF0000">return</span> <span style="color:#8A2BE2">ent</span>

    <span style="color:#FFFF00"><span style="color:#8A2BE2">fontNameField</span></span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;Font&quot;</span>, <span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontName&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSizeField</span></span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;Font Size&quot;</span>, <span style="color:#FDFD6A">1</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontSize&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColorChoice</span></span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;Font Color&quot;</span>, <span style="color:#FDFD6A">2</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontColor&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColorField</span></span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;Background&quot;</span>, <span style="color:#FDFD6A">3</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;backgroundColor&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColorField</span></span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;Cursor Color&quot;</span>, <span style="color:#FDFD6A">4</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;cursorColor&quot;</span>))

    <span style="color:#FFFF00"><span style="color:#8A2BE2">undoCheckVar</span></span> = IntVar(value=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;undoSetting&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">undoCheck</span></span> = ttk.<span style="color:#33CCFF">Checkbutton</span>(<span style="color:#8A2BE2">container</span>, text=<span style="color:#C9CA6B">&quot;Enable undo&quot;</span>, variable=<span style="color:#FFFF00"><span style="color:#8A2BE2">undoCheckVar</span></span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">undoCheck</span></span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">5</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>, pady=<span style="color:#FDFD6A">6</span>)
<span style="color:#75715E"># --- additional settings: syntax highlighting + model auto-load ---</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">syntaxCheckVar</span></span> = IntVar(value=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;syntaxHighlighting&quot;</span>, fallback=<span style="color:#9CDCFE">True</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">syntaxCheck</span></span> = ttk.<span style="color:#33CCFF">Checkbutton</span>(<span style="color:#8A2BE2">container</span>, text=<span style="color:#C9CA6B">&quot;Enable syntax highlighting&quot;</span>, variable=<span style="color:#FFFF00"><span style="color:#8A2BE2">syntaxCheckVar</span></span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">syntaxCheck</span></span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">5</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>, pady=<span style="color:#FDFD6A">6</span>)

    <span style="color:#75715E"># shift rows for AI fields down by 1 to accommodate new checkbox rows</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">aiMaxContextField</span></span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;Max AI Context&quot;</span>, <span style="color:#FDFD6A">6</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;aiMaxContext&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">temperatureField</span></span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;AI Temperature&quot;</span>, <span style="color:#FDFD6A">7</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;temperature&quot;</span>))
    <span style="color:#8A2BE2">top_kField</span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;AI top_k&quot;</span>, <span style="color:#FDFD6A">8</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;top_k&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">seedField</span></span> = <span style="color:#FFA500">mk_row</span>(<span style="color:#C9CA6B">&quot;AI seed&quot;</span>, <span style="color:#FDFD6A">9</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;seed&quot;</span>))

    <span style="color:#75715E"># auto-load AI options</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpenVar = IntVar(value=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;loadAIOnOpen&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNewVar = IntVar(value=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;loadAIOnNew&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>))
    <span style="color:#75715E"># save-formatting option</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">saveFormattingVar</span></span> = IntVar(value=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;saveFormattingInFile&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>))
    ttk.<span style="color:#33CCFF">Checkbutton</span>(<span style="color:#8A2BE2">container</span>, text=<span style="color:#C9CA6B">&quot;Save formatting into file (hidden header)&quot;</span>, variable=<span style="color:#FFFF00"><span style="color:#8A2BE2">saveFormattingVar</span></span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">12</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>, pady=<span style="color:#FDFD6A">6</span>)
    ttk.<span style="color:#33CCFF">Checkbutton</span>(<span style="color:#8A2BE2">container</span>, text=<span style="color:#C9CA6B">&quot;Load AI when opening a file&quot;</span>, variable=<span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpenVar).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">10</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>, pady=<span style="color:#FDFD6A">6</span>)
    ttk.<span style="color:#33CCFF">Checkbutton</span>(<span style="color:#8A2BE2">container</span>, text=<span style="color:#C9CA6B">&quot;Load AI when creating a new file&quot;</span>, variable=<span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNewVar).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">11</span>, column=<span style="color:#FDFD6A">1</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>, pady=<span style="color:#FDFD6A">6</span>)

    <span style="color:#75715E"># update swatches (keep existing swatch code unchanged)</span>
    <span style="color:#8A2BE2">sw_font</span> = Label(<span style="color:#8A2BE2">container</span>, width=<span style="color:#FDFD6A">3</span>, relief=<span style="color:#C9CA6B">&#x27;sunken&#x27;</span>, <span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontColor&quot;</span>))
    <span style="color:#8A2BE2">sw_font</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">2</span>, column=<span style="color:#FDFD6A">2</span>, padx=(<span style="color:#FDFD6A">8</span>,<span style="color:#FDFD6A">0</span>))
    <span style="color:#8A2BE2">sw_bg</span> = Label(<span style="color:#8A2BE2">container</span>, width=<span style="color:#FDFD6A">3</span>, relief=<span style="color:#C9CA6B">&#x27;sunken&#x27;</span>, <span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;backgroundColor&quot;</span>))
    <span style="color:#8A2BE2">sw_bg</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">3</span>, column=<span style="color:#FDFD6A">2</span>, padx=(<span style="color:#FDFD6A">8</span>,<span style="color:#FDFD6A">0</span>))
    <span style="color:#8A2BE2">sw_cursor</span> = Label(<span style="color:#8A2BE2">container</span>, width=<span style="color:#FDFD6A">3</span>, relief=<span style="color:#C9CA6B">&#x27;sunken&#x27;</span>, <span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;cursorColor&quot;</span>))
    <span style="color:#8A2BE2">sw_cursor</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">4</span>, column=<span style="color:#FDFD6A">2</span>, padx=(<span style="color:#FDFD6A">8</span>,<span style="color:#FDFD6A">0</span>))
    
    <span style="color:#75715E"># color chooser callbacks update both entry and swatch</span>
    <span style="color:#FF0000">def</span> <span style="color:#FFA500">choose_font_color</span>():
        <span style="color:#8A2BE2">c</span> = colorchooser.<span style="color:#33CCFF">askcolor</span>(<span style="color:#8A2BE2">title</span>=<span style="color:#C9CA6B">&quot;Font Color&quot;</span>, initialcolor=<span style="color:#FFFF00"><span style="color:#8A2BE2">fontColorChoice</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">hexc</span> = <span style="color:#FFA500">get_hex_color</span>(<span style="color:#8A2BE2">c</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">hexc</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColorChoice</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColorChoice</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">hexc</span>)
            <span style="color:#8A2BE2">sw_font</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(<span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">hexc</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">choose_background_color</span>():
        <span style="color:#8A2BE2">c</span> = colorchooser.<span style="color:#33CCFF">askcolor</span>(<span style="color:#8A2BE2">title</span>=<span style="color:#C9CA6B">&#x27;Background Color&#x27;</span>, initialcolor=<span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColorField</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">hexc</span> = <span style="color:#FFA500">get_hex_color</span>(<span style="color:#8A2BE2">c</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">hexc</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColorField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColorField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">hexc</span>)
            <span style="color:#8A2BE2">sw_bg</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(<span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">hexc</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">choose_cursor_color</span>():
        <span style="color:#8A2BE2">c</span> = colorchooser.<span style="color:#33CCFF">askcolor</span>(<span style="color:#8A2BE2">title</span>=<span style="color:#C9CA6B">&quot;Cursor Color&quot;</span>, initialcolor=<span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColorField</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">hexc</span> = <span style="color:#FFA500">get_hex_color</span>(<span style="color:#8A2BE2">c</span>)
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">hexc</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColorField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
            <span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColorField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">hexc</span>)
            <span style="color:#8A2BE2">sw_cursor</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(<span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">hexc</span>)

    <span style="color:#75715E"># chooser buttons (visually grouped)</span>
    <span style="color:#8A2BE2">btn_frame</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">container</span>)
    <span style="color:#8A2BE2">btn_frame</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">10</span>, column=<span style="color:#FDFD6A">0</span>, columnspan=<span style="color:#FDFD6A">3</span>, pady=(<span style="color:#FDFD6A">8</span>,<span style="color:#FDFD6A">0</span>), sticky=<span style="color:#C9CA6B">&#x27;ew&#x27;</span>)
    <span style="color:#8A2BE2">btn_frame</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">0</span>, weight=<span style="color:#FDFD6A">1</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btn_frame</span>, text=<span style="color:#C9CA6B">&#x27;Choose Font Color&#x27;</span>, command=<span style="color:#FFA500">choose_font_color</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">0</span>, padx=<span style="color:#FDFD6A">4</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btn_frame</span>, text=<span style="color:#C9CA6B">&#x27;Choose Background&#x27;</span>, command=<span style="color:#FFA500">choose_background_color</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">1</span>, padx=<span style="color:#FDFD6A">4</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">btn_frame</span>, text=<span style="color:#C9CA6B">&#x27;Choose Cursor Color&#x27;</span>, command=<span style="color:#FFA500">choose_cursor_color</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">2</span>, padx=<span style="color:#FDFD6A">4</span>, sticky=<span style="color:#C9CA6B">&#x27;w&#x27;</span>)

    <span style="color:#75715E"># Save/Refresh/Close buttons at the bottom with spacing</span>
    <span style="color:#8A2BE2">action_frame</span> = ttk.<span style="color:#33CCFF">Frame</span>(<span style="color:#8A2BE2">top</span>, padding=(<span style="color:#FDFD6A">12</span>,<span style="color:#FDFD6A">8</span>))
    <span style="color:#8A2BE2">action_frame</span>.<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">1</span>, column=<span style="color:#FDFD6A">0</span>, sticky=<span style="color:#C9CA6B">&#x27;ew&#x27;</span>)
    <span style="color:#8A2BE2">action_frame</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">0</span>, weight=<span style="color:#FDFD6A">1</span>)
    <span style="color:#8A2BE2">action_frame</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">1</span>, weight=<span style="color:#FDFD6A">0</span>)
    <span style="color:#8A2BE2">action_frame</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">2</span>, weight=<span style="color:#FDFD6A">0</span>)
    <span style="color:#8A2BE2">action_frame</span>.<span style="color:#33CCFF">columnconfigure</span>(<span style="color:#FDFD6A">3</span>, weight=<span style="color:#FDFD6A">0</span>)

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">on_closing</span>():
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontName&quot;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontNameField</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontSize&quot;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSizeField</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontColor&quot;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColorChoice</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;backgroundColor&quot;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColorField</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;cursorColor&quot;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColorField</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;undoSetting&quot;</span>, <span style="color:#9CDCFE">str</span>(bool(<span style="color:#FFFF00"><span style="color:#8A2BE2">undoCheckVar</span></span>.<span style="color:#33CCFF">get</span>())))
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;aiMaxContext&quot;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">aiMaxContextField</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;temperature&quot;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">temperatureField</span></span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;top_k&quot;</span>, <span style="color:#8A2BE2">top_kField</span>.<span style="color:#33CCFF">get</span>())
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;seed&quot;</span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">seedField</span></span>.<span style="color:#33CCFF">get</span>())

        <span style="color:#75715E"># persist new options</span>
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;syntaxHighlighting&quot;</span>, <span style="color:#9CDCFE">str</span>(bool(<span style="color:#FFFF00"><span style="color:#8A2BE2">syntaxCheckVar</span></span>.<span style="color:#33CCFF">get</span>())))
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;loadAIOnOpen&quot;</span>, <span style="color:#9CDCFE">str</span>(bool(<span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpenVar.<span style="color:#33CCFF">get</span>())))
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;loadAIOnNew&quot;</span>, <span style="color:#9CDCFE">str</span>(bool(<span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNewVar.<span style="color:#33CCFF">get</span>())))
        <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;saveFormattingInFile&quot;</span>, <span style="color:#9CDCFE">str</span>(bool(<span style="color:#FFFF00"><span style="color:#8A2BE2">saveFormattingVar</span></span>.<span style="color:#33CCFF">get</span>())))

        <span style="color:#FF0000">try</span>:
            <span style="color:#FF0000">with</span> <span style="color:#9CDCFE">open</span>(<span style="color:#8A2BE2">INI_PATH</span>, <span style="color:#C9CA6B">&#x27;w&#x27;</span>) <span style="color:#FF0000">as</span> configfile:
                <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">write</span>(configfile)
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

        <span style="color:#75715E"># reload runtime values that non-AI settings depend on</span>
        <span style="color:#FFA500">nonlocal_values_reload</span>()

        <span style="color:#75715E"># apply syntax highlighting toggle immediately</span>
        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">updateSyntaxHighlighting</span></span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#FDFD6A">1</span> <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">syntaxCheckVar</span></span>.<span style="color:#33CCFF">get</span>() <span style="color:#FF0000">else</span> <span style="color:#FDFD6A">0</span>)
            <span style="color:#FF0000">if</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">syntaxCheckVar</span></span>.<span style="color:#33CCFF">get</span>():
                <span style="color:#FFFF00"><span style="color:#FFA500">highlightPythonInit</span></span>()
            <span style="color:#FF0000">else</span>:
                <span style="color:#75715E"># clear tags</span>
                <span style="color:#FF0000">for</span> <span style="color:#8A2BE2">t</span> <span style="color:#FF0000">in</span> (<span style="color:#C9CA6B">&#x27;string&#x27;</span>, <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>, <span style="color:#C9CA6B">&#x27;comment&#x27;</span>, <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>, <span style="color:#C9CA6B">&#x27;def&#x27;</span>, <span style="color:#C9CA6B">&#x27;number&#x27;</span>, <span style="color:#C9CA6B">&#x27;variable&#x27;</span>,
                          <span style="color:#C9CA6B">&#x27;decorator&#x27;</span>, <span style="color:#C9CA6B">&#x27;class_name&#x27;</span>, <span style="color:#C9CA6B">&#x27;constant&#x27;</span>, <span style="color:#C9CA6B">&#x27;attribute&#x27;</span>, <span style="color:#C9CA6B">&#x27;builtin&#x27;</span>, <span style="color:#C9CA6B">&#x27;todo&#x27;</span>):
                    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">tag_remove</span>(<span style="color:#8A2BE2">t</span>, <span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end&quot;</span>)
                <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;Syntax highlighting disabled.&quot;</span>
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

        <span style="color:#75715E"># update runtime auto-load flags</span>
        <span style="color:#FF0000">global</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpen, <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNew
        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpen = bool(<span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpenVar.<span style="color:#33CCFF">get</span>())
            <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNew = bool(<span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNewVar.<span style="color:#33CCFF">get</span>())
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

        <span style="color:#8A2BE2">top</span>.<span style="color:#33CCFF">destroy</span>()

    <span style="color:#FF0000">def</span> <span style="color:#FFA500">refresh_from_file</span>():
        <span style="color:#FFFF00"><span style="color:#8A2BE2">fontNameField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">fontNameField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontName&quot;</span>))
        <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSizeField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSizeField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontSize&quot;</span>))
        <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColorChoice</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColorChoice</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontColor&quot;</span>))
        <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColorField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColorField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;backgroundColor&quot;</span>))
        <span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColorField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColorField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;cursorColor&quot;</span>))
        <span style="color:#FFFF00"><span style="color:#8A2BE2">undoCheckVar</span></span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;undoSetting&quot;</span>))
        <span style="color:#FFFF00"><span style="color:#8A2BE2">aiMaxContextField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">aiMaxContextField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;aiMaxContext&quot;</span>))
        <span style="color:#8A2BE2">top_kField</span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#8A2BE2">top_kField</span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;top_k&quot;</span>))
        <span style="color:#FFFF00"><span style="color:#8A2BE2">seedField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">seedField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;seed&quot;</span>))
        <span style="color:#FFFF00"><span style="color:#8A2BE2">temperatureField</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#FDFD6A">0</span>, END)
        <span style="color:#FFFF00"><span style="color:#8A2BE2">temperatureField</span></span>.<span style="color:#33CCFF">insert</span>(<span style="color:#FDFD6A">0</span>, <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;temperature&quot;</span>))

        <span style="color:#75715E"># refresh the new checkboxes</span>
        <span style="color:#FF0000">try</span>:
            <span style="color:#FFFF00"><span style="color:#8A2BE2">syntaxCheckVar</span></span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;syntaxHighlighting&quot;</span>, fallback=<span style="color:#9CDCFE">True</span>))
            <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpenVar.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;loadAIOnOpen&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>))
            <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNewVar.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;loadAIOnNew&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>))
            <span style="color:#FFFF00"><span style="color:#8A2BE2">saveFormattingVar</span></span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;saveFormattingInFile&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>))
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

        <span style="color:#75715E"># update swatches to match refreshed values</span>
        <span style="color:#FF0000">try</span>:
            <span style="color:#8A2BE2">sw_font</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(<span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontColor&quot;</span>))
            <span style="color:#8A2BE2">sw_bg</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(<span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;backgroundColor&quot;</span>))
            <span style="color:#8A2BE2">sw_cursor</span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(<span style="color:#8A2BE2">bg</span>=<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;cursorColor&quot;</span>))
        <span style="color:#FF0000">except</span> Exception:
            <span style="color:#FF0000">pass</span>

    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">action_frame</span>, text=<span style="color:#C9CA6B">&quot;Save&quot;</span>, command=<span style="color:#FFA500">on_closing</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">1</span>, padx=<span style="color:#FDFD6A">6</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">action_frame</span>, text=<span style="color:#C9CA6B">&quot;Refresh from file&quot;</span>, command=<span style="color:#FFA500">refresh_from_file</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">2</span>, padx=<span style="color:#FDFD6A">6</span>)
    ttk.<span style="color:#33CCFF">Button</span>(<span style="color:#8A2BE2">action_frame</span>, text=<span style="color:#C9CA6B">&quot;Close&quot;</span>, command=<span style="color:#8A2BE2">top</span>.<span style="color:#33CCFF">destroy</span>).<span style="color:#33CCFF">grid</span>(row=<span style="color:#FDFD6A">0</span>, column=<span style="color:#FDFD6A">3</span>, padx=<span style="color:#FDFD6A">6</span>)

    <span style="color:#75715E"># initial focus &amp; center the dialog</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fontNameField</span></span>.<span style="color:#33CCFF">focus_set</span>()
    <span style="color:#FFA500">center_window</span>(<span style="color:#8A2BE2">top</span>)
    <span style="color:#FFA500">refresh_from_file</span>()


<span style="color:#FF0000">def</span> <span style="color:#FFA500">nonlocal_values_reload</span>():
    <span style="color:#C9CA6B">&quot;&quot;&quot;Reloads runtime variables from config and applies them to the editor.&quot;&quot;&quot;</span>
    <span style="color:#FF0000">global</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColor</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColor</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">undoSetting</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColor</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">aiMaxContext</span></span>, <span style="color:#8A2BE2">temperature</span>, <span style="color:#8A2BE2">top_k</span>, <span style="color:#8A2BE2">seed</span>
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontName&quot;</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontSize&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">fontColor</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;fontColor&quot;</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColor</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;backgroundColor&quot;</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">undoSetting</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;undoSetting&quot;</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColor</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;cursorColor&quot;</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">aiMaxContext</span></span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;aiMaxContext&quot;</span>))
    <span style="color:#8A2BE2">seed</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;seed&quot;</span>))
    <span style="color:#8A2BE2">top_k</span> = <span style="color:#9CDCFE">int</span>(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;top_k&quot;</span>))
    <span style="color:#8A2BE2">temperature</span> = float(<span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">get</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;temperature&quot;</span>))
    <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnOpen = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;loadAIOnOpen&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNew = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;loadAIOnNew&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">saveFormattingInFile</span></span> = <span style="color:#8A2BE2">config</span>.<span style="color:#33CCFF">getboolean</span>(<span style="color:#C9CA6B">&quot;Section1&quot;</span>, <span style="color:#C9CA6B">&quot;saveFormattingInFile&quot;</span>, fallback=<span style="color:#9CDCFE">False</span>)

    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(font=(<span style="color:#FFFF00"><span style="color:#8A2BE2">fontName</span></span>, <span style="color:#FFFF00"><span style="color:#8A2BE2">fontSize</span></span>), <span style="color:#8A2BE2">bg</span>=<span style="color:#FFFF00"><span style="color:#8A2BE2">backgroundColor</span></span>, fg=<span style="color:#FFFF00"><span style="color:#8A2BE2">fontColor</span></span>, insertbackground=<span style="color:#FFFF00"><span style="color:#8A2BE2">cursorColor</span></span>, undo=<span style="color:#FFFF00"><span style="color:#8A2BE2">undoSetting</span></span>)


<span style="color:#FF0000">def</span> <span style="color:#FFA500">setting_modal</span>():
    <span style="color:#FFA500">create_config_window</span>()


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Misc helpers / periodic tasks</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#8A2BE2">stop_event</span> = threading.<span style="color:#33CCFF">Event</span>()


<span style="color:#FF0000">def</span> <span style="color:#FFA500">ready_update</span>():
    <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#FFFF00"><span style="color:#33CCFF">after</span></span>(<span style="color:#FDFD6A">1000</span>, <span style="color:#FF0000">lambda</span>: <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>.<span style="color:#8A2BE2"><span style="color:#33CCFF">config</span></span>(text=<span style="color:#C9CA6B">&quot;Ready&quot;</span>))


<span style="color:#FF0000">def</span> <span style="color:#FFFF00"><span style="color:#FFA500">newFile</span></span>():
    <span style="color:#FFFF00"><span style="color:#8A2BE2">textArea</span></span>.<span style="color:#33CCFF">delete</span>(<span style="color:#C9CA6B">&#x27;1.0&#x27;</span>, <span style="color:#C9CA6B">&#x27;end&#x27;</span>)
    <span style="color:#FFFF00"><span style="color:#8A2BE2">statusBar</span></span>[<span style="color:#C9CA6B">&#x27;text&#x27;</span>] = <span style="color:#C9CA6B">&quot;New Document!&quot;</span>
    <span style="color:#FF0000">try</span>:
        <span style="color:#FF0000">if</span> <span style="color:#8A2BE2">_ML_AVAILABLE</span> <span style="color:#FF0000">and</span> <span style="color:#FFFF00"><span style="color:#8A2BE2">loadA</span></span>IOnNew <span style="color:#FF0000">and</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loaded</span> <span style="color:#FF0000">and</span> <span style="color:#FF0000">not</span> <span style="color:#8A2BE2">_model_loading</span>:
            Thread(target=<span style="color:#FF0000">lambda</span>: <span style="color:#FFA500">_start_model_load</span>(start_autocomplete=<span style="color:#9CDCFE">False</span>), daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()
    <span style="color:#FF0000">except</span> Exception:
        <span style="color:#FF0000">pass</span>
    Thread(target=<span style="color:#FFA500">ready_update</span>, daemon=<span style="color:#9CDCFE">True</span>).<span style="color:#8A2BE2"><span style="color:#33CCFF">start</span></span>()


<span style="color:#75715E"># periodic highlight updater (lightweight)</span>
<span style="color:#75715E">#def update_highlights():</span>
<span style="color:#75715E">#    if updateSyntaxHighlighting.get():</span>
<span style="color:#75715E">#        Thread(target=highlight_python_helper, daemon=True).start()</span>
<span style="color:#75715E">#    else:</span>
<span style="color:#75715E">#        for t in (<span style="color:#C9CA6B">&#x27;string&#x27;</span>, <span style="color:#C9CA6B">&#x27;keyword&#x27;</span>, <span style="color:#C9CA6B">&#x27;comment&#x27;</span>, <span style="color:#C9CA6B">&#x27;selfs&#x27;</span>, <span style="color:#C9CA6B">&#x27;def&#x27;</span>, <span style="color:#C9CA6B">&#x27;number&#x27;</span>):</span>
<span style="color:#75715E">#            textArea.tag_remove(t, <span style="color:#C9CA6B">&quot;1.0&quot;</span>, <span style="color:#C9CA6B">&quot;end&quot;</span>)</span>
<span style="color:#75715E">#    root.after(2000, update_highlights)</span>


<span style="color:#75715E"># Start background updater</span>
<span style="color:#75715E">#root.after(2000, update_highlights)</span>

<span style="color:#75715E"># populate recent menu</span>
<span style="color:#FF0000">try</span>:
    <span style="color:#FFA500">refresh_recent_menu</span>()
<span style="color:#FF0000">except</span> Exception:
    <span style="color:#FF0000">pass</span>


<span style="color:#75715E"># -------------------------</span>
<span style="color:#75715E"># Main loop</span>
<span style="color:#75715E"># -------------------------</span>
<span style="color:#FF0000">def</span> <span style="color:#FFA500">main</span>():
    <span style="color:#FF0000">try</span>:
        <span style="color:#FFFF00"><span style="color:#8A2BE2">root</span></span>.<span style="color:#33CCFF">mainloop</span>()
    <span style="color:#FF0000">finally</span>:
        <span style="color:#8A2BE2">stop_event</span>.<span style="color:#33CCFF"><span style="color:#9CDCFE">set</span></span>()


<span style="color:#FF0000">if</span> <span style="color:#FFA500">__name__</span> == <span style="color:#C9CA6B">&#x27;<span style="color:#FFA500">__main__</span>&#x27;</span>:
    <span style="color:#FFA500">main</span>()</strong>
</div>
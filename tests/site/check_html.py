#!/usr/bin/env python3
"""Tag-balance checker for the aiking static pages."""
import sys, glob, os
from html.parser import HTMLParser

VOID = {'area','base','br','col','embed','hr','img','input','link','meta',
        'param','source','track','wbr'}

class Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"line {self.getpos()[0]}: closing </{tag}> with empty stack")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
            return
        # look for the tag deeper in the stack (mismatched nesting)
        names = [t for t, _ in self.stack]
        if tag in names:
            idx = len(names) - 1 - names[::-1].index(tag)
            skipped = self.stack[idx+1:]
            self.errors.append(
                f"line {self.getpos()[0]}: </{tag}> closes over unclosed "
                + ", ".join(f"<{t}> (opened line {p[0]})" for t, p in skipped))
            self.stack = self.stack[:idx]
        else:
            self.errors.append(f"line {self.getpos()[0]}: stray closing </{tag}> (top of stack: <{self.stack[-1][0]}>)")

for path in sorted(sys.argv[1:]):
    with open(path, encoding='utf-8') as fh:
        src = fh.read()
    c = Checker()
    try:
        c.feed(src)
        c.close()
    except Exception as e:
        print(f"{path}: PARSER EXCEPTION {e}")
        continue
    probs = list(c.errors)
    if c.stack:
        probs.append("unclosed at EOF: " + ", ".join(f"<{t}> (line {p[0]})" for t, p in c.stack))
    if probs:
        print(f"{path}:")
        for p in probs:
            print(f"  {p}")
    else:
        print(f"{path}: OK")

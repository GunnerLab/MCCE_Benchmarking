#!/usr/bin/env python

"""
Module: interactive.py

To test/demo cli args setting in interactive mode

ENTRY_POINTS = {"setup": "bench_setup",
                "launch": "bench_batch", # used by crontab :: launch 1 batch
                "analyze": "bench_analyze",
                "compare": "bench_compare"}

"""

from mcce_benchmark import ENTRY_POINTS, SUB1, SUB2, USER
from prompt_toolkit import PromptSession, prompt
from prompt_toolkit import print_formatted_text
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from prompt_toolkit.shortcuts import message_dialog, radiolist_dialog


def misc():
    " TMP "

    html_completer = WordCompleter(['<html>', '<body>', '<head>', '<title>'])
    nested_completer = NestedCompleter.from_nested_dict({
        'show': {
            'version': None,
            'clock': None,
            'ip': {
                'interface': {'brief'}
            }
        },
        'exit': None,
    })

    # Create prompt object.
    #session = PromptSession()
    #text = session.prompt('# ', completer=nested_completer)
    #print('You said: %s' % text)

    return


def main():

    session = PromptSession()

    message_dialog(
        title = 'Interactive Benchmarking Inputs Entry',
        text = f"Hi {USER}!\nDo you want to try MCCE_Benchmarking in intractive mode?\nPress ENTER to quit.").run()

    action = radiolist_dialog(
        title = "ACTION - Benchmarking action to take:",
        text = "Select one:",
        values=[
            (ENTRY_POINTS["setup"], "Setup a set of runs"),
            (ENTRY_POINTS["launch"], "Launch a batch of runs"),
            (ENTRY_POINTS["analyze"], "Analyze a set of runs"),
            (ENTRY_POINTS["compare"], "Compare two sets of runs")
        ]
    ).run()

    print_formatted_text(type(action), action)

    pdbs = radiolist_dialog(
        title = "Source of pdbs",
        text = "Which is/was the source of the pdbs in the set?",
        values=[
            (SUB1, "pKa DBv1"),
            (SUB2, "my list"),
        ]
    ).run()

    msg = f"> {action} "
    if action == ENTRY_POINTS["setup"]:
        msg = msg + f"{pdbs}"

    message_dialog(
    title="The equivalent cli command so far would be:",
    text= f"{msg}\nPress ENTER to quit."
    ).run()



if __name__ == "__main__":
    main()

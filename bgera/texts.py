#!/usr/bin/env python
# coding: utf-8
"""
All words the student hears, in one place.

HOW TO TRANSLATE
----------------
Every message has a short key.  English lives in EN, Georgian lives in KA.
To add a Georgian message, copy the key from EN into KA and write the
Georgian text.  Anything missing from KA falls back to English, so the app
never breaks while you are still translating.

Placeholders like {name} or {x} must stay exactly the same in both languages,
but they may appear in any order.

To see what is still untranslated, run:

    python -m bgera.texts

Written for screen readers: keep every line short.  One idea per line.
Long explanations belong in HELP topics, not in confirmations.
"""

# ---------------------------------------------------------------------------
# English
# ---------------------------------------------------------------------------

EN = {
    # ---- start up -------------------------------------------------------
    "welcome": "Welcome to BgeraPrint.",
    "choose_language": "Press 1 for English, or 2 for Georgian, then Enter. ",
    "ask_printer_model": "Type your QIDI printer model in small letters, for example xmax3. ",
    "ask_ip": "Type your printer's IP address, for example 10.1.202.192. ",
    "ask_port": "Type your printer's port number, for example 7125. ",
    "ready": "Ready. Type help and press Enter to learn the commands. Type a shape name to begin.",
    "unknown_model": "I do not know that printer model. Please try again.",

    # ---- general --------------------------------------------------------
    "unknown": "I do not understand '{word}'. Type help for a list of commands.",
    "did_you_mean": "I do not understand '{word}'. Did you mean '{guess}'?",
    "need_number": "'{word}' needs a number after it, for example {word} 20.",
    "number_too_small": "{word} must be at least {low}.",
    "number_too_big": "{word} can be at most {high}.",
    "ok": "Done.",
    "nothing_yet": "You have not made anything yet. Type a shape name, such as cube.",
    "cancelled": "Cancelled.",
    "goodbye": "Goodbye.",

    # ---- making shapes --------------------------------------------------
    "shape_added": "Added {shape}, named {name}.",
    "shape_hint_cube": "A cube needs width, length and height. Say for example: width 20 length 30 height 10.",
    "shape_hint_ball": "A ball needs its width across. Say for example: across 30.",
    "shape_hint_rod": "A rod needs width across and height. Say for example: across 20 height 40.",
    "shape_hint_cone": "A cone needs width across at the bottom and height. Say for example: across 30 height 40.",
    "shape_hint_pyramid": "A pyramid needs width across, height and number of sides. Say for example: across 30 height 40 sides 4.",
    "shape_hint_prism": "A prism needs width across, height and number of sides. Say for example: across 20 height 40 sides 6.",
    "shape_hint_tube": "A tube needs width across, height and wall thickness. Say for example: across 30 height 40 thick 3.",
    "shape_hint_donut": "A donut needs width across of the ring and thickness of the ring. Say for example: across 40 thick 8.",
    "shape_hint_wedge": "A wedge is a ramp. It needs width, length and height. Say for example: width 20 length 40 height 15.",
    "shape_hint_star": "A star needs width across, height and number of points. Say for example: across 40 height 5 points 5.",
    "shape_hint_plate": "A plate is a thin flat base. It needs width, length and height. Say for example: width 80 length 30 height 3.",
    "shape_hint_text": "Type: text Nino. Then you can set height and thick.",
    "shape_hint_braille": "Type: braille nino. Dots are added at the standard braille size.",
    "shape_hint_ring": "A ring needs width across, height and wall thickness. Say for example: across 20 height 4 thick 2.",

    "text_needs_words": "Tell me what the text should say, for example: text Nino.",
    "braille_needs_words": "Tell me what the braille should say, for example: braille nino.",
    "braille_skipped": "I cannot write these characters in braille: {chars}. I left them out.",
    "braille_made": "Braille for '{words}' made. {cells} cells, {width} millimetres wide.",

    "size_set": "{name} is now {dims}.",
    "no_part_named": "There is no part named {name}. Type list to hear the parts.",
    "part_removed": "Removed {name}.",
    "part_renamed": "{old} is now called {new}.",
    "renamed_taken": "There is already a part called {new}.",

    # ---- moving and turning ---------------------------------------------
    "moved": "Moved {name} {dir} {amount} millimetres.",
    "turned": "Turned {name} {amount} degrees around the {axis} line.",
    "centred": "{name} is now in the middle of the bed.",
    "stacked": "{top} is now sitting on top of {bottom}.",
    "beside": "{a} is now beside {b}.",
    "mirrored": "{name} is now mirrored {dir}.",
    "scaled": "{name} is now {factor} times its size.",
    "rounded": "Rounded the edges of {name} by {amount} millimetres.",
    "smoothed": "Wrapped a smooth skin around {name}.",
    "copied": "Made {count} copies of {name}, {gap} millimetres apart, going {dir}.",
    "ringed": "Placed {count} copies of {name} in a circle {across} millimetres across.",
    "hollowed": "Hollowed out {name}, leaving walls {thick} millimetres thick.",

    # ---- combining ------------------------------------------------------
    "joined": "Joined {a} and {b} into {name}.",
    "cut": "Cut {b} out of {a}. The result is called {name}.",
    "overlapped": "Kept only the part where {a} and {b} overlap. The result is called {name}.",
    "need_two_parts": "You need at least two parts before you can {action}. Type list to hear the parts.",

    # ---- describing -----------------------------------------------------
    "list_header": "Your model has {count} parts.",
    "list_item": "{index}. {name}, a {shape}, {dims}, at position {pos}.",
    "size_report": "Your model is {x} wide, {y} long and {z} tall, in millimetres.",
    "volume_report": "It uses about {grams} grams of plastic.",
    "describe_empty": "Your model is empty.",
    "build_ok": "Model built.",
    "build_failed": "The model could not be built. {reason}",
    "undo_done": "Undone. {what}",
    "undo_empty": "There is nothing left to undo.",
    "redo_done": "Redone. {what}",
    "redo_empty": "There is nothing to redo.",
    "new_model": "Started a new empty model.",

    # ---- projects -------------------------------------------------------
    "saved": "Saved your model as {name}.",
    "opened": "Opened {name}.",
    "no_project": "There is no saved project called {name}.",
    "projects_header": "You have {count} saved projects.",
    "projects_item": "{index}. {name}, saved {when}.",
    "projects_none": "You have no saved projects yet. Type save and a name to keep one.",
    "exported": "Saved the shape file to {path}.",

    # ---- print settings -------------------------------------------------
    "setting_changed": "{setting} is now {value}.",
    "setting_unknown_value": "'{value}' is not a choice for {setting}. Choices are: {choices}.",
    "settings_header": "Your print settings are:",
    "settings_line": "{setting}: {value}",
    "settings_reset": "Print settings are back to normal.",

    # ---- preparing and printing ----------------------------------------
    "preparing": "Preparing your model for the printer. Please wait.",
    "prepared": "Ready to print. It will take {time} and use about {grams} grams of plastic.",
    "prepare_failed": "Preparing failed. {reason}",
    "prepare_first": "Prepare the model first. Type prepare and press Enter.",
    "confirm_print": "Type print again to start printing, or type back to change something.",
    "sending_to_printer": "Sending your file to the printer.",
    "print_started": "The printer has started. Type status to hear how it is going.",
    "print_failed": "The printer did not accept the file. {reason}",
    "printer_offline": "I cannot reach the printer at {ip}. Check that it is switched on and on the same network.",
    "status_printing": "Printing {name}. {percent} percent done. About {left} left.",
    "status_idle": "The printer is not printing anything right now.",
    "status_paused": "The printer is paused.",
    "print_cancelled": "The print has been stopped.",
    "print_paused": "The print is paused. Type resume to carry on.",
    "print_resumed": "The print is running again.",
    "no_print_running": "There is no print running.",
    "confirm_cancel": "Type stop again to really stop the print.",

    # ---- printers -------------------------------------------------------
    "printers_header": "You have {count} printers set up.",
    "printers_item": "{index}. {name}, a {model}, at {ip}. {current}",
    "printer_current": "This is the one in use.",
    "printer_switched": "Now using the printer called {name}.",
    "printer_added": "Added the printer {name}.",
    "printer_removed": "Removed the printer {name}.",
    "no_printer_named": "There is no printer called {name}.",

    # ---- sharing files --------------------------------------------------
    "send_ask_ip": "Type the IP address of the computer you are sending to: ",
    "send_ask_port": "Type the port number, for example 5001: ",
    "send_ask_name": "Type your name, so your teacher knows whose file it is: ",
    "send_progress": "Sending, {percent} percent.",
    "send_ok": "Sent {name}.",
    "send_failed": "Could not send the file. {reason}",
    "receive_ask_port": "Type the port number to listen on, for example 5001: ",
    "receive_waiting": "Waiting for files on port {port}. Type done when everyone has sent theirs.",
    "receive_got": "Received {name} from {who}.",
    "receive_done": "Received {count} files. They are all in your Downloads folder.",
    "receive_none": "No files were received.",

    # ---- choosing how to work ------------------------------------------
    "which_interface": "How would you like to use BgeraPrint today?",
    "interface_menus": "Menus",
    "interface_menus_hint": "choose everything with the arrow keys and Enter",
    "interface_typing": "Typing",
    "interface_typing_hint": "type commands such as: cube, width 30",
    "interface_chosen_menus": "Menus it is. Use the up and down arrows, then press Enter.",
    "interface_chosen_typing": "Typing it is. Type help at any time.",
    "switch_hint": "Type menu to swap to the arrow key menus at any time.",

    "which_numbers": "And how would you like to set sizes and numbers?",
    "numbers_arrows": "With the arrow keys",
    "numbers_arrows_hint": "left and right change it, faster the longer you hold them",
    "numbers_typed": "By typing them",
    "numbers_typed_hint": "type the number and press Enter",
    "numbers_chosen_arrows": "Right. Left and right arrows change a number, "
                            "starting at a tenth of a millimetre.",
    "numbers_chosen_typed": "Right. You will be asked to type each number.",

    # ---- checking the app itself ----------------------------------------
    "check_start": "Checking that everything works. This takes about a minute.",
    "check_ok": "{part}: working.",
    "check_bad": "{part}: NOT working. {why}",
    "check_all_good": "Everything works. {passed} checks passed.",
    "check_some_bad": "{failed} of {total} checks failed. The app may not work properly.",
    "check_modelling": "the modelling program",
    "check_slicing": "the slicing program",
    "check_profile": "the printer settings file",
    "check_models": "the ready made models",
    "check_build": "making a shape",
    "check_slice": "getting a shape ready to print",
    "check_printer": "reaching the printer",

    # ---- lessons --------------------------------------------------------
    "lesson_start": "Lesson {n}: {title}. There are {steps} steps. Type next to go on, or stop to leave the lesson.",
    "lesson_step": "Step {n} of {total}. {text}",
    "lesson_try": "Now you try. Type: {command}",
    "lesson_good": "That is right.",
    "lesson_retry": "Not quite. Try typing: {command}",
    "lesson_end": "Lesson finished. Well done.",
    "lesson_left": "You have left the lesson.",
    "lessons_header": "There are {count} lessons.",
    "lessons_item": "{index}. {title}",
}


# ---------------------------------------------------------------------------
# Georgian
# ---------------------------------------------------------------------------
# Fill these in.  Keys that are not here fall back to English.
# The keys already present were carried over from BgeraPrint version 1.3.1.

KA = {
    "welcome": "კეთილი იყოს თქვენი მობრძანება BgeraPrint-ში!",
    "choose_language": "აპლიკაცია ხელმისაწვდომია ინგლისურ და ქართულ ენებზე. აირჩიეთ ენა: ინგლისურისთვის დააჭირეთ 1-ს, ქართულისთვის 2-ს ",
    "ask_printer_model": "ეს აპლიკაცია ამ დროისთვის თავსებადია მხოლოდ ქიდის პრინტერებთან. გთხოვთ შეიყვანოთ თქვენი პრინტერის მოდელი პატარა ასოებით, გამოტოვებისა და დამატებითი სიმბოლოების გარეშე, მაგალითად xmax3 ",
    "ask_ip": "გთხოვთ შეიყვანოთ თქვენი პრინტერის IP მისამართი ",
    "ask_port": "გთხოვთ შეიყვანოთ თქვენი პრინტერის პორტის ნომერი ",
    "unknown_model": "სიმბოლო არასწორია, სცადეთ ხელახლა.",
    "unknown": "სიმბოლო არასწორია, სცადეთ ხელახლა.",

    # --- GE-TODO: everything below this line still needs Georgian ---------
}


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

_LANG = 1  # 1 = English, 2 = Georgian


def set_language(lan):
    """1 for English, 2 for Georgian."""
    global _LANG
    _LANG = 2 if int(lan) == 2 else 1


def get_language():
    return _LANG


def t(key, **kw):
    """Look up a message and fill in its placeholders."""
    table = KA if _LANG == 2 else EN
    text = table.get(key)
    if text is None:
        text = EN.get(key, key)
    if kw:
        try:
            text = text.format(**kw)
        except (KeyError, IndexError, ValueError):
            # A translation with a wrong placeholder must never crash the app.
            text = EN.get(key, key)
            try:
                text = text.format(**kw)
            except Exception:
                pass
    return text


def say(key, **kw):
    """Print one message.  Everything the student hears goes through here."""
    print(t(key, **kw))


def missing_translations():
    """Keys that still have no Georgian text."""
    return sorted(k for k in EN if k not in KA)


if __name__ == "__main__":
    missing = missing_translations()
    print(f"{len(missing)} of {len(EN)} messages still need Georgian:\n")
    for key in missing:
        print(f'    "{key}": "",   # {EN[key]}')

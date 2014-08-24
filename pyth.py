#!/usr/bin/python3
############################################################################
# This python program is an interpreter for the pyth programming language. #
# It is still in development - expect new versions often.                  #
#                                                                          #
# To use, provide pyth code as first command line argument.                #
# Further input on further lines.                                          #
# Prints out resultant python code for debugging purposes, then runs the   #
# pyth program.                                                            #
#                                                                          #
# More information:                                                        #
# The parse function takes a string of pyth code, and returns a single     #
# python expression ready to be executed.                                  #
# general_parse is the same but for multiple expressions.                  #
# This program also defines the built-ins that the resultant expression    #
# uses, once expanded.                                                     #
############################################################################
from extra_parse import *
from macros import *
from data import *
import copy as c


# Set reset for the globals.
global c_to_f
global next_c_to_f
global c_to_i
reset_c_to_f = c.deepcopy(c_to_f)
reset_next_c_to_f = c.deepcopy(next_c_to_f)
reset_c_to_i = c.deepcopy(c_to_i)


# Run it!
def general_parse(code):
    global c_to_f
    global next_c_to_f
    global c_to_i
    # Reset the globals.
    c_to_f = c.deepcopy(reset_c_to_f)
    next_c_to_f = c.deepcopy(reset_next_c_to_f)
    c_to_i = c.deepcopy(reset_c_to_i)
    code = prepend_parse(code)
    # Parsing
    args_list = []
    parsed = 'Not empty'
    while parsed != '':
        if add_print(code):
            code = 'p"\\n"'+code
        parsed, code = parse(code)
        # Necessary for backslash not to infinite loop
        if code and code[0] == ';':
            code = code[1:]
        args_list.append(parsed)
    # Build the output string.
    py_code = '\n'.join(args_list[:-1])
    return py_code


def parse(code, spacing="\n "):
    # If we've reached the end of the string, give up.
    if code == '':
        return '', ''
    # Separate active character from the rest of the code.
    active_char = code[0]
    rest_code = code[1:]
    # Deal with numbers
    if active_char in ".0123456789":
        return num_parse(active_char, rest_code)
    # String literals
    if active_char == '"':
        return str_parse(active_char, rest_code)
    # Python code literals
    if active_char == '$':
        return python_parse(active_char, rest_code)
    # End paren is magic (early-end current function/statement).
    if active_char == ')':
        return '', rest_code
    # Semicolon is more magic (early-end all active functions/statements).
    if active_char == ';':
        if rest_code == '':
            return '', ''
        else:
            return '', ';'+rest_code
    # Designated variables
    if active_char in variables:
        return active_char, rest_code
    # Replace replaements
    if active_char in replacements:
        return replace_parse(active_char, rest_code, spacing)
    # And for general functions
    if active_char in c_to_f:
        return function_parse(active_char, rest_code)
    # General format functions/operators
    if active_char in c_to_i:
        return infix_parse(active_char, rest_code)
    # Statements:
    if active_char in c_to_s:
        return statement_parse(active_char, rest_code, spacing)
    # If we get here, the character has not been implemented.
    # There is no non-ASCII support.
    raise PythParseError(active_char, rest_code)


def function_parse(active_char, rest_code):
    global c_to_f
    global next_c_to_f
    func_name, arity = c_to_f[active_char]
    init_paren = (active_char not in no_init_paren)
    # Swap what variables are used in the map, filter or reduce.
    if active_char in next_c_to_f:
        temp = c_to_f[active_char]
        c_to_f[active_char] = next_c_to_f[active_char][0]
        next_c_to_f[active_char] = next_c_to_f[active_char][1:] + [temp]
    # Recurse until terminated by end paren or EOF
    # or received enough arguments
    args_list = []
    parsed = 'Not empty'
    while len(args_list) != arity and parsed != '':
        parsed, rest_code = parse(rest_code)
        args_list.append(parsed)
    # Build the output string.
    py_code = func_name
    if init_paren:
        py_code += '('
    if len(args_list) > 0 and args_list[-1] == '':
        args_list = args_list[:-1]
    py_code += ','.join(args_list)
    py_code += ')'
    return py_code, rest_code


def infix_parse(active_char, rest_code):
    global c_to_i
    infixes, arity = c_to_i[active_char]
    # Advance infixes.
    if active_char in next_c_to_i:
        c_to_i[active_char] = next_c_to_i[active_char]
    args_list = []
    parsed = 'Not empty'
    while len(args_list) != arity and parsed != '':
        parsed, rest_code = parse(rest_code)
        args_list.append(parsed)
    # Statements that cannot have anything after them
    if active_char in end_statement:
        rest_code = ")" + rest_code
    py_code = infixes[0]
    for i in range(len(args_list)):
        py_code += args_list[i]
        py_code += infixes[i+1]
    return py_code, rest_code


def statement_parse(active_char, rest_code, spacing):
    # Handle the initial portion (head)
    infixes, arity = c_to_s[active_char]
    args_list = []
    parsed = 'Not empty'
    while len(args_list) != arity and parsed != '':
        parsed, rest_code = parse(rest_code)
        args_list.append(parsed)
    part_py_code = infixes[0]
    for i in range(len(args_list)):
        part_py_code += args_list[i]
        part_py_code += infixes[i+1]
    # Handle the body - ends object as well.
    assert rest_code != ''
    args_list = []
    parsed = 'Not empty'
    while parsed != '':
        if add_print(rest_code):
            rest_code = 'p"\\n"' + rest_code
        parsed, rest_code = parse(rest_code, spacing+' ')
        args_list.append(parsed)
    # Trim the '' away and combine.
    if args_list[-1] == '':
        args_list = args_list[:-1]
    all_pieces = [part_py_code] + args_list
    return spacing.join(all_pieces), rest_code


def replace_parse(active_char, rest_code, spacing):
    format_str, format_num = replacements[active_char]
    format_chars = tuple(rest_code[:format_num])
    new_code = format_str.format(*format_chars) + rest_code[format_num:]
    return parse(new_code, spacing)


# Prependers are magic. Automatically prepend to program if present.
# First occurance must not be in a string.
def prepend_parse(code):
    out_code = code
    for prep_char in sorted(prepend):
        if prep_char in code:
            first_loc = code.index(prep_char)
            if first_loc == 0 or \
                    code[:first_loc].count('"') % 2 == 0 and \
                    code[first_loc-1] != "\\":
                out_code = prepend[prep_char] + out_code
    return out_code


# Prepend print to any line starting with a function, var or
# safe infix.
def add_print(code):
    if len(code) > 0:
        if (code[0] not in 'p ' and code[0] in c_to_f) or \
            code[0] in variables or \
            code[0] in "@&|]'?\\\".0123456789#," or \
            ((code[0] in 'JK' or code[0] in prepend) and
                c_to_i[code[0]] == next_c_to_i[code[0]]):
            return True
    return False


if __name__ == '__main__':
    # Check for command line flags.
    # If debug is on, print code, python code, separator.
    # If help is on, print help message.
    if len(sys.argv) > 1 and \
            "-h" in sys.argv[1:] \
            or "--help" in sys.argv[1:] \
            or len(sys.argv) == 1:
        print("""This is the Pyth -> Python compliler and executor.
Give file containing Pyth code as final command line argument.

Command line flags:
-c or --code:   Give code as final command arg, instead of file name.
-d or --debug   Show input code, generated python code.
-l or --line    Run each line as a program, instead of just first line.
                Must not be combined with -c.
-h or --help    Show this help message.

See opening comment in pyth.py for more info.""")
    else:
        file_or_string = sys.argv[-1]
        flags = sys.argv[1:-1]
        verbose_flags = [flag for flag in flags if flag[:2] == '--']
        short_flags = [flag for flag in flags if flag[:2] != '--']
        debug_on = any('d' in flag for flag in short_flags) or \
            '--debug' in verbose_flags
        code_on = any('c' in flag for flag in short_flags) or \
            "--code" in verbose_flags
        line_on = any('l' in flag for flag in short_flags) or \
            "-line" in verbose_flags
        if code_on and line_on:
            print("Error: cannot handle multiline input from command line.")
        else:
            if code_on:
                    code = file_or_string
                    py_code_list = [(code, general_parse(code))]
            else:
                code_file = file_or_string
                if line_on:
                    code = (line[:-1] for line in list(open(code_file)))
                    py_code_list = [(code_line, general_parse(code_line))
                                    or code_line in code]
                else:
                    code = list(open(file_or_string))[0][:-1]
                    py_code_list = [(code, general_parse(code))]
            # Loop through the code lines - unless -l, only one line.
            for code_line, py_code_line in py_code_list:
                # Debug message
                if debug_on:
                    if len(py_code_line) > 0:
                        print('='*50)
                        print(str(len(code_line)) + ": " + code_line)
                        print('='*50)
                        print(py_code_line)
                    elif len(code_line) > 0:
                        print('='*50)
                        print(code_line)
                # Run the code.
                exec(py_code_line)

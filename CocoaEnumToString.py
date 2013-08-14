#!/usr/bin/env python

import itertools
import argparse
import sys
import re
from os import path
from clang import cindex
from clang.cindex import CursorKind

def all_children(node):
    return itertools.chain(iter([node]), *map(all_children, 
                                              node.get_children()))
    
def all_constant_decls(enum):
    return iter(child for child in all_children(enum) if 
                    child.kind == CursorKind.ENUM_CONSTANT_DECL)
                    
def indent_all_lines(s, indent):
    return '\n'.join(indent + line for line in s.split('\n'))
    
def format_as_array(enum, title, indent):
    all_members = ['[{0.spelling}]=@"{0.spelling}"'.format(constant) 
                        for constant in all_constant_decls(enum)]
    all_members = ",\n".join(all_members)
                                
    return "NSString * const {}[] = {{{}}};".format(title, all_members)
                                                    
def format_as_func(enum, title, indent):
    case_str = 'case {0.spelling}:\n{indent}return @"{0.spelling}";'
    all_cases = [case_str.format(constant, indent=indent)
                        for constant in all_constant_decls(enum)]
    all_cases.append('default:\n{}@"";'.format(indent))
    all_cases = "\n".join(all_cases)
    
    switch = "switch( val ){{\n{}\n}}".format(indent_all_lines(all_cases, 
                                                               indent))
    
    func_str = "NSString * {}({name} val){{\n{body}\n}}"
    return func_str.format(title, name=enum.spelling, 
                           body=indent_all_lines(switch, indent))
                           
parser = argparse.ArgumentParser(description="Use libclang to find enums in "
                                  "the specified Objective-C file and emit a "
                                  "construct (array or function) to "
                                  "map between the constant values and "
                                  "their names.")
parser.add_argument("--arr", "--array", action="store_const", const="array",
                    dest="construct", help="Emit an array for the mapping.")
parser.add_argument("-c", "--construct", default="array",
                    help="Specify 'function' or any prefix ('f', 'fun', etc.) "
                         "to emit a function that uses a switch statement for "
                         "the mapping; specify 'array' or any prefix for "
                         "an array (this is the default). Whichever of -c, "
                         "--arr, or --fun occurs last in the argument list "
                         " will dictate the output.")
# Allow for either all names to be listed after a single flag, or for 
# one flag to be used per name
parser.add_argument("-e", "--enums", action="append", #default=[],
                    help="Specify particular enums to capture; by default "
                    "all enums in the given file are used. This argument may "
                    "be present multiple times. Names which are not found in "
                    "the input file are ignored.")
parser.add_argument("--fun", "--func", "--function", action="store_const", 
                    const="function", dest="construct", 
                    help="Emit a function for the mapping.")
parser.add_argument("-i", "--indent", default="4s",
                    help="Number and type of character to use for indentation."
                    " Digit plus either 't' (for tabs) or 's' (spaces), e.g., "
                    "'4s' (which is the default)")
parser.add_argument("-n", "--name", default="StringFor%e",
                    help="Name for the construct; the prefix will "
# Escape percent sign because argparse is doing some formatting of its own.
                    "be added. Any appearances of '%%e' in this argument will "
                    "be replaced with each enum name. The default is "
                    "'StringFor%%e'.")
parser.add_argument("-o", "--output",
                    help="If this argument is present, output should go to a "
                    "file which will be created at the specified path. An "
                    "error will be raised if the file already exists.")
parser.add_argument("-p", "--prefix", default="",
                    help="Prefix to add to the name of emitted construct, "
                    "e.g. 'NS'")
parser.add_argument("file", help="Path to the file which should be parsed.")
                                           

arguments = parser.parse_args()    

if "function".startswith(arguments.construct):
    format_enum = format_as_func 
elif "array".startswith(arguments.construct):
    format_enum = format_as_array
else:
   parser.error("Neither 'function' nor 'array' specified for construct ")

match = re.match(r"(\d*)([st])", arguments.indent)
if not match.group(2):
    parser.error("Neither tabs nor spaces specified for indentation.")
else:
    indent_char = '\t' if match.group(2) == 't' else ' '
    indent = indent_char * int(match.group(1) or 1)
    
if arguments.output:
    if path.exists(arguments.output):
        sys.stderr.write("Error: Requested output file exists: "
                         "{}\n".format(arguments.output))
        sys.exit(1)
    else:
        out_f = open(arguments.output, 'w')
else:
    out_f = sys.stdout
  
target_file_name = arguments.file

# Ignore the fact that system libclang probably doesn't match the version
# of the Python bindings.
cindex.Config.set_compatibility_check(False)
# Use what's likely to be a newer version than that found in /usr/lib
cindex.Config.set_library_file("/Applications/Xcode.app/Contents/Developer/"
                               "Toolchains/XcodeDefault.xctoolchain/usr/lib/"
                               "libclang.dylib")

# Preprocessor macros that resolve into enums; these are defined in
# NSObjCRuntime.h, but including that directly causes redefinition errors due
# to it being also imported.
ns_options_def = ("NS_OPTIONS(_type, _name)=enum _name : "
                 "_type _name; enum _name : _type")
ns_enum_def = ("NS_ENUM(_type, _name)=enum _name : _type _name; "
              "enum _name : _type")

tu = cindex.TranslationUnit.from_source(target_file_name, 
                                        args=["-ObjC", "-D", ns_enum_def,
                                              "-D", ns_options_def, "-D",
                                              "NS_ENUM_AVAILABLE="])
                                              
enums = [node for node in all_children(tu.cursor) if 
                node.kind == CursorKind.ENUM_DECL and
                node.location.file.name.find(target_file_name) != -1]
if arguments.enums:
    enums = filter(lambda enum: enum.spelling in arguments.enums, enums)

               
for enum in enums:
    title = arguments.prefix + arguments.name.replace("%e", enum.spelling)
    out_f.write(format_enum(enum, title, indent))
    out_f.write("\n\n")

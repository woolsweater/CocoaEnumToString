#!/usr/bin/env python

"""
CocoaEnumToString, copyright 2013 Joshua Caswell.

Parse a specified Cocoa header file and emit ObjC code to translate the values
of any enums found within into their names as NSStrings.
"""
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

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
    
def format_anonymous(enum, title):
    const_str = 'NSString * const {} = @"{}";\n'
    constants = [const_str.format(title.replace('%e', constant.spelling),
                                  constant.spelling)
                            for constant in all_constant_decls(enum)]
    return "".join(constants)
        
    
def format_as_array(enum, title, indent):
    all_members = ['[{0}] = @"{0}"'.format(constant.spelling) 
                        for constant in all_constant_decls(enum)]
    all_members = ",\n".join(all_members)
                                
    title = title.replace('%e', enum.spelling)
    array_str = "NSString * const {}[] = {{\n{}\n}};"
    return array_str.format(title, indent_all_lines(all_members, indent))
                                                    
def format_as_func(enum, title, indent):
    case_str = 'case {0}:\n{1}return @"{0}";'
    all_cases = [case_str.format(constant.spelling, indent)
                        for constant in all_constant_decls(enum)]
    all_cases.append('default:\n{}@"";'.format(indent))
    all_cases = "\n".join(all_cases)
    
    switch = "switch( val ){{\n{}\n}}".format(indent_all_lines(all_cases, 
                                                               indent))
    title = title.replace('%e', enum.spelling)
    func_str = "NSString * {}({} val){{\n{}\n}}"
    return func_str.format(title, enum.spelling, 
                           indent_all_lines(switch, indent))
                           

parser = argparse.ArgumentParser(description="Use libclang to find enums in "
                                  "the specified Objective-C file and emit a "
                                  "construct (array or function) that "
                                  "maps between the constant values and "
                                  "their names.")
# This argument must be added to the parser first for its default to override
# that of --arr and --fun
parser.add_argument("-c", "--construct", default="array",
                    help="Specify 'function' or any prefix ('f', 'fun', etc.) "
                         "to emit a function that uses a switch statement for "
                         "the mapping; specify 'array' or any prefix for "
                         "an array (this is the default). Whichever of -c, "
                         "--arr, or --fun occurs last in the argument list "
                         "will dictate the output.")
parser.add_argument("--arr", "--array", action="store_const", const="array",
                    dest="construct", help="Emit an array for the mapping.")
parser.add_argument("-e", "--enums", action="append",
                    help="Specify particular enums to capture; by default "
                    "all enums in the given file are used. This argument may "
                    "be present multiple times. Names which are not found in "
                    "the input file are ignored.")
parser.add_argument("--fun", "--func", "--function", action="store_const", 
                    const="function", dest="construct", 
                    help="Emit a function for the mapping.")
parser.add_argument("-i", "--indent", default="4s",
                    help="Number and type of character to use for indentation."
                    " Digits plus either 't' (for tabs) or 's' (for spaces), "
                    "e.g., '4s', which is the default.")
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
                    help="Cocoa-style prefix to add to the name of emitted "
                    "construct, e.g. 'NS'")
parser.add_argument("file", help="Path to the file which should be parsed.")
                                           

arguments = parser.parse_args()

if "array".startswith(arguments.construct):
    format_enum = format_as_array 
elif "function".startswith(arguments.construct):
    format_enum = format_as_func
else:
   parser.error("Neither 'function' nor 'array' specified for construct.")

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

title = arguments.prefix + arguments.name

for enum in enums:
    if not enum.spelling:
        out_f.write(format_anonymous(enum, title))
    else:
        out_f.write(format_enum(enum, title, indent))
    out_f.write("\n\n")

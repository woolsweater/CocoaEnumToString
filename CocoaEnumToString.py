import itertools
from clang import cindex
from clang.cindex import CursorKind

INDENT = "    "

def all_children(node):
    return itertools.chain(iter([node]), *map(all_children, node.get_children()))
    
def all_constant_decls(enum):
    return iter(child for child in all_children(enum) if 
                    child.kind == CursorKind.ENUM_CONSTANT_DECL)
                    
def indent_all_lines(s, indent):
    return '\n'.join(indent + line for line in s.split('\n'))
    
def format_as_array(enum, prefix=""):
    all_members = ['[{0.spelling}}]=@"{0.spelling}}"'.format(constant) 
                        for constant in all_constant_decls(enum)]
    all_members = ",\n".join(all_members)
                                
    return "NSString * const {}StringsFor{}[] = {{{}}};".format(prefix, 
                                                                enum.spelling, 
                                                                all_members)
                                                    
def format_as_func(enum, prefix):
    case_str = 'case {0.spelling}:\n{indent}return @"{0.spelling}";'
    all_cases = [case_str.format(constant, indent=INDENT)
                        for constant in all_constant_decls(enum)]
    all_cases.append('default:\n{}@"";'.format(INDENT))
    all_cases = "\n".join(all_cases)
    
    switch = "switch( val ){{\n{}\n}}".format(indent_all_lines(all_cases, INDENT))
    
    func_str = "NSString * {}StringFor{name}({name} val){{\n{body}\n}}"
    return func_str.format(prefix, name=enum.spelling, 
                           body=indent_all_lines(switch, INDENT))
    
    
target_file_name = "NSFileManager.h"
prefix = "WSS"
format_enum = format_as_func

# Ignore the fact that system libclang probably doesn't match the version
# of the Python bindings.
cindex.Config.set_compatibility_check(False)
# Use what's likely to be a newer version than that found in /usr/lib
cindex.Config.set_library_file("/Applications/Xcode.app/Contents/Developer/"
                               "Toolchains/XcodeDefault.xctoolchain/usr/lib/"
                               "libclang.dylib")
                               
FOUNDATION_HEADERS = ("/Applications/Xcode.app/Contents/Developer/Platforms/"
                     "MacOSX.platform/Developer/SDKs/MacOSX10.8.sdk/System/"
                     "Library/Frameworks/Foundation.framework/Versions/C/"
                     "Headers/")
# Include NSObjCRuntime.h for the definitions of NS_ENUM and NS_OPTIONS.
# This causes redefinition errors because
tu = cindex.TranslationUnit.from_source(FOUNDATION_HEADERS + target_file_name, 
                                        args=["-ObjC", 
                                              "-include" + FOUNDATION_HEADERS +
                                              "NSObjCRuntime.h"])
                                              
enums = [node for node in all_children(tu.cursor) if 
                        node.kind == CursorKind.ENUM_DECL and
                        node.location.file.name.find(target_file_name) != -1]
                        
for enum in enums:
    print format_enum(enum, prefix)
    print '\n'
                                



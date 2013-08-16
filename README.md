CocoaEnumToString
=================

Python script that uses libclang to parse a Cocoa file looking for enums and create a mapping -- either a function with a switch statement or an array -- between the constant values and their names.

  usage: CocoaEnumToString.py [-h] [-c CONSTRUCT] [--arr] [-e ENUMS] [--fun]
                              [-i INDENT] [-n NAME] [-o OUTPUT] [-p PREFIX]
                              file

  Use libclang to find enums in the specified Objective-C file and emit a
  construct (array or function) that maps between the constant values and their
  names.

  positional arguments:
    file                  Path to the file which should be parsed.

  optional arguments:
    -h, --help            show this help message and exit
    -c CONSTRUCT, --construct CONSTRUCT
                          Specify 'function' or any prefix ('f', 'fun', etc.) to
                          emit a function that uses a switch statement for the
                          mapping; specify 'array' or any prefix for an array
                          (this is the default). Whichever of -c, --arr, or
                          --fun occurs last in the argument list will dictate
                          the output.
    --arr, --array        Emit an array for the mapping.
    -e ENUMS, --enums ENUMS
                          Specify particular enums to capture; by default all
                          enums in the given file are used. This argument may be
                          present multiple times. Names which are not found in
                          the input file are ignored.
    --fun, --func, --function
                          Emit a function for the mapping.
    -i INDENT, --indent INDENT
                          Number and type of character to use for indentation.
                          Digits plus either 't' (for tabs) or 's' (for spaces),
                          e.g., '4s', which is the default.
    -n NAME, --name NAME  Name for the construct; the prefix will be added. Any
                          appearances of '%e' in this argument will be replaced
                          with each enum name. The default is 'StringFor%e'.
    -o OUTPUT, --output OUTPUT
                          If this argument is present, output should go to a
                          file which will be created at the specified path. An
                          error will be raised if the file already exists.
    -p PREFIX, --prefix PREFIX
                          Cocoa-style prefix to add to the name of emitted
                          construct, e.g. 'NS'

Sample use:

    CocoaEnumToString.py -p WSS -e NSFileManagerItemReplacementOptions /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.8.sdk/System/Library/Frameworks/Foundation.framework/Versions/C/Headers/NSFileManager.h
    
Output:
   
    NSString * const WSSStringForNSFileManagerItemReplacementOptions[] = {
        [NSFileManagerItemReplacementUsingNewMetadataOnly] = @"NSFileManagerItemReplacementUsingNewMetadataOnly",
        [NSFileManagerItemReplacementWithoutDeletingBackupItem] = @"NSFileManagerItemReplacementWithoutDeletingBackupItem"
    };
    
Function output:

    NSString * WSSStringForNSFileManagerItemReplacementOptions(NSFileManagerItemReplacementOptions val){
        switch( val ){
            case NSFileManagerItemReplacementUsingNewMetadataOnly:
                return @"NSFileManagerItemReplacementUsingNewMetadataOnly";
            case NSFileManagerItemReplacementWithoutDeletingBackupItem:
                return @"NSFileManagerItemReplacementWithoutDeletingBackupItem";
            default:
                @"";
        }
    }

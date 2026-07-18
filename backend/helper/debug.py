import inspect
import os

def debug_print(*args, **kwargs):
    frame = inspect.currentframe().f_back
    
    # Clean up the file path to show just the filename, not the full system path
    filename = os.path.basename(frame.f_code.co_filename)
    line_number = frame.f_lineno
    raw_func = frame.f_code.co_name
    
    # 🎯 Check if we are running at the root/global script level
    if raw_func == "<module>":
        context = f"[{filename}:{line_number}]"
    else:
        context = f"[{filename}:{line_number} in {raw_func}()]"
        
    print(context, end="\n\n", *args, **kwargs)
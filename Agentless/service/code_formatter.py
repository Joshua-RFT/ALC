import os
import json
import ast
import subprocess

# --- Helper Functions for AST Parsing ---

def _get_node_text(node, lines):
    """Extracts the source text of an AST node from the file's lines."""
    start_line = node.lineno - 1 # AST is 1-indexed, list is 0-indexed
    # end_lineno is available in Python 3.8+ for many compound statements
    end_line = getattr(node, 'end_lineno', node.lineno) # Fallback to node.lineno if end_lineno not present

    # Ensure end_line is at least start_line + 1 for multi-line, or just start_line for single.
    # However, ast.get_source_segment is more accurate for exact text.
    # Here, we stick to line numbers from AST.
    # If end_lineno is the same as lineno, it's a single-line definition for the header.
    # The body will extend further. The end_lineno for a class/function should ideally cover its whole body.
    node_lines = lines[start_line:end_line] # Slicing up to end_line
    return [line.rstrip('\n') for line in node_lines]

def _parse_python_file_details(file_path, file_lines):
    """
    Parses a Python file using AST to extract classes, functions, and methods.
    """
    parsed_data = {
        "classes": [],
        "functions": [],
        "text": [line.rstrip('\n') for line in file_lines]
    }
    try:
        tree = ast.parse("".join(file_lines)) # ast.parse needs a single string
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, 'end_lineno', node.lineno),
                    "text": _get_node_text(node, file_lines),
                    "methods": []
                }
                for item in node.body:
                    if isinstance(item, ast.FunctionDef): # Methods
                        method_info = {
                            "name": item.name,
                            "start_line": item.lineno,
                            "end_line": getattr(item, 'end_lineno', item.lineno),
                            "text": _get_node_text(item, file_lines)
                        }
                        class_info["methods"].append(method_info)
                parsed_data["classes"].append(class_info)
            elif isinstance(node, ast.FunctionDef): # Top-level functions
                function_info = {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, 'end_lineno', node.lineno),
                    "text": _get_node_text(node, file_lines)
                }
                parsed_data["functions"].append(function_info)
    except SyntaxError as e:
        print(f"SyntaxError parsing {file_path}: {e}. Storing raw text only.")
    except Exception as e:
        print(f"Error parsing Python file {file_path}: {e}. Storing raw text only.")

    # Ensure end_line values are present (using start_line as a fallback if getattr returned None, which it shouldn't with the current fallback to node.lineno)
    for item_list in [parsed_data["classes"], parsed_data["functions"]]:
        for item in item_list:
            if item["end_line"] is None: item["end_line"] = item["start_line"]
            if "methods" in item:
                for sub_item in item["methods"]:
                    if sub_item["end_line"] is None: sub_item["end_line"] = sub_item["start_line"]
    return parsed_data

# --- Helper function to get Git commit ---
def _get_base_commit(repo_dir: str) -> str:
    """Tries to get the current git commit hash."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8' # Specify encoding for consistency
        )
        return result.stdout.strip()
    except FileNotFoundError:
        print("Warning: Git command not found. Cannot get base_commit.")
        return "unknown_git_not_found"
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not get git commit in '{repo_dir}' (is this a git repository?): {e}")
        return "unknown_not_a_git_repo"
    except Exception as e:
        print(f"Warning: An unexpected error occurred while getting git commit: {e}")
        return "unknown_git_error"

# --- Main Function ---
def format_code_to_json_detailed(source_code_dir: str,
                                 output_json_path: str,
                                 instance_id: str,
                                 repo_name: str = None,
                                 excluded_dirs: list = None,
                                 excluded_files: list = None):
    """
    Traverses the source code directory, parses Python files, and formats
    the structure and content into a detailed JSON file.

    Args:
        source_code_dir (str): The root directory of the source code.
        output_json_path (str): The path to save the output JSON file.
        instance_id (str): Unique identifier for this snapshot (e.g., zip package name).
        repo_name (str, optional): The name of the repository (e.g., 'sphinx-doc/sphinx').
                                   If None, it will be derived from the source_code_dir.
        excluded_dirs (list, optional): List of directory names to exclude.
                                        Defaults to typical temporary/build directories.
        excluded_files (list, optional): List of file names to exclude. Defaults to ['.DS_Store'].
    """
    if not os.path.isdir(source_code_dir):
        print(f"Error: Source directory '{source_code_dir}' not found.")
        return

    if repo_name is None:
        repo_name = os.path.basename(os.path.abspath(source_code_dir))
        print(f"Derived repo_name: {repo_name}")

    if excluded_dirs is None:
        excluded_dirs = ['.venv', 'venv', '__pycache__', 'node_modules', '.vscode', 'build', 'dist', '.eggs']
    if excluded_files is None:
        excluded_files = ['.DS_Store']

    base_commit_hash = _get_base_commit(source_code_dir)
    root_structure = {}
    print(f"Processing code from {source_code_dir} for repository '{repo_name}' (commit: {base_commit_hash}, instance_id: {instance_id})")

    source_code_dir_abs = os.path.abspath(source_code_dir)

    for dirpath, dirnames, filenames in os.walk(source_code_dir_abs, topdown=True):
        # Filter directories in-place to prevent os.walk from traversing them
        dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
        # Filter files
        filenames = [f for f in filenames if f not in excluded_files]

        relative_dir_path = os.path.relpath(dirpath, source_code_dir_abs)
        current_level_dict = root_structure
        if relative_dir_path != ".":
            path_parts = relative_dir_path.split(os.sep)
            for part in path_parts:
                current_level_dict = current_level_dict.setdefault(part, {})
                # Ensure we are still in a dictionary (e.g. no file/folder name conflict)
                if not isinstance(current_level_dict, dict):
                    print(f"Error: Path conflict. Expected a directory dict for '{part}' in '{relative_dir_path}', but found {type(current_level_dict)}. Overwriting with empty dict.")
                    # This part of path_parts will be re-initialized. Sibling entries under the parent of 'part' might be lost.
                    # To handle this more gracefully, one might rename the conflicting key or merge, but that's complex.
                    # For now, we simply log and re-initialize to avoid crashing.
                    parent_path_parts = path_parts[:path_parts.index(part)]
                    parent_dict = root_structure
                    for p_part in parent_path_parts:
                        parent_dict = parent_dict[p_part]
                    parent_dict[part] = {}
                    current_level_dict = parent_dict[part]


        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            display_path = os.path.join(relative_dir_path, filename) if relative_dir_path != '.' else filename

            if os.path.islink(file_path):
                print(f"  - Skipping symlink: {display_path}")
                current_level_dict[filename] = {"type": "symlink", "target": os.readlink(file_path)} # Optionally record symlink info
                continue

            try:
                if filename.endswith(".py"):
                    print(f"  - Processing Python file: {display_path}")
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f: # 'ignore' for robustness
                            lines = f.readlines()
                        file_details = _parse_python_file_details(file_path, lines)
                        current_level_dict[filename] = file_details
                    except Exception as e: # Catch read errors specifically too
                        print(f"Warning: Could not read/parse Python file {file_path}: {e}")
                        current_level_dict[filename] = {"error": f"Could not read/parse Python file: {e}"}

                else:
                    # For non-Python files, an empty object as per spec
                    print(f"  - Adding non-Python file: {display_path}")
                    current_level_dict[filename] = {}
            except Exception as e: # General catch-all for other processing issues for a file
                print(f"Warning: Could not process file {file_path}: {e}")
                current_level_dict[filename] = {"error": f"Could not process file: {e}"}

    output_data = {
        "repo": repo_name,
        "base_commit": base_commit_hash,
        "structure": root_structure,
        "instance_id": instance_id
    }

    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2) # Using indent=2
        print(f"\nCode structure JSON saved to {output_json_path}")
    except Exception as e:
        print(f"Error saving code JSON to {output_json_path}: {e}")

if __name__ == '__main__':
    print("Setting up a dummy project for testing...")
    TEST_REPO_DIR = "test_repo_detailed"
    # Clean up previous test run if any
    if os.path.exists(TEST_REPO_DIR):
        import shutil
        print(f"Removing existing test directory: {TEST_REPO_DIR}")
        shutil.rmtree(TEST_REPO_DIR)
    if os.path.exists("repo_structure_detailed.json"):
        os.remove("repo_structure_detailed.json")

    os.makedirs(os.path.join(TEST_REPO_DIR, "src", "utils"), exist_ok=True)
    os.makedirs(os.path.join(TEST_REPO_DIR, "docs"), exist_ok=True)
    os.makedirs(os.path.join(TEST_REPO_DIR, ".git", "objects", "pack"), exist_ok=True) # For testing .git inclusion
    os.makedirs(os.path.join(TEST_REPO_DIR, ".git", "logs", "refs", "heads"), exist_ok=True)
    os.makedirs(os.path.join(TEST_REPO_DIR, ".tx"), exist_ok=True) # For testing .tx/config
    os.makedirs(os.path.join(TEST_REPO_DIR, ".venv", "bin"), exist_ok=True) # For testing exclusion

    with open(os.path.join(TEST_REPO_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Test Repository\nThis is a test.")

    with open(os.path.join(TEST_REPO_DIR, "src", "main.py"), "w", encoding="utf-8") as f:
        f.write("""\
import os

def global_function(arg1, arg2):
    \"\"\"A global function.\"\"\"
    print(f"Called with {arg1} and {arg2}")
    # Another comment
    return arg1 + arg2

class MyClass:
    \"\"\"This is MyClass.
    It has multiple lines in docstring.
    \"\"\"
    class_var = 100

    def __init__(self, value: int): # With type hint
        self.value = value
        # A comment within __init__

    def get_value(self) -> int: # With return type hint
        \"\"\"Returns the value.\"\"\"
        return self.value

    def _internal_method(self):
        pass # This is an internal method
        # It can span multiple lines
""")

    with open(os.path.join(TEST_REPO_DIR, "src", "utils", "helpers.py"), "w", encoding="utf-8") as f:
        f.write("""\
# Helper functions
def utility_one(): # A simple one liner
    pass

def utility_two(param: str) -> str: # Another one
    # with a comment
    # and another line
    return param * 2 # calculation
""")
    with open(os.path.join(TEST_REPO_DIR, "LICENSE"), "w", encoding="utf-8") as f:
        f.write("MIT License...")

    with open(os.path.join(TEST_REPO_DIR, ".git", "config"), "w", encoding="utf-8") as f:
        f.write("[core]\n\trepositoryformatversion = 0\n")
    with open(os.path.join(TEST_REPO_DIR, ".git", "HEAD"), "w", encoding="utf-8") as f:
        f.write("ref: refs/heads/main\n")
    with open(os.path.join(TEST_REPO_DIR, ".git", "objects", "pack", "dummy.pack"), "w", encoding="utf-8") as f:
        f.write("binary pack data placeholder") # Placeholder
    with open(os.path.join(TEST_REPO_DIR, ".tx", "config"), "w", encoding="utf-8") as f:
        f.write("[main]\nhost = https://www.transifex.com\n")
    with open(os.path.join(TEST_REPO_DIR, ".venv", "activate_this.py"), "w", encoding="utf-8") as f:
        f.write("# Virtualenv script\n")


    is_git_initialized = False
    if not os.path.exists(os.path.join(TEST_REPO_DIR, ".git")):
         print(f"Warning: .git directory manually created but test repo {TEST_REPO_DIR} is not a true git repo for HEAD commit.")
    else: # If .git exists, try to make it a bit more real for commit hash
        try:
            print(f"Ensuring '{TEST_REPO_DIR}' is a Git repository for base_commit testing...")
            # Check if it's already a git repo from a previous partial run
            check_git = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=TEST_REPO_DIR, capture_output=True, text=True)
            if check_git.stdout.strip() != "true":
                 subprocess.run(['git', 'init'], cwd=TEST_REPO_DIR, check=True, capture_output=True)
                 is_git_initialized = True
            else:
                 print(f"'{TEST_REPO_DIR}' is already a git work tree.")
                 is_git_initialized = True # Assume it's fine

            if is_git_initialized:
                subprocess.run(['git', 'config', 'user.email', "you@example.com"], cwd=TEST_REPO_DIR, check=True)
                subprocess.run(['git', 'config', 'user.name', "Your Name"], cwd=TEST_REPO_DIR, check=True)
                subprocess.run(['git', 'add', '.'], cwd=TEST_REPO_DIR, check=True, capture_output=True)
                # Check if there are any changes to commit
                status_result = subprocess.run(['git', 'status', '--porcelain'], cwd=TEST_REPO_DIR, capture_output=True, text=True)
                if status_result.stdout.strip():
                    subprocess.run(['git', 'commit', '-m', 'Initial test commit'], cwd=TEST_REPO_DIR, check=True, capture_output=True)
                    print("Dummy git repository initialized/updated and committed.")
                else:
                    print("No changes to commit in dummy git repository.")
        except Exception as e:
            print(f"Could not initialize/commit dummy git repo in '{TEST_REPO_DIR}' (git might not be installed or configured): {e}")
            # .git directory might exist but no commits yet. _get_base_commit will handle this.


    print("\nRunning the formatter...")
    format_code_to_json_detailed(
        source_code_dir=TEST_REPO_DIR,
        output_json_path="repo_structure_detailed.json",
        instance_id=f"{os.path.basename(TEST_REPO_DIR)}__snapshot-12345", # Example instance_id
        repo_name="my-example/test_repo_detailed",
        # Explicitly not excluding .git here, but still excluding .venv
        excluded_dirs=['.venv', '__pycache__', 'node_modules', 'build', 'dist', '.eggs', '.pytest_cache']
    )

    print("\n--- Content of repo_structure_detailed.json (first 50 lines) ---")
    try:
        with open("repo_structure_detailed.json", "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < 50:
                    print(line, end='')
                else:
                    print("... (file truncated for display)")
                    break
    except FileNotFoundError:
        print("repo_structure_detailed.json not found.")

    print(f"\nTest finished. Check '{TEST_REPO_DIR}' and 'repo_structure_detailed.json'.")
    # Consider cleaning up by uncommenting below:
    # import shutil
    # print("\nCleaning up dummy project...")
    # shutil.rmtree(TEST_REPO_DIR)
    # if os.path.exists("repo_structure_detailed.json"):
    #     os.remove("repo_structure_detailed.json")

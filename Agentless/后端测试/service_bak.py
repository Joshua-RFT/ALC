import os
import zipfile
import tempfile
import json
from flask import Flask, request, jsonify, current_app
import traceback # For logging errors
from code_formatter import format_code_to_json_detailed
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
import code_formatter

# Assume Agentless library is installed and available in the environment
# import Agentless
# --- global var
global_source_directory = None
global_output_file = None
global_unique_instance_id = None
global_repository_git_name = None

# --- Mock Agentless for demonstration if the actual library isn't installed ---
# If you have the real library, comment out this mock section
class MockAgentlessArgs:
    def __init__(self, file_path, file_name):
        print(f"MockAgentlessArgs initialized with path: {file_path}, name: {file_name}")
        self.file_path = file_path
        self.file_name = file_name

class MockAgentless:
    _api_key = None
    _project_file_loc = None
    _openai_api_url = None

    @classmethod
    def set_API_KEY(cls, api_key):
        cls._api_key = api_key
        print(f"MockAgentless: API Key set to {api_key}")

    @classmethod
    def set_PROJECT_FILE_LOC(cls, loc):
        cls._project_file_loc = loc
        print(f"MockAgentless: Project file location set to {loc}")

    @classmethod
    def set_OPENAI_API_URL(cls, url):
        cls._openai_api_url = url
        print(f"MockAgentless: OpenAI API URL set to {url}")

    AgentlessArgs = MockAgentlessArgs # Assign the inner class

    def __init__(self, agentless_args):
        self.agentless_args = agentless_args
        self._result = None
        print("MockAgentless instance created.")
        print(f"Using project location: {MockAgentless._project_file_loc}")
        print(f"Using API Key: {MockAgentless._api_key}")
        print(f"Using API URL: {MockAgentless._openai_api_url}")
        print(f"Using AgentlessArgs: Path={agentless_args.file_path}, Name={agentless_args.file_name}")


    def run(self):
        print("MockAgentless: Running mock agentless...")
        # Simulate processing time and result
        # In a real scenario, this would call the actual Agentless logic
        import time
        time.sleep(1)

        # Simulate reading the bug description JSON
        bug_desc_path = os.path.join(self.agentless_args.file_path, self.agentless_args.file_name)
        try:
            with open(bug_desc_path, 'r', encoding='utf-8') as f:
                bug_data = json.load(f)
                simulated_analysis = f"Based on description: '{bug_data.get('bug_description', 'No description')}', the simulated problem analysis is... (This is mock analysis)"
                simulated_diff = f"--- a/some/file.py\n+++ b/some/file.py\n@@ -1,5 +1,6 @@\n # Original line\n-print('Hello')\n+print('Hello, World!') # Fix applied\n # Another line\n"
                self._result = ["success", {"code_diff": simulated_diff, "problem_analysis": simulated_analysis}]
                print("MockAgentless: Mock run successful.")
        except Exception as e:
             print(f"MockAgentless: Error reading bug description file: {e}")
             self._result = ["error", {"message": f"Mock error: could not read bug description {bug_desc_path}"}]


    def result(self):
        print("MockAgentless: Returning mock result.")
        return self._result

# Use the mock Agentless or the real one
try:
    import Agentless # Try importing the real one
    print("Using actual Agentless library.")
except ImportError:
    print("Actual Agentless library not found.")
    #Agentless = MockAgentless # Use the mock if real not found
    exit(0)


# --- Configuration ---
# Agentless OpenAI API URL (from user's example, should ideally be configurable)
AGENTLESS_OPENAI_API_URL = 'https://api.deepseek.com/v1'


# --- Helper Functions / Formatting Tools ---
# Placeholder for the tool that formats source code into JSON
# This implementation walks the directory and puts relative paths and content into a JSON
# def format_code_to_json(source_code_dir: str, output_json_path: str):
#     """
#     Traverses the source code directory and formats file contents into a JSON file.
#     Example JSON structure: {'files': [{'path': 'relative/path', 'content': 'file content'}, ...]}
#     """
#     code_data = {'files': []}
#     print(f"Formatting code from {source_code_dir} to {output_json_path}")
#     for root, _, files in os.walk(source_code_dir):
#         for file in files:
#             file_path = os.path.join(root, file)
#             relative_path = os.path.relpath(file_path, source_code_dir)
#             # Skip binary files or specific directories if needed
#             if os.path.islink(file_path) or not os.path.isfile(file_path):
#                 continue
#             try:
#                 # Attempt to read as text, handle potential errors (e.g., binary files)
#                 with open(file_path, 'r', encoding='utf-8') as f:
#                     content = f.read()
#                 code_data['files'].append({'path': relative_path, 'content': content})
#                 print(f"  - Added: {relative_path}")
#             except Exception as e:
#                 print(f"Warning: Could not read file {file_path} as text (skipping or handle differently): {e}")
#                 # Optionally add error info or handle binary files specifically
#                 pass # Skip file on read error
#
#     try:
#         with open(output_json_path, 'w', encoding='utf-8') as f:
#             json.dump(code_data, f, indent=4)
#         print(f"Code formatted JSON saved to {output_json_path}")
#     except Exception as e:
#         print(f"Error saving code JSON to {output_json_path}: {e}")
#         raise # Re-raise to be caught by processor


def process_my_repository(target_id):
    #source_directory = "/path/to/your/repository"  # 替换为你的实际代码库路径
    source_directory = global_source_directory
    output_file = global_output_file      # 替换为你想要的输出文件名
    unique_instance_id = global_unique_instance_id # 替换为你的实例ID
    repository_git_name = global_repository_git_name # 例如 "octocat/Spoon-Knife"



    print(f"开始处理代码库: {source_directory}")
    print(f'输入文件路径{source_directory}')

    try:
        # 如果使用 "from code_formatter import format_code_to_json_detailed"
        format_code_to_json_detailed(
            source_code_dir=source_directory,
            output_json_path=output_file,
            instance_id=unique_instance_id,
            repo_name=repository_git_name,
            # 你还可以根据需要传递 excluded_dirs 或 excluded_files
            # excluded_dirs=['.git', '.idea', 'build'],
            # excluded_files=['.DS_Store', 'temp.log']
        )

        # 如果使用 "import code_formatter"
        # code_formatter.format_code_to_json_detailed(
        #     source_code_dir=source_directory,
        #     output_json_path=output_file,
        #     instance_id=unique_instance_id,
        #     repo_name=repository_git_name
        # )

        print(f"代码库结构已成功保存到: {os.path.abspath(output_file)}")

    except FileNotFoundError:
        print(f"错误：源目录 '{source_directory}' 未找到。请检查路径。")
    except Exception as e:
        print(f"在处理过程中发生错误: {e}")


# Placeholder for the tool that formats bug description into JSON
# This implementation simply wraps the description string in a JSON object
def format_description_to_json(description: str, output_json_path: str):
    """
    Formats the bug description string into a JSON file.
    Example JSON structure: {'bug_description': '...'}
    """
    description_data = {'bug_description': description}
    print(f"Formatting bug description to {output_json_path}")
    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(description_data, f, indent=4)
        print(f"Bug description JSON saved to {output_json_path}")
    except Exception as e:
         print(f"Error saving description JSON to {output_json_path}: {e}")
         raise # Re-raise to be caught by processor


# --- Core Processing Logic Class ---
class BugFixProcessor:
    def __init__(self, api_key: str, target_id: str, bug_description: str, code_zip_stream):
        self.api_key = api_key
        self.target_id = target_id
        self.bug_description = bug_description
        self.code_zip_stream = code_zip_stream
        self.temp_dir = BASE_DIR + 'temp' # To be set by the temporary directory context manager
        self.code_dir = BASE_DIR + 'code' # Directory where code is unpacked
        self.code_json_path = None # Path to formatted code JSON
        self.description_json_path = None # Path to formatted description JSON
        source_directory = BASE_DIR + f'/code/{target_id}'
        output_file = f'{self.target_id}'  # 替换为你想要的输出文件名
        unique_instance_id = f"{target_id}"  # 替换为你的实例ID
        repository_git_name = "your_username/your_project"  # 例如 "octocat/Spoon-Knife"
        global global_output_file, global_unique_instance_id, global_repository_git_name, global_source_directory
        global_output_file = output_file
        global_unique_instance_id = unique_instance_id
        global_repository_git_name = repository_git_name
        global_source_directory = source_directory

    def process(self):
        """
        Main method to orchestrate the bug fixing process.
        """
        # Initial result structure
        result = {"target_id": self.target_id, "status": "failed", "message": "Processing started.", "data": None}

        try:
            # 1. Create a temporary directory for file operations
            # Use TemporaryDirectory context manager for automatic cleanup
            with tempfile.TemporaryDirectory() as temp_dir:
                self.temp_dir = temp_dir
                print(f"Using temporary directory: {self.temp_dir}")

                # Define paths within the temporary directory
                self.code_dir = os.path.join(self.temp_dir, "source_code")
                self.code_json_path = os.path.join(self.temp_dir, "source_code_formatted.json")
                self.description_json_path = os.path.join(self.temp_dir, "bug_description.json")

                # Ensure the code directory exists before unpacking
                os.makedirs(self.code_dir, exist_ok=True)

                # 2. Unpack the zip file stream
                print("Starting zip unpacking...")
                #这里要改code_dir,要不然会存在C:/   /temp
                #self._unpack_zip(self.code_dir)
                self._unpack_zip(global_source_directory)
                print(f"Code unpacked successfully to: {self.code_dir}")

                # 3. Format code to JSON
                print("Starting code formatting...")
                #format_code_to_json(self.code_dir, self.code_json_path)
                process_my_repository(self.target_id)
                print(f"Code formatted JSON created at: {self.code_json_path}")

                # 4. Format bug description to JSON
                print("Starting bug description formatting...")
                format_description_to_json(self.bug_description, self.description_json_path)
                print(f"Bug description JSON created at: {self.description_json_path}")

                # 5. Call Agentless library
                print("Calling Agentless library...")
                agentless_result = self._call_agentless(BASE_DIR + f'{self.target_id}', self.description_json_path)
                print(f"Agentless call finished with status: {agentless_result[0]}")

                # 6. Process Agentless result
                status, context = agentless_result
                if status == "success": # Assuming Agentless returns "success" on completion
                    result["status"] = "success"
                    result["message"] = "Bug fix generated successfully."
                    # Assuming context is a dict with 'code_diff' and 'problem_analysis'
                    result["data"] = {
                        "code_diff": context.get("code_diff", "No diff provided by Agentless."),
                        "problem_analysis": context.get("problem_analysis", "No analysis provided by Agentless.")
                    }
                else:
                    result["status"] = "failed"
                    result["message"] = f"Agentless failed to generate fix. Status: {status}."
                    # Include context for debugging purposes if Agentless provides error details
                    result["data"] = {"agentless_cotext": context, "details": "See context for Agentless error details."}


        except zipfile.BadZipFile:
            result["message"] = "Invalid zip file provided. Please upload a valid zip archive."
            result["status"] = "failed"
            print(f"Error: Invalid zip file for target_id {self.target_id}")
        except FileNotFoundError as e:
             result["message"] = f"Internal error: Required file or directory not found during processing. Details: {e}"
             result["status"] = "failed"
             print(f"Error: File not found for target_id {self.target_id}: {e}")
             traceback.print_exc()
        except Exception as e:
            # Catch any other unexpected errors during the process
            result["message"] = f"An unexpected internal error occurred: {e}"
            result["status"] = "failed"
            print(f"An unexpected error occurred for target_id {self.target_id}: {e}")
            # Log the full traceback for debugging on the backend
            traceback.print_exc()

        # Temporary directory and its contents are automatically removed when exiting the 'with' block

        print(f"Processing finished for target_id {self.target_id}. Final status: {result['status']}")
        return result

    def _unpack_zip(self, extract_to_dir: str):
        """Unpacks the zip stream into the specified directory."""
        # The code_zip_stream is a file-like object from Flask request.files
        with zipfile.ZipFile(self.code_zip_stream, 'r') as zip_ref:
            # Ensure extracted files do not escape the target directory (security consideration)
            # This is a basic check, more robust validation might be needed for untrusted sources
            for member in zip_ref.namelist():
                # Skip directories
                if member.endswith('/'):
                    continue
                # Construct the full path where the file will be extracted
                member_path = os.path.join(extract_to_dir, member)
                # Ensure the extraction path is inside the target directory
                if not os.path.abspath(member_path).startswith(os.path.abspath(extract_to_dir)):
                    print(f"Warning: Attempted path traversal detected, skipping {member}")
                    continue
                # Create parent directories if they don't exist
                os.makedirs(os.path.dirname(member_path), exist_ok=True)
                # Extract the file
                with zip_ref.open(member) as source, open(member_path, 'wb') as target:
                    target.write(source.read())


    def _call_agentless(self, project_dir: str, bug_description_json_path: str):
        """Calls the Agentless library with necessary configurations."""
        try:
            print("Configuring Agentless...")
            # Set Agentless configurations using the provided API_KEY and URL
            Agentless.set_API_KEY(api_key=self.api_key)
            Agentless.set_PROJECT_FILE_LOC(project_dir) # Set the location of the code project
            Agentless.set_OPENAI_API_URL(AGENTLESS_OPENAI_API_URL) # Set the OpenAI API URL

            # Prepare arguments for Agentless
            # Based on user's example Agentless.AgentlessArgs("文件路径", "文件名称.json")
            # Interpreting this as directory_containing_json, json_filename
            description_json_directory = os.path.dirname(bug_description_json_path)
            description_json_filename = os.path.basename(bug_description_json_path)

            print(f"AgentlessArgs: directory='{description_json_directory}', filename='{description_json_filename}'")
            agentless_args = Agentless.AgentlessArgs(description_json_directory, description_json_filename)

            # Instantiate and run Agentless
            print("Instantiating Agentless...")
            agentless = Agentless.Agentless(agentless_args=agentless_args)
            print("Running Agentless...")
            agentless.run() # This call is likely synchronous or blocks until done

            # Get results
            print("Getting Agentless result...")
            [status, context] = agentless.result() # Assuming this returns a list [status, context_dict]

            print(f"Agentless returned status: {status}")
            # print(f"Agentless returned context: {context}") # Be cautious printing large context

            return [status, context] # Return the raw result from Agentless

        except Exception as e:
            # Catch errors specifically during the Agentless call
            print(f"Error calling Agentless library for target_id {self.target_id}: {e}")
            traceback.print_exc()
            # Return a specific error status and context for internal Agentless errors
            return ["agentless_error", {"message": f"Error during Agentless execution: {e}"}]


# --- Flask App Initialization ---
app = Flask(__name__)

# --- Flask Route ---
@app.route('/process_bug_fix', methods=['POST'])
def process_bug_fix_route():
    """
    Flask route to receive bug fix request.
    Expects a POST request with form-data:
    - 'code_zip': The zip file of the source code.
    - 'api_data': A JSON string containing {'API_KEY': '...', 'target_id': '...'}.
    - 'bug_description': The text description of the bug.
    """
    print("Received POST request to /process_bug_fix")

    # 1. Validate input data presence
    if 'code_zip' not in request.files:
        print("Missing code_zip file.")
        return jsonify({"target_id": "N/A", "status": "failed", "message": "Missing code_zip file in request."}), 400

    if 'api_data' not in request.form:
         print("Missing api_data form field.")
         return jsonify({"target_id": "N/A", "status": "failed", "message": "Missing api_data form field."}), 400

    if 'bug_description' not in request.form:
         print("Missing bug_description form field.")
         return jsonify({"target_id": "N/A", "status": "failed", "message": "Missing bug_description form field."}), 400

    code_zip_file = request.files['code_zip']
    api_data_str = request.form['api_data']
    bug_description = request.form['bug_description']

    # 2. Parse and validate api_data JSON
    api_key = "N/A" # Default for logging/error reporting if parsing fails
    target_id = "N/A" # Default for logging/error reporting if parsing fails
    try:
        # api_data is expected to be a JSON string in the form data
        api_data = json.loads(api_data_str)
        api_key = api_data.get('API_KEY')
        target_id = api_data.get('target_id')

        if not api_key or not target_id:
             print(f"Invalid api_data format: {api_data_str}. Missing API_KEY or target_id.")
             return jsonify({"target_id": target_id, "status": "failed", "message": "Invalid api_data format. Missing API_KEY or target_id."}), 400

    except json.JSONDecodeError:
         print(f"api_data is not a valid JSON string: {api_data_str}")
         return jsonify({"target_id": "N/A", "status": "failed", "message": "api_data is not a valid JSON string."}), 400
    except Exception as e:
         print(f"Error processing api_data for target_id {target_id}: {e}")
         return jsonify({"target_id": target_id, "status": "failed", "message": f"Error processing api_data: {e}"}), 400


    print(f"Processing request for target_id: {target_id}")

    # 3. Instantiate and run the BugFixProcessor
    # Pass the file stream from the uploaded file directly to the processor
    processor = BugFixProcessor(api_key, target_id, bug_description, code_zip_file.stream)
    processing_result = processor.process() # This will block until processing is done

    # 4. Return the result as JSON
    # Determine HTTP status code based on the processing result status
    # 200 OK for success, 500 Internal Server Error for any failure during processing
    http_status = 200 if processing_result.get("status") == "success" else 500

    print(f"Returning response for target_id {target_id} with status {processing_result['status']} (HTTP {http_status})")
    return jsonify(processing_result), http_status


# --- Run the Flask App ---
if __name__ == '__main__':
    # In a production environment, do not use debug=True and use a production WSGI server
    # (e.g., Gunicorn, uWSGI). Also, bind to a specific host/port.
    print("Starting Flask app...")
    app.run(debug=True, port=5000)
    print("Flask app stopped.")


import os
import zipfile
import tempfile
import json
import datetime
import sys
from flask import Flask, request, jsonify, current_app
import traceback  # For logging errors
from code_formatter import format_code_to_json_detailed  # Assuming this is correctly imported

# BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # This is already defined globally
# import code_formatter # Not needed if using direct import as above

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

    AgentlessArgs = MockAgentlessArgs  # Assign the inner class

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
                # In a real scenario, 'code_diff' and 'problem_analysis' would be generated
                # by Agentless based on the bug_data. For the mock, we can simulate.
                simulated_analysis = f"Based on problem statement: '{bug_data.get('problem_statement', 'No problem statement')}', the simulated problem analysis is... (This is mock analysis)"
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
    # 获取当前文件所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取父目录的绝对路径 (Agentless 目录)
    parent_dir = os.path.dirname(current_dir)

    # 将父目录添加到 sys.path
    sys.path.append(parent_dir)
    import Agentless  # Try importing the real one

    print("Using actual Agentless library.")
    sys.path.remove(parent_dir)
except ImportError:
    print("Actual Agentless library not found. Using MockAgentless.")
    Agentless = MockAgentless  # Use the mock if real not found

# --- Configuration ---
# Agentless OpenAI API URL (from user's example, should ideally be configurable)
AGENTLESS_OPENAI_API_URL = 'https://api.deepseek.com/v1'

# --- Helper Functions / Formatting Tools ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def process_my_repository(target_id):
    source_directory = global_source_directory
    output_file = global_output_file
    unique_instance_id = global_unique_instance_id
    repository_git_name = global_repository_git_name

    print(f"开始处理代码库: {source_directory}")
    print(f'输入文件路径{source_directory}')

    try:
        format_code_to_json_detailed(
            source_code_dir=source_directory,
            #output_json_path=os.path.abspath(os.path.join(os.path.dirname(__file__))),
            output_json_path=output_file,
            instance_id=unique_instance_id,
            repo_name=repository_git_name,
            # You can also pass excluded_dirs or excluded_files as needed
            # excluded_dirs=['.git', '.idea', 'build'],
            # excluded_files=['.DS_Store', 'temp.log']
        )
        print('路径测试点',f'{os.path.abspath(os.path.join(os.path.dirname(__file__)))}')
        print(f"代码库结构已成功保存到: {os.path.abspath(output_file)}")

    except FileNotFoundError:
        print(f"错误：源目录 '{source_directory}' 未找到。请检查路径。")
    except Exception as e:
        print(f"在处理过程中发生错误: {e}")


# Enhanced format_description_to_json function
def format_description_to_json(
        description: str,
        output_json_path: str,
        repo: str,
        instance_id: str,
        base_commit: str,
        patch: str,
        test_patch: str,
        problem_statement: str,
        hints_text: str,
        created_at: str,
        version: str,
        FAIL_TO_PASS: list,
        PASS_TO_PASS: list,
        environment_setup_commit: str
):
    """
    Formats the bug description and associated metadata into a JSON file.
    Example JSON structure:
    {
        "repo": "astropy/astropy",
        "instance_id": "astropy__astropy-12907-deyudada",
        "base_commit": "d16bfe05a744909de4b27f5875fe0d4ed41ce607",
        "patch": "...",
        "test_patch": "...",
        "problem_statement": "...",
        "hints_text": "",
        "created_at": "2022-03-03T15:14:54Z",
        "version": "4.3",
        "FAIL_TO_PASS": ["..."],
        "PASS_TO_PASS": ["..."],
        "environment_setup_commit": "298ccb478e6bf092953bca67a3d29dc6c35f6752"
    }
    """
    description_data = {
        "repo": repo,
        "instance_id": instance_id,
        "base_commit": base_commit,
        "patch": patch,
        "test_patch": test_patch,
        "problem_statement": problem_statement,
        "hints_text": hints_text,
        "created_at": created_at,
        "version": version,
        "FAIL_TO_PASS": FAIL_TO_PASS,
        "PASS_TO_PASS": PASS_TO_PASS,
        "environment_setup_commit": environment_setup_commit
    }
    print(f"Formatting bug description and metadata to {output_json_path}")
    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(description_data, f, indent=4)
        print(f"Bug description JSON saved to {output_json_path}")
    except Exception as e:
        print(f"Error saving description JSON to {output_json_path}: {e}")
        raise  # Re-raise to be caught by processor


# --- Core Processing Logic Class ---
class BugFixProcessor:
    def __init__(
            self,
            api_key: str,
            target_id: str,
            bug_description: str,  # This will likely be the problem_statement now
            code_zip_stream,
            repo: str,
            base_commit: str,
            patch: str,
            test_patch: str,
            hints_text: str,
            created_at: str,
            version: str,
            FAIL_TO_PASS: list,
            PASS_TO_PASS: list,
            environment_setup_commit: str
    ):
        self.api_key = api_key
        self.target_id = target_id
        # Use bug_description as problem_statement as per the desired JSON structure
        self.problem_statement = bug_description
        self.code_zip_stream = code_zip_stream
        self.repo = repo
        self.base_commit = base_commit
        self.patch = patch
        self.test_patch = test_patch
        self.hints_text = hints_text
        self.created_at = created_at
        self.version = version
        self.FAIL_TO_PASS = FAIL_TO_PASS
        self.PASS_TO_PASS = PASS_TO_PASS
        self.environment_setup_commit = environment_setup_commit

        self.temp_dir = BASE_DIR + '/temp'  # To be set by the temporary directory context manager
        self.code_dir = BASE_DIR + '/code'  # Directory where code is unpacked
        self.code_json_path = None  # Path to formatted code JSON
        self.description_json_path = None  # Path to formatted description JSON

        # Update global variables for process_my_repository
        global global_output_file, global_unique_instance_id, global_repository_git_name, global_source_directory
        global_source_directory = os.path.join(self.code_dir, self.target_id)  # Consistent with _unpack_zip
        global_output_file = f'{self.target_id}_code_formatted.json'  # Giving it a more distinct name
        global_unique_instance_id = self.target_id
        global_repository_git_name = self.repo

    def process(self):
        """
        Main method to orchestrate the bug fixing process.
        """
        # Initial result structure
        result = {"target_id": self.target_id, "status": "failed", "message": "Processing started.", "data": None}

        try:
            # 1. Create a temporary directory for file operations
            with tempfile.TemporaryDirectory() as temp_dir:
                self.temp_dir = temp_dir
                print(f"Using temporary directory: {self.temp_dir}")

                # Define paths within the temporary directory
                # The code_dir will be a subdirectory within the temp_dir to hold unpacked code
                self.code_dir = os.path.join(self.temp_dir, "source_code")
                # Ensure global_source_directory points to the correct unpacked location
                global global_source_directory
                global_source_directory = self.code_dir

                self.code_json_path = os.path.join(self.temp_dir, global_output_file)  # Use the global output file name
                self.description_json_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), os.path.pardir, 'dataset','dataset.jsonl')
                )
                # Ensure the code directory exists before unpacking
                os.makedirs(self.code_dir, exist_ok=True)

                # 2. Unpack the zip file stream
                print("Starting zip unpacking...")
                self._unpack_zip(self.code_dir)  # Unpack to the temp code_dir
                print(f"Code unpacked successfully to: {self.code_dir}")

                # 3. Format code to JSON
                print("Starting code formatting...")
                process_my_repository(
                    self.target_id)  # This function now uses global_source_directory and global_output_file
                print(f"Code formatted JSON created at: {self.code_json_path}")

                # 4. Format bug description to JSON with all metadata
                print("Starting bug description formatting...")
                format_description_to_json(
                    description=self.problem_statement, # Using problem_statement as the main bug description
                    output_json_path=self.description_json_path,
                    repo=self.repo,
                    instance_id=self.target_id, # target_id often maps to instance_id
                    base_commit=self.base_commit,
                    patch=self.patch,
                    test_patch=self.test_patch,
                    problem_statement=self.problem_statement,
                    hints_text=self.hints_text,
                    created_at=self.created_at,
                    version=self.version,
                    FAIL_TO_PASS=self.FAIL_TO_PASS,
                    PASS_TO_PASS=self.PASS_TO_PASS,
                    environment_setup_commit=self.environment_setup_commit
                )
                print(f"Bug description JSON created at: {self.description_json_path}")

                # 5. Call Agentless library
                print("Calling Agentless library...")
                # Agentless needs the directory containing the JSON and the JSON filename
                agentless_result = self._call_agentless(os.path.join(os.path.dirname(__file__),f'{self.target_id}.json'), global_unique_instance_id)#要改
                print(f"Agentless call finished with status: {agentless_result[0]}")

                # 6. Process Agentless results
                status, context = agentless_result
                if status == "success":
                    result["status"] = "success"
                    result["message"] = "Bug fix generated successfully."
                    result["data"] = {
                        "code_diff": context.get("code_diff", "No diff provided by Agentless."),
                        "problem_analysis": context.get("problem_analysis", "No analysis provided by Agentless.")
                    }
                else:
                    result["status"] = "failed"
                    result["message"] = f"Agentless failed to generate fix. Status: {status}."
                    result["data"] = {"agentless_context": context,
                                      "details": "See context for Agentless error details."}


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
            result["message"] = f"An unexpected internal error occurred: {e}"
            result["status"] = "failed"
            print(f"An unexpected error occurred for target_id {self.target_id}: {e}")
            traceback.print_exc()

        print(f"Processing finished for target_id {self.target_id}. Final status: {result['status']}")
        return result

    def _unpack_zip(self, extract_to_dir: str):
        """Unpacks the zip stream into the specified directory."""
        with zipfile.ZipFile(self.code_zip_stream, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith('/'):
                    continue
                member_path = os.path.join(extract_to_dir, member)
                if not os.path.abspath(member_path).startswith(os.path.abspath(extract_to_dir)):
                    print(f"Warning: Attempted path traversal detected, skipping {member}")
                    continue
                os.makedirs(os.path.dirname(member_path), exist_ok=True)
                with zip_ref.open(member) as source, open(member_path, 'wb') as target:
                    target.write(source.read())

    def _call_agentless(self, project_dir: str, target_id: str):
        """Calls the Agentless library with necessary configurations."""
        try:
            print("Configuring Agentless...")
            Agentless.set_API_KEY(api_key=self.api_key)
            Agentless.set_PROJECT_FILE_LOC(project_dir)
            Agentless.set_OPENAI_API_URL(AGENTLESS_OPENAI_API_URL)

            print(f"AgentlessArgs: directory='{project_dir}', target_id='{target_id}'")
            agentless_args = Agentless.AgentlessArgs(project_dir, target_id)

            print("Instantiating Agentless...")
            agentless = Agentless.Agentless(agentless_args=agentless_args)
            print("Running Agentless...")
            agentless.run()

            print("Getting Agentless result...")
            [status, context] = agentless.result()

            print(f"Agentless returned status: {status}")
            return [status, context]

        except Exception as e:
            print(f"Error calling Agentless library for target_id {self.target_id}: {e}")
            traceback.print_exc()
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
    - 'bug_details': A JSON string containing all detailed bug metadata.
    """
    print("Received POST request to /process_bug_fix")

    # 1. Validate input data presence
    if 'code_zip' not in request.files:
        print("Missing code_zip file.")
        return jsonify({"target_id": "N/A", "status": "failed", "message": "Missing code_zip file in request."}), 400

    if 'api_data' not in request.form:
        print("Missing api_data form field.")
        return jsonify({"target_id": "N/A", "status": "failed", "message": "Missing api_data form field."}), 400

    if 'bug_description' not in request.form:  # New field for all bug metadata
        print("Missing bug_details form field.")
        return jsonify({"target_id": "N/A", "status": "failed", "message": "Missing bug_details form field."}), 400

    code_zip_file = request.files['code_zip']
    api_data_str = request.form['api_data']
    bug_details_str = request.form['bug_description']  # Get the new bug_details string

    # 2. Parse and validate api_data JSON
    api_key = "N/A"
    target_id = "N/A"
    try:
        api_data = json.loads(api_data_str)
        api_key = api_data.get('API_KEY')
        target_id = api_data.get('target_id')

        if not api_key or not target_id:
            print(f"Invalid api_data format: {api_data_str}. Missing API_KEY or target_id.")
            return jsonify({"target_id": target_id, "status": "failed",
                            "message": "Invalid api_data format. Missing API_KEY or target_id."}), 400

    except json.JSONDecodeError:
        print(f"api_data is not a valid JSON string: {api_data_str}")
        return jsonify({"target_id": "N/A", "status": "failed", "message": "api_data is not a valid JSON string."}), 400
    except Exception as e:
        print(f"Error processing api_data for target_id {target_id}: {e}")
        return jsonify({"target_id": target_id, "status": "failed", "message": f"Error processing api_data: {e}"}), 400

    # 3. Parse and validate bug_details JSON
    bug_details = {}
    try:
        bug_details = json.loads(bug_details_str)
        # Extract all fields from bug_details.
        # Provide default empty values if keys might be missing to prevent KeyError.
        repo = bug_details.get('repo', 'N/A')
        base_commit = bug_details.get('base_commit', 'N/A')
        #patch = bug_details.get('patch', '')
        #test_patch = bug_details.get('test_patch', '')
        problem_statement = bug_details.get('problem_statement', 'No problem statement provided.')
        #hints_text = bug_details.get('hints_text', '')
        #created_at = bug_details.get('created_at', '')
        #version = bug_details.get('version', '')
        #FAIL_TO_PASS = bug_details.get('FAIL_TO_PASS', [])
        #PASS_TO_PASS = bug_details.get('PASS_TO_PASS', [])
        #environment_setup_commit = bug_details.get('environment_setup_commit', '')

        # You might also want to ensure that essential fields are present in bug_details
        if not all([repo, base_commit, problem_statement]):
            print(f"Invalid bug_details format for target_id {target_id}. Missing essential fields.")
            return jsonify({"target_id": target_id, "status": "failed",
                            "message": "Invalid bug_details format. Missing essential fields like repo, base_commit, or problem_statement."}), 400

    except json.JSONDecodeError:
        print(f"bug_details is not a valid JSON string: {bug_details_str}")
        return jsonify(
            {"target_id": target_id, "status": "failed", "message": "bug_details is not a valid JSON string."}), 400
    except Exception as e:
        print(f"Error processing bug_details for target_id {target_id}: {e}")
        return jsonify(
            {"target_id": target_id, "status": "failed", "message": f"Error processing bug_details: {e}"}), 400

    print(f"Processing request for target_id: {target_id}")

    # 4. Instantiate and run the BugFixProcessor
    processor = BugFixProcessor(
        api_key=api_key,
        target_id=target_id,
        bug_description=problem_statement,  # Pass problem_statement as bug_description
        code_zip_stream=code_zip_file.stream,
        repo='',
        base_commit='',
        patch='',
        test_patch='',
        hints_text='',
        created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        version='',
        FAIL_TO_PASS=[],
        PASS_TO_PASS=[],
        environment_setup_commit=''
    )
    processing_result = processor.process()

    # 5. Return the result as JSON
    http_status = 200 if processing_result.get("status") == "success" else 500

    print(
        f"Returning response for target_id {target_id} with status {processing_result['status']} (HTTP {http_status})")
    return jsonify(processing_result), http_status


# --- Run the Flask App ---
if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True, port=5000)
    print("Flask app stopped.")

import os
import zipfile
import tempfile
import json
import datetime
import sys
from flask import Flask, request, jsonify
import traceback
import shutil # 导入 shutil 模块
from flask_cors import CORS # 1. 导入 CORS 扩展

# --- Configuration and Base Paths ---
# BASE_DIR should point to the directory containing service.py (i.e., Agentless/service)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the absolute path for the Agentless module parent directory (Agentless/)
AGENTLESS_MODULE_PARENT_DIR = os.path.dirname(BASE_DIR)

# Add AGENTLESS_MODULE_PARENT_DIR to sys.path for Agentless import
if AGENTLESS_MODULE_PARENT_DIR not in sys.path:
    sys.path.insert(0, AGENTLESS_MODULE_PARENT_DIR)

# Assume code_formatter is in the same directory as service.py or accessible via sys.path
try:
    from code_formatter import format_code_to_json_detailed
except ImportError:
    print("Error: 'code_formatter.py' not found. Please ensure it's in the same directory as 'service.py' or accessible via PYTHONPATH.")
    sys.exit(1) # Exit if essential module is missing

# Agentless OpenAI API URL (from user's example, should ideally be configurable)
AGENTLESS_OPENAI_API_URL = 'https://api.deepseek.com/v1'


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
        import time
        time.sleep(1)

        # Simulate reading the bug description JSON
        # In the mock, we assume the file_path is the directory and file_name is the JSON file.
        # This aligns with how the Agentless call is made with the formatted code JSON.
        bug_desc_path = os.path.join(self.agentless_args.file_path, self.agentless_args.file_name)
        try:
            with open(bug_desc_path, 'r', encoding='utf-8') as f:
                bug_data = json.load(f)
                simulated_analysis = f"Based on formatted code file: '{bug_data.get('repo_name', 'No repo name')}' and instance ID '{bug_data.get('instance_id', 'No instance ID')}', the simulated problem analysis is... (This is mock analysis)"
                simulated_diff = f"--- a/some/file.py\n+++ b/some/file.py\n@@ -1,5 +1,6 @@\n # Original line\n-print('Hello')\n+print('Hello, World!') # Fix applied\n # Another line\n"
                self._result = ["success", {"code_diff": simulated_diff, "problem_analysis": simulated_analysis}]
                print("MockAgentless: Mock run successful.")
        except Exception as e:
            print(f"MockAgentless: Error reading file for mock run: {e}")
            self._result = ["error", {"message": f"Mock error: could not read file {bug_desc_path}"}]

    def result(self):
        print("MockAgentless: Returning mock result.")
        return self._result


# Use the mock Agentless or the real one
try:
    import Agentless  # Try importing the real one
    print("Using actual Agentless library.")
except ImportError:
    print("Actual Agentless library not found. Using MockAgentless.")
    Agentless = MockAgentless


# --- Helper Functions ---
def append_to_jsonl(data: dict, file_path: str):
    """Appends a dictionary as a JSON line to a .jsonl file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        print(f"Data successfully appended to {file_path}")
    except Exception as e:
        print(f"Error appending data to {file_path}: {e}")
        raise


# --- Core Processing Logic Class ---
class BugFixProcessor:
    def __init__(
            self,
            api_key: str,
            target_id: str,
            bug_description_data: dict,  # Pass the entire parsed bug_details dictionary
            code_zip_stream,
            api_key_embedding: str,
    ):
        self.api_key = api_key
        self.target_id = target_id
        self.bug_description_data = bug_description_data
        self.code_zip_stream = code_zip_stream
        self.api_key_embedding = api_key_embedding

        # Define final output paths relative to BASE_DIR (Agentless/service/)
        self.final_code_json_path = os.path.join(BASE_DIR, f'{self.target_id}.json')
        # This will be Agentless/dataset/dataset.jsonl
        self.dataset_jsonl_path = os.path.abspath(os.path.join(BASE_DIR, os.pardir, 'dataset', 'dataset.jsonl'))


    def process(self):
        """
        Main method to orchestrate the bug fixing process.
        """
        # --- MODIFICATION START ---
        # 1. 确保初始状态是 "failed"，作为默认值
        result = {"target_id": self.target_id, "status": "failed", "message": "Processing started.", "data": None}
        # --- MODIFICATION END ---

        # Use a temporary directory for unpacking code to avoid conflicts and clean up easily
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_code_dir = os.path.join(temp_dir, "source_code")
            os.makedirs(temp_code_dir, exist_ok=True)
            temp_code_json_output_path = os.path.join(temp_dir, f'{self.target_id}.json')

            try:
                # 1. Unpack the zip file stream to the temporary directory
                print(f"Starting zip unpacking to: {temp_code_dir}...")
                self._unpack_zip(temp_code_dir)
                print(f"Code unpacked successfully to: {temp_code_dir}")

                # 2. Format code to JSON in the temporary directory
                print("Starting code formatting...")
                format_code_to_json_detailed(
                    source_code_dir=temp_code_dir,
                    output_json_path=temp_code_json_output_path, # Save to temp location first
                    instance_id=self.target_id,
                    repo_name=self.bug_description_data.get('repo', 'unknown_repo')
                )
                print(f"Code formatted JSON temporarily created at: {temp_code_json_output_path}")

                # 3. Move the formatted code JSON to its final destination
                # 使用 shutil.move 替换 os.rename 来处理跨磁盘移动
                shutil.move(temp_code_json_output_path, self.final_code_json_path)
                print(f"Code formatted JSON moved to final path: {self.final_code_json_path}")

                # 4. Append bug description to dataset.jsonl
                print("Appending bug description to dataset.jsonl...")
                # The format_description_to_json is integrated here to directly append to JSONL
                append_to_jsonl(self.bug_description_data, self.dataset_jsonl_path)
                print(f"Bug description appended to: {self.dataset_jsonl_path}")

                # 5. Call Agentless library with the final code JSON path
                print("Calling Agentless library...")
                # Agentless needs the directory and the filename separately, if not, adjust.
                # Assuming Agentless.AgentlessArgs expects (directory, filename)
                agentless_result = self._call_agentless(
                    file_path=os.path.dirname(self.final_code_json_path),
                    file_name=os.path.basename(self.final_code_json_path)
                )
                print(f"Agentless call finished with status: {agentless_result[0]}")

                # 6. Process Agentless results
                status, context = agentless_result
                # --- MODIFICATION START ---
                # 2. 根据 _call_agentless 返回的 "status" (字符串 "success" 或 "error" 或 "agentless_error") 来判断
                if status == "success":
                    result["status"] = "success"
                    result["message"] = "Bug fix generated successfully."
                    result["data"] = {
                        "code_diff": context.get("code_diff", "No diff provided by Agentless."),
                        "problem_analysis": context.get("problem_analysis", "No analysis provided by Agentless.")
                    }
                else: # 处理 "error" 或 "agentless_error" 或其他非 "success" 的状态
                    result["status"] = "failed"
                    result["message"] = f"Agentless failed to generate fix. Status: {status}."
                    # 安全地处理 context，确保它是一个字典
                    if isinstance(context, dict):
                        result["data"] = {"agentless_context": context, "details": "See context for Agentless error details."}
                    else:
                        result["data"] = {"agentless_context": {"message": str(context)}, "details": "Agentless internal error or unexpected context type."}
                # --- MODIFICATION END ---

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
                # 确保通用异常捕获也设置 status 为 "failed"
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
                # Prevent directory traversal vulnerability
                member_path = os.path.join(extract_to_dir, member)
                if not os.path.abspath(member_path).startswith(os.path.abspath(extract_to_dir)):
                    print(f"Warning: Attempted path traversal detected, skipping {member}")
                    continue
                # Create directories if they don't exist
                os.makedirs(os.path.dirname(member_path), exist_ok=True)
                # Extract file
                if not member.endswith('/'): # Only extract files, not directories themselves
                    with zip_ref.open(member) as source, open(member_path, 'wb') as target:
                        target.write(source.read())

    def _call_agentless(self, file_path: str, file_name: str):
        """Calls the Agentless library with necessary configurations."""
        try:
            print("Configuring Agentless...")
            Agentless.set_API_KEY(api_key=self.api_key)
            Agentless.set_EMBEDDING_API_KEY(API_KEY=self.api_key_embedding)
            # Agentless.set_PROJECT_FILE_LOC expects the directory containing the file
            Agentless.set_PROJECT_FILE_LOC(file_path)
            Agentless.set_OPENAI_API_URL(AGENTLESS_OPENAI_API_URL)

            print(f"AgentlessArgs: file_path='{file_path}', file_name='{file_name}'")
            parts = file_name.rsplit('.', 1)  # 从右边开始，最多分割一次
            file_name_split = parts[0]
            agentless_args = Agentless.AgentlessArgs(file_path, file_name_split)

            print("Instantiating Agentless...")
            agentless = Agentless.Agentless(agentless_args=agentless_args)
            print("Running Agentless...")
            agentless.run()

            print("Getting Agentless result...")
            [status, context] = agentless.result() # MockAgentless 返回 "success" 或 "error"

            print(f"Agentless returned status: {status}")
            return [status, context]

        except Exception as e:
            print(f"Error calling Agentless library for target_id {self.target_id}: {e}")
            traceback.print_exc()
            # 如果 Agentless 库内部发生异常，返回 "agentless_error" 状态
            return ["agentless_error", {"message": f"Error during Agentless execution: {e}"}]


# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app, resources={r"/process_bug_fix": {"origins": "http://localhost:1002"}})

# --- Flask Route ---
@app.route('/process_bug_fix', methods=['POST'])
def process_bug_fix_route():
    """
    Flask route to receive bug fix request.
    Expects a POST request with form-data:
    - 'code_zip': The zip file of the source code.
    - 'api_data': A JSON string containing {'API_KEY': '...', 'target_id': '...'}.
    - 'bug_description': A JSON string containing at least {'problem_statement': '...'}.
                         Other fields will be set to defaults if not provided.
    """
    print("Received POST request to /process_bug_fix")

    # 1. Validate input data presence
    required_files = ['code_zip']
    required_forms = ['api_data', 'bug_description']

    for field in required_files:
        if field not in request.files:
            print(f"Missing {field} file.")
            return jsonify({"target_id": "N/A", "status": "failed", "message": f"Missing {field} file in request."}), 400
    for field in required_forms:
        if field not in request.form:
            print(f"Missing {field} form field.")
            return jsonify({"target_id": "N/A", "status": "failed", "message": f"Missing {field} form field."}), 400

    code_zip_file = request.files['code_zip']
    api_data_str = request.form['api_data']
    bug_details_str = request.form['bug_description']

    # Initialize with default values for error handling
    api_key = "N/A"
    target_id = "N/A"
    bug_details = {}

    # 2. Parse and validate api_data JSON
    try:
        api_data = json.loads(api_data_str)
        api_key = api_data.get('API_KEY')
        target_id = api_data.get('target_id')
        api_key_embedding = api_data.get('API_KEY_EMBEDDING')

        if not api_key or not target_id or not api_key_embedding:
            print(f"Invalid api_data format: {api_data_str}. Missing API_KEY or target_id or api_key_embedding.")
            return jsonify({"target_id": target_id, "status": "failed",
                            "message": "Invalid api_data format. Missing API_KEY or target_id or api_key_embedding."}), 400

    except json.JSONDecodeError:
        print(f"api_data is not a valid JSON string: {api_data_str}")
        return jsonify({"target_id": "N/A", "status": "failed", "message": "api_data is not a valid JSON string."}), 400
    except Exception as e:
        print(f"Error processing api_data for target_id {target_id}: {e}")
        return jsonify({"target_id": target_id, "status": "failed", "message": f"Error processing api_data: {e}"}), 400

    # 3. Parse and validate bug_details JSON, filling in defaults
    try:
        raw_bug_details = json.loads(bug_details_str)

        # Ensure 'problem_statement' is present, which is the only required field
        if 'problem_statement' not in raw_bug_details:
            print(f"Invalid bug_description format for target_id {target_id}. Missing 'problem_statement'.")
            return jsonify({"target_id": target_id, "status": "failed",
                            "message": "Invalid bug_description format. Missing 'problem_statement'."}), 400

        # Construct the full bug_details dictionary with defaults
        bug_details = {
            "repo": raw_bug_details.get('repo', 'unknown_repo'),
            "instance_id": target_id, # Always use target_id from api_data as the primary instance_id
            "base_commit": raw_bug_details.get('base_commit', 'N/A'),
            "patch": raw_bug_details.get('patch', ''),
            "test_patch": raw_bug_details.get('test_patch', ''),
            "problem_statement": raw_bug_details['problem_statement'], # This is guaranteed to be present
            "hints_text": raw_bug_details.get('hints_text', ''),
            "created_at": raw_bug_details.get('created_at', datetime.datetime.now().isoformat() + 'Z'),
            "version": raw_bug_details.get('version', 'N/A'),
            "FAIL_TO_PASS": raw_bug_details.get('FAIL_TO_PASS', []),
            "PASS_TO_PASS": raw_bug_details.get('PASS_TO_PASS', []),
            "environment_setup_commit": raw_bug_details.get('environment_setup_commit', '')
        }

    except json.JSONDecodeError:
        print(f"bug_description is not a valid JSON string: {bug_details_str}")
        return jsonify(
            {"target_id": target_id, "status": "failed", "message": "bug_description is not a valid JSON string."}), 400
    except Exception as e:
        print(f"Error processing bug_description for target_id {target_id}: {e}")
        return jsonify(
            {"target_id": target_id, "status": "failed", "message": f"Error processing bug_description: {e}"}), 400

    print(f"Processing request for target_id: {target_id}")

    # 4. Instantiate and run the BugFixProcessor
    processor = BugFixProcessor(
        api_key=api_key,
        target_id=target_id,
        bug_description_data=bug_details, # Pass the fully constructed dictionary
        code_zip_stream=code_zip_file.stream,
        api_key_embedding=api_key_embedding,
    )
    processing_result = processor.process()

    # 5. Return the result as JSON
    # --- MODIFICATION START ---
    # 3. 根据 BugFixProcessor 返回的 processing_result 中的 "status" 字段来设置 HTTP 状态码
    http_status = 200 if processing_result.get("status") == "success" else 500
    # --- MODIFICATION END ---

    print(
        f"Returning response for target_id {target_id} with status {processing_result['status']} (HTTP {http_status})")
    return jsonify(processing_result), http_status


# --- Run the Flask App ---
if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True, port=5000)
    print("Flask app stopped.")
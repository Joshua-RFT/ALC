# Agentless.py
import json
import subprocess
import os

conda_env = [
    "conda",
    "run",
    "-n",
    "agentless"
]

def set_API_KEY(api_key):
    os.environ["OPENAI_API_KEY"] = api_key

def set_OPENAI_API_URL(api_url):
    os.environ["OPENAI_API_URL"] = api_url

def set_PROJECT_FILE_LOC(PROJECT_FILE_LOC):
    os.environ["PROJECT_FILE_LOC"] = PROJECT_FILE_LOC

def set_EMBEDDING_API_KEY(API_KEY):
    os.environ["EMBEDDING_API_KEY"] = API_KEY

class AgentlessArgs:
    """
    Attributes:
        PROJECT_FILE_LOC: str
        target_id: str
    """
    def __init__(self, PROJECT_FILE_LOC, target_id):
        self.PROJECT_FILE_LOC = PROJECT_FILE_LOC
        self.target_id = target_id
        self._tasks = {}  # 内部保存所有子任务

    def create_task(self, task_name, **task_args):
        task = Task(self, **task_args)
        self._tasks[task_name] = task
        setattr(self, task_name, task)  # 动态设置成属性 a.B = taskB对象

class Task:
    def __init__(self, parent, **task_args):
        self.parent = parent  # 保存父对象
        for k, v in task_args.items():
            setattr(self, k, v)  # 动态赋值任务自己的数据

    def get_public(self, name):
        """访问父对象的公共数据"""
        return getattr(self.parent, name)


class Agentless:
    def __init__(self,agentless_args):
        self.agentless_args = agentless_args
        self.context = None
        self.status = None
        self.construct_args(self.agentless_args)

    def construct_args(self, agentless_args):
        agentless_args.create_task('localize',
                                   file_level='--file_level',
                                   irrelevant='--irrelevant',
                                   output_folder='--output_folder',
                                   num_threads='--num_threads',
                                   skip_existing='--skip_existing',
                                   related_level='--related_level',
                                   top_n='--top_n',
                                   compress_assign='--compress_assign',
                                   compress='--compress',
                                   start_file='--start_file',
                                   fine_grain_line_level='--fine_grain_line_level',
                                   temperature='--temperature',
                                   num_samples='--num_samples',
                                   merge='--merge',
                                   target_id='--target_id'
                                   )
        agentless_args.create_task('retrieve',
                                   index_type='--index_type',
                                   filter_type='--filter_type',
                                   filter_file='--filter_file',
                                   output_folder='--output_folder',
                                   persist_dir='--persist_dir',
                                   num_threads='--num_threads',
                                   target_id='--target_id'
                                   )

        agentless_args.create_task('combine',
                                   retrieval_loc_file='--retrieval_loc_file',
                                   model_loc_file='--model_loc_file',
                                   top_n='--top_n',
                                   output_folder='--output_folder'
                                   )

        agentless_args.create_task('repair',
                                   loc_file='--loc_file',
                                   output_folder='--output_folder',
                                   loc_interval='--loc_interval',
                                   top_n='--top_n',
                                   context_window='--context_window',
                                   max_samples='--max_samples',
                                   cot='--cot',
                                   diff_format='--diff_format',
                                   gen_and_process='--gen_and_process',
                                   num_threads='--num_threads',
                                   target_id='--target_id'
                                   )

    def localize(self, localize_args_list):
        subprocess.run(conda_env + ['python', 'agentless/fl/localize.py'] + localize_args_list, check=True)

    def retrieve(self, retrieve_args_list):
        subprocess.run(conda_env + ['python', 'agentless/fl/retrieve.py'] + retrieve_args_list, check=True)

    def combine(self, combine_args_list):
        subprocess.run(conda_env + ['python', 'agentless/fl/combine.py'] + combine_args_list, check=True)

    def repair(self, repair_args_list):
        subprocess.run(conda_env + ['python', 'agentless/repair/repair.py'] + repair_args_list, check=True)

    def get_result(self):
        file_path = r"results\swe-bench-lite\repair_sample_1\output.jsonl" # 注意：这个路径是硬编码的
        key = 'raw_output'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # output.jsonl 文件通常每行是一个JSON对象，而不是一个单一的JSON数组/对象。
                # 如果是jsonlines格式，需要逐行读取和解析。
                # 假设这里我们只关心第一个JSON对象（或者文件本身就是一个大的JSON对象）
                # 为了安全起见，如果可能是jsonlines，应该这样处理：
                # lines = f.readlines()
                # if lines:
                #     data = json.loads(lines[0]) # 或者循环处理所有行
                # else:
                #     data = {}
                data = json.load(f) # 如果文件确实是单个JSON对象
                self.status = 200
                return data.get(key)
        except FileNotFoundError:
            print(f"错误: 文件 '{file_path}' 未找到。")
            self.status = 404 # 更合适的HTTP状态码
            return None
        except json.JSONDecodeError:
            print(f"错误: 文件 '{file_path}' 不是有效的 JSON 格式。")
            self.status = 400
            return None
        except Exception as e:
            print(f"发生未知错误: {e}")
            self.status = 500
            return None

    def result(self):
        self.context = self.get_result()
        return [self.status, self.context]


    def run(self):
        # print('Agentless run Successful,exit')
        # exit(1)
        agentless_args = self.agentless_args

        # localize0: Corresponds to:
        # python agentless/fl/localize.py --file_level \
        #                                --output_folder results/swe-bench-lite/file_level \
        #                                --num_threads 1 \
        #                                --skip_existing \
        #				                 --target_id=<actual_target_id>
        localize0_args = [
            agentless_args.localize.file_level,
            agentless_args.localize.output_folder, "results/swe-bench-lite/file_level",
            agentless_args.localize.num_threads, "1", # 根据你的注释，PowerShell用1，bash用10. 请选择一个或使其可配置
            agentless_args.localize.skip_existing,
            agentless_args.localize.target_id, agentless_args.target_id,
        ]
        print(f"Running localize (0) with args: {localize0_args}")
        self.localize(localize0_args)
        #exit()

        # localize1: Corresponds to:
        # python agentless/fl/localize.py --file_level \
        #                                --irrelevant \
        #                                --output_folder results/swe-bench-lite/file_level_irrelevant \
        #                                --num_threads 1 \
        #                                --skip_existing \
        #				                 --target_id=<actual_target_id>
        localize1_args = [
            agentless_args.localize.file_level,
            agentless_args.localize.irrelevant,
            agentless_args.localize.output_folder, 'results/swe-bench-lite/file_level_irrelevant',
            agentless_args.localize.num_threads, "1",
            agentless_args.localize.skip_existing,
            agentless_args.localize.target_id, agentless_args.target_id
        ]
        print(f"Running localize (1) with args: {localize1_args}")
        self.localize(localize1_args)

        # retrieve1: Corresponds to:
        # python agentless/fl/retrieve.py --index_type simple \
        #                                --filter_type given_files \
        #                                --filter_file results/swe-bench-lite/file_level_irrelevant/loc_outputs.jsonl \
        #                                --output_folder results/swe-bench-lite/retrievel_embedding \
        #                                --persist_dir embedding/swe-bench_simple \
        #                                --num_threads 1 \
        #				                 --target_id=<actual_target_id>
        retrieve1_args = [
            agentless_args.retrieve.index_type, "simple",
            agentless_args.retrieve.filter_type, "given_files",
            agentless_args.retrieve.filter_file, 'results/swe-bench-lite/file_level_irrelevant/loc_outputs.jsonl',
            agentless_args.retrieve.output_folder, 'results/swe-bench-lite/retrievel_embedding',
            agentless_args.retrieve.persist_dir, 'embedding/swe-bench_simple',
            agentless_args.retrieve.num_threads, "1",
            agentless_args.retrieve.target_id, agentless_args.target_id
        ]
        print(f"Running retrieve (1) with args: {retrieve1_args}")
        self.retrieve(retrieve1_args)

        # combine1: Corresponds to:
        # python agentless/fl/combine.py  --retrieval_loc_file results/swe-bench-lite/retrievel_embedding/retrieve_locs.jsonl \
        #                                --model_loc_file results/swe-bench-lite/file_level/loc_outputs.jsonl \
        #                                --top_n 3 \
        #                                --output_folder results/swe-bench-lite/file_level_combined
        combine1_args = [
            agentless_args.combine.retrieval_loc_file, 'results/swe-bench-lite/retrievel_embedding/retrieve_locs.jsonl',
            agentless_args.combine.model_loc_file, 'results/swe-bench-lite/file_level/loc_outputs.jsonl',
            agentless_args.combine.top_n, "3",
            agentless_args.combine.output_folder, 'results/swe-bench-lite/file_level_combined',
        ]
        print(f"Running combine (1) with args: {combine1_args}")
        self.combine(combine1_args)

        # localize2: Corresponds to:
        # python agentless/fl/localize.py --related_level \
        #                                --output_folder results/swe-bench-lite/related_elements \
        #                                --top_n 3 \
        #                                --compress_assign \
        #                                --compress \
        #                                --start_file results/swe-bench-lite/file_level_combined/combined_locs.jsonl \
        #                                --num_threads 1 \
        #                                --skip_existing \
        #				                 --target_id=<actual_target_id>
        localize2_args = [
            agentless_args.localize.related_level,
            agentless_args.localize.output_folder, 'results/swe-bench-lite/related_elements',
            agentless_args.localize.top_n, "3",
            agentless_args.localize.compress_assign,
            agentless_args.localize.compress,
            agentless_args.localize.start_file, 'results/swe-bench-lite/file_level_combined/combined_locs.jsonl',
            agentless_args.localize.num_threads, "1",
            agentless_args.localize.skip_existing,
            agentless_args.localize.target_id, agentless_args.target_id
        ]
        print(f"Running localize (2) with args: {localize2_args}")
        self.localize(localize2_args)

        # localize3: Corresponds to:
        # python agentless/fl/localize.py --fine_grain_line_level \
        #                                --output_folder results/swe-bench-lite/edit_location_samples \
        #                                --top_n 3 \
        #                                --compress \
        #                                --temperature 0.8 \
        #                                --num_samples 1 \
        #                                --start_file results/swe-bench-lite/related_elements/loc_outputs.jsonl \
        #                                --num_threads 1 \
        #                                --skip_existing \
        #				                 --target_id=<actual_target_id>
        localize3_args = [
            agentless_args.localize.fine_grain_line_level,
            agentless_args.localize.output_folder, 'results/swe-bench-lite/edit_location_samples',
            agentless_args.localize.top_n, "3",
            agentless_args.localize.compress,
            agentless_args.localize.temperature, "0.8",
            agentless_args.localize.num_samples, "1",
            agentless_args.localize.start_file, 'results/swe-bench-lite/related_elements/loc_outputs.jsonl',
            agentless_args.localize.num_threads, "1",
            agentless_args.localize.skip_existing,
            agentless_args.localize.target_id, agentless_args.target_id
        ]
        print(f"Running localize (3) with args: {localize3_args}")
        self.localize(localize3_args)

        # localize4: Corresponds to:
        # python agentless/fl/localize.py --merge \
        #                                --output_folder results/swe-bench-lite/edit_location_individual \
        #                                --top_n 3 \
        #                                --num_samples 1 \
        #                                --start_file results/swe-bench-lite/edit_location_samples/loc_outputs.jsonl \
        #				                 --target_id=<actual_target_id>
        localize4_args = [
            agentless_args.localize.merge,
            agentless_args.localize.output_folder, 'results/swe-bench-lite/edit_location_individual',
            agentless_args.localize.top_n, "3",
            agentless_args.localize.num_samples, "1",
            agentless_args.localize.start_file, 'results/swe-bench-lite/edit_location_samples/loc_outputs.jsonl',
            agentless_args.localize.target_id, agentless_args.target_id
        ]
        print(f"Running localize (4) with args: {localize4_args}")
        self.localize(localize4_args)

        # repair_args: Corresponds to (example for i=0):
        # python agentless/repair/repair.py --loc_file results/swe-bench-lite/edit_location_individual/loc_merged_0-0_outputs.jsonl \
        #                                  --output_folder results/swe-bench-lite/repair_sample_1 \
        #                                  --loc_interval \
        #                                  --top_n=3 \
        #                                  --context_window=10 \
        #                                  --max_samples 1  \
        #                                  --cot \
        #                                  --diff_format \
        #                                  --gen_and_process \
        #                                  --num_threads 1 \
        #				                   --target_id=<actual_target_id>

        # Your original code implies a loop here, but currently runs for a single case (i=0)
        # For simplicity, I'm replicating the single case. If a loop is needed, adapt this part.
        loc_file_val = "results/swe-bench-lite/edit_location_individual/loc_merged_0-0_outputs.jsonl"
        output_folder_val = "results/swe-bench-lite/repair_sample_1"

        current_repair_args = [
            agentless_args.repair.loc_file, loc_file_val,
            agentless_args.repair.output_folder, output_folder_val,
            agentless_args.repair.loc_interval,
            agentless_args.repair.top_n, "3",
            agentless_args.repair.context_window, "10",
            agentless_args.repair.max_samples, "1",
            agentless_args.repair.cot,
            agentless_args.repair.diff_format,
            agentless_args.repair.gen_and_process,
            agentless_args.repair.num_threads, "1",
            agentless_args.repair.target_id, agentless_args.target_id
        ]
        print(f"Running repair with args: {current_repair_args}")
        self.repair(current_repair_args)

        print("##########脚本结束############")

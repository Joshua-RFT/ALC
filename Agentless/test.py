import Agentless

Agentless.set_API_KEY(api_key="sk-d0a0f3193ca546a684bec5a662c77f72")
#Agentless.set_PROJECT_FILE_LOC(r"F:\Python\Agentless\SWE-Bench\swebench_repo_structure\repo_structure\repo_structures")
Agentless.set_PROJECT_FILE_LOC(r"F:\Python\Agentless\service")

Agentless.set_OPENAI_API_URL('https://api.deepseek.com/v1')

def Agentless_test_run():
    print("Agentless Test Run")

#agentless_args = Agentless.AgentlessArgs(r"F:\Python\Agentless\SWE-Bench\swebench_repo_structure\repo_structure\repo_structures", "astropy__astropy-12907-deyudada")
agentless_args = Agentless.AgentlessArgs(r"F:\Python\Agentless\service", "astropy__astropy-12907-deyudada")

agentless = Agentless.Agentless(agentless_args=agentless_args)
#agentless.run() #Agentless 测试结束
result = [status, context] = agentless.result()
print(result)
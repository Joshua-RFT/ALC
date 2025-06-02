<script setup lang='ts'>
import { ref, computed } from 'vue'
import { NButton, NInput, NUpload, NCard, NSpace, NAlert, NSpin, useMessage, NInputGroup, NInputGroupLabel, NText, NDivider } from 'naive-ui'
import { SvgIcon } from '@/components/common'
import { useBasicLayout } from '@/hooks/useBasicLayout'

const ms = useMessage()
const { isMobile } = useBasicLayout()

// 表单数据
const codeFile = ref<File | null>(null)
const bugDescription = ref('')
const deepseekApiKey = ref('')
const aliyunEmbeddingKey = ref('')
const targetId = ref('')

// 状态管理
const loading = ref(false)
const result = ref<string>('')
const showResult = ref(false)

// 文件上传处理
const handleFileChange = (data: { file: any, fileList: any[], event?: Event }) => {
  const uploadFile = data.file
  if (uploadFile && uploadFile.file) {
    codeFile.value = uploadFile.file
    // 自动设置target_id为文件名（去掉.zip后缀）
    const fileName = uploadFile.file.name
    if (fileName.endsWith('.zip')) {
      targetId.value = fileName.slice(0, -4)
    } else {
      targetId.value = fileName
    }
  }
  return false // 阻止自动上传
}

// 表单验证
const isFormValid = computed(() => {
  return codeFile.value && 
         bugDescription.value.trim() && 
         deepseekApiKey.value.trim() && 
         aliyunEmbeddingKey.value.trim() && 
         targetId.value.trim()
})

// 提交修复请求
const handleSubmit = async () => {
  if (!isFormValid.value) {
    ms.error('请填写完整信息')
    return
  }

  loading.value = true
  showResult.value = false
  
  try {
    const formData = new FormData()
    
    // 添加文件
    formData.append('code_zip', codeFile.value!)
    
    // 添加API数据
    const apiData = {
      API_KEY: deepseekApiKey.value,
      target_id: targetId.value,
      API_KEY_EMBEDDING: aliyunEmbeddingKey.value
    }
    formData.append('api_data', JSON.stringify(apiData))
    
    // 添加bug描述
    const bugDescriptionData = {
      problem_statement: bugDescription.value
    }
    formData.append('bug_description', JSON.stringify(bugDescriptionData))
    
    // 发送请求
    // 发送请求
    const response = await fetch('http://127.0.0.1:5000/process_bug_fix', {
      method: 'POST',
      body: formData
    })
    
    // 修改：不要在这里就抛出错误，先尝试解析响应
    let responseData
    try {
      responseData = await response.json()
    } catch (error: any) {
      throw new Error(`响应解析失败: ${error.message}`)
    }
    
    // 处理响应数据
    if (response.ok && responseData.status === 'success') {
      // 成功情况
      if (responseData.data && responseData.data.agentless_context && responseData.data.agentless_context.length > 0) {
        result.value = responseData.data.agentless_context[0]
        showResult.value = true
        ms.success('代码修复建议生成成功!')
      } else {
        result.value = '未能生成有效的修复建议，请检查输入信息或重试。'
        showResult.value = true
        ms.warning('生成结果为空，请检查输入信息')
      }
    } else if (responseData.status === 'failed') {
      // 失败情况，但可能有部分结果
      let content = ''
      
      // 处理不同的数据结构
      // 处理不同的数据结构
      if (responseData.data && responseData.data.agentless_context) {
        if (Array.isArray(responseData.data.agentless_context)) {
          // 数组格式
          content = responseData.data.agentless_context[0] || ''
        } else if (responseData.data.agentless_context.message) {
          // 对象格式，提取 message 字段
          try {
            // 尝试解析为JSON
            const messageArray = JSON.parse(responseData.data.agentless_context.message)
            content = Array.isArray(messageArray) ? messageArray[0] : messageArray
          } catch (parseError) {
            console.error('JSON解析失败:', parseError)
            // 如果JSON解析失败，直接使用message字符串
            content = responseData.data.agentless_context.message
          }
        } else {
          // 如果agentless_context是对象但没有message字段，尝试直接使用
          content = JSON.stringify(responseData.data.agentless_context, null, 2)
        }
      }
      
      if (content) {
        result.value = content
        showResult.value = true
        ms.warning(`处理失败，但返回了部分结果: ${responseData.message}`)
      } else {
        result.value = `处理失败: ${responseData.message || '未知错误'}`
        showResult.value = true
        ms.error('代码修复失败')
      }
    } else {
      // 其他错误情况
      throw new Error(`HTTP错误: ${response.status}`)
    }
    
  } catch (error: any) {
    console.error('请求失败:', error)
    ms.error(`请求失败: ${error.message || '未知错误'}`)
    result.value = `错误信息: ${error.message || '请求失败，请检查网络连接和后端服务'}`
    showResult.value = true
  } finally {
    loading.value = false
  }
}

// 重置表单
const handleReset = () => {
  codeFile.value = null
  bugDescription.value = ''
  deepseekApiKey.value = ''
  aliyunEmbeddingKey.value = ''
  targetId.value = ''
  result.value = ''
  showResult.value = false
}

// 复制结果到剪贴板
const copyResult = async () => {
  try {
    await navigator.clipboard.writeText(result.value)
    ms.success('结果已复制到剪贴板')
  } catch (error) {
    ms.error('复制失败')
  }
}
</script>

<template>
  <div class="flex flex-col w-full h-full">
    <main class="flex-1 overflow-hidden">
      <div class="h-full overflow-y-auto">
        <div class="w-full max-w-4xl m-auto p-4">
          <!-- 页面标题 -->
          <div class="text-center mb-6">
            <h1 class="text-2xl font-bold text-gray-800 dark:text-white mb-2">
              <SvgIcon icon="ri:tools-fill" class="inline mr-2 text-blue-500" />
              AI 代码修复工具
            </h1>
            <p class="text-gray-600 dark:text-gray-300">上传代码文件，描述遇到的问题，获取AI修复建议</p>
          </div>

          <!-- 主要内容区域 -->
          <NSpace vertical size="large">
            <!-- 配置表单 -->
            <NCard title="配置信息" class="shadow-sm">
              <NSpace vertical size="medium">
                <!-- API密钥配置 -->
                <NSpace vertical size="small">
                  <NInputGroup>
                    <NInputGroupLabel>DeepSeek API Key</NInputGroupLabel>
                    <NInput 
                      v-model:value="deepseekApiKey" 
                      placeholder="请输入DeepSeek API密钥"
                      type="password"
                      show-password-on="click"
                    />
                  </NInputGroup>
                  
                  <NInputGroup>
                    <NInputGroupLabel>阿里云嵌入API Key</NInputGroupLabel>
                    <NInput 
                      v-model:value="aliyunEmbeddingKey" 
                      placeholder="请输入阿里云嵌入API密钥"
                      type="password"
                      show-password-on="click"
                    />
                  </NInputGroup>
                  
                  <NInputGroup>
                    <NInputGroupLabel>目标ID</NInputGroupLabel>
                    <NInput 
                      v-model:value="targetId" 
                      placeholder="目标ID（通常与文件名相同）"
                    />
                  </NInputGroup>
                </NSpace>
              </NSpace>
            </NCard>

            <!-- 文件上传和问题描述 -->
            <NCard title="问题信息" class="shadow-sm">
              <NSpace vertical size="medium">
                <!-- 文件上传 -->
                <div>
                  <NText class="font-medium mb-2 block">代码文件 (.zip)</NText>
                  <NUpload
                    :max="1"
                    accept=".zip"
                    :on-change="handleFileChange"
                    :show-file-list="true"
                    :default-file-list="[]"
                  >
                    <NButton>
                      <template #icon>
                        <SvgIcon icon="ri:upload-cloud-line" />
                      </template>
                      选择ZIP文件
                    </NButton>
                  </NUpload>
                  <NText depth="3" class="text-sm mt-1 block">
                    请上传包含代码的ZIP压缩文件
                  </NText>
                </div>

                <!-- 问题描述 -->
                <div>
                  <NText class="font-medium mb-2 block">问题描述</NText>
                  <NInput
                    v-model:value="bugDescription"
                    type="textarea"
                    placeholder="请详细描述遇到的问题，例如：我想获得加法结果，意外的乘法返回"
                    :autosize="{ minRows: 3, maxRows: 6 }"
                  />
                </div>
              </NSpace>
            </NCard>

            <!-- 操作按钮 -->
            <NSpace justify="center" size="medium">
              <NButton 
                type="primary" 
                size="large"
                :disabled="!isFormValid || loading"
                :loading="loading"
                @click="handleSubmit"
              >
                <template #icon>
                  <SvgIcon icon="ri:magic-line" />
                </template>
                {{ loading ? '分析修复中...' : '开始修复' }}
              </NButton>
              
              <NButton 
                size="large"
                :disabled="loading"
                @click="handleReset"
              >
                <template #icon>
                  <SvgIcon icon="ri:refresh-line" />
                </template>
                重置
              </NButton>
            </NSpace>

            <!-- 结果显示 -->
            <NCard v-if="showResult" title="修复建议" class="shadow-sm">
              <template #header-extra>
                <NButton size="small" @click="copyResult">
                  <template #icon>
                    <SvgIcon icon="ri:file-copy-line" />
                  </template>
                  复制
                </NButton>
              </template>
              
              <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <pre class="whitespace-pre-wrap text-sm font-mono">{{ result }}</pre>
              </div>
            </NCard>

            <!-- 使用说明 -->
            <NCard title="使用说明" class="shadow-sm">
              <NSpace vertical size="small">
                <NAlert type="info" :show-icon="false">
                  <strong>使用步骤：</strong>
                  <ol class="list-decimal list-inside mt-2 space-y-1">
                    <li>填写DeepSeek和阿里云的API密钥</li>
                    <li>上传包含代码的ZIP文件</li>
                    <li>输入目标ID（通常与文件名相同）</li>
                    <li>详细描述遇到的问题</li>
                    <li>点击"开始修复"获取AI建议</li>
                  </ol>
                </NAlert>
                
                <NAlert type="warning" :show-icon="false">
                  <strong>注意事项：</strong>
                  <ul class="list-disc list-inside mt-2 space-y-1">
                    <li>请确保后端服务已启动（127.0.0.1:5000）</li>
                    <li>上传的ZIP文件应包含完整的代码结构</li>
                    <li>问题描述越详细，修复建议越准确</li>
                    <li>请妥善保管API密钥，避免泄露</li>
                  </ul>
                </NAlert>
              </NSpace>
            </NCard>
          </NSpace>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.n-card {
  margin-bottom: 0;
}

pre {
  max-height: 400px;
  overflow-y: auto;
}
</style>
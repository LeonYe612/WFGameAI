<!--
  脚本详情组件
  @file wfgame-ai-web/src/views/scripts/ScriptDetail.vue
  @author WFGame AI Team
  @date 2024-05-15
-->
<template>
  <div class="script-detail-container" v-loading="loading">
    <!-- 标题栏 -->
    <div class="page-header">
      <div class="title-section">
        <el-button type="text" icon="el-icon-back" @click="goBack">返回</el-button>
        <h2 v-if="script">{{ isEditMode ? '编辑脚本: ' : '' }}{{ script.name }}</h2>
      </div>
      <div class="actions">
        <template v-if="!isEditMode">
          <el-button type="primary" icon="el-icon-video-play" @click="executeScript" :disabled="!script || !script.is_active">
            执行脚本
          </el-button>
          <el-button type="warning" icon="el-icon-edit" @click="editScript" :disabled="!script">
            编辑脚本
          </el-button>
        </template>
        <template v-else>
          <el-button type="primary" icon="el-icon-check" @click="saveScript" :loading="saveLoading">保存</el-button>
          <el-button type="info" icon="el-icon-close" @click="cancelEdit">取消</el-button>
        </template>
      </div>
    </div>

    <!-- 脚本信息 -->
    <el-card class="info-card" v-if="script">
      <div class="info-header">
        <h3>基本信息</h3>
        <el-tag v-if="!isEditMode" :type="getScriptTypeTag(script.type)" size="medium">{{ script.type_display }}</el-tag>
      </div>
      
      <template v-if="!isEditMode">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="脚本ID">{{ script.id }}</el-descriptions-item>
          <el-descriptions-item label="所属分类">{{ script.category_name }}</el-descriptions-item>
          <el-descriptions-item label="创建者">{{ script.author_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-switch
              v-model="script.is_active"
              :active-color="script.is_active ? '#13ce66' : '#ff4949'"
              :inactive-color="script.is_active ? '#13ce66' : '#ff4949'"
              @change="toggleScriptActive"
            ></el-switch>
            {{ script.is_active ? '已启用' : '已禁用' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(script.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="最后更新">{{ formatDate(script.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="执行次数">{{ script.execution_count }}</el-descriptions-item>
          <el-descriptions-item label="执行记录">
            <el-link type="primary" @click="showExecutions">
              查看执行记录 ({{ script.executions_count || 0 }})
            </el-link>
          </el-descriptions-item>
        </el-descriptions>

        <div class="description-section" v-if="script.description">
          <h4>脚本描述</h4>
          <p>{{ script.description }}</p>
        </div>
      </template>
      
      <template v-else>
        <el-form ref="form" :model="editForm" :rules="formRules" label-width="120px">
          <el-form-item label="脚本名称" prop="name">
            <el-input v-model="editForm.name" placeholder="请输入脚本名称"></el-input>
          </el-form-item>
          <el-form-item label="脚本类型" prop="type">
            <el-select v-model="editForm.type" placeholder="请选择脚本类型" style="width:100%">
              <el-option label="手动" value="manual"></el-option>
              <el-option label="录制" value="record" disabled></el-option>
              <el-option label="自动生成" value="generated"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="所属分类" prop="category">
            <el-select v-model="editForm.category" placeholder="请选择脚本分类" style="width:100%">
              <el-option
                v-for="category in categories"
                :key="category.id"
                :label="category.name"
                :value="category.id"
              ></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="脚本描述" prop="description">
            <el-input
              type="textarea"
              v-model="editForm.description"
              placeholder="请输入脚本描述"
              :rows="3"
            ></el-input>
          </el-form-item>
          <el-form-item label="是否启用" prop="is_active">
            <el-switch v-model="editForm.is_active"></el-switch>
          </el-form-item>
        </el-form>
      </template>
    </el-card>

    <!-- 脚本内容 -->
    <el-card class="content-card" v-if="script">
      <div slot="header">
        <span>脚本内容</span>
        <template v-if="!isEditMode">
          <el-button 
            style="float: right; padding: 3px 0" 
            type="text"
            @click="formatContent"
          >格式化</el-button>
        </template>
      </div>
      
      <pre v-if="!isEditMode" class="script-content">{{ formattedContent }}</pre>
      
      <el-form-item v-else label="脚本内容" prop="content">
        <el-input
          type="textarea"
          v-model="editForm.content"
          placeholder="请输入脚本内容（JSON格式）"
          :rows="15"
          class="script-editor"
        ></el-input>
        <div class="editor-actions">
          <el-button type="text" @click="formatEditorContent">格式化JSON</el-button>
          <el-button type="text" @click="validateJson">验证JSON</el-button>
        </div>
      </el-form-item>
    </el-card>

    <!-- 执行记录 -->
    <el-dialog
      title="执行记录"
      :visible.sync="executionsVisible"
      width="80%"
    >
      <el-table
        v-loading="executionsLoading"
        :data="executions"
        border
        style="width: 100%"
        :header-cell-style="{ backgroundColor: '#f5f7fa' }"
      >
        <el-table-column prop="id" label="ID" width="80"></el-table-column>
        <el-table-column prop="status_display" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="executed_by_name" label="执行人" width="120"></el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.end_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="execution_time" label="执行时长" width="100">
          <template #default="{ row }">
            {{ row.execution_time ? `${row.execution_time.toFixed(2)}秒` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="result" label="执行结果">
          <template #default="{ row }">
            <el-tooltip v-if="row.result" effect="dark" placement="top">
              <div slot="content" v-html="formatResult(row.result)"></div>
              <el-button type="text">查看结果</el-button>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button
              size="mini"
              type="primary"
              icon="el-icon-view"
              @click="viewExecutionDetail(row)"
            >详情</el-button>
            <el-button
              size="mini"
              type="success"
              icon="el-icon-refresh"
              @click="retryExecution(row)"
              :disabled="row.status !== 'failed'"
            >重试</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-container">
        <el-pagination
          background
          layout="prev, pager, next, sizes, total"
          :page-sizes="[10, 20, 50, 100]"
          :current-page="executionsPagination.currentPage"
          :page-size="executionsPagination.pageSize"
          :total="executionsPagination.total"
          @current-change="handleExecutionsPageChange"
          @size-change="handleExecutionsPageSizeChange"
        ></el-pagination>
      </div>
    </el-dialog>

    <!-- 执行脚本对话框 -->
    <el-dialog
      title="执行脚本"
      :visible.sync="executeDialogVisible"
      width="50%"
    >
      <el-form
        ref="executeForm"
        :model="executeForm"
        :rules="executeFormRules"
        label-width="120px"
      >
        <el-form-item label="目标设备" prop="device">
          <el-select v-model="executeForm.device" placeholder="请选择执行设备" style="width:100%">
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            ></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="执行参数" prop="params">
          <el-input
            type="textarea"
            v-model="executeForm.params"
            placeholder="可选参数，JSON格式"
            :rows="3"
          ></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="executeDialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="confirmExecute" :loading="executeLoading">执 行</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import {
  getScriptDetail,
  executeScript,
  toggleScriptActive,
  getScriptExecutions,
  updateScript,
  getScriptCategories
} from '@/api/scripts';
import { getDevices } from '@/api/devices';
import { formatDate } from '@/utils/format';

export default {
  name: 'ScriptDetail',
  
  data() {
    return {
      script: null,
      loading: false,
      
      // 编辑相关
      isEditMode: false,
      saveLoading: false,
      editForm: {
        id: null,
        name: '',
        type: '',
        category: '',
        description: '',
        content: '',
        is_active: true
      },
      categories: [],
      formRules: {
        name: [
          { required: true, message: '请输入脚本名称', trigger: 'blur' },
          { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
        ],
        type: [
          { required: true, message: '请选择脚本类型', trigger: 'change' }
        ],
        category: [
          { required: true, message: '请选择所属分类', trigger: 'change' }
        ],
        content: [
          { required: true, message: '请输入脚本内容', trigger: 'blur' }
        ]
      },
      
      // 格式化内容
      formattedContent: '',
      
      // 执行记录
      executions: [],
      executionsVisible: false,
      executionsLoading: false,
      executionsPagination: {
        currentPage: 1,
        pageSize: 10,
        total: 0
      },
      
      // 执行脚本
      executeDialogVisible: false,
      executeLoading: false,
      executeForm: {
        device: '',
        params: ''
      },
      executeFormRules: {
        device: [
          { required: true, message: '请选择执行设备', trigger: 'change' }
        ]
      },
      
      // 设备列表
      devices: []
    };
  },
  
  created() {
    // 检查是否为编辑模式
    this.isEditMode = this.$route.meta.isEdit === true;
    this.fetchScriptDetail();
    this.fetchDevices();
    this.fetchCategories();
  },
  
  methods: {
    // 格式化日期
    formatDate,
    
    // 获取脚本类型对应的标签样式
    getScriptTypeTag(type) {
      const typeMap = {
        record: 'danger',
        manual: 'success',
        generated: 'primary'
      };
      return typeMap[type] || 'info';
    },
    
    // 获取执行状态对应的标签样式
    getStatusTag(status) {
      const statusMap = {
        pending: 'info',
        running: 'warning',
        completed: 'success',
        failed: 'danger',
        cancelled: 'info'
      };
      return statusMap[status] || 'info';
    },
    
    // 返回上一页
    goBack() {
      if (this.isEditMode) {
        // 如果在编辑模式，返回到详情页
        this.$router.push({ name: 'ScriptDetail', params: { id: this.$route.params.id } });
      } else {
        // 否则返回列表
        this.$router.push({ name: 'ScriptsList' });
      }
    },
    
    // 格式化结果
    formatResult(result) {
      if (!result) return '';
      
      try {
        // 尝试解析JSON
        const resultObj = typeof result === 'object' ? result : JSON.parse(result);
        return JSON.stringify(resultObj, null, 2)
          .replace(/\\n/g, '<br>')
          .replace(/\n/g, '<br>')
          .replace(/ /g, '&nbsp;');
      } catch (e) {
        // 如果不是JSON，则直接返回
        return String(result).replace(/\n/g, '<br>');
      }
    },
    
    // 获取分类列表
    async fetchCategories() {
      try {
        const response = await getScriptCategories();
        this.categories = response.data.results || response.data;
      } catch (error) {
        this.$message.error('获取分类列表失败');
        console.error('获取分类列表失败:', error);
      }
    },
    
    // 获取脚本详情
    async fetchScriptDetail() {
      this.loading = true;
      
      try {
        const response = await getScriptDetail(this.$route.params.id);
        this.script = response.data;
        
        // 如果是编辑模式，初始化表单
        if (this.isEditMode) {
          this.initEditForm();
        } else {
          // 格式化脚本内容
          this.formatContent();
        }
      } catch (error) {
        this.$message.error('获取脚本详情失败');
        console.error('获取脚本详情失败:', error);
      } finally {
        this.loading = false;
      }
    },
    
    // 初始化编辑表单
    initEditForm() {
      if (!this.script) return;
      
      // 处理脚本内容，确保是格式化的JSON字符串
      let content = this.script.content;
      if (typeof content === 'object') {
        content = JSON.stringify(content, null, 2);
      } else if (typeof content === 'string') {
        try {
          content = JSON.stringify(JSON.parse(content), null, 2);
        } catch (e) {
          console.warn('JSON解析失败:', e);
        }
      }
      
      // 初始化表单数据
      this.editForm = {
        id: this.script.id,
        name: this.script.name,
        type: this.script.type,
        category: this.script.category,
        description: this.script.description,
        content: content,
        is_active: this.script.is_active
      };
    },
    
    // 获取设备列表
    async fetchDevices() {
      try {
        const response = await getDevices({ status: 'online' });
        this.devices = response.data.results || response.data;
      } catch (error) {
        this.$message.error('获取设备列表失败');
        console.error('获取设备列表失败:', error);
      }
    },
    
    // 编辑脚本
    editScript() {
      this.$router.push({ name: 'ScriptEdit', params: { id: this.script.id } });
    },
    
    // 取消编辑
    cancelEdit() {
      if (this.hasChanges()) {
        this.$confirm('您有未保存的更改，确定要取消吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }).then(() => {
          this.goBack();
        }).catch(() => {});
      } else {
        this.goBack();
      }
    },
    
    // 检查是否有未保存的更改
    hasChanges() {
      if (!this.script) return false;
      
      return (
        this.editForm.name !== this.script.name ||
        this.editForm.type !== this.script.type ||
        this.editForm.category !== this.script.category ||
        this.editForm.description !== this.script.description ||
        this.editForm.is_active !== this.script.is_active ||
        this.editForm.content !== JSON.stringify(this.script.content, null, 2)
      );
    },
    
    // 保存编辑
    saveScript() {
      this.$refs.form.validate(async (valid) => {
        if (!valid) return;
        
        this.saveLoading = true;
        
        try {
          // 验证JSON格式
          let contentObject;
          try {
            contentObject = JSON.parse(this.editForm.content);
          } catch (e) {
            this.$message.error('脚本内容不是有效的JSON格式');
            this.saveLoading = false;
            return;
          }
          
          // 构建更新数据
          const updateData = {
            id: this.editForm.id,
            name: this.editForm.name,
            type: this.editForm.type,
            category: this.editForm.category,
            description: this.editForm.description,
            content: contentObject,
            is_active: this.editForm.is_active
          };
          
          // 提交更新
          await updateScript(this.editForm.id, updateData);
          
          this.$message.success('脚本更新成功');
          
          // 返回详情页
          this.$router.push({ name: 'ScriptDetail', params: { id: this.script.id } });
        } catch (error) {
          const message = error.response?.data?.message || '更新失败';
          this.$message.error(message);
          console.error('更新脚本失败:', error);
        } finally {
          this.saveLoading = false;
        }
      });
    },
    
    // 格式化JSON编辑器内容
    formatEditorContent() {
      try {
        const json = JSON.parse(this.editForm.content);
        this.editForm.content = JSON.stringify(json, null, 2);
        this.$message.success('JSON已格式化');
      } catch (e) {
        this.$message.error('无效的JSON格式: ' + e.message);
      }
    },
    
    // 验证JSON
    validateJson() {
      try {
        JSON.parse(this.editForm.content);
        this.$message.success('JSON格式有效');
      } catch (e) {
        this.$message.error('无效的JSON格式: ' + e.message);
      }
    },
    
    // 格式化脚本内容
    formatContent() {
      if (!this.script || !this.script.content) {
        this.formattedContent = '';
        return;
      }
      
      try {
        // 如果是JSON对象，转为格式化的JSON字符串
        if (typeof this.script.content === 'object') {
          this.formattedContent = JSON.stringify(this.script.content, null, 2);
        } else if (typeof this.script.content === 'string') {
          // 尝试解析JSON字符串并格式化
          const content = JSON.parse(this.script.content);
          this.formattedContent = JSON.stringify(content, null, 2);
        } else {
          // 其他情况，直接显示
          this.formattedContent = String(this.script.content);
        }
      } catch (e) {
        // 如果解析失败，直接显示原内容
        this.formattedContent = String(this.script.content);
        console.warn('脚本内容格式化失败:', e);
      }
    },
    
    // 切换脚本启用状态
    async toggleScriptActive() {
      try {
        await toggleScriptActive(this.script.id);
        this.$message.success(`脚本已${this.script.is_active ? '启用' : '禁用'}`);
      } catch (error) {
        // 恢复状态
        this.script.is_active = !this.script.is_active;
        this.$message.error('切换脚本状态失败');
        console.error('切换脚本状态失败:', error);
      }
    },
    
    // 显示执行记录
    async showExecutions() {
      this.executionsVisible = true;
      this.fetchExecutions();
    },
    
    // 获取执行记录
    async fetchExecutions() {
      if (!this.script) return;
      
      this.executionsLoading = true;
      
      try {
        const response = await getScriptExecutions(this.script.id, {
          page: this.executionsPagination.currentPage,
          page_size: this.executionsPagination.pageSize
        });
        
        this.executions = response.data.results || response.data;
        if (response.data.count !== undefined) {
          this.executionsPagination.total = response.data.count;
        }
      } catch (error) {
        this.$message.error('获取执行记录失败');
        console.error('获取执行记录失败:', error);
      } finally {
        this.executionsLoading = false;
      }
    },
    
    // 执行记录分页变化
    handleExecutionsPageChange(currentPage) {
      this.executionsPagination.currentPage = currentPage;
      this.fetchExecutions();
    },
    
    // 执行记录每页数量变化
    handleExecutionsPageSizeChange(pageSize) {
      this.executionsPagination.pageSize = pageSize;
      this.executionsPagination.currentPage = 1;
      this.fetchExecutions();
    },
    
    // 查看执行详情
    viewExecutionDetail(execution) {
      this.$router.push({
        name: 'ExecutionDetail',
        params: { id: execution.id }
      });
    },
    
    // 重试执行
    async retryExecution(execution) {
      this.$confirm('确认要重新执行此脚本?', '重试确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.executeDialogVisible = true;
      }).catch(() => {});
    },
    
    // 执行脚本
    executeScript() {
      this.executeForm = {
        device: '',
        params: ''
      };
      this.executeDialogVisible = true;
    },
    
    // 确认执行脚本
    confirmExecute() {
      this.$refs.executeForm.validate(async (valid) => {
        if (!valid) return;
        
        this.executeLoading = true;
        
        try {
          // 执行脚本
          const response = await executeScript(this.script.id);
          this.$message.success('脚本执行已开始');
          this.executeDialogVisible = false;
          
          // 刷新脚本详情
          this.fetchScriptDetail();
          
          // 跳转到执行详情页面
          if (response.data && response.data.id) {
            this.$router.push({
              name: 'ExecutionDetail',
              params: { id: response.data.id }
            });
          }
        } catch (error) {
          this.$message.error('执行脚本失败');
          console.error('执行脚本失败:', error);
        } finally {
          this.executeLoading = false;
        }
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.script-detail-container {
  padding: 20px;
  
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .title-section {
      display: flex;
      align-items: center;
      
      h2 {
        margin: 0;
        margin-left: 10px;
        font-size: 24px;
      }
    }
    
    .actions {
      display: flex;
      gap: 10px;
    }
  }
  
  .info-card {
    margin-bottom: 20px;
    
    .info-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      
      h3 {
        margin: 0;
      }
    }
    
    .description-section {
      margin-top: 20px;
      
      h4 {
        margin-bottom: 10px;
        color: #606266;
      }
      
      p {
        white-space: pre-line;
        color: #606266;
      }
    }
  }
  
  .content-card {
    .script-content {
      background-color: #f5f7fa;
      border-radius: 4px;
      padding: 15px;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: monospace;
      font-size: 14px;
      overflow: auto;
      max-height: 400px;
    }
    
    .script-editor {
      font-family: monospace;
      
      :deep(.el-textarea__inner) {
        font-family: monospace;
        line-height: 1.5;
        padding: 15px;
      }
    }
    
    .editor-actions {
      display: flex;
      justify-content: flex-end;
      margin-top: 8px;
      gap: 10px;
    }
  }
  
  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style> 
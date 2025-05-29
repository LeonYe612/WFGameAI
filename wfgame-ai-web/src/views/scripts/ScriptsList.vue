<!--
  脚本列表组件
  @file wfgame-ai-web/src/views/scripts/ScriptsList.vue
  @author WFGame AI Team
  @date 2024-05-15
-->
<template>  <div class="scripts-list-container">
    <!-- 演示提示横幅 -->
    <el-alert
      title="🎯 演示模式：加入日志过滤功能"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 20px;"
    >
      <template slot>
        当前为<strong>静态演示版本</strong>，数据已写死包含 start_app1.json（加入日志）和 stop_app1.json（不加入日志）。
        使用上方的"加入日志"过滤器可以立即看到过滤效果！
      </template>
    </el-alert>

    <!-- 标题栏 -->
    <div class="page-header">
      <h2>脚本管理</h2>
      <div class="actions">
        <el-button type="danger" @click="openRecordDialog">
          <i class="el-icon-video-camera"></i> 开始录制
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <i class="el-icon-plus"></i> 新建脚本
        </el-button>
      </div>
    </div>

    <!-- 搜索和过滤 -->
    <div class="filter-container">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-input
            v-model="query.name"
            placeholder="搜索脚本"
            prefix-icon="el-icon-search"
            clearable
            @clear="fetchScripts"
            @keyup.enter.native="fetchScripts"
          ></el-input>
        </el-col>
        <el-col :span="6">
          <el-select
            v-model="query.type"
            placeholder="脚本类型"
            clearable
            @change="fetchScripts"
          >
            <el-option label="录制" value="record"></el-option>
            <el-option label="手动" value="manual"></el-option>
            <el-option label="自动生成" value="generated"></el-option>
          </el-select>
        </el-col>        <el-col :span="6">
          <el-select
            v-model="query.category"
            placeholder="脚本分类"
            clearable
            @change="fetchScripts"
          >
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
            ></el-option>
          </el-select>
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 10px;">
        <el-col :span="6">
          <el-select
            v-model="query.include_in_log"
            placeholder="加入日志"
            clearable
            @change="fetchScripts"
          >
            <el-option label="加入日志" :value="true"></el-option>
            <el-option label="不加入日志" :value="false"></el-option>
          </el-select>
        </el-col>
      </el-row>
    </div>

    <!-- 多选设备区块 -->
    <div class="device-multiselect-bar" style="margin-bottom: 10px;">
      <el-select v-model="selectedDevices" multiple placeholder="批量选择设备" style="width: 400px;">
        <el-option
          v-for="device in devices"
          :key="device.id"
          :label="device.name"
          :value="device.id"
        ></el-option>
      </el-select>
      <el-button type="primary" :disabled="selectedDevices.length === 0" style="margin-left: 10px;" @click="batchExecuteScript">
        批量执行选中脚本
      </el-button>
    </div>

    <!-- 脚本列表 -->
    <el-table
      v-loading="loading"
      :data="scripts"
      border
      style="width: 100%"
      :header-cell-style="{ backgroundColor: '#f5f7fa' }"
    >
      <el-table-column prop="name" label="名称" min-width="180">
        <template #default="{ row }">
          <el-link type="primary" @click="viewScriptDetail(row)">{{ row.name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="type_display" label="类型" width="120">
        <template #default="{ row }">
          <el-tag
            :type="getScriptTypeTag(row.type)"
            size="small"
          >{{ row.type_display }}</el-tag>
        </template>
      </el-table-column>      <el-table-column prop="category_name" label="分类" width="150"></el-table-column>
      <el-table-column label="加入日志" width="120">
        <template #default="{ row }">
          <el-tag
            :type="row.include_in_log ? 'success' : 'info'"
            size="small"
          >{{ row.include_in_log ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建日期" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="最后修改" width="180">
        <template #default="{ row }">
          {{ formatDate(row.updated_at) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_active"
            :active-color="row.is_active ? '#13ce66' : '#ff4949'"
            :inactive-color="row.is_active ? '#13ce66' : '#ff4949'"
            @change="toggleScriptActive(row)"
          ></el-switch>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250">
        <template #default="{ row }">
          <el-button
            size="mini"
            type="primary"
            icon="el-icon-video-play"
            @click="executeScript(row)"
            :disabled="!row.is_active"
          >执行</el-button>
          <el-button
            size="mini"
            type="info"
            icon="el-icon-edit"
            @click="editScript(row)"
          >编辑</el-button>
          <el-button
            size="mini"
            type="danger"
            icon="el-icon-delete"
            @click="deleteScriptConfirm(row)"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        background
        layout="prev, pager, next, sizes, total"
        :page-sizes="[10, 20, 50, 100]"
        :current-page="pagination.currentPage"
        :page-size="pagination.pageSize"
        :total="pagination.total"
        @current-change="handleCurrentChange"
        @size-change="handleSizeChange"
      ></el-pagination>
    </div>

    <!-- 创建/编辑脚本对话框 -->
    <el-dialog
      :title="dialogTitle"
      :visible.sync="dialogVisible"
      width="60%"
      :before-close="handleDialogClose"
    >
      <el-form
        ref="scriptForm"
        :model="scriptForm"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="脚本名称" prop="name">
          <el-input v-model="scriptForm.name" placeholder="请输入脚本名称"></el-input>
        </el-form-item>
        <el-form-item label="脚本类型" prop="type">
          <el-select v-model="scriptForm.type" placeholder="请选择脚本类型" style="width:100%">
            <el-option label="手动" value="manual"></el-option>
            <el-option label="自动生成" value="generated"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="所属分类" prop="category">
          <el-select v-model="scriptForm.category" placeholder="请选择脚本分类" style="width:100%">
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
            v-model="scriptForm.description"
            placeholder="请输入脚本描述"
            :rows="3"
          ></el-input>
        </el-form-item>
        <el-form-item label="脚本内容" prop="content">
          <el-input
            type="textarea"
            v-model="scriptForm.content"
            placeholder="请输入脚本内容（JSON格式）"
            :rows="10"
          ></el-input>
        </el-form-item>
        <el-form-item label="是否启用" prop="is_active">
          <el-switch v-model="scriptForm.is_active"></el-switch>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="saveScript" :loading="saveLoading">保 存</el-button>
      </span>
    </el-dialog>

    <!-- 录制脚本对话框 -->
    <el-dialog
      title="录制脚本"
      :visible.sync="recordDialogVisible"
      width="50%"
    >
      <el-form
        ref="recordForm"
        :model="recordForm"
        :rules="recordFormRules"
        label-width="120px"
      >
        <el-form-item label="脚本名称" prop="name">
          <el-input v-model="recordForm.name" placeholder="请输入脚本名称"></el-input>
        </el-form-item>
        <el-form-item label="所属分类" prop="category">
          <el-select v-model="recordForm.category" placeholder="请选择脚本分类" style="width:100%">
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
            ></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="目标设备" prop="device">
          <el-select v-model="recordForm.device" placeholder="请选择录制设备" style="width:100%">
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            ></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="录制说明" prop="description">
          <el-input
            type="textarea"
            v-model="recordForm.description"
            placeholder="请输入录制说明"
            :rows="3"
          ></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="recordDialogVisible = false">取 消</el-button>
        <el-button type="danger" @click="startRecording" :loading="recordingLoading">开始录制</el-button>
      </span>
    </el-dialog>

    <!-- 执行脚本对话框 -->
    <el-dialog
      :title="`执行脚本: ${currentScript.name || ''}`"
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
          <!-- 多选设备 -->
          <el-select v-model="executeForm.device" multiple placeholder="请选择执行设备" style="width:100%">
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
        <el-button type="primary" @click="confirmExecute" :loading="executeLoading">批量执 行</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import {
    createScript,
    deleteScript,
    executeScript,
    getScriptDetail,
    toggleScriptActive,
    updateScript
} from '@/api/scripts';
import { formatDate } from '@/utils/format';

export default {
  name: 'ScriptsList',

  data() {
    return {      // 查询参数
      query: {
        name: '',
        type: '',
        category: '',
        include_in_log: ''
      },

      // 数据列表
      scripts: [],
      categories: [],
      devices: [],

      // 加载状态
      loading: false,
      saveLoading: false,
      recordingLoading: false,
      executeLoading: false,

      // 分页配置
      pagination: {
        currentPage: 1,
        pageSize: 10,
        total: 0
      },

      // 创建/编辑对话框
      dialogVisible: false,
      dialogTitle: '创建脚本',
      dialogMode: 'create', // create 或 edit
      scriptForm: {
        name: '',
        type: 'manual',
        category: '',
        description: '',
        content: '',
        is_active: true
      },

      // 表单验证规则
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

      // 录制对话框
      recordDialogVisible: false,
      recordForm: {
        name: '',
        category: '',
        device: '',
        description: ''
      },
      recordFormRules: {
        name: [
          { required: true, message: '请输入脚本名称', trigger: 'blur' }
        ],
        category: [
          { required: true, message: '请选择所属分类', trigger: 'change' }
        ],
        device: [
          { required: true, message: '请选择录制设备', trigger: 'change' }
        ]
      },

      // 执行脚本
      executeDialogVisible: false,
      currentScript: {},
      executeForm: {
        device: '',
        params: ''
      },
      executeFormRules: {
        device: [
          { required: true, message: '请选择执行设备', trigger: 'change' }
        ]
      },
      // 多选设备
      selectedDevices: []
    };
  },

  created() {
    this.fetchScripts();
    this.fetchCategories();
    this.fetchDevices();
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
    },    // 获取脚本列表 - 静态数据演示版本
    async fetchScripts() {
      this.loading = true;

      // 模拟API延迟
      setTimeout(() => {
        // 【演示模式：静态数据】
        const allScripts = [
          {
            id: 1,
            name: 'start_app1.json',
            type: 'manual',
            type_display: '手动',
            category_name: '应用启动',
            description: '启动应用程序的脚本',
            content: '{"steps": [{"action": "start_app", "package": "com.example.app"}]}',
            is_active: true,
            include_in_log: true,  // 加入日志
            created_at: '2024-05-20T10:30:00Z',
            updated_at: '2024-05-25T14:20:00Z'
          },
          {
            id: 2,
            name: 'stop_app1.json',
            type: 'manual',
            type_display: '手动',
            category_name: '应用管理',
            description: '停止应用程序的脚本',
            content: '{"steps": [{"action": "stop_app", "package": "com.example.app"}]}',
            is_active: true,
            include_in_log: false,  // 不加入日志
            created_at: '2024-05-20T11:15:00Z',
            updated_at: '2024-05-25T15:30:00Z'
          },
          {
            id: 3,
            name: 'test_login.json',
            type: 'record',
            type_display: '录制',
            category_name: '用户操作',
            description: '用户登录测试脚本',
            content: '{"steps": [{"action": "click", "element": "login_button"}]}',
            is_active: true,
            include_in_log: true,  // 加入日志
            created_at: '2024-05-21T09:00:00Z',
            updated_at: '2024-05-26T10:45:00Z'
          },
          {
            id: 4,
            name: 'cleanup_cache.json',
            type: 'generated',
            type_display: '自动生成',
            category_name: '系统维护',
            description: '清理缓存的维护脚本',
            content: '{"steps": [{"action": "clear_cache"}]}',
            is_active: false,
            include_in_log: false,  // 不加入日志
            created_at: '2024-05-22T16:20:00Z',
            updated_at: '2024-05-27T08:10:00Z'
          }
        ];

        // 应用过滤条件
        let filteredScripts = allScripts;

        // 名称搜索过滤
        if (this.query.name) {
          filteredScripts = filteredScripts.filter(script =>
            script.name.toLowerCase().includes(this.query.name.toLowerCase())
          );
        }

        // 类型过滤
        if (this.query.type) {
          filteredScripts = filteredScripts.filter(script =>
            script.type === this.query.type
          );
        }

        // 分类过滤
        if (this.query.category) {
          filteredScripts = filteredScripts.filter(script =>
            script.category_name === this.query.category
          );
        }

        // 【核心功能】加入日志过滤
        if (this.query.include_in_log !== '' && this.query.include_in_log !== null) {
          filteredScripts = filteredScripts.filter(script =>
            script.include_in_log === this.query.include_in_log
          );
        }

        this.scripts = filteredScripts;
        this.pagination.total = filteredScripts.length;
        this.loading = false;

        console.log('过滤条件:', this.query);
        console.log('过滤后的脚本:', filteredScripts);
      }, 300);
    },    // 获取分类列表 - 静态数据演示版本
    async fetchCategories() {
      // 【演示模式：静态数据】
      this.categories = [
        { id: '应用启动', name: '应用启动' },
        { id: '应用管理', name: '应用管理' },
        { id: '用户操作', name: '用户操作' },
        { id: '系统维护', name: '系统维护' }
      ];
    },

    // 获取设备列表 - 静态数据演示版本
    async fetchDevices() {
      // 静态演示数据
      this.devices = [
        { id: 1, name: '测试设备-Android-01' },
        { id: 2, name: '测试设备-Android-02' },
        { id: 3, name: '测试设备-iOS-01' }
      ];
    },

    // 分页变化
    handleCurrentChange(currentPage) {
      this.pagination.currentPage = currentPage;
      this.fetchScripts();
    },

    // 每页数量变化
    handleSizeChange(pageSize) {
      this.pagination.pageSize = pageSize;
      this.fetchScripts();
    },

    // 打开创建脚本对话框
    openCreateDialog() {
      this.dialogMode = 'create';
      this.dialogTitle = '创建脚本';
      this.scriptForm = {
        name: '',
        type: 'manual',
        category: '',
        description: '',
        content: '{\n  "steps": []\n}',
        is_active: true
      };
      this.dialogVisible = true;
    },

    // 打开编辑脚本对话框
    async editScript(script) {
      this.dialogMode = 'edit';
      this.dialogTitle = `编辑脚本: ${script.name}`;

      try {
        // 获取脚本详情
        const response = await getScriptDetail(script.id);
        const scriptData = response.data;

        this.scriptForm = {
          id: scriptData.id,
          name: scriptData.name,
          type: scriptData.type,
          category: scriptData.category,
          description: scriptData.description,
          content: typeof scriptData.content === 'object'
            ? JSON.stringify(scriptData.content, null, 2)
            : scriptData.content,
          is_active: scriptData.is_active
        };

        this.dialogVisible = true;
      } catch (error) {
        this.$message.error('获取脚本详情失败');
        console.error('获取脚本详情失败:', error);
      }
    },

    // 保存脚本
    saveScript() {
      this.$refs.scriptForm.validate(async (valid) => {
        if (!valid) return;

        this.saveLoading = true;

        try {
          // 处理脚本内容，确保是JSON字符串
          let formData = { ...this.scriptForm };

          if (typeof formData.content === 'string') {
            try {
              // 尝试解析JSON字符串，确保格式正确
              JSON.parse(formData.content);
            } catch (e) {
              this.$message.error('脚本内容格式错误，请确保是有效的JSON格式');
              this.saveLoading = false;
              return;
            }
          }

          let response;
          if (this.dialogMode === 'create') {
            response = await createScript(formData);
            this.$message.success('创建脚本成功');
          } else {
            response = await updateScript(formData.id, formData);
            this.$message.success('更新脚本成功');
          }

          this.dialogVisible = false;
          this.fetchScripts();
        } catch (error) {
          const message = error.response?.data?.message || '操作失败';
          this.$message.error(message);
          console.error('保存脚本失败:', error);
        } finally {
          this.saveLoading = false;
        }
      });
    },

    // 确认删除脚本
    deleteScriptConfirm(script) {
      this.$confirm(`确认删除脚本 "${script.name}"?`, '删除确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.deleteScript(script.id);
      }).catch(() => {});
    },

    // 删除脚本
    async deleteScript(id) {
      try {
        await deleteScript(id);
        this.$message.success('删除脚本成功');
        this.fetchScripts();
      } catch (error) {
        this.$message.error('删除脚本失败');
        console.error('删除脚本失败:', error);
      }
    },

    // 查看脚本详情
    viewScriptDetail(script) {
      this.$router.push({ name: 'ScriptDetail', params: { id: script.id } });
    },

    // 切换脚本启用状态
    async toggleScriptActive(script) {
      try {
        await toggleScriptActive(script.id);
        this.$message.success(`脚本已${script.is_active ? '启用' : '禁用'}`);
      } catch (error) {
        // 恢复状态
        script.is_active = !script.is_active;
        this.$message.error('切换脚本状态失败');
        console.error('切换脚本状态失败:', error);
      }
    },

    // 打开录制对话框
    openRecordDialog() {
      this.recordForm = {
        name: `录制脚本_${new Date().toISOString().slice(0, 10)}`,
        category: '',
        device: '',
        description: ''
      };
      this.recordDialogVisible = true;
    },

    // 开始录制
    startRecording() {
      this.$refs.recordForm.validate(async (valid) => {
        if (!valid) return;

        this.recordingLoading = true;

        try {
          // 这里应该调用录制脚本的API
          // 目前模拟执行
          setTimeout(() => {
            this.$message.success('录制已开始');
            this.recordDialogVisible = false;
            this.recordingLoading = false;
          }, 1000);
        } catch (error) {
          this.$message.error('开始录制失败');
          console.error('开始录制失败:', error);
          this.recordingLoading = false;
        }
      });
    },

    // 执行脚本
    executeScript(script) {
      this.currentScript = script;
      this.executeForm = {
        device: this.selectedDevices.length > 0 ? [...this.selectedDevices] : [], // 支持批量
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
          // 支持批量设备ID
          const deviceIds = Array.isArray(this.executeForm.device) ? this.executeForm.device : [this.executeForm.device];
          // TODO: 需后端支持批量执行API，参数为脚本ID和设备ID数组
          const response = await executeScript(this.currentScript.id, { devices: deviceIds, params: this.executeForm.params });
          this.$message.success('脚本批量执行已开始');
          this.executeDialogVisible = false;
          // 跳转到执行详情页面（如有返回）
          if (response.data && response.data.id) {
            this.$router.push({
              name: 'ExecutionDetail',
              params: { id: response.data.id }
            });
          }
        } catch (error) {
          this.$message.error('批量执行脚本失败');
          console.error('批量执行脚本失败:', error);
        } finally {
          this.executeLoading = false;
        }
      });
    },

    // 关闭对话框
    handleDialogClose() {
      this.dialogVisible = false;
    },

    // 批量执行脚本（弹出批量执行对话框）
    batchExecuteScript() {
      if (this.selectedDevices.length === 0) {
        this.$message.warning('请先选择设备');
        return;
      }
      // 默认选择第一个脚本，实际可扩展为多脚本批量
      if (this.scripts.length === 0) {
        this.$message.warning('暂无可执行脚本');
        return;
      }
      this.currentScript = this.scripts[0];
      this.executeForm = {
        device: [...this.selectedDevices],
        params: ''
      };
      this.executeDialogVisible = true;
    }
  }
};
</script>

<style lang="scss" scoped>
.scripts-list-container {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      margin: 0;
      font-size: 24px;
    }

    .actions {
      display: flex;
      gap: 10px;
    }
  }

  .filter-container {
    margin-bottom: 20px;
  }

  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
const { defineComponent } = Vue;

export default defineComponent({
  name: "Caption",
  props: {
    icon: {
      type: String,
      default: "fas fa-mobile-alt",
    },
    title: {
      type: String,
      default: "页面标题",
    },
    desc: {
      type: String,
      default: "请填写页面功能描述",
    },
  },
  template: `
    <div class="row mb-4">
      <div class="col-12 d-flex justify-content-between align-items-center">
        <div>
          <h2><i :class="icon"></i> {{ title }}</h2>
          <p class="text-muted">{{ desc }}</p>
        </div>
        <div>
          <slot></slot>
        </div>
      </div>
      <div class="col-12">
        <hr>
      </div>
    </div>
  `,
});

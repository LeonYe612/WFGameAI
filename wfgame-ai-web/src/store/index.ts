import type { App } from "vue";
import { createPinia } from "pinia";
import { Router } from "vue-router";
const store = createPinia();

export function setupStore(app: App<Element>, router?: Router) {
  app.use(store);
  store.use(item => {
    item.store.$router = router;
  });
  console.log("已将路由对象 Router 挂载到 Store.$router!");
}

export { store };

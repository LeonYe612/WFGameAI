import { defineComponent, Fragment } from "vue";
import { hasAuth } from "@/router/utils";
const { VITE_ENABLED_AUTH_COMPONENT } = import.meta.env;

export default defineComponent({
  name: "Auth",
  props: {
    value: {
      type: undefined,
      default: []
    }
  },
  setup(props, { slots }) {
    return () => {
      if (!slots) return null;
      return hasAuth(props.value) || VITE_ENABLED_AUTH_COMPONENT === "false" ? (
        <Fragment>{slots.default?.()}</Fragment>
      ) : null;
    };
  }
});
